"""
Unit tests for QuantificationRunner and Count Matrix Aggregation (Step 3).
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
import pandas as pd

from pipeline.quantification_runner import QuantificationRunner, QuantificationError


class TestQuantificationRunner(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.work_dir = Path(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def create_mock_quant_sf(self, sample_dir: Path, records: list):
        """Helper to create mock quant.sf tab-separated file."""
        sample_dir.mkdir(parents=True, exist_ok=True)
        sf_path = sample_dir / "quant.sf"
        df = pd.DataFrame(records)
        df.to_csv(sf_path, sep="\t", index=False)
        return sf_path

    def test_parse_quant_sf(self):
        """Test parsing valid quant.sf file."""
        records = [
            {"Name": "AT1G01010.1", "Length": 1000, "EffectiveLength": 900.0, "TPM": 50.0, "NumReads": 100.0},
            {"Name": "AT1G01010.2", "Length": 1200, "EffectiveLength": 1100.0, "TPM": 30.0, "NumReads": 60.0},
        ]
        s_dir = self.work_dir / "sample_1"
        sf_path = self.create_mock_quant_sf(s_dir, records)

        df_parsed = QuantificationRunner.parse_quant_sf(sf_path)
        self.assertEqual(len(df_parsed), 2)
        self.assertIn("NumReads", df_parsed.columns)

    def test_aggregate_salmon_quants_to_counts_default(self):
        """Test aggregating 2 samples into gene-level count matrix using default isoform splitting."""
        rec1 = [
            {"Name": "AT1G01010.1", "Length": 1000, "EffectiveLength": 900.0, "TPM": 50.0, "NumReads": 100.0},
            {"Name": "AT1G01010.2", "Length": 1200, "EffectiveLength": 1100.0, "TPM": 30.0, "NumReads": 50.0},
            {"Name": "AT1G02020.1", "Length": 800, "EffectiveLength": 700.0, "TPM": 10.0, "NumReads": 25.0},
        ]
        rec2 = [
            {"Name": "AT1G01010.1", "Length": 1000, "EffectiveLength": 900.0, "TPM": 10.0, "NumReads": 20.0},
            {"Name": "AT1G01010.2", "Length": 1200, "EffectiveLength": 1100.0, "TPM": 15.0, "NumReads": 30.0},
            {"Name": "AT1G02020.1", "Length": 800, "EffectiveLength": 700.0, "TPM": 40.0, "NumReads": 80.0},
        ]

        s1_dir = self.work_dir / "S1"
        s2_dir = self.work_dir / "S2"

        self.create_mock_quant_sf(s1_dir, rec1)
        self.create_mock_quant_sf(s2_dir, rec2)

        quant_map = {"S1": s1_dir, "S2": s2_dir}
        df_counts = QuantificationRunner.aggregate_salmon_quants_to_counts(quant_map)

        self.assertEqual(list(df_counts.columns), ["S1", "S2"])

        # Gene AT1G01010 sum: S1 = 100+50=150, S2 = 20+30=50
        self.assertEqual(df_counts.loc["AT1G01010", "S1"], 150)
        self.assertEqual(df_counts.loc["AT1G01010", "S2"], 50)

        # Gene AT1G02020 sum: S1 = 25, S2 = 80
        self.assertEqual(df_counts.loc["AT1G02020", "S1"], 25)
        self.assertEqual(df_counts.loc["AT1G02020", "S2"], 80)

    def test_generate_counts_matrix_file(self):
        """Test generating counts_matrix.csv file on disk."""
        rec1 = [{"Name": "GENE_A.1", "Length": 500, "EffectiveLength": 400.0, "TPM": 1.0, "NumReads": 42.0}]
        s1_dir = self.work_dir / "S1"
        self.create_mock_quant_sf(s1_dir, rec1)

        out_csv = self.work_dir / "counts_matrix.csv"
        QuantificationRunner.generate_counts_matrix_file({"S1": s1_dir}, out_csv)

        self.assertTrue(out_csv.exists())
        df_out = pd.read_csv(out_csv)
        self.assertIn("gene_id", df_out.columns)
        self.assertIn("S1", df_out.columns)
        self.assertEqual(df_out.iloc[0]["gene_id"], "GENE_A")
        self.assertEqual(df_out.iloc[0]["S1"], 42)


if __name__ == "__main__":
    unittest.main()
