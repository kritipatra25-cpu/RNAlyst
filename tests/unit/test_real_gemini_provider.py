"""
Focused Unit & Integration Test for GeminiLLMProvider using google-genai SDK.
"""

import os
import unittest
from agent.llm.providers import GeminiLLMProvider
from agent.llm.client import LLMMessage


class TestRealGeminiProvider(unittest.TestCase):
    """Test suite for GeminiLLMProvider using google-genai SDK."""

    def test_gemini_provider_real_api_call(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.skipTest("GEMINI_API_KEY environment variable is not set")

        provider = GeminiLLMProvider(api_key=api_key)
        self.assertEqual(provider.model_name, "gemini-3.6-flash")

        messages = [
            LLMMessage(role="user", content="Reply with EXACTLY the text: GEMINI_READY")
        ]

        response = provider.generate(messages=messages)

        self.assertIsNotNone(response)
        self.assertEqual(response.finish_reason, "stop")
        self.assertIsNotNone(response.content)
        self.assertIn("GEMINI_READY", response.content)
        # Ensure API key is never in raw text
        self.assertNotIn(api_key, str(response.content))
        self.assertNotIn(api_key, str(response.raw_response))


if __name__ == "__main__":
    unittest.main()
