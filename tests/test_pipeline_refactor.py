"""
Automated Test Suite for Refactored Bulk RNA-seq Pipeline.

Verifies configuration parsing, metadata validation, candidate prioritization,
and performs exact numerical regression testing against locked OSD-678 benchmark artifacts.
"""

import os
import unittest
import pandas as pd
import numpy as np

from pipeline.config_parser import load_dataset_config
from pipeline.input_validation import MetadataValidator
from analysis.interpretation.candidate_prioritizer import CandidatePrioritizer

class TestPipelineRefactor(unittest.TestCase):

    def test_config_parser(self):
        """Test loading and validation of dataset YAML configuration."""
        config_path = "configs/osd678.yaml"
        config = load_dataset_config(config_path)

        self.assertEqual(config.dataset_id, "OSD-678")
        self.assertEqual(config.organism, "Arabidopsis thaliana")
        self.assertEqual(len(config.contrasts), 6)
        self.assertEqual(len(config.interaction_contrasts), 2)
        self.assertEqual(config.candidate_selection.mode, "SPECIFIED_LIST")
        self.assertEqual(len(config.candidate_selection.specified_genes), 8)

    def test_input_validation(self):
        """Test sample metadata sheet validation and replicate auditor."""
        metadata = pd.DataFrame({
            "sample_id": ["S1", "S2", "S3", "S4", "S5", "S6"],
            "genotype": ["Col-0", "Col-0", "Col-0", "phyD", "phyD", "phyD"],
            "spaceflight": ["Flight", "Flight", "Flight", "Flight", "Flight", "Flight"],
            "replicate": ["rep1", "rep2", "rep3", "rep1", "rep2", "rep3"],
            "group": ["Flight_Col-0", "Flight_Col-0", "Flight_Col-0", "Flight_phyD", "Flight_phyD", "Flight_phyD"]
        })

        is_valid, errs = MetadataValidator.validate_sample_sheet(metadata)
        self.assertTrue(is_valid)
        self.assertEqual(len(errs), 0)

        rep_audit = MetadataValidator.audit_replicates(metadata.set_index("sample_id"), "group")
        self.assertEqual(rep_audit["min_replicates"], 3)
        self.assertEqual(rep_audit["status"], "VALID")

    def test_candidate_prioritizer(self):
        """Test candidate gene prioritization and evidence classification logic."""
        prioritizer = CandidatePrioritizer()

        primary_df = pd.DataFrame({
            "gene_id": ["AT1G01010", "AT5G13930"],
            "log2FoldChange": [2.46, -5.19],
            "lfcSE": [0.35, 1.47],
            "pvalue": [1e-10, 4e-4],
            "padj": [1e-9, 2e-3]
        })

        ref_df = pd.DataFrame({
            "gene_id": ["AT1G01010", "AT5G13930"],
            "log2FoldChange": [1.14, -10.68],
            "padj": [0.53, 0.53]
        })

        records = prioritizer.evaluate_candidates(
            candidate_genes=["AT1G01010", "AT5G13930"],
            primary_contrast_df=primary_df,
            reference_de_df=ref_df
        )

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["symbol"], "ANAC001")
        self.assertEqual(records[0]["direction_concordance"], "CONCORDANT")
        self.assertEqual(records[0]["evidence_classification"], "CROSS_TISSUE_REPLICATION_CONCORDANT")
        self.assertEqual(records[1]["symbol"], "CHS")

    def test_osd678_benchmark_regression(self):
        """Verify exact numerical regression against locked OSD-678 benchmark output."""
        benchmark_csv = "results/osd678_validation/candidate_validation/osd678_candidate_comparison.csv"
        self.assertTrue(os.path.exists(benchmark_csv), f"Benchmark CSV missing: {benchmark_csv}")

        df = pd.read_csv(benchmark_csv)
        self.assertEqual(len(df), 8, "Expected exactly 8 candidate genes")

        # Check key candidates
        anac = df[df["gene_id"] == "AT1G01010"].iloc[0]
        self.assertEqual(anac["symbol"], "ANAC001")
        self.assertTrue(np.isclose(anac["osd678_light_lfc"], 2.4599203758331307))
        self.assertTrue(np.isclose(anac["osd678_light_padj"], 9.187680573857266e-11))
        self.assertEqual(anac["direction_concordance"], "CONCORDANT")
        self.assertTrue(anac["passes_osd678_fdr_005"])
        self.assertEqual(anac["evidence_classification"], "CROSS_TISSUE_REPLICATION_CONCORDANT")

        lux = df[df["gene_id"] == "AT3G46640"].iloc[0]
        self.assertEqual(lux["symbol"], "LUX")
        self.assertTrue(np.isclose(lux["osd678_light_lfc"], 0.7322455070673851))
        self.assertTrue(np.isclose(lux["osd678_light_padj"], 0.04064497642732208))
        self.assertEqual(lux["evidence_classification"], "CROSS_TISSUE_REPLICATION_CONCORDANT")

        rboha = df[df["gene_id"] == "AT5G07390"].iloc[0]
        self.assertEqual(rboha["symbol"], "RBOHA")
        self.assertTrue(np.isclose(rboha["osd678_light_lfc"], 5.448672672599422))
        self.assertEqual(rboha["evidence_classification"], "CROSS_TISSUE_REPLICATION_CONCORDANT")

        chs = df[df["gene_id"] == "AT5G13930"].iloc[0]
        self.assertEqual(chs["symbol"], "CHS")
        self.assertTrue(np.isclose(chs["osd678_light_lfc"], -5.193381866729729))
        self.assertEqual(chs["evidence_classification"], "CROSS_TISSUE_REPLICATION_CONCORDANT")

if __name__ == "__main__":
    unittest.main()
