"""
Unit tests for generic BaseTool and ToolResult contracts.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from agent.tools.base_tool import BaseTool, ToolResult, ToolArtifact


class DummyArgsSchema(BaseModel):
    dataset_id: str = Field(..., min_length=3)
    cutoff: float = Field(0.05, gt=0.0, lt=1.0)


class DummyTestTool(BaseTool):
    name = "dummy_test_tool"
    description = "Test tool for validating BaseTool execution contract"
    arguments_schema = DummyArgsSchema

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        if arguments.get("trigger_error"):
            raise ValueError("Simulated computation failure")

        return ToolResult.success_result(
            tool_name=self.name,
            result={"status_message": f"Processed dataset {arguments['dataset_id']}"},
            artifacts=[
                ToolArtifact(
                    artifact_type="csv",
                    path="/tmp/output.csv",
                    description="Dummy output CSV"
                )
            ],
            provenance={"dataset_id": arguments["dataset_id"]}
        )


def test_valid_tool_execution():
    """Test 1: Valid tool result generated successfully."""
    tool = DummyTestTool()
    res = tool.run({"dataset_id": "OSD-678", "cutoff": 0.01})

    assert res.status == "success"
    assert res.tool_name == "dummy_test_tool"
    assert res.error is None
    assert res.result["status_message"] == "Processed dataset OSD-678"
    assert len(res.artifacts) == 1
    assert res.artifacts[0].artifact_type == "csv"
    assert res.provenance["dataset_id"] == "OSD-678"


def test_error_tool_execution():
    """Test 2: Tool execution exception caught and returned as structured ToolResult error."""
    tool = DummyTestTool()
    res = tool.run({"dataset_id": "OSD-678", "cutoff": 0.05, "trigger_error": True})

    assert res.status == "error"
    assert res.tool_name == "dummy_test_tool"
    assert res.error is not None
    assert res.error.error_type == "ValueError"
    assert "Simulated computation failure" in res.error.message


def test_invalid_arguments_rejected():
    """Test 3: Invalid tool arguments rejected before execution."""
    tool = DummyTestTool()
    # cutoff must be < 1.0; 2.5 is invalid
    res = tool.run({"dataset_id": "OSD-678", "cutoff": 2.5})

    assert res.status == "error"
    assert res.error is not None
    assert res.error.error_type == "ArgumentValidationError"
    assert "Invalid arguments supplied to tool" in res.error.message
    assert len(res.error.details) > 0
