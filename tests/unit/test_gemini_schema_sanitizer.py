"""
Unit tests for Gemini schema sanitizer and tool schema compatibility.
"""

import unittest
from typing import Dict, Any, List
from agent.llm.providers import sanitize_gemini_schema
from agent.orchestrator.agent_runner import AgentOrchestrator


def check_disallowed_metadata(obj: Any, path: str = "") -> List[str]:
    """Recursively search object for disallowed JSON Schema metadata fields."""
    disallowed = {
        "additionalProperties",
        "additional_properties",
        "status",
        "title",
        "default",
        "$defs",
        "definitions",
        "anyOf",
        "oneOf",
        "allOf"
    }
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            curr_path = f"{path}.{k}" if path else k
            if k in disallowed:
                found.append(f"Disallowed metadata key '{k}' at '{curr_path}'")
            if k == "properties" and isinstance(v, dict):
                for p_name, p_schema in v.items():
                    found.extend(check_disallowed_metadata(p_schema, f"{curr_path}.{p_name}"))
            else:
                found.extend(check_disallowed_metadata(v, curr_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            found.extend(check_disallowed_metadata(item, f"{path}[{idx}]"))
    return found


class TestGeminiSchemaSanitizer(unittest.TestCase):
    """Test suite for Gemini parameter schema sanitization."""

    def test_sanitize_optional_nullable(self):
        """Test optional/nullable parameters (anyOf with null) are simplified to nullable: True."""
        raw_schema = {
            "type": "object",
            "title": "Args",
            "properties": {
                "lfc_cutoff": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "default": 1.0,
                    "title": "Lfc Cutoff",
                    "description": "Log2 fold change threshold"
                }
            }
        }
        sanitized = sanitize_gemini_schema(raw_schema)
        self.assertNotIn("title", sanitized)
        self.assertNotIn("default", sanitized["properties"]["lfc_cutoff"])
        self.assertNotIn("anyOf", sanitized["properties"]["lfc_cutoff"])
        self.assertEqual(sanitized["properties"]["lfc_cutoff"]["type"], "number")
        self.assertTrue(sanitized["properties"]["lfc_cutoff"].get("nullable"))

    def test_sanitize_array_and_object(self):
        """Test array and object parameters with nested additionalProperties are cleaned."""
        raw_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "genes": {
                    "type": "array",
                    "title": "Genes",
                    "items": {
                        "type": "string",
                        "title": "GeneSymbol"
                    }
                },
                "symbol_map": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "title": "SymbolMap"
                }
            }
        }
        sanitized = sanitize_gemini_schema(raw_schema)
        self.assertNotIn("additionalProperties", sanitized)
        self.assertNotIn("additionalProperties", sanitized["properties"]["symbol_map"])
        self.assertEqual(sanitized["properties"]["genes"]["type"], "array")
        self.assertEqual(sanitized["properties"]["genes"]["items"]["type"], "string")

    def test_sanitize_required_parameters(self):
        """Test required parameter list is preserved."""
        raw_schema = {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string"},
                "contrast": {"type": "string"}
            },
            "required": ["dataset_id"]
        }
        sanitized = sanitize_gemini_schema(raw_schema)
        self.assertEqual(sanitized["required"], ["dataset_id"])

    def test_all_production_tools_sanitization(self):
        """Test that all 11 registered RNAlyst tools produce 100% clean Gemini schemas."""
        orchestrator = AgentOrchestrator()
        tool_schemas = orchestrator.tool_registry.get_tool_schemas()
        self.assertGreater(len(tool_schemas), 0)

        for ts in tool_schemas:
            name = ts["name"]
            raw_params = ts.get("parameters", {})
            clean_params = sanitize_gemini_schema(raw_params)
            issues = check_disallowed_metadata(clean_params, path=f"{name}.parameters")
            self.assertEqual(
                issues, [],
                f"Tool '{name}' parameter schema contains disallowed Gemini keys: {issues}"
            )


if __name__ == "__main__":
    unittest.main()
