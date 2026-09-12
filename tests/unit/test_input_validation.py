"""
Unit tests for pipeline/input_validation.py
"""

import unittest
import tempfile
import gzip
from pathlib import Path
import pandas as pd
from pipeline.input_validation import FASTQValidator, MetadataValidator, ContrastGenerator

class TestInputValidation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fastq_validator_valid_file(self):
        fq_path = self.dir_path / "test.fastq.gz"
        with gzip.open(fq_path, "wt", encoding="utf-8") as f:
            f.write("@READ1\nACGTACGT\n+\nIIIIIIII\n")
            f.write("@READ2\nTGCA\n+\nIIII\n")

        valid, err = FASTQValidator.validate_fastq_file(fq_path)
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_fastq_validator_corrupted_header(self):
        fq_path = self.dir_path / "bad.fastq"
        with open(fq_path, "w", encoding="utf-8") as f:
            f.write("INVALID_HEADER\nACGTACGT\n+\nIIIIIIII\n")

        valid, err = FASTQValidator.validate_fastq_file(fq_path)
        self.assertFalse(valid)
        self.assertIn("must start with '@'", err)

    def test_metadata_audit_replicates(self):
        df = pd.DataFrame({
            "sample_id": ["S1", "S2", "S3", "S4", "S5", "S6"],
            "condition": ["Flight", "Flight", "Flight", "Ground", "Ground", "Ground"]
        })
        res = MetadataValidator.audit_replicates(df, "condition")
        self.assertTrue(res["is_valid_inferential"])
        self.assertEqual(res["status"], "VALID")

    def test_metadata_audit_replicates_warning_n1(self):
        df = pd.DataFrame({
            "sample_id": ["S1", "S2"],
            "condition": ["Flight", "Ground"]
        })
        res = MetadataValidator.audit_replicates(df, "condition")
        self.assertFalse(res["is_valid_inferential"])
        self.assertEqual(res["status"], "EXPLORATORY")

    def test_validate_design_matrix(self):
        df = pd.DataFrame({
            "sample_id": ["S1", "S2", "S3"],
            "Spaceflight": ["Space Flight", "Space Flight", "Ground Control"]
        })
        valid, errs = MetadataValidator.validate_design_matrix(df, "~ Spaceflight", ["Spaceflight", "Space Flight", "Ground Control"])
        self.assertTrue(valid)
        self.assertEqual(len(errs), 0)

    def test_generate_candidate_contrasts_osd120(self):
        df = pd.DataFrame()
        candidates = ContrastGenerator.generate_candidate_contrasts_for_study("OSD-120", df)
        self.assertGreater(len(candidates), 0)
        self.assertEqual(candidates[0]["contrast_id"], "Candidate-120-A")
        self.assertIn("PRIMARY DEVELOPMENT", candidates[0]["status"])

if __name__ == "__main__":
    unittest.main()
