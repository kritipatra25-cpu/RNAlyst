"""
Gene Annotation Tool Contract.

Wraps existing GeneAnnotator implementation as a BaseTool contract with typed schemas,
argument validation, structured ToolResult output, and provenance tracking.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator

from agent.tools.base_tool import BaseTool, ToolResult
from analysis.annotation.gene_annotator import GeneAnnotator


class GeneAnnotationToolArgs(BaseModel):
    """Input arguments for GeneAnnotationTool."""
    gene_id: str = Field(..., description="Target gene identifier (e.g. 'AT1G04400', 'AT3G17609', 'ENSMUSG00000000001')")
    organism: Optional[str] = Field("Arabidopsis thaliana", description="Target organism name (e.g. 'Arabidopsis thaliana', 'Mus musculus')")
    annotation_source: Optional[str] = Field("TAIR10", description="Annotation database source (e.g. 'TAIR10', 'GENCODE_M34')")
    custom_symbol_map: Optional[Dict[str, str]] = Field(None, description="Optional custom mapping of gene IDs to symbols.")

    @validator("gene_id")
    def validate_gene_id(cls, v):
        if not v or not isinstance(v, str) or len(v.strip()) < 2:
            raise ValueError("gene_id must be a non-empty string with at least 2 characters.")
        return v.strip()


class GeneAnnotationTool(BaseTool):
    """Deterministic Multi-Species Gene Annotation Tool."""

    name = "annotate_gene"
    description = "Annotates a gene ID with symbol, description, biotype, and species metadata."
    arguments_schema = GeneAnnotationToolArgs

    def __init__(self, annotator: Optional[GeneAnnotator] = None):
        self.annotator = annotator

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        args = validated_args or GeneAnnotationToolArgs(**arguments)

        try:
            annotator = self.annotator or GeneAnnotator(
                organism=args.organism or "Arabidopsis thaliana",
                annotation_source=args.annotation_source or "TAIR10",
                custom_symbol_map=args.custom_symbol_map
            )

            ann_res = annotator.annotate_gene(args.gene_id)
            symbol = annotator.get_symbol(args.gene_id)

            organism = annotator.provider.organism
            annotation_source = annotator.provider.annotation_source

            result_data = {
                "gene_id": args.gene_id,
                "symbol": symbol,
                "name": ann_res.get("name", f"Transcript {args.gene_id}"),
                "biotype": ann_res.get("biotype", "protein_coding"),
                "organism": organism,
                "annotation_source": annotation_source
            }

            return ToolResult.success_result(
                tool_name=self.name,
                result=result_data,
                provenance={
                    "gene_id": args.gene_id,
                    "organism": organism,
                    "annotation_source": annotation_source,
                    "wrapped_class": "GeneAnnotator"
                }
            )
        except Exception as e:
            return ToolResult.error_result(
                tool_name=self.name,
                error_type=type(e).__name__,
                message=f"Gene annotation failed for '{args.gene_id}': {str(e)}",
                provenance={"gene_id": args.gene_id}
            )
