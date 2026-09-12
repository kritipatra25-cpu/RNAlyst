"""
Unit Test Suite for Step 7 Controlled Agentic Tool Loop Architecture.
Enforces all 10 required agent loop testing scenarios:
1. Successful single-tool execution
2. Multi-step tool execution
3. Tool result returned to LLM as observation
4. Unknown tool rejection
5. Invalid argument rejection
6. Tool execution failure handling
7. Maximum iteration termination
8. Conversation/session continuity
9. No arbitrary code execution
10. Final synthesis using actual tool observations
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import pandas as pd

from agent.orchestrator.agent_runner import AgentOrchestrator, AgentResponse
from agent.llm.client import LLMResponse, ToolCallRequest, LLMMessage
from agent.llm.providers import MockLLMProvider
from agent.tools.registry import ToolRegistry
from agent.tools.base_tool import BaseTool, ToolResult, ToolArtifact
from agent.tools.deseq2_tool import DESeq2Tool
from agent.tools.literature_tool import LiteratureTool
from agent.tools.gene_annotation_tool import GeneAnnotationTool
from agent.tools.visualization_tools import VolcanoPlotTool, PCAPlotTool, HeatmapTool
from agent.tools.candidate_prioritization_tool import CandidatePrioritizationTool


class TestStep7AgentLoop(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_step7_"))

        # Create synthetic DE results file for test execution
        self.de_file = self.test_dir / "de_results.csv"
        df = pd.DataFrame({
            "gene_id": ["AT3G17609", "AT4G04720"],
            "symbol": ["HYH", "HEAT"],
            "log2FoldChange": [2.1, -1.5],
            "shrunk_log2FoldChange": [2.0, -1.4],
            "pvalue": [0.001, 0.005],
            "padj": [0.005, 0.02]
        })
        df.to_csv(self.de_file, index=False)

        self.mock_provider = MockLLMProvider()
        self.orchestrator = AgentOrchestrator(llm_provider=self.mock_provider)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_1_successful_single_tool_execution(self):
        """Test 1: Single tool request executed, observation returned, and final synthesis produced."""
        # Queue Turn 1 Tool Request
        tool_call = ToolCallRequest(
            tool_name="annotate_gene",
            arguments={"gene_id": "AT3G17609"}
        )
        self.mock_provider.queue_response(LLMResponse(
            content=None,
            tool_calls=[tool_call],
            finish_reason="tool_calls"
        ))

        # Queue Turn 2 Final Synthesis Answer
        self.mock_provider.queue_response(LLMResponse(
            content="[STATISTICAL] Gene AT3G17609 is annotated as HYH (HY5-HOMOLOG).",
            tool_calls=[],
            finish_reason="stop"
        ))

        resp = self.orchestrator.agentic_query(user_query="Annotate gene AT3G17609")

        self.assertTrue(resp.success)
        self.assertEqual(resp.iterations_count, 2)
        self.assertEqual(len(resp.tool_results), 1)
        self.assertEqual(resp.tool_results[0].tool_name, "annotate_gene")
        self.assertEqual(resp.tool_results[0].status, "success")
        self.assertIn("HYH", resp.message)

    def test_2_multi_step_tool_execution(self):
        """Test 2: Multi-step tool execution sequence (annotate gene -> generate volcano plot -> synthesize)."""
        # Step 1: Request gene annotation
        call1 = ToolCallRequest(tool_name="annotate_gene", arguments={"gene_id": "AT3G17609"})
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call1], finish_reason="tool_calls"))

        # Step 2: Request volcano plot
        volcano_out = str(self.test_dir / "volcano.png")
        call2 = ToolCallRequest(
            tool_name="generate_volcano_plot",
            arguments={"de_results_path": str(self.de_file), "output_path": volcano_out}
        )
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call2], finish_reason="tool_calls"))

        # Step 3: Final synthesis
        self.mock_provider.queue_response(LLMResponse(
            content="Analysis complete: Gene AT3G17609 annotated and Volcano plot generated at " + volcano_out,
            tool_calls=[],
            finish_reason="stop"
        ))

        resp = self.orchestrator.agentic_query(user_query="Annotate AT3G17609 and plot volcano")

        self.assertTrue(resp.success)
        self.assertEqual(resp.iterations_count, 3)
        self.assertEqual(len(resp.tool_results), 2)
        self.assertEqual(resp.tool_results[0].tool_name, "annotate_gene")
        self.assertEqual(resp.tool_results[1].tool_name, "generate_volcano_plot")
        self.assertTrue(Path(volcano_out).exists())

    def test_3_tool_result_returned_as_observation(self):
        """Test 3: Structured ToolResult is returned to the LLM message history as a 'tool' role observation."""
        call = ToolCallRequest(tool_name="annotate_gene", arguments={"gene_id": "AT3G17609"})
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call], finish_reason="tool_calls"))
        self.mock_provider.queue_response(LLMResponse(content="Done", tool_calls=[], finish_reason="stop"))

        self.orchestrator.agentic_query(user_query="Annotate gene")

        # Inspect call history received by MockLLMProvider in second generate() call
        second_call_messages = self.mock_provider.call_history[1]["messages"]

        tool_messages = [m for m in second_call_messages if m.role == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertEqual(tool_messages[0].tool_call_id, call.call_id)
        self.assertIn('"status":"success"', tool_messages[0].content)
        self.assertIn("AT3G17609", tool_messages[0].content)

    def test_4_unknown_tool_rejection(self):
        """Test 4: Requesting an unregistered tool returns UnknownToolError observation without breaking the loop."""
        call = ToolCallRequest(tool_name="unregistered_kegg_tool", arguments={})
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call], finish_reason="tool_calls"))
        self.mock_provider.queue_response(LLMResponse(
            content="I observed that unregistered_kegg_tool is unavailable.",
            tool_calls=[],
            finish_reason="stop"
        ))

        resp = self.orchestrator.agentic_query(user_query="Run KEGG enrichment")

        self.assertTrue(resp.success)
        self.assertEqual(len(resp.tool_results), 1)
        self.assertEqual(resp.tool_results[0].status, "error")
        self.assertEqual(resp.tool_results[0].error.error_type, "UnknownToolError")
        self.assertIn("unregistered_kegg_tool", resp.tool_results[0].error.message)

    def test_5_invalid_argument_rejection(self):
        """Test 5: Passing invalid tool arguments triggers schema validation rejection before execution."""
        call = ToolCallRequest(
            tool_name="generate_volcano_plot",
            arguments={"de_results_path": str(self.de_file), "fdr_thresh": 2.5}  # Invalid FDR > 1.0
        )
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call], finish_reason="tool_calls"))
        self.mock_provider.queue_response(LLMResponse(content="Argument validation error handled.", tool_calls=[], finish_reason="stop"))

        resp = self.orchestrator.agentic_query(user_query="Generate volcano with FDR 2.5")

        self.assertTrue(resp.success)
        self.assertEqual(resp.tool_results[0].status, "error")
        self.assertEqual(resp.tool_results[0].error.error_type, "ArgumentValidationError")

    def test_6_tool_execution_failure_handling(self):
        """Test 6: Non-existent file path failure captured safely in ToolResult observation."""
        call = ToolCallRequest(
            tool_name="generate_volcano_plot",
            arguments={"de_results_path": str(self.test_dir / "nonexistent.csv")}
        )
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call], finish_reason="tool_calls"))
        self.mock_provider.queue_response(LLMResponse(content="File missing error observed.", tool_calls=[], finish_reason="stop"))

        resp = self.orchestrator.agentic_query(user_query="Plot volcano for missing file")

        self.assertTrue(resp.success)
        self.assertEqual(resp.tool_results[0].status, "error")
        self.assertIn(resp.tool_results[0].error.error_type, ["FileNotFoundError", "MissingPrerequisitesError"])


    def test_7_maximum_iteration_termination(self):
        """Test 7: Agent loop safely terminates with error when max_iterations limit is reached."""
        # Queue continuous tool calls beyond max_iterations=3
        for i in range(5):
            call = ToolCallRequest(tool_name="annotate_gene", arguments={"gene_id": "AT3G17609"})
            self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call], finish_reason="tool_calls"))

        resp = self.orchestrator.agentic_query(user_query="Loop forever", max_iterations=3)

        self.assertFalse(resp.success)
        self.assertEqual(resp.iterations_count, 3)
        self.assertEqual(resp.error_result.error_type, "MaxIterationsReachedError")

    def test_8_conversation_session_continuity(self):
        """Test 8: Session context preserves multi-turn conversation history across agentic_query calls."""
        # Turn 1
        self.mock_provider.queue_response(LLMResponse(content="Turn 1 answer about OSD-678", tool_calls=[], finish_reason="stop"))
        resp1 = self.orchestrator.agentic_query(user_query="First turn on OSD-678", session_id="test_sess_100")
        self.assertTrue(resp1.success)

        # Turn 2: Second query using same session_id
        call2 = ToolCallRequest(tool_name="annotate_gene", arguments={"gene_id": "AT3G17609"})
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call2], finish_reason="tool_calls"))
        self.mock_provider.queue_response(LLMResponse(content="Turn 2 answer", tool_calls=[], finish_reason="stop"))

        resp2 = self.orchestrator.agentic_query(user_query="Second turn query", session_id="test_sess_100")

        self.assertTrue(resp2.success)
        # Verify first call in Turn 2 included history from Turn 1
        turn2_messages = self.mock_provider.call_history[1]["messages"]
        self.assertEqual(turn2_messages[0].content, "First turn on OSD-678")
        self.assertEqual(turn2_messages[1].content, "Turn 1 answer about OSD-678")
        self.assertEqual(turn2_messages[2].content, "Second turn query")

    def test_9_no_arbitrary_code_execution(self):
        """Test 9: Dispatcher strictly routes through registered BaseTool schema; arbitrary code cannot execute."""
        registry = ToolRegistry()
        for t in [
            DESeq2Tool(), LiteratureTool(), GeneAnnotationTool(),
            VolcanoPlotTool(), PCAPlotTool(), HeatmapTool(), CandidatePrioritizationTool()
        ]:
            registry.register(t)

        self.assertEqual(len(registry.list_tools()), 7)
        # Attempting arbitrary system command or code call returns UnknownToolError
        bad_call = ToolCallRequest(tool_name="os.system('rm -rf /')", arguments={})
        res = self.orchestrator.dispatcher.dispatch(bad_call)
        self.assertEqual(res.status, "error")
        self.assertEqual(res.error.error_type, "UnknownToolError")

    def test_10_final_synthesis_using_tool_observations(self):
        """Test 10: Final synthesized response contains outputs derived from actual executed tools."""
        call = ToolCallRequest(tool_name="annotate_gene", arguments={"gene_id": "AT3G17609"})
        self.mock_provider.queue_response(LLMResponse(content=None, tool_calls=[call], finish_reason="tool_calls"))

        synthesis_text = (
            "[STATISTICAL] Gene AT3G17609 (HYH) showed significant differential expression (padj < 0.05). "
            "[LITERATURE-SUPPORTED] HYH is involved in light signaling regulation."
        )
        self.mock_provider.queue_response(LLMResponse(content=synthesis_text, tool_calls=[], finish_reason="stop"))

        resp = self.orchestrator.agentic_query(user_query="Synthesize findings for AT3G17609")

        self.assertTrue(resp.success)
        self.assertEqual(resp.message, synthesis_text)
        self.assertIn("[STATISTICAL]", resp.message)
        self.assertIn("[LITERATURE-SUPPORTED]", resp.message)


if __name__ == "__main__":
    unittest.main()
