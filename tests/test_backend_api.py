"""
Automated Test Suite for RNASeqBackendAPI.

Verifies programmatic dataset discovery, contrast discovery, request validation,
API pipeline execution, provenance preservation, and numerical regression against
locked OSD-678 benchmark artifacts.
"""

import os
import unittest
import pandas as pd
import numpy as np

from pipeline.backend_api import RNASeqBackendAPI, AnalysisRequest, AnalysisResult

class TestRNASeqBackendAPI(unittest.TestCase):

    def setUp(self):
        self.api = RNASeqBackendAPI(configs_dir="configs")

    def test_dataset_discovery(self):
        """Test dataset discovery functionality."""
        datasets = self.api.list_available_datasets()
        self.assertGreaterEqual(len(datasets), 2)

        dataset_ids = [d.dataset_id for d in datasets]
        self.assertIn("OSD-678", dataset_ids)
        self.assertIn("OSD-120", dataset_ids)

        osd678_meta = next(d for d in datasets if d.dataset_id == "OSD-678")
        self.assertEqual(osd678_meta.organism, "Arabidopsis thaliana")
        self.assertEqual(len(osd678_meta.contrast_ids), 6)
        self.assertEqual(len(osd678_meta.interaction_contrast_ids), 2)

    def test_contrast_discovery(self):
        """Test contrast discovery for OSD-678."""
        contrasts = self.api.list_available_contrasts("OSD-678")
        self.assertEqual(len(contrasts), 6)

        c_ids = [c.id for c in contrasts]
        self.assertIn("A1_Col0_Light_Flight_vs_Ground", c_ids)
        self.assertIn("B1_Col0_Dark_Flight_vs_Ground", c_ids)

        a1 = next(c for c in contrasts if c.id == "A1_Col0_Light_Flight_vs_Ground")
        self.assertEqual(a1.numerator, "Flight_Col-0_Light")
        self.assertEqual(a1.denominator, "Ground_Col-0_Light")

    def test_invalid_dataset_rejection(self):
        """Test rejection of unknown dataset IDs."""
        with self.assertRaises(ValueError):
            self.api.list_available_contrasts("INVALID-999")

        req = AnalysisRequest(dataset_id="INVALID-999")
        with self.assertRaises(ValueError):
            self.api.validate_request(req)

    def test_invalid_contrast_rejection(self):
        """Test rejection of invalid contrast IDs for a valid dataset."""
        req = AnalysisRequest(dataset_id="OSD-678", contrast_id="NONEXISTENT_CONTRAST")
        with self.assertRaises(ValueError):
            self.api.validate_request(req)

    def test_malformed_request_rejection(self):
        """Test threshold validation and malformed request rejection."""
        with self.assertRaises(ValueError):
            AnalysisRequest(dataset_id="OSD-678", fdr_cutoff=1.5)

        with self.assertRaises(ValueError):
            AnalysisRequest(dataset_id="OSD-678", fdr_cutoff=-0.01)

        with self.assertRaises(ValueError):
            AnalysisRequest(dataset_id="OSD-678", lfc_cutoff=-1.0)

        with self.assertRaises(ValueError):
            AnalysisRequest(dataset_id="OSD-678", analysis_type="UNSUPPORTED_TYPE")

    def test_provenance_access(self):
        """Test read-only access to execution provenance manifest."""
        prov = self.api.get_provenance("OSD-678")
        self.assertIn("input_file_hashes", prov)
        self.assertIn("output_file_hashes", prov)
        self.assertIn("counts_matrix", prov["input_file_hashes"])

    def test_osd678_api_execution_and_regression(self):
        """Test full API execution and numerical regression verification."""
        req = AnalysisRequest(dataset_id="OSD-678")
        result = self.api.run_analysis(req)

        self.assertIsInstance(result, AnalysisResult)
        self.assertEqual(result.dataset_id, "OSD-678")
        self.assertEqual(result.execution_status, "SUCCESS")
        self.assertTrue(os.path.exists(result.candidate_comparison_csv_path))

        df_cand = pd.read_csv(result.candidate_comparison_csv_path)
        self.assertEqual(len(df_cand), 8)

        # Numerical regression checks for candidate genes
        anac = df_cand[df_cand["gene_id"] == "AT1G01010"].iloc[0]
        self.assertEqual(anac["symbol"], "ANAC001")
        self.assertTrue(np.isclose(anac["osd678_light_lfc"], 2.4599203758331307))
        self.assertTrue(np.isclose(anac["osd678_light_padj"], 9.187680573857266e-11))
        self.assertEqual(anac["direction_concordance"], "CONCORDANT")
        self.assertEqual(anac["evidence_classification"], "CROSS_TISSUE_REPLICATION_CONCORDANT")

        chs = df_cand[df_cand["gene_id"] == "AT5G13930"].iloc[0]
        self.assertEqual(chs["symbol"], "CHS")
        self.assertTrue(np.isclose(chs["osd678_light_lfc"], -5.193381866729729, atol=1e-4))
        self.assertEqual(chs["evidence_classification"], "CROSS_TISSUE_REPLICATION_CONCORDANT")

if __name__ == "__main__":
    unittest.main()
