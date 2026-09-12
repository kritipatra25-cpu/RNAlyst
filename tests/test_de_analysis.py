import os
import sys
import io
import unittest
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.statistics.de_engine import perform_differential_expression, load_sample_metadata, load_count_matrix
from pipeline.orchestrator import AnalysisOrchestrator
from pipeline.job_models import JobStatus, StepStatus, ArtifactType


class TestDEAnalysisEngine(unittest.TestCase):

    def setUp(self):
        self.orchestrator = AnalysisOrchestrator()
        self.test_dir = PROJECT_ROOT / "data" / "uploads"
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Create valid synthetic count matrix: 20 genes x 6 samples (3 Control, 3 Treated)
        np.random.seed(42)
        ctrl_counts = np.random.randint(50, 200, size=(20, 3))
        # Make top 5 genes significantly upregulated in treated group
        treat_counts = np.random.randint(50, 200, size=(20, 3))
        treat_counts[:5, :] += 500

        counts = np.hstack([ctrl_counts, treat_counts])
        sample_cols = ["S1_ctrl", "S2_ctrl", "S3_ctrl", "S4_treat", "S5_treat", "S6_treat"]
        df_counts = pd.DataFrame(counts, columns=sample_cols)
        df_counts.insert(0, "gene_id", [f"GENE_{i+1:02d}" for i in range(20)])

        self.de_file_id = "test_de_fixture_98765"
        self.matrix_path = self.test_dir / f"{self.de_file_id}_counts.csv"
        df_counts.to_csv(self.matrix_path, index=False)

        # Create valid metadata CSV
        df_meta = pd.DataFrame({
            "sample": sample_cols,
            "condition": ["Control", "Control", "Control", "Treated", "Treated", "Treated"]
        })
        self.metadata_path = self.test_dir / f"{self.de_file_id}_metadata.csv"
        df_meta.to_csv(self.metadata_path, index=False)

    def test_1_perform_differential_expression_schema_and_values(self):
        """Test perform_differential_expression produces expected schema and summary."""
        res = perform_differential_expression(
            self.matrix_path,
            self.metadata_path,
            reference_level="Control"
        )

        self.assertIn("summary", res)
        self.assertIn("contrast", res)
        self.assertIn("results", res)
        self.assertIn("dataframe", res)

        summary = res["summary"]
        self.assertEqual(summary["total_genes"], 20)
        self.assertGreaterEqual(summary["significant_genes"], 1)
        self.assertEqual(summary["contrast"], ["condition", "Treated", "Control"])

        # Check gene results schema
        first_gene = res["results"][0]
        self.assertIn("gene_id", first_gene)
        self.assertIn("baseMean", first_gene)
        self.assertIn("log2FoldChange", first_gene)
        self.assertIn("stat", first_gene)
        self.assertIn("pvalue", first_gene)
        self.assertIn("padj", first_gene)
        self.assertIn("significant", first_gene)

    def test_2_group_and_replicate_validation(self):
        """Test metadata group and replicate count validations."""
        # 1. Single condition metadata
        df_invalid1 = pd.DataFrame({
            "sample": ["S1", "S2", "S3"],
            "condition": ["Control", "Control", "Control"]
        })
        inv1_path = self.test_dir / "invalid1_meta.csv"
        df_invalid1.to_csv(inv1_path, index=False)

        with self.assertRaises(ValueError) as ctx1:
            load_sample_metadata(inv1_path)
        self.assertIn("at least 2 distinct experimental groups", str(ctx1.exception))

        # 2. Insufficient replicates (< 2 per group)
        df_invalid2 = pd.DataFrame({
            "sample": ["S1", "S2"],
            "condition": ["Control", "Treated"]
        })
        inv2_path = self.test_dir / "invalid2_meta.csv"
        df_invalid2.to_csv(inv2_path, index=False)

        with self.assertRaises(ValueError) as ctx2:
            load_sample_metadata(inv2_path)
        self.assertIn("at least 2 replicates per condition", str(ctx2.exception))

    def test_3_orchestrator_de_step_execution(self):
        """Test orchestrator running DE step on valid matrix + metadata."""
        job = self.orchestrator.create_job(
            file_id=self.de_file_id,
            plan=["differential_expression"]
        )
        updated_job = self.orchestrator.execute_job(job.analysis_id)

        self.assertEqual(updated_job.status, JobStatus.COMPLETED)
        self.assertEqual(len(updated_job.steps), 1)
        self.assertEqual(updated_job.steps[0].status, StepStatus.COMPLETED)

        # Verify registered artifacts (JSON summary + DE_TABLE CSV)
        self.assertGreaterEqual(len(updated_job.artifacts), 2)
        artifact_types = [a.type for a in updated_job.artifacts]
        self.assertIn(ArtifactType.JSON_DATA, artifact_types)
        self.assertIn(ArtifactType.DE_TABLE, artifact_types)

        for art in updated_job.artifacts:
            self.assertTrue(os.path.exists(art.path))

    def test_4_missing_metadata_or_matrix_clean_failure(self):
        """Test running DE step when metadata is missing results in clean failure."""
        missing_meta_file_id = "missing_meta_de_uuid_11111"
        # Write matrix only, no metadata
        df_m = pd.DataFrame({"gene_id": ["G1"], "S1": [10], "S2": [20]})
        df_m.to_csv(self.test_dir / f"{missing_meta_file_id}_counts.csv", index=False)

        job = self.orchestrator.create_job(
            file_id=missing_meta_file_id,
            plan=["differential_expression"]
        )
        updated_job = self.orchestrator.execute_job(job.analysis_id)

        self.assertEqual(updated_job.status, JobStatus.FAILED)
        self.assertEqual(updated_job.steps[0].status, StepStatus.FAILED)
        self.assertIn(
            "Differential expression requires a gene-by-sample count matrix and sample metadata",
            updated_job.steps[0].message
        )


if __name__ == "__main__":
    unittest.main()
