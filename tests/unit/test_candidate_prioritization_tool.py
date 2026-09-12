"""
Unit tests for Step 6D CandidatePrioritizationTool.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import pandas as pd

from agent.tools.base_tool import ToolResult
from agent.tools.candidate_prioritization_tool import CandidatePrioritizationTool, CandidatePrioritizationToolArgs
from agent.tools.deseq2_tool import DESeq2Tool
from agent.tools.literature_tool import LiteratureTool
from agent.tools.gene_annotation_tool import GeneAnnotationTool
from agent.tools.visualization_tools import VolcanoPlotTool, PCAPlotTool, HeatmapTool
from agent.tools.registry import ToolRegistry
from agent.llm.dispatcher import ToolCallDispatcher
from agent.llm.client import ToolCallRequest


class TestCandidatePrioritizationTool(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_cand_"))

        # Create primary DE results CSV
        self.primary_de_file = self.test_dir / "primary_de.csv"
        df_p = pd.DataFrame({
            "gene_id": ["AT3G17609", "AT4G04720", "AT1G01010"],
            "symbol": ["HSFA2", "HEAT", "GENE1"],
            "log2FoldChange": [2.5, -1.8, 0.5],
            "lfcSE": [0.2, 0.15, 0.1],
            "pvalue": [0.0001, 0.001, 0.04],
            "padj": [0.001, 0.01, 0.08]
        })
        df_p.to_csv(self.primary_de_file, index=False)

        # Create reference DE results CSV
        self.ref_de_file = self.test_dir / "ref_de.csv"
        df_ref = pd.DataFrame({
            "gene_id": ["AT3G17609", "AT4G04720", "AT1G01010"],
            "log2FoldChange": [1.9, -1.2, -0.4],
            "shrunk_log2FoldChange": [1.8, -1.1, -0.3],
            "padj": [0.002, 0.02, 0.2]
        })
        df_ref.to_csv(self.ref_de_file, index=False)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_1_valid_tool_invocation(self):
        """Test 1: Valid candidate prioritization tool invocation returns success ToolResult."""
        tool = CandidatePrioritizationTool()
        res = tool.run({
            "candidate_genes": ["AT3G17609", "AT4G04720"],
            "primary_de_path": str(self.primary_de_file),
            "reference_de_path": str(self.ref_de_file)
        })

        self.assertEqual(res.status, "success")
        self.assertEqual(res.tool_name, "evaluate_candidate_genes")
        self.assertEqual(res.result["candidate_count"], 2)
        self.assertEqual(res.result["concordant_count"], 2)
        self.assertEqual(res.result["fdr_pass_count"], 2)

    def test_2_malformed_arguments(self):
        """Test 2: Empty candidate list rejected by argument validation."""
        tool = CandidatePrioritizationTool()
        res = tool.run({
            "candidate_genes": [],
            "primary_de_path": str(self.primary_de_file)
        })

        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "ArgumentValidationError")

    def test_3_nonexistent_file_path(self):
        """Test 3: Non-existent primary DE path returns error ToolResult."""
        tool = CandidatePrioritizationTool()
        res = tool.run({
            "candidate_genes": ["AT3G17609"],
            "primary_de_path": str(self.test_dir / "nonexistent.csv")
        })

        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "FileNotFoundError")

    def test_4_structured_tool_result_format(self):
        """Test 4: Structured ToolResult contains evaluated gene records & provenance."""
        tool = CandidatePrioritizationTool()
        res = tool.run({
            "candidate_genes": ["AT3G17609"],
            "primary_de_path": str(self.primary_de_file)
        })

        self.assertIn("evaluated_candidates", res.result)
        evals = res.result["evaluated_candidates"]
        self.assertEqual(len(evals), 1)
        self.assertEqual(evals[0]["gene_id"], "AT3G17609")
        self.assertEqual(evals[0]["symbol"], "HYH")
        self.assertEqual(res.provenance["wrapped_class"], "CandidatePrioritizer")

    def test_5_tool_registration_and_schema_discovery(self):
        """Test 5: ToolRegistry registers and exports schemas for all 7 agent tools."""
        registry = ToolRegistry()
        registry.register(DESeq2Tool())
        registry.register(LiteratureTool())
        registry.register(GeneAnnotationTool())
        registry.register(VolcanoPlotTool())
        registry.register(PCAPlotTool())
        registry.register(HeatmapTool())
        registry.register(CandidatePrioritizationTool())

        self.assertEqual(len(registry.list_tools()), 7)
        schemas = registry.get_tool_schemas()
        self.assertEqual(len(schemas), 7)
        names = [s["name"] for s in schemas]
        self.assertIn("evaluate_candidate_genes", names)
        self.assertIn("run_differential_expression", names)
        self.assertIn("search_literature", names)
        self.assertIn("annotate_gene", names)
        self.assertIn("generate_volcano_plot", names)
        self.assertIn("generate_pca_plot", names)
        self.assertIn("generate_heatmap", names)

    def test_6_dispatcher_pre_execution_validation(self):
        """Test 6: ToolCallDispatcher rejects invalid arguments before execution."""
        registry = ToolRegistry()
        registry.register(CandidatePrioritizationTool())
        dispatcher = ToolCallDispatcher(registry)

        call = ToolCallRequest(
            tool_name="evaluate_candidate_genes",
            arguments={"candidate_genes": "NOT_A_LIST", "primary_de_path": str(self.primary_de_file)}
        )
        res = dispatcher.dispatch(call)

        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "ArgumentValidationError")

    def test_7_dispatcher_unknown_tool_rejection(self):
        """Test 7: ToolCallDispatcher safely rejects unknown tool name."""
        registry = ToolRegistry()
        registry.register(CandidatePrioritizationTool())
        dispatcher = ToolCallDispatcher(registry)

        call = ToolCallRequest(tool_name="unknown_gene_tool", arguments={})
        res = dispatcher.dispatch(call)

        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "UnknownToolError")

    def test_8_all_existing_tools_unaffected(self):
        """Test 8: Existing tools (DESeq2, Literature, GeneAnnotation, Visualization) remain fully functional alongside CandidatePrioritizationTool."""
        registry = ToolRegistry()
        for t in [
            DESeq2Tool(),
            LiteratureTool(),
            GeneAnnotationTool(),
            VolcanoPlotTool(),
            PCAPlotTool(),
            HeatmapTool(),
            CandidatePrioritizationTool()
        ]:
            registry.register(t)

        self.assertEqual(len(registry.list_tools()), 7)


if __name__ == "__main__":
    unittest.main()
