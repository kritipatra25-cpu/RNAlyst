"""
Unit tests for provider-agnostic LLM tool-calling client, ToolCallDispatcher, and providers.
"""

import pytest
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from agent.tools.base_tool import BaseTool, ToolResult
from agent.tools.registry import ToolRegistry
from agent.tools.deseq2_tool import DESeq2Tool
from agent.tools.literature_tool import LiteratureTool
from agent.llm.client import LLMMessage, ToolCallRequest, LLMResponse, LLMClient
from agent.llm.dispatcher import ToolCallDispatcher
from agent.llm.providers import MockLLMProvider, GeminiLLMProvider, ConfigurationError


class DummyArgsSchema(BaseModel):
    query_str: str = Field(..., min_length=2)


class DummyTool(BaseTool):
    name = "dummy_tool"
    description = "Dummy tool for testing dispatcher safety"
    arguments_schema = DummyArgsSchema

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        return ToolResult.success_result(
            tool_name=self.name,
            result={"echo": arguments["query_str"]}
        )


def test_tool_schemas_exported():
    """Test 1: Tool schemas are correctly exported from ToolRegistry for LLM Client."""
    registry = ToolRegistry()
    registry.register(DESeq2Tool())
    registry.register(LiteratureTool())

    client = LLMClient(provider=MockLLMProvider(), tool_registry=registry)
    schemas = registry.get_tool_schemas()

    assert len(schemas) == 2
    names = [s["name"] for s in schemas]
    assert "run_differential_expression" in names
    assert "search_literature" in names


def test_valid_tool_call_representation():
    """Test 2: Structured ToolCallRequest representation."""
    call = ToolCallRequest(tool_name="search_literature", arguments={"topic": "circadian"})
    assert call.tool_name == "search_literature"
    assert call.arguments["topic"] == "circadian"
    assert call.call_id.startswith("call_")


def test_unknown_tool_rejection():
    """Test 3: Dispatcher safely rejects unknown tools without crashing."""
    registry = ToolRegistry()
    dispatcher = ToolCallDispatcher(registry)

    call = ToolCallRequest(tool_name="unregistered_tool", arguments={})
    res = dispatcher.dispatch(call)

    assert res.status == "error"
    assert res.error.error_type == "UnknownToolError"
    assert "not registered" in res.error.message


def test_invalid_tool_arguments_rejected():
    """Test 4: Dispatcher rejects malformed tool arguments before tool execution."""
    registry = ToolRegistry()
    registry.register(DummyTool())
    dispatcher = ToolCallDispatcher(registry)

    # query_str must be at least 2 chars; 1 char is invalid
    call = ToolCallRequest(tool_name="dummy_tool", arguments={"query_str": "a"})
    res = dispatcher.dispatch(call)

    assert res.status == "error"
    assert res.error.error_type == "ArgumentValidationError"


def test_tool_result_conversion_for_llm():
    """Test 5: ToolResult conversion into LLMMessage for multi-turn LLM context."""
    tool_res = ToolResult.success_result(tool_name="dummy_tool", result={"genes": ["CRY1"]})
    msg = LLMMessage(
        role="tool",
        content=tool_res.model_dump_json(),
        tool_call_id="call_12345"
    )

    assert msg.role == "tool"
    assert msg.tool_call_id == "call_12345"
    assert "CRY1" in msg.content


def test_provider_abstraction_and_configuration():
    """Test 6: GeminiLLMProvider raises ConfigurationError if GEMINI_API_KEY missing."""
    # Test Mock Provider
    mock_provider = MockLLMProvider()
    client = LLMClient(provider=mock_provider)
    resp = client.generate([LLMMessage(role="user", content="Hello")])

    assert resp.content == "Mock assistant response."
    assert len(mock_provider.call_history) == 1

    # Test Gemini Provider missing API Key
    with pytest.raises(ConfigurationError, match="GEMINI_API_KEY is not set"):
        GeminiLLMProvider(api_key="")


def test_no_arbitrary_code_execution():
    """Test 7: Confirm tool call dispatcher only resolves registered tools and never evaluates code."""
    registry = ToolRegistry()
    registry.register(DummyTool())
    dispatcher = ToolCallDispatcher(registry)

    # Malicious eval attempt passed as tool name/arguments
    malicious_call = ToolCallRequest(
        tool_name="__import__('os').system('echo hacked')",
        arguments={"code": "import sys; sys.exit(1)"}
    )

    res = dispatcher.dispatch(malicious_call)

    assert res.status == "error"
    assert res.error.error_type == "UnknownToolError"
