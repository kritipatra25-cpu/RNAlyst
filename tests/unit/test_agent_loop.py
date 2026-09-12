"""
Unit tests for Step 4 Iterative Agentic Tool-Calling Loop in AgentOrchestrator.
All tests use deterministic MockLLMProvider and in-memory tools (zero API/RNA-seq calls).
"""

import pytest
from typing import List
from agent.orchestrator.agent_runner import AgentOrchestrator, AgentResponse
from agent.tools.registry import ToolRegistry
from agent.tools.deseq2_tool import DESeq2Tool
from agent.tools.literature_tool import LiteratureTool
from agent.llm.providers import MockLLMProvider
from agent.llm.client import LLMResponse, ToolCallRequest, LLMMessage


def build_orchestrator(canned_responses: List[LLMResponse]) -> AgentOrchestrator:
    """Helper constructing AgentOrchestrator with MockLLMProvider."""
    provider = MockLLMProvider(canned_responses=canned_responses)
    registry = ToolRegistry()
    registry.register(LiteratureTool())
    registry.register(DESeq2Tool())
    return AgentOrchestrator(llm_provider=provider, tool_registry=registry)


def test_1_no_tool_required():
    """Test 1: User query handled without tool calls."""
    mock_resp = LLMResponse(content="The capital of space plant biology is TAIR.", tool_calls=[], finish_reason="stop")
    orchestrator = build_orchestrator([mock_resp])

    res = orchestrator.agentic_query("General biology question")

    assert res.success is True
    assert res.message == "The capital of space plant biology is TAIR."
    assert res.iterations_count == 1
    assert len(res.tool_results) == 0


def test_2_single_tool_call():
    """Test 2: Single tool call (search_literature) requested by LLM, executed, and synthesized."""
    call = ToolCallRequest(tool_name="search_literature", arguments={"topic": "circadian"})
    step1_resp = LLMResponse(content=None, tool_calls=[call], finish_reason="tool_calls")
    step2_resp = LLMResponse(content="Circadian rhythm genes CRY1 and HYH were identified in literature.", tool_calls=[], finish_reason="stop")

    orchestrator = build_orchestrator([step1_resp, step2_resp])
    res = orchestrator.agentic_query("Find circadian literature")

    assert res.success is True
    assert res.iterations_count == 2
    assert len(res.tool_results) == 1
    assert res.tool_results[0].tool_name == "search_literature"
    assert res.tool_results[0].status == "success"
    assert "CRY1 and HYH" in res.message


def test_3_multi_step_tool_calling():
    """Test 3: Multi-step tool calling (Tool A -> Result A -> Tool B -> Result B -> Final Synthesis)."""
    call1 = ToolCallRequest(tool_name="search_literature", arguments={"gene_id": "CRY1"})
    step1_resp = LLMResponse(content=None, tool_calls=[call1], finish_reason="tool_calls")

    call2 = ToolCallRequest(tool_name="search_literature", arguments={"gene_id": "HYH"})
    step2_resp = LLMResponse(content=None, tool_calls=[call2], finish_reason="tool_calls")

    step3_resp = LLMResponse(content="Integrated multi-gene literature synthesis for CRY1 and HYH.", tool_calls=[], finish_reason="stop")

    orchestrator = build_orchestrator([step1_resp, step2_resp, step3_resp])
    res = orchestrator.agentic_query("Analyze CRY1 and HYH literature")

    assert res.success is True
    assert res.iterations_count == 3
    assert len(res.tool_results) == 2
    assert res.tool_results[0].result["snippets"][0]["symbol"] == "CRY1"
    assert res.tool_results[1].result["snippets"][0]["symbol"] == "HYH"
    assert "Integrated multi-gene" in res.message


def test_4_unknown_tool_rejection():
    """Test 4: LLM requests unknown tool -> dispatcher returns UnknownToolError -> loop handles safely."""
    call_unknown = ToolCallRequest(tool_name="nonexistent_kegg_tool", arguments={})
    step1_resp = LLMResponse(content=None, tool_calls=[call_unknown], finish_reason="tool_calls")
    step2_resp = LLMResponse(content="Sorry, KEGG pathway tool is unavailable.", tool_calls=[], finish_reason="stop")

    orchestrator = build_orchestrator([step1_resp, step2_resp])
    res = orchestrator.agentic_query("Run KEGG pathway")

    assert res.success is True
    assert len(res.tool_results) == 1
    assert res.tool_results[0].status == "error"
    assert res.tool_results[0].error.error_type == "UnknownToolError"
    assert "Sorry, KEGG pathway tool is unavailable." in res.message


def test_5_invalid_arguments_rejected():
    """Test 5: LLM requests valid tool with malformed args -> ArgumentValidationError returned -> loop handles safely."""
    call_bad_args = ToolCallRequest(tool_name="run_differential_expression", arguments={"dataset_id": "OSD-678", "fdr_cutoff": 2.5})
    step1_resp = LLMResponse(content=None, tool_calls=[call_bad_args], finish_reason="tool_calls")
    step2_resp = LLMResponse(content="fdr_cutoff must be between 0.0 and 1.0.", tool_calls=[], finish_reason="stop")

    orchestrator = build_orchestrator([step1_resp, step2_resp])
    res = orchestrator.agentic_query("Run DE with fdr 2.5")

    assert res.success is True
    assert len(res.tool_results) == 1
    assert res.tool_results[0].status == "error"
    assert res.tool_results[0].error.error_type == "ArgumentValidationError"


def test_6_tool_failure_handling():
    """Test 6: Tool failure returned cleanly as ToolResult error."""
    call_fail = ToolCallRequest(tool_name="run_differential_expression", arguments={"dataset_id": "NON_EXISTENT_DATASET"})
    step1_resp = LLMResponse(content=None, tool_calls=[call_fail], finish_reason="tool_calls")
    step2_resp = LLMResponse(content="Dataset NON_EXISTENT_DATASET could not be loaded.", tool_calls=[], finish_reason="stop")

    orchestrator = build_orchestrator([step1_resp, step2_resp])
    res = orchestrator.agentic_query("Analyze INVALID_DS")

    assert res.success is True
    assert res.tool_results[0].status == "error"
    assert "could not be loaded" in res.message


def test_7_maximum_iteration_limit():
    """Test 7: Continuous tool calls hit max_iterations limit and terminate safely without infinite loop."""
    call_infinite = ToolCallRequest(tool_name="search_literature", arguments={"topic": "space"})
    repeat_resp = LLMResponse(content=None, tool_calls=[call_infinite], finish_reason="tool_calls")

    # Queue 5 repeating tool calls
    orchestrator = build_orchestrator([repeat_resp] * 5)
    res = orchestrator.agentic_query("Query causing infinite tools", max_iterations=3)

    assert res.success is False
    assert res.iterations_count == 3
    assert "maximum iteration limit" in res.message
    assert res.error_result.error_type == "MaxIterationsReachedError"


def test_8_conversation_continuity():
    """Test 8: Sequential turns retain session context across queries."""
    resp1 = LLMResponse(content="OSD-678 has 5 contrasts.", tool_calls=[], finish_reason="stop")
    resp2 = LLMResponse(content="Focusing on Light vs Ground contrast.", tool_calls=[], finish_reason="stop")

    orchestrator = build_orchestrator([resp1, resp2])
    session = orchestrator.conversational_manager.create_session()

    res1 = orchestrator.agentic_query("What contrasts in OSD-678?", session_id=session.session_id)
    assert res1.success is True

    res2 = orchestrator.agentic_query("Tell me more about the first one", session_id=session.session_id)
    assert res2.success is True
    assert len(session.turns) == 2
    assert session.turns[0].user_query == "What contrasts in OSD-678?"
    assert session.turns[1].user_query == "Tell me more about the first one"


def test_9_no_arbitrary_execution():
    """Test 9: Malicious tool call names/arguments cannot evaluate Python or shell code."""
    malicious_call = ToolCallRequest(
        tool_name="import os; os.system('echo hacked')",
        arguments={"eval": "exec('import sys; sys.exit()')"}
    )
    step1_resp = LLMResponse(content=None, tool_calls=[malicious_call], finish_reason="tool_calls")
    step2_resp = LLMResponse(content="Tool execution rejected.", tool_calls=[], finish_reason="stop")

    orchestrator = build_orchestrator([step1_resp, step2_resp])
    res = orchestrator.agentic_query("Attempt RCE")

    assert res.success is True
    assert len(res.tool_results) == 1
    assert res.tool_results[0].status == "error"
    assert res.tool_results[0].error.error_type == "UnknownToolError"
