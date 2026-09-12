"""
Literature RAG Search Scientific Tool Wrapper.

Exposes the deterministic LiteratureRAGEngine evidence lookup
as a BaseTool contract with input argument validation and structured ToolResult output.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from agent.tools.base_tool import BaseTool, ToolResult
from agent.rag.literature_engine import LiteratureRAGEngine, LiteratureSnippet


class LiteratureToolArgs(BaseModel):
    """Input argument schema for Literature Search Tool."""
    gene_id: Optional[str] = Field(None, description="Optional gene ID or symbol to query literature for (e.g. 'AT1G04400', 'CRY1')")
    topic: Optional[str] = Field(None, description="Optional search topic or keyword (e.g. 'spaceflight', 'circadian', 'microgravity')")
    organism: Optional[str] = Field(None, description="Optional organism filter (e.g. 'Arabidopsis thaliana', 'Mus musculus')")


class LiteratureTool(BaseTool):
    """Deterministic Literature RAG Search Tool."""

    name = "search_literature"
    description = "Searches peer-reviewed spaceflight and transcriptomics literature for candidate genes or biological topics."
    arguments_schema = LiteratureToolArgs

    def __init__(self, rag_engine: Optional[LiteratureRAGEngine] = None):
        self.engine = rag_engine or LiteratureRAGEngine()

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        args = validated_args or LiteratureToolArgs(**arguments)

        snippets: List[LiteratureSnippet] = []

        if args.gene_id:
            snippets = self.engine.search_gene_literature(gene_id=args.gene_id)
        elif args.topic:
            snippets = self.engine.search_topic_literature(topic=args.topic)
        else:
            snippets = self.engine.get_all_snippets()

        if args.organism and str(args.organism).strip():
            org_clean = str(args.organism).strip().lower()
            snippets = [s for s in snippets if org_clean in s.organism.lower() or org_clean in s.title.lower()]

        snippet_dicts = [s.dict() for s in snippets]

        return ToolResult.success_result(
            tool_name=self.name,
            result={
                "match_count": len(snippets),
                "snippets": snippet_dicts
            },
            artifacts=[],
            provenance={
                "source": "Local Peer-Reviewed Spaceflight Index",
                "query_gene_id": args.gene_id,
                "query_topic": args.topic
            }
        )
