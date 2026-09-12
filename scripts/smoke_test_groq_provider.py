#!/usr/bin/env python3
"""
Lightweight Manual Smoke Test Script for Groq LLM Provider Integration.

Usage:
  export GROQ_API_KEY="your_groq_api_key_here"
  export LLM_PROVIDER="groq"
  export GROQ_MODEL="openai/gpt-oss-120b"
  python3 scripts/smoke_test_groq_provider.py

This script performs ONLY a lightweight API & tool-calling contract check.
It does NOT execute expensive RNA-seq pipeline computations or modified scientific code.
"""

import os
import sys

# Ensure repository root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.llm.client import LLMMessage
from agent.llm.factory import get_llm_provider
from agent.tools.registry import ToolRegistry
from agent.tools.base_tool import BaseTool, ToolResult


class DummyEchoTool(BaseTool):
    name = "echo_test_tool"
    description = "A lightweight test tool for verifying LLM tool-calling schema formatting."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Test query parameter"}
        },
        "required": ["query"]
    }

    def _execute(self, query: str) -> ToolResult:
        return ToolResult.success_result(
            tool_name=self.name,
            result={"echo": query},
            summary=f"Successfully echoed parameter: {query}"
        )


def main():
    print("==================================================")
    print("  RNAlyst Groq LLM Provider Manual Smoke Test")
    print("==================================================")

    provider_env = os.getenv("LLM_PROVIDER", "gemini")
    groq_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    print(f"LLM_PROVIDER: {provider_env}")
    print(f"GROQ_MODEL: {groq_model}")
    print(f"GROQ_API_KEY set: {'YES' if groq_key else 'NO'}")

    if not groq_key:
        print("\nERROR: GROQ_API_KEY is not set in environment.")
        print("Please set GROQ_API_KEY before running this smoke test.")
        sys.exit(1)

    print("\n1. Initializing Provider via Factory...")
    provider = get_llm_provider(provider_name=provider_env, model_name=groq_model)
    print(f"Initialized provider instance: {type(provider).__name__}")

    print("\n2. Setting up Dummy Tool Schema...")
    registry = ToolRegistry()
    registry.register(DummyEchoTool())
    schemas = registry.get_tool_schemas()

    print("\n3. Dispatching minimal test query to Groq...")
    messages = [LLMMessage(role="user", content="Call the echo_test_tool tool with query='RNAlyst_Smoke_Test'.")]

    try:
        response = provider.generate(messages=messages, tools_schema=schemas)
        print(f"Response finish_reason: {response.finish_reason}")
        print(f"Has tool calls: {response.has_tool_calls}")
        if response.content:
            print(f"Assistant Content: {response.content}")

        if response.has_tool_calls:
            print("Tool Calls Requested:")
            for tc in response.tool_calls:
                print(f"  - Tool: {tc.tool_name}, Arguments: {tc.arguments}")

        if response.finish_reason == "error":
            print(f"Provider Error: {response.raw_response.get('error') if isinstance(response.raw_response, dict) else response.raw_response}")
            sys.exit(1)

        print("\nSUCCESS: Groq provider smoke test completed successfully!")

    except Exception as e:
        print(f"\nFAILED: Smoke test threw an unexpected exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
