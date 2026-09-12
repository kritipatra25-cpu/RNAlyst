"""
Unit tests for GroqLLMProvider integration, schema conversion, tool call parsing, and factory resolution.
"""

import json
import os
import io
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

from agent.llm.client import LLMMessage, LLMResponse, ToolCallRequest
from agent.llm.providers import GroqLLMProvider, GeminiLLMProvider, UnavailableLLMProvider, ConfigurationError, sanitize_openai_schema
from agent.llm.factory import get_llm_provider
from agent.orchestrator.agent_runner import AgentOrchestrator


class TestGroqLLMProvider(unittest.TestCase):
    """Test suite for GroqLLMProvider."""

    def test_missing_api_key_raises_configuration_error(self):
        """Verify missing GROQ_API_KEY raises ConfigurationError."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                GroqLLMProvider()

    def test_provider_initialization_with_explicit_key_and_model(self):
        """Verify GroqLLMProvider initializes cleanly with explicit API key and model."""
        provider = GroqLLMProvider(api_key="gsk_test_12345", model_name="openai/gpt-oss-120b")
        self.assertEqual(provider.api_key, "gsk_test_12345")
        self.assertEqual(provider.model_name, "openai/gpt-oss-120b")

    def test_sanitize_openai_schema(self):
        """Test sanitization of raw JSON schemas into OpenAI-compatible parameters format."""
        raw_schema = {
            "type": "object",
            "title": "DESeq2Params",
            "additionalProperties": False,
            "properties": {
                "dataset_id": {"type": "string", "description": "Target project ID", "default": "PROJ_1"},
                "fdr_cutoff": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "description": "FDR significance threshold"
                }
            },
            "required": ["dataset_id"]
        }
        sanitized = sanitize_openai_schema(raw_schema)
        self.assertEqual(sanitized["type"], "object")
        self.assertNotIn("title", sanitized)
        self.assertNotIn("additionalProperties", sanitized)
        self.assertNotIn("default", sanitized["properties"]["dataset_id"])
        self.assertEqual(sanitized["properties"]["fdr_cutoff"]["type"], "number")

    @patch("urllib.request.urlopen")
    def test_generate_text_response(self, mock_urlopen):
        """Test generating plain assistant text response from Groq API."""
        mock_response_data = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "The differential expression analysis reveals 42 significant DEGs."
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        provider = GroqLLMProvider(api_key="gsk_mock_key")
        messages = [LLMMessage(role="user", content="Summarize DE results.")]
        res = provider.generate(messages=messages)

        self.assertFalse(res.has_tool_calls)
        self.assertEqual(res.finish_reason, "stop")
        self.assertIn("42 significant DEGs", res.content)

    @patch("urllib.request.urlopen")
    def test_generate_tool_call_response(self, mock_urlopen):
        """Test parsing structured tool calls returned by Groq API."""
        mock_response_data = {
            "id": "chatcmpl-456",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_deseq2_001",
                                "type": "function",
                                "function": {
                                    "name": "run_differential_expression",
                                    "arguments": '{"dataset_id": "PROJ_TEST", "fdr_cutoff": 0.05}'
                                }
                            }
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        provider = GroqLLMProvider(api_key="gsk_mock_key")
        tools = [{"name": "run_differential_expression", "description": "Run DESeq2", "parameters": {}}]
        messages = [LLMMessage(role="user", content="Run DE for PROJ_TEST.")]
        res = provider.generate(messages=messages, tools_schema=tools)

        self.assertTrue(res.has_tool_calls)
        self.assertEqual(len(res.tool_calls), 1)
        self.assertEqual(res.tool_calls[0].tool_name, "run_differential_expression")
        self.assertEqual(res.tool_calls[0].arguments["dataset_id"], "PROJ_TEST")
        self.assertEqual(res.tool_calls[0].arguments["fdr_cutoff"], 0.05)

    @patch("urllib.request.urlopen")
    def test_http_error_handling(self, mock_urlopen):
        """Test handling of HTTP error status code from Groq API (e.g. 401 Unauthorized)."""
        error_content = json.dumps({"error": {"message": "Invalid API Key"}}).encode("utf-8")
        http_err = urllib.error.HTTPError(
            url="https://api.groq.com/openai/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(error_content)
        )
        mock_urlopen.side_effect = http_err

        provider = GroqLLMProvider(api_key="invalid_key")
        messages = [LLMMessage(role="user", content="Hello")]
        res = provider.generate(messages=messages)

        self.assertEqual(res.finish_reason, "error")
        self.assertIn("Invalid API Key", str(res.raw_response.get("error")))

    def test_factory_resolution_groq(self):
        """Test get_llm_provider resolving GroqLLMProvider when LLM_PROVIDER=groq."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "gsk_test"}, clear=True):
            provider = get_llm_provider()
            self.assertIsInstance(provider, GroqLLMProvider)

    def test_factory_resolution_gemini_default(self):
        """Test get_llm_provider resolving GeminiLLMProvider when LLM_PROVIDER=gemini or default."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "test_gemini_key"}, clear=True):
            with patch("agent.llm.providers.GeminiLLMProvider.__init__", return_value=None):
                provider = get_llm_provider()
                self.assertIsInstance(provider, GeminiLLMProvider)

    def test_agent_orchestrator_initializes_with_factory(self):
        """Test AgentOrchestrator resolving provider from factory when not explicitly passed."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "gsk_test"}, clear=True):
            orchestrator = AgentOrchestrator()
            self.assertIsInstance(orchestrator.provider, GroqLLMProvider)
            self.assertEqual(orchestrator.provider.model_name, "openai/gpt-oss-120b")

    def test_groq_provider_rejects_gemini_model_name(self):
        """Regression Test: Verify GroqLLMProvider replaces Gemini model identifier with valid Groq model."""
        provider = GroqLLMProvider(api_key="gsk_test_key", model_name="gemini-3.6-flash")
        self.assertNotEqual(provider.model_name, "gemini-3.6-flash")
        self.assertEqual(provider.model_name, "openai/gpt-oss-120b")

    def test_factory_groq_provider_replaces_gemini_model_name(self):
        """Regression Test: Verify get_llm_provider replaces Gemini model identifier with valid Groq model for groq provider."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "gsk_test"}, clear=True):
            provider = get_llm_provider(model_name="gemini-3.6-flash")
            self.assertIsInstance(provider, GroqLLMProvider)
            self.assertEqual(provider.model_name, "openai/gpt-oss-120b")


if __name__ == "__main__":
    unittest.main()

