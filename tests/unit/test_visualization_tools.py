"""
Unit tests for Step 6C Visualization Agent Tools (VolcanoPlotTool, PCAPlotTool, HeatmapTool).
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np

from agent.tools.base_tool import ToolResult, ToolArtifact
from agent.tools.visualization_tools import (
    VolcanoPlotTool,
    VolcanoPlotToolArgs,
    PCAPlotTool,
    PCAPlotToolArgs,
    HeatmapTool,
    HeatmapToolArgs
)
from agent.tools.deseq2_tool import DESeq2Tool
from agent.tools.gene_annotation_tool import GeneAnnotationTool
from agent.tools.literature_tool import LiteratureTool
from agent.tools.registry import ToolRegistry
from agent.llm.dispatcher import ToolCallDispatcher
from agent.llm.client import ToolCallRequest


class TestVisualizationTools(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_vis_"))

        # Create lightweight synthetic DE results CSV
        self.de_file = self.test_dir / "de_results.csv"
        de_df = pd.DataFrame({
            "gene_id": [f"AT{i}G00000" for i in range(1, 11)],
            "symbol": [f"SYM{i}" for i in range(1, 11)],
            "baseMean": np.random.uniform(10, 1000, 10),
            "log2FoldChange": np.random.uniform(-3, 3, 10),
            "shrunk_log2FoldChange": np.random.uniform(-2.5, 2.5, 10),
            "lfcSE": [0.1] * 10,
            "pvalue": [0.001 * i for i in range(1, 11)],
            "padj": [0.005 * i for i in range(1, 11)]
        })
        de_df.to_csv(self.de_file, index=False)

        # Create lightweight synthetic VST counts CSV
        self.vst_file = self.test_dir / "vst_counts.csv"
        vst_data = {"gene_id": [f"AT{i}G00000" for i in range(1, 11)]}
        for s in ["S1_GC", "S2_GC", "S3_FLT", "S4_FLT"]:
            vst_data[s] = np.random.uniform(5, 15, 10)
        vst_df = pd.DataFrame(vst_data)
        vst_df.to_csv(self.vst_file, index=False)

        # Create lightweight synthetic sample table CSV
        self.sample_file = self.test_dir / "sample_table.csv"
        sample_df = pd.DataFrame({
            "sample_id": ["S1_GC", "S2_GC", "S3_FLT", "S4_FLT"],
            "condition": ["Control", "Control", "Spaceflight", "Spaceflight"]
        }).set_index("sample_id", drop=False)
        sample_df.to_csv(self.sample_file, index=False)

        self.out_volcano = str(self.test_dir / "volcano.png")
        self.out_pca = str(self.test_dir / "pca.png")
        self.out_heatmap = str(self.test_dir / "heatmap.png")

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_1_valid_volcano_plot_tool_invocation(self):
        """Test 1: Valid volcano plot tool invocation generates figure and success ToolResult."""
        tool = VolcanoPlotTool()
        res = tool.run({
            "de_results_path": str(self.de_file),
            "output_path": self.out_volcano,
            "fdr_thresh": 0.05,
            "lfc_thresh": 1.0
        })

        self.assertEqual(res.status, "success")
        self.assertEqual(res.tool_name, "generate_volcano_plot")
        self.assertTrue(Path(self.out_volcano).exists())
        self.assertEqual(res.result["total_genes"], 10)

    def test_2_valid_pca_plot_tool_invocation(self):
        """Test 2: Valid PCA plot tool invocation generates figure and success ToolResult."""
        tool = PCAPlotTool()
        res = tool.run({
            "vst_counts_path": str(self.vst_file),
            "sample_table_path": str(self.sample_file),
            "group_col": "condition",
            "output_path": self.out_pca,
            "top_n_genes": 5
        })

        self.assertEqual(res.status, "success")
        self.assertEqual(res.tool_name, "generate_pca_plot")
        self.assertTrue(Path(self.out_pca).exists())
        self.assertIn("pc1_var", res.result)
        self.assertIn("pc2_var", res.result)

    def test_3_valid_heatmap_tool_invocation(self):
        """Test 3: Valid heatmap tool invocation generates figure and success ToolResult."""
        tool = HeatmapTool()
        res = tool.run({
            "vst_counts_path": str(self.vst_file),
            "de_results_path": str(self.de_file),
            "sample_table_path": str(self.sample_file),
            "output_path": self.out_heatmap,
            "top_n": 5
        })

        self.assertEqual(res.status, "success")
        self.assertEqual(res.tool_name, "generate_heatmap")
        self.assertTrue(Path(self.out_heatmap).exists())
        self.assertEqual(res.result["top_n_requested"], 5)

    def test_4_malformed_arguments(self):
        """Test 4: Out-of-bounds numerical cutoffs rejected by schema validation."""
        volcano_tool = VolcanoPlotTool()
        res_volcano = volcano_tool.run({
            "de_results_path": str(self.de_file),
            "fdr_thresh": 1.5  # Invalid FDR > 1.0
        })
        self.assertEqual(res_volcano.status, "error")
        self.assertEqual(res_volcano.error.error_type, "ArgumentValidationError")

        pca_tool = PCAPlotTool()
        res_pca = pca_tool.run({
            "vst_counts_path": str(self.vst_file),
            "sample_table_path": str(self.sample_file),
            "top_n_genes": 1  # Invalid < 2 for PCA
        })
        self.assertEqual(res_pca.status, "error")
        self.assertEqual(res_pca.error.error_type, "ArgumentValidationError")

    def test_5_missing_required_arguments(self):
        """Test 5: Empty/missing required file paths rejected by schema validation or prerequisite check."""
        tool = VolcanoPlotTool()
        res = tool.run({"de_results_path": "   "})
        self.assertEqual(res.status, "error")
        self.assertIn(res.error.error_type, ("ArgumentValidationError", "MissingPrerequisitesError"))

    def test_6_structured_tool_result_output(self):
        """Test 6: Structured ToolResult contains output metrics and provenance metadata."""
        tool = VolcanoPlotTool()
        res = tool.run({
            "de_results_path": str(self.de_file),
            "output_path": self.out_volcano
        })

        self.assertEqual(res.tool_name, "generate_volcano_plot")
        self.assertEqual(res.provenance["wrapped_class"], "VisualizationEngine")
        self.assertEqual(res.provenance["wrapped_method"], "plot_volcano")

    def test_7_artifact_output_metadata(self):
        """Test 7: ToolResult exposes figure image ToolArtifact metadata."""
        tool = VolcanoPlotTool()
        res = tool.run({
            "de_results_path": str(self.de_file),
            "output_path": self.out_volcano
        })

        self.assertEqual(len(res.artifacts), 1)
        artifact = res.artifacts[0]
        self.assertEqual(artifact.artifact_type, "image")
        self.assertEqual(artifact.path, self.out_volcano)

    def test_8_tool_registration_and_discovery(self):
        """Test 8: ToolRegistry registers and exports schemas for all 3 visualization tools."""
        registry = ToolRegistry()
        registry.register(VolcanoPlotTool())
        registry.register(PCAPlotTool())
        registry.register(HeatmapTool())

        schemas = registry.get_tool_schemas()
        self.assertEqual(len(schemas), 3)
        tool_names = [s["name"] for s in schemas]
        self.assertIn("generate_volcano_plot", tool_names)
        self.assertIn("generate_pca_plot", tool_names)
        self.assertIn("generate_heatmap", tool_names)

    def test_9_invalid_tool_arguments_rejected_before_execution(self):
        """Test 9: ToolCallDispatcher rejects malformed tool arguments before execution."""
        registry = ToolRegistry()
        registry.register(VolcanoPlotTool())
        dispatcher = ToolCallDispatcher(registry)

        call = ToolCallRequest(
            tool_name="generate_volcano_plot",
            arguments={"de_results_path": str(self.de_file), "fdr_thresh": -0.1}
        )
        res = dispatcher.dispatch(call)

        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "ArgumentValidationError")

    def test_10_unknown_tool_rejected_safely(self):
        """Test 10: ToolCallDispatcher safely rejects unknown tool request."""
        registry = ToolRegistry()
        registry.register(VolcanoPlotTool())
        dispatcher = ToolCallDispatcher(registry)

        call = ToolCallRequest(tool_name="nonexistent_plot_tool", arguments={})
        res = dispatcher.dispatch(call)

        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "UnknownToolError")

    def test_11_existing_tools_unaffected(self):
        """Test 11: Existing tools (DESeq2, Literature, GeneAnnotation) operate alongside visualization tools."""
        registry = ToolRegistry()
        registry.register(DESeq2Tool())
        registry.register(LiteratureTool())
        registry.register(GeneAnnotationTool())
        registry.register(VolcanoPlotTool())
        registry.register(PCAPlotTool())
        registry.register(HeatmapTool())

        self.assertEqual(len(registry.list_tools()), 6)
        names = [t.name for t in registry.list_tools()]
        self.assertIn("run_differential_expression", names)
        self.assertIn("search_literature", names)
        self.assertIn("annotate_gene", names)
        self.assertIn("generate_volcano_plot", names)
        self.assertIn("generate_pca_plot", names)
        self.assertIn("generate_heatmap", names)


if __name__ == "__main__":
    unittest.main()
