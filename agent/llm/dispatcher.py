"""
Tool Call Dispatcher for AI Agent Platform.

Validates and executes ToolCallRequest objects securely using registered BaseTool instances.
Ensures zero arbitrary code execution (no eval/exec/shell execution).
"""

from typing import Dict, List, Any, Optional
from agent.tools.base_tool import BaseTool, ToolResult
from agent.tools.registry import ToolRegistry
from agent.llm.client import ToolCallRequest


class ToolCallDispatcher:
    """Safe dispatcher for resolving and executing LLM tool call requests."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def dispatch(self, tool_call: ToolCallRequest) -> ToolResult:
        """Resolve requested tool, validate arguments, and execute deterministic run()."""
        tool = self.registry.get(tool_call.tool_name)

        if not tool:
            return ToolResult.error_result(
                tool_name=tool_call.tool_name,
                error_type="UnknownToolError",
                message=f"Requested tool '{tool_call.tool_name}' is not registered in ToolRegistry.",
                details=[f"Available tools: {[t.name for t in self.registry.list_tools()]}"]
            )

        # BaseTool.run() internally validates arguments against tool schema before execution
        return tool.run(arguments=tool_call.arguments)

    def dispatch_batch(self, tool_calls: List[ToolCallRequest]) -> List[ToolResult]:
        """Dispatch multiple tool calls in sequence."""
        return [self.dispatch(call) for call in tool_calls]
