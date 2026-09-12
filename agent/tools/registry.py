"""
Tool Registry for AI Agent Platform.

Manages registration, lookup, and schema metadata export for discoverable BaseTool instances.
"""

from typing import Dict, List, Any, Optional
from agent.tools.base_tool import BaseTool


TOOL_CATEGORIES = {
    "create_project": "INGESTION",
    "validate_fastq": "INGESTION",
    "fetch_osdr_study": "INGESTION",
    "quantify_reads": "QUANTIFICATION",
    "run_differential_expression": "STATISTICS",
    "annotate_genes": "ANNOTATION",
    "evaluate_candidate_genes": "PRIORITIZATION",
    "generate_volcano_plot": "VISUALIZATION",
    "generate_pca_plot": "VISUALIZATION",
    "generate_heatmap_plot": "VISUALIZATION",
    "generate_qc_plot": "VISUALIZATION",
    "search_literature": "LITERATURE",
}


class ToolRegistry:
    """Registry managing discoverable BaseTool instances with dynamic search capability."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance by its unique name."""
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Return list of all registered tool instances."""
        return list(self._tools.values())

    def list_tools_by_category(self, category: str) -> List[BaseTool]:
        """Filter registered tools by category string."""
        target_cat = category.strip().upper()
        return [
            tool for name, tool in self._tools.items()
            if TOOL_CATEGORIES.get(name, "GENERAL") == target_cat
        ]

    def find_tools_for_intent(self, query: str, top_k: int = 5) -> List[BaseTool]:
        """
        Dynamically retrieve registered tools matching a query string or intent keywords.
        Ensures optimal tool selection context for LLM agents.
        """
        q_lower = query.lower()
        matched = []

        keywords_map = {
            "create_project": ["create", "project", "init", "setup", "workspace"],
            "validate_fastq": ["fastq", "upload", "validate", "check", "reads", "pair"],
            "fetch_osdr_study": ["osdr", "nasa", "accession", "study", "download"],
            "quantify_reads": ["quantify", "salmon", "quant", "counts", "matrix", "tximport"],
            "run_differential_expression": ["deseq2", "differential", "expression", "deg", "foldchange", "pvalue"],
            "annotate_genes": ["annotate", "symbol", "description", "functional", "tair"],
            "evaluate_candidate_genes": ["candidate", "prioritize", "score", "rank", "evaluate"],
            "generate_volcano_plot": ["volcano", "plot", "figure", "lfc", "fdr"],
            "generate_pca_plot": ["pca", "variance", "component", "cluster"],
            "generate_heatmap_plot": ["heatmap", "clustering", "expression_pattern"],
            "generate_qc_plot": ["qc", "quality", "control", "phred", "reads", "gc"],
            "search_literature": ["literature", "pubmed", "paper", "spaceflight", "biology"]
        }

        for name, tool in self._tools.items():
            kw_list = keywords_map.get(name, [name.lower()])
            if any(kw in q_lower for kw in kw_list) or any(w in tool.description.lower() for w in q_lower.split()):
                matched.append(tool)

        # If no specific keyword matches, return all tools up to top_k
        return matched if matched else self.list_tools()[:top_k]

    def get_tool_schemas(self, tools: Optional[List[BaseTool]] = None) -> List[Dict[str, Any]]:
        """Export provider-agnostic schemas for specified or all registered tools."""
        target_tools = tools if tools is not None else list(self._tools.values())
        schemas = []
        for tool in target_tools:
            schema = {
                "name": tool.name,
                "description": tool.description,
                "category": TOOL_CATEGORIES.get(tool.name, "GENERAL"),
                "parameters": tool.arguments_schema.model_json_schema() if tool.arguments_schema else {}
            }
            schemas.append(schema)
        return schemas
