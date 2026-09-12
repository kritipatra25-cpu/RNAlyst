"""
Provider-Agnostic LLM Tool-Calling Client & Data Contracts.

Defines typed representations for messages, tool call requests, LLM responses,
and the abstract BaseLLMProvider / LLMClient interfaces.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from agent.tools.registry import ToolRegistry


class ToolCallRequest(BaseModel):
    """Structured representation of a single tool call requested by an LLM."""
    call_id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}", description="Unique call identifier")
    tool_name: str = Field(..., description="Target registered tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Raw arguments passed by LLM")


class LLMMessage(BaseModel):
    """Structured message in a multi-turn LLM conversation."""
    role: str = Field(..., description="Message sender role: 'user', 'assistant', 'system', or 'tool'")
    content: Optional[str] = Field(None, description="Textual content of the message")
    tool_calls: List[ToolCallRequest] = Field(default_factory=list, description="Tool calls requested by assistant turn")
    tool_call_id: Optional[str] = Field(None, description="Target tool call ID if role is 'tool'")


class LLMResponse(BaseModel):
    """Structured response returned by an LLM provider."""
    content: Optional[str] = Field(None, description="Assistant text response if available")
    tool_calls: List[ToolCallRequest] = Field(default_factory=list, description="List of requested tool calls")
    finish_reason: str = Field("stop", description="Completion status: 'stop', 'tool_calls', 'error'")
    raw_response: Optional[Any] = Field(None, description="Raw provider response object if preserved")

    @property
    def has_tool_calls(self) -> bool:
        """Check if assistant requested one or more tool calls."""
        return len(self.tool_calls) > 0


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM Providers (Gemini, OpenAI, Mock, etc.)."""

    @abstractmethod
    def generate(
        self,
        messages: List[LLMMessage],
        tools_schema: Optional[List[Dict[str, Any]]] = None
    ) -> LLMResponse:
        """Generate response from provider given conversation history and available tool schemas."""
        pass


class LLMClient:
    """High-level client connecting LLM Providers with ToolRegistry tool schemas."""

    def __init__(self, provider: BaseLLMProvider, tool_registry: Optional[ToolRegistry] = None):
        self.provider = provider
        self.registry = tool_registry

    def generate(
        self,
        messages: List[LLMMessage],
        include_tools: bool = True
    ) -> LLMResponse:
        """Send messages to provider, automatically supplying registered tool schemas if enabled."""
        tools_schema = None
        if include_tools and self.registry:
            tools_schema = self.registry.get_tool_schemas()

        return self.provider.generate(messages=messages, tools_schema=tools_schema)
