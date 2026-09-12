"""
Unit & Integration Test Suite for Dynamic Visualization Behavior & Figure Provenance.
"""

import os
import tempfile
import unittest
from pathlib import Path
import pandas as pd

from agent.tools.visualization_tools import (
    VolcanoPlotTool,
    PCAPlotTool,
    HeatmapTool,
    QCPlotTool,
    _resolve_project_artifact
)
from agent.tools.registry import ToolRegistry
from agent.orchestrator.agent_runner import AgentOrchestrator, AgentResponse


class TestDynamicVisualizations(unittest.TestCase):
    """Test suite covering dynamic visualization tool execution, prerequisite checks, and provenance."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

        # Create dummy VST counts CSV
        self.vst_path = self.tmp_path / "vst_counts.csv"
        vst_df = pd.DataFrame({
            "sample1": [10.2, 8.5, 5.1, 12.0, 9.1],
            "sample2": [10.1, 8.7, 5.0, 11.8, 9.3],
            "sample3": [4.1, 2.2, 11.5, 3.8, 4.0],
            "sample4": [4.3, 2.0, 11.2, 3.9, 4.2]
        }, index=["GENE_A", "GENE_B", "GENE_C", "GENE_D", "GENE_E"])
        vst_df.index.name = "gene_id"
        vst_df.to_csv(self.vst_path)

        # Create dummy Sample metadata CSV
        self.sample_path = self.tmp_path / "sample_metadata.csv"
        sample_df = pd.DataFrame({
            "sample_id": ["sample1", "sample2", "sample3", "sample4"],
            "condition": ["Control", "Control", "Treated", "Treated"]
        })
        sample_df.to_csv(self.sample_path, index=False)

        # Create dummy DE results CSV
        self.de_path = self.tmp_path / "de_results.csv"
        de_df = pd.DataFrame({
            "gene_id": ["GENE_A", "GENE_B", "GENE_C", "GENE_D", "GENE_E"],
            "symbol": ["GeneA", "GeneB", "GeneC", "GeneD", "GeneE"],
            "log2FoldChange": [2.5, -1.8, 3.1, -0.2, 0.1],
            "shrunk_log2FoldChange": [2.4, -1.7, 3.0, -0.2, 0.1],
            "pvalue": [0.0001, 0.002, 0.00001, 0.4, 0.8],
            "padj": [0.0005, 0.005, 0.00005, 0.5, 0.9]
        })
        de_df.to_csv(self.de_path, index=False)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_pca_tool_execution_and_provenance(self):
        """Verify PCA tool generates PCA plot with complete provenance attached."""
        out_file = self.tmp_path / "pca_output.png"
        tool = PCAPlotTool()

        res = tool.run({
            "vst_counts_path": str(self.vst_path),
            "sample_table_path": str(self.sample_path),
            "output_path": str(out_file),
            "project_id": "TEST_PROJECT_001"
        })

        if res.status != "success":
            print(f"\nPCA TOOL ERROR: {res.error}")
        self.assertEqual(res.status, "success")
        self.assertTrue(out_file.exists())
        self.assertEqual(len(res.artifacts), 1)
        self.assertEqual(res.artifacts[0].artifact_type, "image")

        # Provenance verification
        prov = res.provenance
        self.assertEqual(prov.get("project_id"), "TEST_PROJECT_001")
        self.assertEqual(prov.get("tool"), "generate_pca_plot")
        self.assertEqual(prov.get("method"), "VisualizationEngine.plot_pca")
        self.assertEqual(prov.get("source_artifact"), str(self.vst_path))
        self.assertIn("relevant_parameters", prov)

    def test_volcano_tool_execution_and_provenance(self):
        """Verify Volcano tool generates Volcano plot with complete provenance attached."""
        out_file = self.tmp_path / "volcano_output.png"
        tool = VolcanoPlotTool()

        res = tool.run({
            "de_results_path": str(self.de_path),
            "output_path": str(out_file),
            "fdr_thresh": 0.05,
            "lfc_thresh": 1.0,
            "project_id": "TEST_PROJECT_001"
        })

        if res.status != "success":
            print(f"\nVOLCANO TOOL ERROR: {res.error}")
        self.assertEqual(res.status, "success")
        self.assertTrue(out_file.exists())
        self.assertEqual(len(res.artifacts), 1)
        self.assertEqual(res.artifacts[0].artifact_type, "image")

        prov = res.provenance
        self.assertEqual(prov.get("project_id"), "TEST_PROJECT_001")
        self.assertEqual(prov.get("tool"), "generate_volcano_plot")
        self.assertEqual(prov.get("method"), "VisualizationEngine.plot_volcano")
        self.assertEqual(prov.get("source_artifact"), str(self.de_path))
        self.assertEqual(prov.get("relevant_parameters").get("fdr_thresh"), 0.05)

    def test_heatmap_tool_execution_and_provenance(self):
        """Verify Heatmap tool generates Heatmap plot with complete provenance attached."""
        out_file = self.tmp_path / "heatmap_output.png"
        tool = HeatmapTool()

        res = tool.run({
            "vst_counts_path": str(self.vst_path),
            "de_results_path": str(self.de_path),
            "output_path": str(out_file),
            "top_n": 3,
            "project_id": "TEST_PROJECT_001"
        })

        if res.status != "success":
            print(f"\nHEATMAP TOOL ERROR: {res.error}")
        self.assertEqual(res.status, "success")
        self.assertTrue(out_file.exists())
        self.assertEqual(len(res.artifacts), 1)
        self.assertEqual(res.artifacts[0].artifact_type, "image")

        prov = res.provenance
        self.assertEqual(prov.get("project_id"), "TEST_PROJECT_001")
        self.assertEqual(prov.get("tool"), "generate_heatmap")
        self.assertEqual(prov.get("method"), "VisualizationEngine.plot_heatmap")
        self.assertEqual(prov.get("source_artifact"), str(self.vst_path))

    def test_qc_tool_execution_and_provenance(self):
        """Verify QC tool generates QC summary plot with complete provenance attached."""
        out_file = self.tmp_path / "qc_output.png"
        tool = QCPlotTool()

        res = tool.run({
            "output_path": str(out_file),
            "project_id": "TEST_PROJECT_001"
        })

        if res.status != "success":
            print(f"\nQC TOOL ERROR: {res.error}")
        self.assertEqual(res.status, "success")
        self.assertTrue(out_file.exists())
        self.assertEqual(len(res.artifacts), 1)
        self.assertEqual(res.artifacts[0].artifact_type, "image")

        prov = res.provenance
        self.assertEqual(prov.get("project_id"), "TEST_PROJECT_001")
        self.assertEqual(prov.get("tool"), "generate_qc_plot")
        self.assertEqual(prov.get("method"), "VisualizationEngine.generate_qc_plot")

    def test_missing_de_prerequisites_structured_failure(self):
        """Verify requesting a volcano plot when DE results are missing produces a structured error explanation."""
        tool = VolcanoPlotTool()
        non_existent_path = str(self.tmp_path / "non_existent_de.csv")

        res = tool.run({
            "de_results_path": non_existent_path,
            "project_id": "CUSTOM_NO_DE_PROJECT"
        })

        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "MissingPrerequisitesError")
        self.assertIn("Differential expression results are missing", res.error.message)
        self.assertIn("recommendation", res.provenance)

    def test_registry_contains_qc_plot_tool(self):
        """Verify registry contains all 4 visualization tools."""
        reg = ToolRegistry()
        reg.register(PCAPlotTool())
        reg.register(VolcanoPlotTool())
        reg.register(HeatmapTool())
        reg.register(QCPlotTool())

        self.assertIsNotNone(reg.get("generate_pca_plot"))
        self.assertIsNotNone(reg.get("generate_volcano_plot"))
        self.assertIsNotNone(reg.get("generate_heatmap"))
        self.assertIsNotNone(reg.get("generate_qc_plot"))

        qc_tools = reg.find_tools_for_intent("show sequencing quality QC")
        self.assertTrue(any(t.name == "generate_qc_plot" for t in qc_tools))


if __name__ == "__main__":
    unittest.main()
