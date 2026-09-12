"""
Unit tests for wrapped scientific tools (DESeq2Tool, LiteratureTool) and ToolRegistry.
"""

import pytest
from agent.tools.deseq2_tool import DESeq2Tool, DESeq2ToolArgs
from agent.tools.literature_tool import LiteratureTool, LiteratureToolArgs
from agent.tools.registry import ToolRegistry
from agent.rag.literature_engine import LiteratureRAGEngine


def test_deseq2_tool_argument_validation():
    """Test DESeq2Tool input argument validation."""
    tool = DESeq2Tool()

    # Invalid FDR > 1.0
    res = tool.run({"dataset_id": "OSD-678", "fdr_cutoff": 1.5})
    assert res.status == "error"
    assert res.error.error_type == "ArgumentValidationError"

    # Invalid LFC < 0
    res2 = tool.run({"dataset_id": "OSD-678", "lfc_cutoff": -0.5})
    assert res2.status == "error"
    assert res2.error.error_type == "ArgumentValidationError"


def test_literature_tool_wrapping():
    """Test LiteratureTool wrapping around LiteratureRAGEngine."""
    engine = LiteratureRAGEngine()
    tool = LiteratureTool(rag_engine=engine)

    # Topic search
    res = tool.run({"topic": "circadian"})
    assert res.status == "success"
    assert res.tool_name == "search_literature"
    assert "snippets" in res.result
    assert res.result["match_count"] >= 1
    assert len(res.result["snippets"]) == res.result["match_count"]

    # Gene search
    res_gene = tool.run({"gene_id": "CRY1"})
    assert res_gene.status == "success"
    assert res_gene.result["match_count"] >= 1


def test_tool_registry():
    """Test ToolRegistry registration, lookup, and schema export."""
    registry = ToolRegistry()
    deseq_tool = DESeq2Tool()
    lit_tool = LiteratureTool()

    registry.register(deseq_tool)
    registry.register(lit_tool)

    assert len(registry.list_tools()) == 2
    assert registry.get("run_differential_expression") is deseq_tool
    assert registry.get("search_literature") is lit_tool

    schemas = registry.get_tool_schemas()
    assert len(schemas) == 2
    tool_names = [s["name"] for s in schemas]
    assert "run_differential_expression" in tool_names
    assert "search_literature" in tool_names


def test_duplicate_registration_rejected():
    """Test registering duplicate tool name raises ValueError."""
    registry = ToolRegistry()
    deseq_tool = DESeq2Tool()

    registry.register(deseq_tool)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(deseq_tool)
