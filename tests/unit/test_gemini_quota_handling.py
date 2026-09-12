"""
Unit Test Suite for Gemini 429 Resource Exhaustion & Quota Handling.

Verifies:
1. Transient 429 error with retry delay
2. Daily/project quota exhaustion detection
3. Circuit breaker preventing subsequent network requests after quota exhaustion
4. Concise structured error messages without raw RPC payloads
5. Production provider resolution to GeminiLLMProvider (gemini-3.6-flash)
"""

import unittest
from unittest.mock import MagicMock, patch
from agent.llm.providers import GeminiLLMProvider, parse_gemini_error
from agent.llm.client import LLMMessage
from agent.orchestrator.agent_runner import AgentOrchestrator


class DummyGoogleAPIError(Exception):
    """Simulated Google API exception for testing."""
    def __init__(self, message, code=429):
        super().__init__(message)
        self.code = code
        self.message = message


class TestGeminiQuotaHandling(unittest.TestCase):
    """Test suite covering Gemini 429 quota exhaustion and transient rate limiting."""

    def test_parse_gemini_error_daily_quota_exhausted(self):
        """Verify explicit detection of free_tier_requests daily quota exhaustion."""
        err_msg = (
            "429 RESOURCE_EXHAUSTED: Quota metric "
            "'generativelanguage.googleapis.com/generate_content_free_tier_requests' "
            "exceeded for limit '20' per-day"
        )
        err = DummyGoogleAPIError(err_msg, code=429)
        category, msg, retry_delay = parse_gemini_error(err)

        self.assertEqual(category, "quota_exhausted")
        self.assertEqual(msg, "Gemini API quota has been exhausted for this project. No additional model requests were attempted.")
        self.assertIsNone(retry_delay)

    def test_parse_gemini_error_transient_rate_limit(self):
        """Verify extraction of retry delay for transient rate limits."""
        err_msg = "429 RESOURCE_EXHAUSTED: Rate limit exceeded. Retry after 5 seconds."
        err = DummyGoogleAPIError(err_msg, code=429)
        category, msg, retry_delay = parse_gemini_error(err)

        self.assertEqual(category, "transient_rate_limit")
        self.assertIn("Please retry after 5 seconds.", msg)
        self.assertEqual(retry_delay, 5.0)

    @patch("google.genai.Client")
    def test_quota_exhaustion_circuit_breaker(self, mock_client_cls):
        """Verify that daily quota exhaustion sets circuit breaker and blocks subsequent network calls."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Configure client to raise daily quota exhaustion exception on first call
        err_msg = "RESOURCE_EXHAUSTED: generate_content_free_tier_requests limit exceeded"
        mock_client.models.generate_content.side_effect = DummyGoogleAPIError(err_msg, code=429)

        provider = GeminiLLMProvider(api_key="mock_api_key_123", model_name="gemini-3.6-flash")
        msg = LLMMessage(role="user", content="Hello")

        # First call triggers 429 and sets _quota_exhausted
        resp1 = provider.generate(messages=[msg])

        self.assertEqual(resp1.finish_reason, "error")
        self.assertEqual(
            resp1.raw_response.get("error"),
            "Gemini API quota has been exhausted for this project. No additional model requests were attempted."
        )
        self.assertTrue(provider._quota_exhausted)
        self.assertEqual(mock_client.models.generate_content.call_count, 1)

        # Second call MUST NOT invoke generate_content (circuit breaker active!)
        resp2 = provider.generate(messages=[msg])

        self.assertEqual(resp2.finish_reason, "error")
        self.assertEqual(
            resp2.raw_response.get("error"),
            "Gemini API quota has been exhausted for this project. No additional model requests were attempted."
        )
        # Call count MUST remain 1!
        self.assertEqual(mock_client.models.generate_content.call_count, 1)

    @patch("time.sleep", return_value=None)
    @patch("google.genai.Client")
    def test_transient_rate_limit_retry(self, mock_client_cls, mock_sleep):
        """Verify transient rate limit retries once respecting retry delay."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        err_msg = "429 RESOURCE_EXHAUSTED: Rate limit exceeded. Retry after 2 seconds."
        success_response = MagicMock()
        success_response.text = "Analysis completed."
        success_response.function_calls = None

        # First call fails with transient 429, second call succeeds
        mock_client.models.generate_content.side_effect = [
            DummyGoogleAPIError(err_msg, code=429),
            success_response
        ]

        provider = GeminiLLMProvider(api_key="mock_api_key_123", model_name="gemini-3.6-flash")
        msg = LLMMessage(role="user", content="Test prompt")

        resp = provider.generate(messages=[msg])

        self.assertEqual(resp.finish_reason, "stop")
        self.assertEqual(resp.content, "Analysis completed.")
        mock_sleep.assert_called_once_with(2.0)
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    @patch("google.genai.Client")
    def test_concise_error_returned_to_orchestrator(self, mock_client_cls):
        """Verify AgentOrchestrator returns concise error message without raw RPC dump."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        err_msg = "429 RESOURCE_EXHAUSTED: free_tier_requests daily limit 20 exceeded"
        mock_client.models.generate_content.side_effect = DummyGoogleAPIError(err_msg, code=429)

        provider = GeminiLLMProvider(api_key="mock_api_key_123", model_name="gemini-3.6-flash")
        orchestrator = AgentOrchestrator(llm_provider=provider)

        res = orchestrator.agentic_query(user_query="Summarize project QC")

        self.assertFalse(res.success)
        self.assertEqual(res.operation, "AGENTIC_QUERY")
        self.assertIn("Gemini API quota has been exhausted for this project", res.message)
        self.assertNotIn("generativelanguage.googleapis.com", res.message)
        self.assertNotIn("RESOURCE_EXHAUSTED:", res.message)

    def test_production_provider_default_resolution(self):
        """Verify default production provider resolves to GeminiLLMProvider with gemini-3.6-flash."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key_123"}):
            with patch("google.genai.Client"):
                orchestrator = AgentOrchestrator()
                self.assertIsInstance(orchestrator.provider, GeminiLLMProvider)
                self.assertEqual(orchestrator.provider.model_name, "gemini-3.6-flash")


if __name__ == "__main__":
    unittest.main()
