import os
import sys
import unittest
import numpy as np
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from visualization.plots_engine import (
    generate_pca_plot, generate_volcano_plot, generate_heatmap_plot, generate_qc_plot
)
from pipeline.orchestrator import AnalysisOrchestrator
from pipeline.job_models import JobStatus, ArtifactType


class TestVisualizationEngine(unittest.TestCase):

    def setUp(self):
        self.orchestrator = AnalysisOrchestrator()
        self.output_dir = PROJECT_ROOT / "data" / "artifacts"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir = PROJECT_ROOT / "data" / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def test_1_generate_pca_plot(self):
        """Test PCA plot generator creates non-empty PNG file."""
        pca_result = {
            "n_samples": 4,
            "n_genes": 10,
            "explained_variance_percentage": {"PC1": 75.5, "PC2": 15.2},
            "total_explained_variance": 90.7,
            "coordinates": [
                {"sample_id": "C1", "PC1": -10.5, "PC2": 2.1, "group": "Control"},
                {"sample_id": "C2", "PC1": -9.8, "PC2": -1.5, "group": "Control"},
                {"sample_id": "T1", "PC1": 11.2, "PC2": 3.0, "group": "Treated"},
                {"sample_id": "T2", "PC1": 9.1, "PC2": -3.6, "group": "Treated"}
            ]
        }
        out_path = self.output_dir / "test_pca_output.png"
        res_path = generate_pca_plot(pca_result, out_path)

        self.assertTrue(res_path.exists())
        self.assertGreater(res_path.stat().st_size, 0)

    def test_2_generate_volcano_plot(self):
        """Test Volcano plot generator creates non-empty PNG file."""
        de_df = pd.DataFrame({
            "gene_id": [f"G_{i}" for i in range(10)],
            "log2FoldChange": [-2.5, -1.2, 0.1, 0.5, 2.8, 3.1, -0.2, 0.4, -3.0, 1.9],
            "padj": [0.001, 0.04, 0.8, 0.9, 0.0001, 0.005, 0.6, 0.7, 0.02, 0.03],
            "significant": [True, True, False, False, True, True, False, False, True, True]
        })
        out_path = self.output_dir / "test_volcano_output.png"
        res_path = generate_volcano_plot(de_df, out_path)

        self.assertTrue(res_path.exists())
        self.assertGreater(res_path.stat().st_size, 0)

    def test_3_generate_heatmap_plot(self):
        """Test Heatmap plot generator creates non-empty PNG file for significant genes."""
        samples = ["C1", "C2", "T1", "T2"]
        df_counts = pd.DataFrame({
            "C1": [10, 15, 100, 200],
            "C2": [12, 14, 110, 210],
            "T1": [80, 95, 20, 30],
            "T2": [85, 90, 25, 35]
        }, index=["G_0", "G_1", "G_2", "G_3"])

        df_de = pd.DataFrame({
            "gene_id": ["G_0", "G_1", "G_2", "G_3"],
            "log2FoldChange": [3.0, 2.8, -2.5, -2.6],
            "padj": [0.001, 0.002, 0.003, 0.004]
        })

        out_path = self.output_dir / "test_heatmap_output.png"
        res_path = generate_heatmap_plot(df_counts, df_de, output_path=out_path)

        self.assertIsNotNone(res_path)
        self.assertTrue(res_path.exists())
        self.assertGreater(res_path.stat().st_size, 0)

    def test_4_heatmap_graceful_skip_for_zero_significant_genes(self):
        """Test Heatmap generator returns None when 0 significant genes exist."""
        df_counts = pd.DataFrame({"C1": [10], "T1": [10]}, index=["G_0"])
        df_nonsig_de = pd.DataFrame({
            "gene_id": ["G_0"],
            "log2FoldChange": [0.1],
            "padj": [0.9]
        })

        out_path = self.output_dir / "test_nonsig_heatmap.png"
        if out_path.exists():
            out_path.unlink()
        res_path = generate_heatmap_plot(df_counts, df_nonsig_de, output_path=out_path)

        self.assertIsNone(res_path)
        self.assertFalse(out_path.exists())

    def test_5_generate_qc_plot(self):
        """Test multi-panel QC plot generator creates non-empty PNG file."""
        qc_results = {
            "total_reads": 1000,
            "gc_content_percent": 48.5,
            "mean_phred_quality": 38.2,
            "mean_read_length": 150.0
        }
        out_path = self.output_dir / "test_qc_output.png"
        res_path = generate_qc_plot(qc_results, out_path)

        self.assertTrue(res_path.exists())
        self.assertGreater(res_path.stat().st_size, 0)

    def test_6_orchestrator_plot_artifact_provenance(self):
        """Test orchestrator execution registers plot artifacts with parent_artifact_id metadata."""
        vis_file_id = "test_vis_prov_fixture"
        counts_path = self.uploads_dir / f"{vis_file_id}_counts.csv"
        meta_path = self.uploads_dir / f"{vis_file_id}_metadata.csv"

        df_counts = pd.DataFrame({
            "gene_id": ["G1", "G2", "G3", "G4"],
            "C1": [10, 15, 500, 600],
            "C2": [12, 14, 520, 610],
            "T1": [100, 150, 50, 60],
            "T2": [110, 140, 55, 65]
        })
        df_counts.to_csv(counts_path, index=False)

        df_meta = pd.DataFrame({
            "sample": ["C1", "C2", "T1", "T2"],
            "condition": ["Control", "Control", "Treated", "Treated"]
        })
        df_meta.to_csv(meta_path, index=False)

        job = self.orchestrator.create_job(
            file_id=vis_file_id,
            plan=["pca", "differential_expression"]
        )
        updated_job = self.orchestrator.execute_job(job.analysis_id)

        self.assertEqual(updated_job.status, JobStatus.COMPLETED)
        plot_artifacts = [a for a in updated_job.artifacts if a.type == ArtifactType.PLOT]
        self.assertGreaterEqual(len(plot_artifacts), 2)  # PCA, Volcano, Heatmap

        for plot_art in plot_artifacts:
            self.assertIn("parent_artifact_id", plot_art.metadata)
            self.assertIn("source_file", plot_art.metadata)
            self.assertTrue(os.path.exists(plot_art.path))


if __name__ == "__main__":
    unittest.main()
