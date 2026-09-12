"""
Candidate Gene Prioritization Agent Tool Contract.

Wraps deterministic CandidatePrioritizer cross-contrast gene evaluation and
concordance classification as a BaseTool contract with typed schemas, argument
validation, structured ToolResult output, and provenance tracking.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field, validator

from agent.tools.base_tool import BaseTool, ToolResult, ToolArtifact
from analysis.interpretation.candidate_prioritizer import CandidatePrioritizer


class CandidatePrioritizationToolArgs(BaseModel):
    """Input argument schema for CandidatePrioritizationTool."""
    candidate_genes: List[str] = Field(..., description="List of target gene identifiers to evaluate (e.g. ['AT3G17609', 'AT4G04720']).")
    primary_de_path: str = Field(..., description="Path to primary differential expression results CSV file (containing gene_id, log2FoldChange, pvalue, padj).")
    secondary_de_path: Optional[str] = Field(None, description="Optional path to secondary contrast DE results CSV file.")
    reference_de_path: Optional[str] = Field(None, description="Optional path to reference cross-dataset DE results CSV file.")
    custom_symbol_map: Optional[Dict[str, str]] = Field(None, description="Optional custom mapping of gene IDs to symbols.")

    @validator("candidate_genes")
    def validate_candidate_genes(cls, v):
        if not v or not isinstance(v, list) or len(v) == 0:
            raise ValueError("candidate_genes must be a non-empty list of gene IDs.")
        cleaned = [str(g).strip() for g in v if str(g).strip()]
        if not cleaned:
            raise ValueError("candidate_genes must contain valid non-empty gene ID strings.")
        return cleaned

    @validator("primary_de_path")
    def validate_primary_path(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("primary_de_path must be a non-empty file path string.")
        return v.strip()


class CandidatePrioritizationTool(BaseTool):
    """Deterministic Cross-Contrast Candidate Gene Prioritization Tool."""

    name = "evaluate_candidate_genes"
    description = "Evaluates and prioritizes a list of candidate genes across primary, secondary, and reference differential expression results for directional concordance and evidence classification."
    arguments_schema = CandidatePrioritizationToolArgs

    def __init__(self, prioritizer: Optional[CandidatePrioritizer] = None):
        self.prioritizer = prioritizer

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        args = validated_args or CandidatePrioritizationToolArgs(**arguments)

        primary_p = Path(args.primary_de_path)
        if not primary_p.exists():
            return ToolResult.error_result(
                tool_name=self.name,
                error_type="FileNotFoundError",
                message=f"Primary DE results CSV file not found at: {primary_p}",
                provenance={"primary_de_path": str(primary_p)}
            )

        try:
            primary_df = pd.read_csv(primary_p)

            secondary_df = None
            if args.secondary_de_path:
                sec_p = Path(args.secondary_de_path)
                if sec_p.exists():
                    secondary_df = pd.read_csv(sec_p)

            reference_df = None
            if args.reference_de_path:
                ref_p = Path(args.reference_de_path)
                if ref_p.exists():
                    reference_df = pd.read_csv(ref_p)

            prioritizer = self.prioritizer or CandidatePrioritizer(symbol_map=args.custom_symbol_map)

            eval_records = prioritizer.evaluate_candidates(
                candidate_genes=args.candidate_genes,
                primary_contrast_df=primary_df,
                secondary_contrast_df=secondary_df,
                reference_de_df=reference_df
            )

            concordant_count = sum(1 for r in eval_records if r.get("direction_concordance") == "CONCORDANT")
            fdr_pass_count = sum(1 for r in eval_records if r.get("passes_osd678_fdr_005") is True)

            return ToolResult.success_result(
                tool_name=self.name,
                result={
                    "candidate_count": len(eval_records),
                    "concordant_count": concordant_count,
                    "fdr_pass_count": fdr_pass_count,
                    "evaluated_candidates": eval_records
                },
                provenance={
                    "primary_de_path": str(primary_p),
                    "secondary_de_path": str(args.secondary_de_path) if args.secondary_de_path else None,
                    "reference_de_path": str(args.reference_de_path) if args.reference_de_path else None,
                    "wrapped_class": "CandidatePrioritizer",
                    "wrapped_method": "evaluate_candidates"
                }
            )
        except Exception as e:
            return ToolResult.error_result(
                tool_name=self.name,
                error_type=type(e).__name__,
                message=f"Candidate prioritization evaluation failed: {str(e)}",
                provenance={"primary_de_path": str(primary_p)}
            )
