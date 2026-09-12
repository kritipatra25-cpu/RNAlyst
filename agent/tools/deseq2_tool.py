"""
DESeq2 Differential Expression Scientific Tool Wrapper.

Exposes the deterministic RNASeqBackendAPI differential expression pipeline
as a BaseTool contract with input argument validation and structured ToolResult output.
"""

from typing import Dict, List, Any, Optional, Type
from pydantic import BaseModel, Field, validator

from agent.tools.base_tool import BaseTool, ToolResult, ToolArtifact
from pipeline.backend_api import RNASeqBackendAPI, AnalysisRequest, AnalysisResult, AnalysisErrorResult


class DESeq2ToolArgs(BaseModel):
    """Input argument schema for DESeq2 Differential Expression Tool."""
    dataset_id: str = Field(..., description="Target dataset identifier (e.g., 'OSD-678', 'OSD-120')")
    contrast_id: Optional[str] = Field(None, description="Optional specific contrast ID to evaluate")
    fdr_cutoff: float = Field(0.05, description="False Discovery Rate significance threshold (0.0, 1.0)")
    lfc_cutoff: float = Field(1.0, description="Absolute log2 fold-change significance threshold (>= 0.0)")

    @validator("dataset_id")
    def validate_dataset_id(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("dataset_id must be a non-empty string.")
        return v.strip().upper()

    @validator("fdr_cutoff")
    def validate_fdr(cls, v):
        if v <= 0.0 or v >= 1.0:
            raise ValueError(f"fdr_cutoff must be between 0.0 and 1.0 strictly. Got: {v}")
        return v

    @validator("lfc_cutoff")
    def validate_lfc(cls, v):
        if v < 0.0:
            raise ValueError(f"lfc_cutoff must be non-negative. Got: {v}")
        return v


class DESeq2Tool(BaseTool):
    """Deterministic DESeq2 RNA-seq Differential Expression Analysis Tool."""

    name = "run_differential_expression"
    description = "Executes deterministic PyDESeq2 differential expression analysis for configured RNA-seq datasets."
    arguments_schema = DESeq2ToolArgs

    def __init__(self, backend_api: Optional[RNASeqBackendAPI] = None):
        self.api = backend_api or RNASeqBackendAPI()

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        args = validated_args or DESeq2ToolArgs(**arguments)

        req = AnalysisRequest(
            dataset_id=args.dataset_id,
            contrast_id=args.contrast_id,
            fdr_cutoff=args.fdr_cutoff,
            lfc_cutoff=args.lfc_cutoff
        )

        success, result, error = self.api.run_analysis_safe(req)

        if not success or not result:
            err_msg = error.message if error else "Unknown backend analysis failure"
            err_type = error.error_type if error else "DESeq2ExecutionError"
            return ToolResult.error_result(
                tool_name=self.name,
                error_type=err_type,
                message=err_msg,
                details=error.details if error else [],
                provenance={"dataset_id": args.dataset_id}
            )

        artifacts = []
        if result.analysis_summary_path:
            artifacts.append(ToolArtifact(
                artifact_type="json",
                path=result.analysis_summary_path,
                description="Analysis summary JSON"
            ))
        if result.candidate_comparison_csv_path:
            artifacts.append(ToolArtifact(
                artifact_type="csv",
                path=result.candidate_comparison_csv_path,
                description="Prioritized candidate genes comparison CSV"
            ))
        if result.provenance_manifest_path:
            artifacts.append(ToolArtifact(
                artifact_type="json",
                path=result.provenance_manifest_path,
                description="Execution provenance manifest JSON"
            ))

        return ToolResult.success_result(
            tool_name=self.name,
            result={
                "dataset_id": result.dataset_id,
                "execution_status": result.execution_status,
                "contrast_count": result.contrast_count,
                "candidate_count": result.candidate_count,
                "summary_metrics": result.summary_metrics,
                "output_dir": result.output_dir
            },
            artifacts=artifacts,
            provenance={
                "dataset_id": result.dataset_id,
                "engine": "PyDESeq2 v0.5.4",
                "fdr_cutoff": args.fdr_cutoff,
                "lfc_cutoff": args.lfc_cutoff
            }
        )
