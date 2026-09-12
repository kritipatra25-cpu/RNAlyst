"""
Unit tests for Step 6B GeneAnnotationTool contract, registration, dispatcher, and safety.
"""

import unittest
from typing import Dict, Any

from agent.tools.base_tool import ToolResult
from agent.tools.gene_annotation_tool import GeneAnnotationTool, GeneAnnotationToolArgs
from agent.tools.deseq2_tool import DESeq2Tool
from agent.tools.literature_tool import LiteratureTool
from agent.tools.registry import ToolRegistry
from agent.llm.dispatcher import ToolCallDispatcher
from agent.llm.client import ToolCallRequest
from analysis.annotation.gene_annotator import GeneAnnotator


class TestGeneAnnotationTool(unittest.TestCase):

    def test_1_valid_gene_annotation_request(self):
        """Test 1: Valid gene annotation request returns expected symbol."""
        tool = GeneAnnotationTool()
        res = tool.run({"gene_id": "AT3G17609"})

        self.assertEqual(res.status, "success")
        self.assertEqual(res.result["gene_id"], "AT3G17609")
        self.assertEqual(res.result["symbol"], "HYH")
        self.assertEqual(res.result["organism"], "Arabidopsis thaliana")

    def test_2_invalid_malformed_gene_id(self):
        """Test 2: Short or empty gene ID rejected by schema validation."""
        tool = GeneAnnotationTool()
        res = tool.run({"gene_id": "a"})

        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "ArgumentValidationError")

    def test_3_unknown_organism_source_handling(self):
        """Test 3: Custom organism and annotation source handled gracefully."""
        tool = GeneAnnotationTool()
        res = tool.run({
            "gene_id": "AT1G01010",
            "organism": "Custom Plant",
            "annotation_source": "CUSTOM_DB",
            "custom_symbol_map": {"AT1G01010": "ANAC001"}
        })

        self.assertEqual(res.status, "success")
        self.assertEqual(res.result["symbol"], "ANAC001")
        self.assertEqual(res.result["organism"], "Custom Plant")
        self.assertEqual(res.result["annotation_source"], "CUSTOM_DB")

    def test_4_structured_tool_result_output(self):
        """Test 4: Structured ToolResult contains all expected schema fields."""
        tool = GeneAnnotationTool()
        res = tool.run({"gene_id": "AT5G57630"})

        self.assertEqual(res.tool_name, "annotate_gene")
        self.assertIn("gene_id", res.result)
        self.assertIn("symbol", res.result)
        self.assertIn("name", res.result)
        self.assertIn("biotype", res.result)
        self.assertIn("organism", res.result)
        self.assertIn("annotation_source", res.result)
        self.assertEqual(res.result["symbol"], "CIPK21")

    def test_5_provenance_preservation(self):
        """Test 5: Provenance dictionary preserves metadata."""
        tool = GeneAnnotationTool()
        res = tool.run({"gene_id": "AT3G46640"})

        self.assertEqual(res.provenance["gene_id"], "AT3G46640")
        self.assertEqual(res.provenance["organism"], "Arabidopsis thaliana")
        self.assertEqual(res.provenance["annotation_source"], "TAIR10")
        self.assertEqual(res.provenance["wrapped_class"], "GeneAnnotator")

    def test_6_tool_registration_and_discovery(self):
        """Test 6: ToolRegistry exports annotate_gene JSON schema."""
        registry = ToolRegistry()
        registry.register(GeneAnnotationTool())

        schemas = registry.get_tool_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]["name"], "annotate_gene")
        self.assertIn("gene_id", schemas[0]["parameters"]["properties"])

    def test_7_llm_tool_call_dispatch(self):
        """Test 7: ToolCallDispatcher resolves and executes annotate_gene ToolCallRequest."""
        registry = ToolRegistry()
        registry.register(GeneAnnotationTool())
        dispatcher = ToolCallDispatcher(registry)

        call = ToolCallRequest(tool_name="annotate_gene", arguments={"gene_id": "AT5G07390"})
        res = dispatcher.dispatch(call)

        self.assertEqual(res.status, "success")
        self.assertEqual(res.result["symbol"], "RBOHA")

    def test_8_invalid_tool_arguments_rejected_before_execution(self):
        """Test 8: Dispatcher rejects malformed tool arguments before execution."""
        registry = ToolRegistry()
        registry.register(GeneAnnotationTool())
        dispatcher = ToolCallDispatcher(registry)

        call = ToolCallRequest(tool_name="annotate_gene", arguments={"gene_id": ""})
        res = dispatcher.dispatch(call)

        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "ArgumentValidationError")

    def test_9_unknown_tool_rejected_safely(self):
        """Test 9: Dispatcher safely returns UnknownToolError for unregistered tools."""
        registry = ToolRegistry()
        registry.register(GeneAnnotationTool())
        dispatcher = ToolCallDispatcher(registry)

        call = ToolCallRequest(tool_name="unknown_tool", arguments={})
        res = dispatcher.dispatch(call)

        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "UnknownToolError")

    def test_10_existing_tools_unaffected(self):
        """Test 10: DESeq2Tool and LiteratureTool operate unchanged alongside GeneAnnotationTool."""
        registry = ToolRegistry()
        registry.register(DESeq2Tool())
        registry.register(LiteratureTool())
        registry.register(GeneAnnotationTool())

        self.assertEqual(len(registry.list_tools()), 3)
        names = [t.name for t in registry.list_tools()]
        self.assertIn("run_differential_expression", names)
        self.assertIn("search_literature", names)
        self.assertIn("annotate_gene", names)


if __name__ == "__main__":
    unittest.main()

