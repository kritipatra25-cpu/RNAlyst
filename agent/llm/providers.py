"""
LLM Provider Implementations for AI Agent Platform.

Includes GeminiLLMProvider (live Google Gemini API) and MockLLMProvider (offline unit tests).
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from agent.llm.client import BaseLLMProvider, LLMMessage, LLMResponse, ToolCallRequest

logger = logging.getLogger(__name__)


def sanitize_gemini_schema(schema: Any) -> Any:
    """
    Recursively sanitize JSON schema dictionary to be strictly compatible
    with Gemini FunctionDeclaration parameter schema.

    - Simplifies anyOf/oneOf/allOf (e.g. Optional[T] represented as anyOf with null)
    - Removes unsupported keys: additionalProperties, additional_properties, title,
      default, status, $defs, definitions, $schema, prefixItems, unevaluatedProperties.
    - Preserves type, description, properties, required, items, enum, nullable.
    """
    if not isinstance(schema, dict):
        return schema

    s = dict(schema)

    # 1. Expand anyOf / oneOf / allOf (e.g., Optional[T] or Union)
    for combinator in ("anyOf", "oneOf", "allOf"):
        if combinator in s:
            options = s.pop(combinator)
            if isinstance(options, list) and options:
                non_null_options = [
                    opt for opt in options
                    if isinstance(opt, dict) and opt.get("type") != "null"
                ]
                if non_null_options:
                    chosen = sanitize_gemini_schema(non_null_options[0])
                    for k, v in chosen.items():
                        if k not in s:
                            s[k] = v
                s["nullable"] = True

    # 2. Clean properties map
    if "properties" in s and isinstance(s["properties"], dict):
        clean_props = {}
        for prop_name, prop_schema in s["properties"].items():
            clean_props[prop_name] = sanitize_gemini_schema(prop_schema)
        s["properties"] = clean_props

    # 3. Clean items if array
    if "items" in s and isinstance(s["items"], dict):
        s["items"] = sanitize_gemini_schema(s["items"])

    allowed_schema_keys = {
        "type",
        "description",
        "properties",
        "required",
        "items",
        "enum",
        "nullable",
        "format"
    }

    disallowed_schema_keys = {
        "title",
        "default",
        "additionalProperties",
        "additional_properties",
        "status",
        "$defs",
        "definitions",
        "$schema",
        "prefixItems",
        "unevaluatedProperties"
    }

    cleaned = {}
    for k, v in s.items():
        if k in disallowed_schema_keys:
            continue
        if k in allowed_schema_keys:
            cleaned[k] = v

    if "required" in cleaned:
        if isinstance(cleaned["required"], list):
            cleaned["required"] = [str(r) for r in cleaned["required"]]
        else:
            cleaned.pop("required", None)

    return cleaned


def parse_gemini_error(e: Exception) -> Tuple[str, str, Optional[float]]:
    """
    Parse a Gemini API exception to categorize it, extract retry timing if applicable,
    and format a concise, clean error message.

    Returns:
        (category, concise_message, retry_delay_seconds)
        category can be: "quota_exhausted", "transient_rate_limit", or "api_error"
    """
    import re
    err_str = str(e)
    err_type = type(e).__name__

    # Parse retry delay from error message or exception attributes
    retry_delay = None
    retry_match = re.search(r"retry[_\s]*delay[^\d]*(\d+(?:\.\d+)?)", err_str, re.IGNORECASE) or \
                  re.search(r"retry[_\s]*after[^\d]*(\d+(?:\.\d+)?)", err_str, re.IGNORECASE) or \
                  re.search(r"seconds:\s*(\d+(?:\.\d+)?)", err_str, re.IGNORECASE)
    if retry_match:
        try:
            retry_delay = float(retry_match.group(1))
        except ValueError:
            pass

    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    is_429 = code == 429 or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "ResourceExhausted" in err_type

    if is_429:
        is_daily_quota = any(
            k in err_str.lower() for k in [
                "free_tier_requests",
                "quota exceeded",
                "quota_exhausted",
                "daily quota",
                "per-day",
                "per day",
                "free tier limit",
                "generate_content_free_tier_requests"
            ]
        )

        if is_daily_quota or ("resource_exhausted" in err_str.lower() and not retry_delay):
            msg = "Gemini API quota has been exhausted for this project. No additional model requests were attempted."
            return "quota_exhausted", msg, None
        else:
            delay_info = f" Please retry after {int(retry_delay)} seconds." if retry_delay else ""
            msg = f"Gemini API rate limit reached.{delay_info}"
            return "transient_rate_limit", msg, retry_delay

    # Generic or other API errors
    clean_msg = err_str.split("\n")[0]
    if len(clean_msg) > 150:
        clean_msg = clean_msg[:150] + "..."
    return "api_error", f"Gemini API error ({err_type}): {clean_msg}", None


class ConfigurationError(RuntimeError):
    """Raised when provider configuration or environment variables are missing."""
    pass


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini LLM Provider integration using modern google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3.6-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY is not set. Please set GEMINI_API_KEY in environment or configuration."
            )
        self.model_name = model_name
        self._quota_exhausted = False

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise ConfigurationError("google-genai package is not installed.")

    def generate(
        self,
        messages: List[LLMMessage],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
        retry_attempted: bool = False
    ) -> LLMResponse:
        """Call Gemini API via google-genai SDK with prompt messages and tool schemas."""
        if self._quota_exhausted:
            logger.warning("Prevented Gemini API call: Quota already exhausted.")
            return LLMResponse(
                content=None,
                tool_calls=[],
                finish_reason="error",
                raw_response={"error": "Gemini API quota has been exhausted for this project. No additional model requests were attempted."}
            )

        try:
            from google.genai import types

            config = None
            if tools_schema:
                fn_decls = []
                for schema in tools_schema:
                    raw_params = schema.get("parameters")
                    clean_params = sanitize_gemini_schema(raw_params) if raw_params else None
                    fn_decl = types.FunctionDeclaration(
                        name=schema["name"],
                        description=schema.get("description", ""),
                        parameters=clean_params
                    )
                    fn_decls.append(fn_decl)
                tools = [types.Tool(function_declarations=fn_decls)]
                config = types.GenerateContentConfig(tools=tools)

            contents = []
            for msg in messages:
                role = "model" if msg.role in ("assistant", "model") else "user"
                if msg.content:
                    contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))

            if not contents:
                contents = [types.Content(role="user", parts=[types.Part.from_text(text="Analyze input.")])]

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )

            tool_calls = []
            if getattr(response, "function_calls", None):
                for fc in response.function_calls:
                    args_dict = fc.args if isinstance(fc.args, dict) else dict(fc.args) if fc.args else {}
                    tool_calls.append(ToolCallRequest(
                        tool_name=fc.name,
                        arguments=args_dict
                    ))

            content_text = getattr(response, "text", None)
            if content_text is None and not tool_calls:
                content_text = str(response)

            finish_reason = "tool_calls" if tool_calls else "stop"

            return LLMResponse(
                content=content_text,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                raw_response=response
            )
        except Exception as e:
            category, concise_msg, retry_delay = parse_gemini_error(e)
            if category == "quota_exhausted":
                self._quota_exhausted = True
                logger.error("Gemini API daily/project quota exhausted: %s", concise_msg)
                return LLMResponse(
                    content=None,
                    tool_calls=[],
                    finish_reason="error",
                    raw_response={"error": concise_msg}
                )
            elif category == "transient_rate_limit":
                if retry_delay and retry_delay <= 10.0 and not retry_attempted:
                    logger.warning("Transient Gemini 429 rate limit. Retrying after %s seconds...", retry_delay)
                    import time
                    time.sleep(retry_delay)
                    return self.generate(messages, tools_schema, retry_attempted=True)
                logger.error("Gemini API transient rate limit: %s", concise_msg)
                return LLMResponse(
                    content=None,
                    tool_calls=[],
                    finish_reason="error",
                    raw_response={"error": concise_msg}
                )
            else:
                logger.error("Gemini API error: %s", concise_msg)
                return LLMResponse(
                    content=None,
                    tool_calls=[],
                    finish_reason="error",
                    raw_response={"error": concise_msg}
                )


class UnavailableLLMProvider(BaseLLMProvider):
    """Explicit error provider used when Gemini API key or SDK is missing."""

    def __init__(self, error_message: str):
        self.error_message = error_message

    def generate(
        self,
        messages: List[LLMMessage],
        tools_schema: Optional[List[Dict[str, Any]]] = None
    ) -> LLMResponse:
        return LLMResponse(
            content=None,
            tool_calls=[],
            finish_reason="error",
            raw_response={"error": self.error_message}
        )


class MockLLMProvider(BaseLLMProvider):
    """Deterministic Mock LLM Provider for offline unit tests."""

    def __init__(self, canned_responses: Optional[List[LLMResponse]] = None):
        self.canned_responses = canned_responses or []
        self.call_history: List[Dict[str, Any]] = []

    def queue_response(self, response: LLMResponse) -> None:
        """Queue a canned response to be returned by subsequent generate() calls."""
        self.canned_responses.append(response)

    def generate(
        self,
        messages: List[LLMMessage],
        tools_schema: Optional[List[Dict[str, Any]]] = None
    ) -> LLMResponse:
        """Record input and return next queued canned response or a fallback mock response."""
        self.call_history.append({
            "messages": messages,
            "tools_schema": tools_schema
        })

        if self.canned_responses:
            return self.canned_responses.pop(0)

        # Fallback default mock response
        return LLMResponse(
            content="Mock assistant response.",
            tool_calls=[],
            finish_reason="stop"
        )


def sanitize_openai_schema(schema: Any) -> Any:
    """
    Sanitize JSON schema dictionary for OpenAI / Groq tool function parameter definitions.
    """
    if not isinstance(schema, dict):
        return schema

    s = dict(schema)

    # Expand anyOf / oneOf / allOf
    for combinator in ("anyOf", "oneOf", "allOf"):
        if combinator in s:
            options = s.pop(combinator)
            if isinstance(options, list) and options:
                non_null_options = [
                    opt for opt in options
                    if isinstance(opt, dict) and opt.get("type") != "null"
                ]
                if non_null_options:
                    chosen = sanitize_openai_schema(non_null_options[0])
                    for k, v in chosen.items():
                        if k not in s:
                            s[k] = v

    if "properties" in s and isinstance(s["properties"], dict):
        clean_props = {}
        for prop_name, prop_schema in s["properties"].items():
            clean_props[prop_name] = sanitize_openai_schema(prop_schema)
        s["properties"] = clean_props

    if "items" in s and isinstance(s["items"], dict):
        s["items"] = sanitize_openai_schema(s["items"])

    disallowed_keys = {
        "title",
        "default",
        "additionalProperties",
        "additional_properties",
        "$defs",
        "definitions",
        "$schema",
        "prefixItems",
        "unevaluatedProperties"
    }
    cleaned = {k: v for k, v in s.items() if k not in disallowed_keys}

    if "type" not in cleaned and "properties" in cleaned:
        cleaned["type"] = "object"

    return cleaned


class GroqLLMProvider(BaseLLMProvider):
    """
    LLM Provider integration for Groq API using OpenAI-compatible REST endpoint.
    Supports chat completion, system/user/assistant turns, and tool-calling function execution.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ConfigurationError(
                "GROQ_API_KEY is not set. Please set GROQ_API_KEY in environment or configuration."
            )
        resolved_model = model_name
        if not resolved_model or resolved_model.lower().startswith("gemini"):
            resolved_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.model_name = resolved_model
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def generate(
        self,
        messages: List[LLMMessage],
        tools_schema: Optional[List[Dict[str, Any]]] = None
    ) -> LLMResponse:
        """Call Groq OpenAI-compatible chat API with messages and tools."""
        import json
        import urllib.request
        import urllib.error

        # Format OpenAI-compatible tools
        tools_payload = None
        if tools_schema:
            tools_payload = []
            for schema in tools_schema:
                raw_params = schema.get("parameters")
                clean_params = sanitize_openai_schema(raw_params) if raw_params else {"type": "object", "properties": {}}
                tools_payload.append({
                    "type": "function",
                    "function": {
                        "name": schema["name"],
                        "description": schema.get("description", ""),
                        "parameters": clean_params
                    }
                })

        # Format OpenAI-compatible messages
        formatted_messages = []
        for msg in messages:
            content = msg.content or ""
            if len(content) > 3500:
                content = content[:3500] + "\n...[truncated for token limit]..."

            if msg.role == "tool":
                formatted_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id or "call_default",
                    "content": content or "{}"
                })
            elif msg.role in ("assistant", "model"):
                asst_msg = {"role": "assistant"}
                if content:
                    asst_msg["content"] = content
                if msg.tool_calls:
                    asst_msg["tool_calls"] = [
                        {
                            "id": tc.call_id,
                            "type": "function",
                            "function": {
                                "name": tc.tool_name,
                                "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else str(tc.arguments)
                            }
                        } for tc in msg.tool_calls
                    ]
                formatted_messages.append(asst_msg)
            else:
                role = "system" if msg.role == "system" else "user"
                formatted_messages.append({
                    "role": role,
                    "content": content
                })


        if not formatted_messages:
            formatted_messages = [{"role": "user", "content": "Analyze input."}]

        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "temperature": 0.1
        }
        if tools_payload:
            payload["tools"] = tools_payload

        req_body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "RNAlyst-AI-Agent/1.0"
        }

        req = urllib.request.Request(self.api_url, data=req_body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))

            choices = resp_data.get("choices", [])
            if not choices:
                return LLMResponse(
                    content=None,
                    tool_calls=[],
                    finish_reason="error",
                    raw_response={"error": "Groq API returned an empty choices list."}
                )

            choice = choices[0]
            msg_obj = choice.get("message", {})
            content_text = msg_obj.get("content")

            tool_calls = []
            if msg_obj.get("tool_calls"):
                for tc in msg_obj["tool_calls"]:
                    func = tc.get("function", {})
                    t_name = func.get("name", "")
                    raw_args = func.get("arguments", "{}")
                    try:
                        args_dict = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args_dict = {}
                    call_id = tc.get("id") or f"call_{t_name}"
                    tool_calls.append(ToolCallRequest(
                        call_id=call_id,
                        tool_name=t_name,
                        arguments=args_dict
                    ))

            finish_reason = "tool_calls" if tool_calls else choice.get("finish_reason", "stop")

            return LLMResponse(
                content=content_text,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                raw_response=resp_data
            )

        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                err_msg = err_body.get("error", {}).get("message") or str(err_body)
            except Exception:
                err_msg = str(e)
            logger.error("Groq API HTTP error (%s): %s", e.code, err_msg)
            return LLMResponse(
                content=None,
                tool_calls=[],
                finish_reason="error",
                raw_response={"error": f"Groq API HTTP error ({e.code}): {err_msg}"}
            )
        except Exception as e:
            logger.error("Groq API unexpected error: %s", e)
            return LLMResponse(
                content=None,
                tool_calls=[],
                finish_reason="error",
                raw_response={"error": f"Groq API error: {str(e)}"}
            )
