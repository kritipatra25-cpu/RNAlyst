"""
Unit tests for Scientific Prerequisite Engine & Biological Replication Guardrails.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import pandas as pd

from agent.tools.prerequisite_engine import (
    PrerequisiteEngine,
    MissingPrerequisitesError,
    InsufficientReplicatesError
)
from scientific_guardrails.replicate_rules import validate_biological_replicates
from pipeline.schemas.input_schemas import SampleSheetInput


class TestScientificPrerequisiteEngine(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.engine = PrerequisiteEngine(projects_dir=self.test_dir)
        self.project_id = "TEST_PROJ"
        self.proj_dir = Path(self.test_dir) / self.project_id
        (self.proj_dir / "data" / "uploads").mkdir(parents=True, exist_ok=True)
        (self.proj_dir / "results").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_1_qc_prerequisites_missing(self):
        valid, err = self.engine.validate_qc_prerequisites(self.project_id)
        self.assertFalse(valid)
        self.assertIsNotNone(err)
        self.assertEqual(err["error_type"], "MissingPrerequisitesError")
        self.assertIn("fastq_files", err["missing_prerequisites"])

    def test_2_qc_prerequisites_success(self):
        fastq_file = self.proj_dir / "data" / "uploads" / "sample1_R1.fastq.gz"
        fastq_file.write_text("@HEADER\nATCG\n+\nIIII\n")
        valid, err = self.engine.validate_qc_prerequisites(self.project_id)
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_3_quantification_bypassed_if_direct_counts(self):
        valid, err = self.engine.validate_quantification_prerequisites(
            project_id=self.project_id,
            has_salmon_binary=False,
            has_direct_counts=True
        )
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_4_pca_prerequisites_insufficient_samples(self):
        counts_csv = self.proj_dir / "data" / "counts_matrix.csv"
        df = pd.DataFrame({"gene_id": ["G1", "G2"], "S1": [10, 20]})
        df.to_csv(counts_csv, index=False)

        valid, err = self.engine.validate_pca_prerequisites(self.project_id, counts_matrix_path=counts_csv)
        self.assertFalse(valid)
        self.assertEqual(err["error_type"], "MissingPrerequisitesError")
        self.assertIn("multiple_biological_samples", err["missing_prerequisites"])

    def test_5_pca_prerequisites_valid(self):
        counts_csv = self.proj_dir / "data" / "counts_matrix.csv"
        df = pd.DataFrame({"gene_id": ["G1", "G2"], "S1": [10, 20], "S2": [15, 25]})
        df.to_csv(counts_csv, index=False)

        valid, err = self.engine.validate_pca_prerequisites(self.project_id, counts_matrix_path=counts_csv)
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_6_de_prerequisites_single_replicate_rejected(self):
        counts_csv = self.proj_dir / "data" / "counts_matrix.csv"
        df_counts = pd.DataFrame({"gene_id": ["G1", "G2"], "S1": [10, 20], "S2": [100, 200]})
        df_counts.to_csv(counts_csv, index=False)

        meta_csv = self.proj_dir / "data" / "sample_metadata.csv"
        df_meta = pd.DataFrame({"sample_id": ["S1", "S2"], "condition": ["Control", "Treatment"]})
        df_meta.to_csv(meta_csv, index=False)

        valid, err = self.engine.validate_de_prerequisites(
            project_id=self.project_id,
            counts_matrix_path=counts_csv,
            sample_metadata_path=meta_csv
        )
        self.assertFalse(valid)
        self.assertEqual(err["error_type"], "InsufficientReplicatesError")
        self.assertIn("biological_replicates_ge_2", err["missing_prerequisites"])

    def test_7_de_prerequisites_valid_replication(self):
        counts_csv = self.proj_dir / "data" / "counts_matrix.csv"
        df_counts = pd.DataFrame({"gene_id": ["G1", "G2"], "S1": [10, 20], "S2": [12, 22], "S3": [100, 200], "S4": [110, 210]})
        df_counts.to_csv(counts_csv, index=False)

        meta_csv = self.proj_dir / "data" / "sample_metadata.csv"
        df_meta = pd.DataFrame({"sample_id": ["S1", "S2", "S3", "S4"], "condition": ["Control", "Control", "Treatment", "Treatment"]})
        df_meta.to_csv(meta_csv, index=False)

        valid, err = self.engine.validate_de_prerequisites(
            project_id=self.project_id,
            counts_matrix_path=counts_csv,
            sample_metadata_path=meta_csv
        )
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_8_replicate_rules_guardrail_rejection(self):
        from pipeline.schemas.input_schemas import SampleMetadata, SampleSheetInput, LayoutType
        samples = [
            SampleMetadata(sample_id="S1", biological_unit_id="U1", condition="Control", is_technical_replicate=False),
            SampleMetadata(sample_id="S2", biological_unit_id="U2", condition="Treatment", is_technical_replicate=False)
        ]
        sheet = SampleSheetInput(
            organism="Arabidopsis thaliana",
            layout=LayoutType.SINGLE,
            samples=samples,
            fastq_files={},
            reference_group="Control",
            comparison_group="Treatment"
        )
        status, warnings = validate_biological_replicates(sheet)
        self.assertEqual(status, "EXPLORATORY")
        self.assertTrue(any("N < 2" in w or "WARNING" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
