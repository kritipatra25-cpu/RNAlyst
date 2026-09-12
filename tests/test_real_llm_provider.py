import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.llm_provider import (
    LLMIntentProposal, OpenAILLMProvider, GeminiLLMProvider, MockLLMProvider
)
from pipeline.llm_factory import LLMProviderFactory
from pipeline.planner import AnalysisPlanner
from pipeline.orchestrator import AnalysisOrchestrator
from pipeline.job_models import JobStatus


class TestRealLLMProviderIntegration(unittest.TestCase):

    def setUp(self):
        self.uploads_dir = PROJECT_ROOT / "data" / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

        self.valid_id = "test_real_llm_valid_fixture"
        self.counts_path = self.uploads_dir / f"{self.valid_id}_counts.csv"
        self.meta_path = self.uploads_dir / f"{self.valid_id}_metadata.csv"

        pd.DataFrame({
            "gene_id": ["G1", "G2"],
            "C1": [10, 20], "C2": [12, 22],
            "T1": [100, 200], "T2": [110, 210]
        }).to_csv(self.counts_path, index=False)

        pd.DataFrame({
            "sample": ["C1", "C2", "T1", "T2"],
            "condition": ["Control", "Control", "Treated", "Treated"]
        }).to_csv(self.meta_path, index=False)

    def test_1_factory_configuration(self):
        """Test LLMProviderFactory instantiates correct providers based on input/env."""
        p_none = LLMProviderFactory.get_provider("none")
        self.assertIsNone(p_none)

        p_mock = LLMProviderFactory.get_provider("mock")
        self.assertIsInstance(p_mock, MockLLMProvider)

        p_openai = LLMProviderFactory.get_provider("openai", api_key="sk-fake")
        self.assertIsInstance(p_openai, OpenAILLMProvider)

        p_gemini = LLMProviderFactory.get_provider("gemini", api_key="gm-fake")
        self.assertIsInstance(p_gemini, GeminiLLMProvider)

    @patch("urllib.request.urlopen")
    def test_2_openai_mocked_success(self, mock_urlopen):
        """Test OpenAILLMProvider with mocked HTTP success response parses structured output."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "proposed_goal": "Perform DE on treated vs control",
                        "proposed_steps": ["pca", "differential_expression"],
                        "suggested_intent": "DIFFERENTIAL_EXPRESSION",
                        "reasoning": "User asked for DE analysis"
                    })
                }
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        provider = OpenAILLMProvider(api_key="sk-fake")
        proposal = provider.generate_intent_proposal("Compare treated vs control and find DE genes")

        self.assertIsInstance(proposal, LLMIntentProposal)
        self.assertEqual(proposal.proposed_goal, "Perform DE on treated vs control")
        self.assertEqual(proposal.proposed_steps, ["pca", "differential_expression"])

    @patch("google.genai.Client")
    def test_3_gemini_mocked_success(self, mock_client_cls):
        """Test GeminiLLMProvider with mocked google-genai SDK response parses structured output."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "proposed_goal": "Execute PCA plot pipeline",
            "proposed_steps": ["pca"],
            "suggested_intent": "PCA",
            "reasoning": "User requested sample clustering"
        })
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key="gm-fake")
        provider.client = mock_client

        proposal = provider.generate_intent_proposal("Do PCA to see sample clustering")

        self.assertIsInstance(proposal, LLMIntentProposal)
        self.assertEqual(proposal.proposed_steps, ["pca"])
        self.assertEqual(proposal.suggested_intent, "PCA")

    def test_4_missing_api_key_resiliency(self):
        """Test missing API key raises error cleanly, allowing AnalysisPlanner to fallback."""
        p_openai = OpenAILLMProvider(api_key="")
        with self.assertRaises(ValueError):
            p_openai.generate_intent_proposal("Run DE")

        # Planner ingests provider, catches ValueError, and falls back to keyword parsing
        planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=p_openai)
        plan = planner.create_analysis_plan(
            file_id=self.valid_id,
            user_question="Compare treated vs control and find DE genes"
        )
        self.assertTrue(plan.is_valid)
        self.assertIn("differential_expression", plan.selected_steps)

    @patch("urllib.request.urlopen")
    def test_5_api_timeout_rate_limit_resiliency(self, mock_urlopen):
        """Test HTTP timeout / network error triggers clean planner fallback."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("HTTP 429 Too Many Requests")

        provider = OpenAILLMProvider(api_key="sk-fake")
        planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=provider)

        plan = planner.create_analysis_plan(
            file_id=self.valid_id,
            user_question="Run PCA on dataset"
        )

        self.assertTrue(plan.is_valid)
        self.assertIn("pca", plan.selected_steps)

    @patch("urllib.request.urlopen")
    def test_6_schema_validation_resiliency(self, mock_urlopen):
        """Test malformed non-JSON or invalid schema response triggers clean planner fallback."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "This is plain text, not JSON"}}]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        provider = OpenAILLMProvider(api_key="sk-fake")
        planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=provider)

        plan = planner.create_analysis_plan(
            file_id=self.valid_id,
            user_question="Run DE analysis"
        )

        self.assertTrue(plan.is_valid)
        self.assertIn("differential_expression", plan.selected_steps)

    @patch("urllib.request.urlopen")
    def test_7_adversarial_defense_with_mocked_real_provider(self, mock_urlopen):
        """Test adversarial path injection in real LLM output is completely ignored by planner."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "proposed_goal": "Perform DE on /etc/passwd",
                        "proposed_steps": ["differential_expression"],
                        "suggested_intent": "DIFFERENTIAL_EXPRESSION",
                        "reasoning": "Use /etc/passwd and /tmp/fake.csv",
                        "injected_paths": ["/etc/passwd", "/tmp/fake.csv"]
                    })
                }
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        provider = OpenAILLMProvider(api_key="sk-fake")
        planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=provider)

        plan = planner.create_analysis_plan(
            file_id=self.valid_id,
            user_question="Run DE analysis"
        )

        self.assertTrue(plan.is_valid)
        for inp in plan.required_inputs:
            if inp.resolved_path:
                self.assertNotIn("/etc/passwd", inp.resolved_path)
                self.assertNotIn("fake.csv", inp.resolved_path)

    def test_8_backward_compatibility(self):
        """Test default factory behavior maintains backward compatibility."""
        provider = LLMProviderFactory.get_provider("none")
        self.assertIsNone(provider)

        orchestrator = AnalysisOrchestrator(uploads_dir=self.uploads_dir, llm_provider=provider)
        job = orchestrator.create_job(
            file_id=self.valid_id,
            user_question="Do PCA to see clustering"
        )
        self.assertTrue(job.structured_plan.is_valid)
        self.assertEqual(job.plan, ["pca"])


if __name__ == "__main__":
    unittest.main()
