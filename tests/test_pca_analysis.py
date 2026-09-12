import os
import sys
import io
import unittest
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.statistics.pca_engine import perform_pca, load_expression_matrix
from visualization.plots_engine import generate_pca_plot
from pipeline.orchestrator import AnalysisOrchestrator
from pipeline.job_models import JobStatus, StepStatus, ArtifactType


class TestPCAAnalysisEngine(unittest.TestCase):

    def setUp(self):
        self.orchestrator = AnalysisOrchestrator()
        self.test_dir = PROJECT_ROOT / "data" / "uploads"
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Create a valid synthetic expression matrix CSV
        # 10 genes (rows) x 4 samples (columns)
        np.random.seed(42)
        counts = np.random.randint(10, 1000, size=(10, 4))
        df = pd.DataFrame(
            counts,
            columns=["Sample_1", "Sample_2", "Sample_3", "Sample_4"]
        )
        df.insert(0, "gene_id", [f"GENE_{i+1:02d}" for i in range(10)])

        self.matrix_file_id = "test_matrix_uuid_12345"
        self.matrix_path = self.test_dir / f"{self.matrix_file_id}_counts.csv"
        df.to_csv(self.matrix_path, index=False)

        # Metadata
        self.sample_metadata = {
            "Sample_1": "Control",
            "Sample_2": "Control",
            "Sample_3": "Treated",
            "Sample_4": "Treated"
        }

    def test_1_perform_pca_calculation_and_structure(self):
        """Test perform_pca produces exact expected schema and values."""
        res = perform_pca(self.matrix_path, sample_metadata=self.sample_metadata)

        self.assertIn("samples", res)
        self.assertIn("coordinates", res)
        self.assertIn("explained_variance_ratio", res)
        self.assertIn("explained_variance_percentage", res)
        self.assertIn("total_explained_variance", res)
        self.assertEqual(res["n_samples"], 4)
        self.assertEqual(res["n_genes"], 10)

        self.assertEqual(len(res["coordinates"]), 4)
        first_coord = res["coordinates"][0]
        self.assertEqual(first_coord["sample_id"], "Sample_1")
        self.assertEqual(first_coord["group"], "Control")
        self.assertIn("PC1", first_coord)
        self.assertIn("PC2", first_coord)

    def test_2_generate_pca_plot(self):
        """Test generate_pca_plot creates a valid PNG file on disk."""
        pca_res = perform_pca(self.matrix_path, sample_metadata=self.sample_metadata)
        output_png = self.test_dir / "test_pca_output.png"

        result_path = generate_pca_plot(pca_res, output_png)
        self.assertTrue(result_path.exists())
        self.assertGreater(result_path.stat().st_size, 1000)  # Non-empty image

    def test_3_orchestrator_pca_step_execution_and_artifacts(self):
        """Test orchestrator running PCA step on valid expression matrix."""
        job = self.orchestrator.create_job(
            file_id=self.matrix_file_id,
            plan=["pca"]
        )
        updated_job = self.orchestrator.execute_job(job.analysis_id)

        self.assertEqual(updated_job.status, JobStatus.COMPLETED)
        self.assertEqual(len(updated_job.steps), 1)
        self.assertEqual(updated_job.steps[0].status, StepStatus.COMPLETED)

        # Verify registered artifacts (JSON + Plot)
        self.assertEqual(len(updated_job.artifacts), 2)
        artifact_types = [a.type for a in updated_job.artifacts]
        self.assertIn(ArtifactType.JSON_DATA, artifact_types)
        self.assertIn(ArtifactType.PLOT, artifact_types)

        for art in updated_job.artifacts:
            self.assertTrue(os.path.exists(art.path))

    def test_4_missing_expression_matrix_clean_failure(self):
        """Test running PCA step on missing expression matrix produces clean failure."""
        fastq_file_id = "missing_matrix_fastq_uuid_99999"

        job = self.orchestrator.create_job(
            file_id=fastq_file_id,
            plan=["pca"]
        )
        updated_job = self.orchestrator.execute_job(job.analysis_id)

        self.assertEqual(updated_job.status, JobStatus.FAILED)
        self.assertEqual(updated_job.steps[0].status, StepStatus.FAILED)
        self.assertIn(
            "PCA requires a gene-by-sample expression/count matrix",
            updated_job.steps[0].message
        )


if __name__ == "__main__":
    unittest.main()
