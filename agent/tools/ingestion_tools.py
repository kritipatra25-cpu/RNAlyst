"""
Structured Agent Tools for Data Ingestion & Dataset-Agnostic Workflow (Step 4).

Exposes project setup, FASTQ validation, transcript quantification, and OSDR dataset discovery
as structured BaseTool contracts for LLM tool-calling orchestration.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Type
from pydantic import BaseModel, Field, validator

from agent.tools.base_tool import BaseTool, ToolResult, ToolArtifact
from pipeline.project_manager import ProjectManager
from pipeline.upload_handler import UploadHandler
from pipeline.quantification_runner import QuantificationRunner
from pipeline.osdr_client import NASAOSDRClient
from pipeline.schemas.project_schemas import (
    DataOrigin, LayoutType, Sample, SampleManifest, ContrastSpec, ExperimentalDesign
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 1. CreateProjectTool
# -----------------------------------------------------------------------------
class CreateProjectInput(BaseModel):
    """Input arguments for creating a dataset-agnostic RNA-seq project."""
    project_id: str = Field(..., description="Unique project slug identifier (e.g. MOUSE_LIVER_2026)")
    name: str = Field(..., description="Human-readable project title")
    origin: str = Field("LOCAL_FASTQ", description="Data origin: LOCAL_FASTQ or OSDR_ACCESSION")
    organism: Optional[str] = Field(None, description="Target organism scientific name (or None if UNRESOLVED)")
    condition_column: Optional[str] = Field(None, description="Primary experimental design factor column name")
    sample_ids: Optional[List[str]] = Field(None, description="List of sample IDs")
    conditions: Optional[List[str]] = Field(None, description="Parallel list of condition group labels matching sample_ids")
    numerator_level: Optional[str] = Field(None, description="Treatment / Numerator group label for primary contrast")
    reference_level: Optional[str] = Field(None, description="Control / Reference group label for primary contrast")

    @validator("project_id")
    def validate_id(cls, v):
        if not v or not isinstance(v, str) or " " in v.strip():
            raise ValueError("project_id must be a non-empty string without spaces.")
        return v.strip().upper()


class CreateProjectTool(BaseTool):
    """Tool for creating a new dataset-agnostic RNA-seq project and workspace layout."""

    name = "create_project"
    description = (
        "Initialize a new dataset-agnostic bulk RNA-seq project workspace with sample metadata, "
        "experimental design matrix, and dynamic backend configuration."
    )
    arguments_schema: Optional[Type[BaseModel]] = CreateProjectInput

    def __init__(self, projects_dir: str = "projects", configs_dir: str = "configs"):
        self.project_manager = ProjectManager(projects_dir=projects_dir, configs_dir=configs_dir)

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        inp: CreateProjectInput = validated_args or CreateProjectInput(**arguments)

        sample_ids = inp.sample_ids or []
        conditions = inp.conditions or []

        if sample_ids and conditions and len(sample_ids) != len(conditions):
            raise ValueError(f"Sample count ({len(sample_ids)}) does not match condition count ({len(conditions)})")

        samples = [
            Sample(sample_id=sid, condition=cond)
            for sid, cond in zip(sample_ids, conditions)
        ]

        # Calculate replicate count
        cond_counts = {}
        for c in conditions:
            cond_counts[c] = cond_counts.get(c, 0) + 1

        min_reps = min(cond_counts.values()) if cond_counts else 0
        rep_status = "INFERENTIAL" if min_reps >= 3 else ("EXPLORATORY" if min_reps > 0 else "UNRESOLVED")

        org = inp.organism or "UNRESOLVED"
        factor_col = inp.condition_column or "condition"

        manifest = SampleManifest(
            samples=samples,
            layout=LayoutType.PAIRED,
            organism=org,
            condition_column=factor_col,
            total_samples=len(samples),
            min_replicates_per_group=min_reps,
            replicate_status=rep_status
        )

        num_lvl = inp.numerator_level or "UNRESOLVED"
        ref_lvl = inp.reference_level or "UNRESOLVED"

        contrast = ContrastSpec(
            id=f"{num_lvl}_vs_{ref_lvl}",
            factor=factor_col,
            numerator=num_lvl,
            denominator=ref_lvl,
            description=f"{num_lvl} vs {ref_lvl}"
        )

        unique_conds = sorted(list(set(conditions))) if conditions else ["UNRESOLVED"]
        design = ExperimentalDesign(
            design_formula=f"~ {factor_col}",
            factors={factor_col: unique_conds},
            reference_levels={factor_col: ref_lvl},
            contrasts=[contrast]
        )

        origin_enum = DataOrigin.OSDR_ACCESSION if inp.origin == "OSDR_ACCESSION" else DataOrigin.LOCAL_FASTQ

        project = self.project_manager.create_project(
            project_id=inp.project_id,
            name=inp.name,
            origin=origin_enum,
            organism=org,
            manifest=manifest,
            design=design
        )

        summary_text = (
            f"Successfully initialized project '{project.project_id}' ({project.name}). "
            f"Organism: {project.organism}. Total samples: {manifest.total_samples}. "
            f"Replicate status: {rep_status} (min N={min_reps}). "
            f"Primary contrast: {contrast.id}."
        )

        res_data = {
            "summary": summary_text,
            "project_id": project.project_id,
            "organism": project.organism,
            "total_samples": manifest.total_samples,
            "replicate_status": rep_status,
            "contrast_id": contrast.id
        }

        return ToolResult.success_result(
            tool_name=self.name,
            result=res_data,
            provenance={"project_id": project.project_id, "action": "create_project"}
        )


# -----------------------------------------------------------------------------
# 2. ValidateFASTQTool
# -----------------------------------------------------------------------------
class ValidateFASTQInput(BaseModel):
    """Input arguments for FASTQ file validation."""
    fastq_file_path: str = Field(..., description="Path to single FASTQ file (.fastq or .fastq.gz)")
    paired_file_path: Optional[str] = Field(None, description="Optional path to paired R2 FASTQ file")


class ValidateFASTQTool(BaseTool):
    """Tool for validating FASTQ file syntax, gzip magic bytes, non-zero size, and paired headers."""

    name = "validate_fastq"
    description = (
        "Validate single or paired-end FASTQ file syntax, gzip magic bytes, non-zero file size, "
        "and read header consistency."
    )
    arguments_schema: Optional[Type[BaseModel]] = ValidateFASTQInput

    def __init__(self, sandbox_root: str = "data/uploads"):
        self.upload_handler = UploadHandler(sandbox_root=sandbox_root)

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        inp: ValidateFASTQInput = validated_args or ValidateFASTQInput(**arguments)
        f1_path = Path(inp.fastq_file_path)

        if not f1_path.exists():
            return ToolResult.error_result(
                tool_name=self.name,
                error_type="FileNotFoundError",
                message=f"FASTQ file does not exist: {f1_path}"
            )

        res1 = self.upload_handler.validate_uploaded_fastq(f1_path)

        if inp.paired_file_path:
            f2_path = Path(inp.paired_file_path)
            if not f2_path.exists():
                return ToolResult.error_result(
                    tool_name=self.name,
                    error_type="FileNotFoundError",
                    message=f"Paired R2 FASTQ file does not exist: {f2_path}"
                )

            res_pair = self.upload_handler.validate_uploaded_fastq_pair(f1_path, f2_path)
            is_valid = res1["is_valid"] and res_pair["is_valid"]
            err_msg = res1.get("error") or res_pair.get("error")
            summary = f"Paired FASTQ validation for {f1_path.name} & {f2_path.name}: {'PASSED' if is_valid else 'FAILED'}."
            data = {"r1": res1, "pair": res_pair, "is_valid": is_valid, "summary": summary}
        else:
            is_valid = res1["is_valid"]
            err_msg = res1.get("error")
            summary = f"Single FASTQ validation for {f1_path.name}: {'PASSED' if is_valid else 'FAILED'}."
            data = {"r1": res1, "is_valid": is_valid, "summary": summary}

        if err_msg:
            summary += f" Error: {err_msg}"
            data["summary"] = summary

        if is_valid:
            return ToolResult.success_result(
                tool_name=self.name,
                result=data,
                provenance={"r1_path": str(f1_path), "is_valid": is_valid}
            )
        else:
            return ToolResult.error_result(
                tool_name=self.name,
                error_type="FASTQValidationError",
                message=summary,
                details=[err_msg] if err_msg else []
            )


# -----------------------------------------------------------------------------
# 3. QuantifyReadsTool
# -----------------------------------------------------------------------------
class QuantifyReadsInput(BaseModel):
    """Input arguments for transcript quantification and count matrix generation."""
    project_id: str = Field(..., description="Target project slug identifier")
    quant_directories: Dict[str, str] = Field(..., description="Mapping of sample_id -> Path to quant directory or quant.sf file")
    tx2gene_path: Optional[str] = Field(None, description="Optional path to tx2gene mapping CSV file")


class QuantifyReadsTool(BaseTool):
    """Tool for aggregating Salmon transcript quantification into gene count matrices."""

    name = "quantify_reads"
    description = (
        "Aggregate transcript quantification outputs (Salmon quant.sf files) into a gene-level "
        "counts matrix for downstream PyDESeq2 differential expression."
    )
    arguments_schema: Optional[Type[BaseModel]] = QuantifyReadsInput

    def __init__(self, projects_dir: str = "projects"):
        self.projects_dir = Path(projects_dir).resolve()

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        inp: QuantifyReadsInput = validated_args or QuantifyReadsInput(**arguments)
        clean_id = inp.project_id.strip().upper()
        proj_dir = self.projects_dir / clean_id

        if not proj_dir.exists():
            return ToolResult.error_result(
                tool_name=self.name,
                error_type="DirectoryNotFoundError",
                message=f"Project directory missing for '{clean_id}' at {proj_dir}"
            )

        output_csv = proj_dir / "data" / "counts_matrix.csv"
        quant_map = {sid: Path(p) for sid, p in inp.quant_directories.items()}
        tx2gene_p = Path(inp.tx2gene_path) if inp.tx2gene_path else None

        generated_csv = QuantificationRunner.generate_counts_matrix_file(
            quant_dir_map=quant_map,
            output_csv_path=output_csv,
            tx2gene_path=tx2gene_p
        )

        summary = (
            f"Successfully generated counts matrix for project '{clean_id}' across {len(quant_map)} samples "
            f"at {generated_csv}."
        )

        artifact = ToolArtifact(
            artifact_type="csv",
            path=str(generated_csv),
            description=f"Generated gene-level count matrix for project {clean_id}"
        )

        return ToolResult.success_result(
            tool_name=self.name,
            result={
                "summary": summary,
                "project_id": clean_id,
                "counts_matrix_path": str(generated_csv),
                "sample_count": len(quant_map)
            },
            artifacts=[artifact],
            provenance={"project_id": clean_id, "counts_matrix_path": str(generated_csv)}
        )


# -----------------------------------------------------------------------------
# 4. FetchOSDRStudyTool
# -----------------------------------------------------------------------------
class FetchOSDRStudyInput(BaseModel):
    """Input arguments for OSDR study metadata discovery."""
    accession: str = Field(..., description="NASA OSDR accession identifier (e.g. OSD-120, OSD-678, OSD-379)")


class FetchOSDRStudyTool(BaseTool):
    """Tool for discovering NASA OSDR study metadata, sample factors, and file inventory."""

    name = "fetch_osdr_study"
    description = (
        "Query NASA OSDR REST API for study metadata, sample factor matrices, file inventory, "
        "and estimated total raw data size in bytes."
    )
    arguments_schema: Optional[Type[BaseModel]] = FetchOSDRStudyInput

    def __init__(self):
        self.osdr_client = NASAOSDRClient()

    def _execute(self, arguments: Dict[str, Any], validated_args: Optional[BaseModel] = None) -> ToolResult:
        inp: FetchOSDRStudyInput = validated_args or FetchOSDRStudyInput(**arguments)
        acc = inp.accession.strip().upper()

        meta = self.osdr_client.fetch_study_metadata(acc)
        df_samples = self.osdr_client.parse_sample_table(meta)
        inventory = self.osdr_client.audit_file_inventory(meta)

        raw_size_gb = round(inventory.get("total_raw_size_bytes", 0) / (1024 ** 3), 2)
        sample_count = len(df_samples)

        summary = (
            f"Retrieved NASA OSDR study '{acc}'. Found {sample_count} samples and "
            f"{len(inventory.get('raw_fastq_files', []))} raw FASTQ files "
            f"(Total estimated raw size: {raw_size_gb} GB)."
        )

        return ToolResult.success_result(
            tool_name=self.name,
            result={
                "summary": summary,
                "accession": acc,
                "sample_count": sample_count,
                "raw_file_count": len(inventory.get("raw_fastq_files", [])),
                "total_raw_size_bytes": inventory.get("total_raw_size_bytes", 0),
                "total_raw_size_gb": raw_size_gb,
                "assay_count": len(meta.get("assays", []))
            },
            provenance={"accession": acc, "action": "fetch_osdr_metadata"}
        )
