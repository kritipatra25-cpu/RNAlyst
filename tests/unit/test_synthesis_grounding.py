import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.orchestrator.agent_runner import AgentOrchestrator, AgentResponse
from agent.orchestrator.intent_parser import NaturalLanguageIntentParser
from agent.reasoning.scientific_synthesizer import ScientificSynthesizer
from pipeline.backend_api import AnalysisResult


class TestSynthesisGroundingRegression(unittest.TestCase):
    """Regression test suite enforcing strict dynamic grounding and prohibiting stale OSD-678 content."""

    def setUp(self):
        self.orchestrator = AgentOrchestrator()
        self.custom_project_id = "3862DEF1-9D01-4D21-AA0C-1DDB3D1346F3"

    def test_custom_project_cannot_receive_osd678_content(self):
        """Test A: A custom project query does NOT receive OSD-678, Arabidopsis, or static DEG fallbacks."""
        parser = NaturalLanguageIntentParser()
        intent = parser.parse("Summarize the FASTQ QC metrics for the uploaded dataset", active_dataset_id=self.custom_project_id)
        self.assertEqual(intent.dataset_id, self.custom_project_id)
        self.assertNotEqual(intent.dataset_id, "OSD-678")

    def test_synthesis_context_contains_current_project_ids(self):
        """Test B: Synthesis context prompt contains current project_id and active metadata."""
        mock_provider = MagicMock()
        mock_provider.generate.return_value = MagicMock(
            content="QC summary for 3862DEF1-9D01-4D21-AA0C-1DDB3D1346F3",
            finish_reason="STOP",
            has_tool_calls=False,
            tool_calls=[]
        )
        orchestrator = AgentOrchestrator(llm_provider=mock_provider)
        
        resp = orchestrator.query("Summarize QC metrics", dataset_id=self.custom_project_id)
        self.assertTrue(resp.success)
        self.assertEqual(resp.dataset_id, self.custom_project_id)
        
        # Verify provider generate call received message containing custom_project_id
        last_messages = mock_provider.generate.call_args[1].get("messages") or mock_provider.generate.call_args[0][0]
        context_text = "".join([m.content for m in last_messages if m.content])
        self.assertIn(self.custom_project_id, context_text)
        self.assertNotIn("OSD-678", context_text)

    def test_static_benchmark_biological_values_cannot_enter_synthesis(self):
        """Test C: Static benchmark numbers (e.g. 7,949 DEGs, 27,330 genes, Col-0/Ws/phyD) are absent from grounding context."""
        mock_provider = MagicMock()
        mock_provider.generate.return_value = MagicMock(
            content="Analysis of uploaded project 3862DEF1-9D01-4D21-AA0C-1DDB3D1346F3",
            finish_reason="STOP",
            has_tool_calls=False,
            tool_calls=[]
        )
        orchestrator = AgentOrchestrator(llm_provider=mock_provider)
        orchestrator.query("What are the top DEGs?", dataset_id=self.custom_project_id)
        
        last_messages = mock_provider.generate.call_args[1].get("messages") or mock_provider.generate.call_args[0][0]
        context_text = "".join([m.content for m in last_messages if m.content])
        
        stale_terms = ["OSD-678", "Arabidopsis thaliana", "7,949", "27,330", "Col-0", "phyD", "Ws"]
        for term in stale_terms:
            self.assertNotIn(term, context_text)

    def test_missing_metrics_reported_as_unavailable(self):
        """Test D: Missing candidates/metrics produce explicit unavailable/not computed statements rather than hardcoded TAIR fallbacks."""
        synthesizer = ScientificSynthesizer()
        mock_result = AnalysisResult(
            dataset_id=self.custom_project_id,
            execution_status="COMPLETED",
            output_dir="/tmp/dummy",
            analysis_summary_path="/tmp/dummy/summary.json",
            candidate_comparison_csv_path="/tmp/dummy/cand.csv",
            provenance_manifest_path="/tmp/dummy/prov.json",
            contrast_count=0,
            candidate_count=0,
            summary_metrics={}
        )
        report = synthesizer.synthesize(mock_result, candidate_records=[], query_text="Summarize candidate genes")
        report_md = report.full_markdown_report()
        
        self.assertIn(self.custom_project_id, report_md)
        self.assertNotIn("AT1G01010", report_md)
        self.assertNotIn("AT3G17609", report_md)
        self.assertNotIn("NPJ Microgravity (2021)", report_md)
        self.assertIn("No specific peer-reviewed literature citations found", report_md)


if __name__ == "__main__":
    unittest.main()
