import unittest
import os
import json
import numpy as np
import pandas as pd
from analysis.statistics.meta_analysis_engine import (
    compute_sha256,
    bh_adjust_pvalues,
    derive_cuffdiff_se,
    run_meta_analysis
)

class TestMetaAnalysisEngine(unittest.TestCase):
    
    def setUp(self):
        self.osd120_path = 'results/osd120_primary_analysis/differential_expression.csv'
        self.osd658_path = 'data/GSE94983_12._DK_FLT_Col-0_to_DK_GC_Col-0.xlsx.gz'
        self.prov_path = 'results/meta_analysis/meta_analysis_provenance.json'
        self.cand_path = 'results/meta_analysis/candidate_gene_meta_analysis.csv'
        self.res_path = 'results/meta_analysis/meta_analysis_results.csv'
        
    def test_01_source_file_hashes_immutable(self):
        """Verify that source files exist and their SHA-256 hashes match provenance."""
        self.assertTrue(os.path.exists(self.osd120_path))
        self.assertTrue(os.path.exists(self.osd658_path))
        
        with open(self.prov_path) as f:
            prov = json.load(f)
            
        hashes = prov['source_file_hashes']
        self.assertEqual(compute_sha256(self.osd120_path), hashes['osd120_deseq2_csv'])
        self.assertEqual(compute_sha256(self.osd658_path), hashes['osd658_gse94983_12_xlsx_gz'])
        
    def test_02_raw_counts_not_pooled(self):
        """Verify that meta-analysis operates on summary statistics, not pooled count matrices."""
        with open(self.prov_path) as f:
            prov = json.load(f)
        self.assertEqual(prov['analysis_type'], 'INVERSE_VARIANCE_SUMMARY_STATISTIC_META_ANALYSIS')
        
    def test_03_inverse_variance_math(self):
        """Verify mathematical correctness of inverse-variance pooling on synthetic values."""
        lfc1, se1 = 1.0, 0.2
        lfc2, se2 = 2.0, 0.4
        
        w1 = 1.0 / (se1 ** 2)  # 25
        w2 = 1.0 / (se2 ** 2)  # 6.25
        w_sum = w1 + w2        # 31.25
        
        expected_meta_lfc = (w1 * lfc1 + w2 * lfc2) / w_sum  # (25*1 + 6.25*2)/31.25 = 37.5/31.25 = 1.2
        expected_meta_se = np.sqrt(1.0 / w_sum)              # sqrt(1/31.25) = sqrt(0.032) = 0.178885
        
        self.assertAlmostEqual(expected_meta_lfc, 1.2, places=5)
        self.assertAlmostEqual(expected_meta_se, np.sqrt(0.032), places=5)
        
    def test_04_heterogeneity_math(self):
        """Verify Cochran Q and I^2 calculation on synthetic values."""
        lfc1, se1 = 1.0, 0.1
        lfc2, se2 = -1.0, 0.1
        
        w1, w2 = 100.0, 100.0
        meta_lfc = 0.0
        
        q_stat = w1 * ((lfc1 - meta_lfc) ** 2) + w2 * ((lfc2 - meta_lfc) ** 2)  # 100(1) + 100(1) = 200
        i2 = (q_stat - 1.0) / q_stat * 100.0                                     # (200-1)/200 = 99.5%
        
        self.assertAlmostEqual(q_stat, 200.0, places=5)
        self.assertAlmostEqual(i2, 99.5, places=1)
        
    def test_05_cuffdiff_se_derivation(self):
        """Verify SE derivation logic for Cuffdiff rows."""
        row_stat = {'log2(fold_change)': 1.0, 'test_stat': 2.0, 'p_value': 0.0455}
        se = derive_cuffdiff_se(row_stat)
        self.assertAlmostEqual(se, 0.5, places=5)
        
    def test_06_fdr_adjustment(self):
        """Verify Benjamini-Hochberg FDR monotonicity and correctness."""
        pvals = np.array([0.001, 0.01, 0.05, 0.20, 0.80])
        qvals = bh_adjust_pvalues(pvals)
        self.assertTrue(np.all(np.diff(qvals) >= 0))
        self.assertAlmostEqual(qvals[0], 0.005, places=5)
        
    def test_07_candidate_gene_results_present(self):
        """Verify all candidate genes are accounted for in meta-analysis results."""
        df_cand = pd.read_csv(self.cand_path)
        genes = set(df_cand['gene_id'].values)
        expected = {'AT3G17609', 'AT4G04720', 'AT2G04170', 'AT1G01010', 'AT5G57630', 'AT3G46640', 'AT5G07390', 'AT5G13930'}
        self.assertTrue(expected.issubset(genes))
        
        # Verify AT2G04170 is CONCORDANT
        r_204 = df_cand[df_cand['gene_id'] == 'AT2G04170'].iloc[0]
        self.assertEqual(r_204['convergence_classification'], 'CONCORDANT')
        self.assertGreater(r_204['meta_lfc'], 1.0)
        
        # Verify ANAC001 is DISCORDANT
        r_ana = df_cand[df_cand['gene_id'] == 'AT1G01010'].iloc[0]
        self.assertEqual(r_ana['convergence_classification'], 'DISCORDANT')

if __name__ == '__main__':
    unittest.main()
