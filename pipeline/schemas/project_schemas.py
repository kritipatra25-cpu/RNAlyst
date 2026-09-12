"""
Canonical Data Model Schemas for Dataset-Agnostic RNA-Seq Projects.

Defines Pydantic V2 models for projects, samples, experimental designs,
versioned references, analysis runs, artifacts, and provenance manifests.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, validator


class DataOrigin(str, Enum):
    OSDR_ACCESSION = "OSDR_ACCESSION"
    LOCAL_FASTQ = "LOCAL_FASTQ"
    PROCESSED_COUNT_MATRIX = "PROCESSED_COUNT_MATRIX"


class LayoutType(str, Enum):
    SINGLE = "SINGLE"
    PAIRED = "PAIRED"


class Sample(BaseModel):
    """Metadata representation of a single RNA-seq sample."""
    sample_id: str = Field(..., description="Unique sample identifier")
    condition: str = Field("UNRESOLVED", description="Experimental group / condition name")
    replicate_id: Optional[str] = Field(None, description="Optional replicate identifier")
    layout: LayoutType = Field(LayoutType.SINGLE, description="Single-end or paired-end read layout")
    batch: Optional[str] = Field(None, description="Optional batch covariate identifier")
    genotype: Optional[str] = Field(None, description="Optional genotype identifier")
    tissue: Optional[str] = Field(None, description="Optional tissue identifier")
    fastq_r1_path: Optional[str] = Field(None, description="Path to R1 FASTQ file")
    fastq_r2_path: Optional[str] = Field(None, description="Path to R2 FASTQ file (if paired-end)")
    file_size_bytes: Optional[int] = Field(None, description="Total size in bytes of raw reads")
    is_valid: bool = Field(True, description="Whether sample passes pre-analysis validation checks")

    @validator("sample_id", "condition")
    def validate_non_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("sample_id and condition must be non-empty strings.")
        return v.strip()


class SampleManifest(BaseModel):
    """Validated sample sheet and layout summary for a dataset."""
    samples: List[Sample] = Field(..., description="List of sample specifications")
    layout: LayoutType = Field(LayoutType.PAIRED, description="Sequencing layout type")
    organism: str = Field(..., description="Target organism scientific name")
    condition_column: str = Field("condition", description="Primary experimental design factor column")
    total_samples: int = Field(0, description="Total count of samples")
    min_replicates_per_group: int = Field(0, description="Minimum biological replicates per group")
    replicate_status: str = Field("INFERENTIAL", description="INFERENTIAL (N>=3) or EXPLORATORY (N<3)")

    def __post_init_custom__(self):
        self.total_samples = len(self.samples)


class ContrastSpec(BaseModel):
    """Specification of a differential comparison contrast."""
    id: str = Field(..., description="Unique contrast identifier (e.g. Flight_vs_Ground)")
    factor: str = Field(..., description="Metadata factor column name")
    numerator: str = Field(..., description="Treatment / Numerator group level")
    denominator: str = Field(..., description="Control / Reference group level")
    description: str = Field("", description="Human-readable biological description")


class ExperimentalDesign(BaseModel):
    """Experimental design formula, factor levels, and contrast specifications."""
    design_formula: str = Field("~ condition", description="R-style DESeq2 formula")
    factors: Dict[str, List[str]] = Field(default_factory=dict, description="Factor column names to level lists")
    reference_levels: Dict[str, str] = Field(default_factory=dict, description="Factor column names to reference levels")
    contrasts: List[ContrastSpec] = Field(default_factory=list, description="Defined statistical contrasts")


class ReferenceSpec(BaseModel):
    """First-class reference genome, transcriptome, and annotation provenance specification."""
    organism: str = Field(..., description="Target organism scientific name")
    source: str = Field("Ensembl", description="Reference source database (TAIR10, Ensembl, GENCODE)")
    version_build: str = Field("TAIR10", description="Reference version build identifier")
    transcriptome_fasta: Optional[str] = Field(None, description="Path to reference transcriptome FASTA")
    gtf_annotation: Optional[str] = Field(None, description="Path to GTF annotation file")
    tx2gene_csv: Optional[str] = Field(None, description="Path to transcript-to-gene mapping CSV")
    salmon_index_dir: Optional[str] = Field(None, description="Path to pre-computed Salmon index")
    sha256_hashes: Dict[str, str] = Field(default_factory=dict, description="SHA-256 checksums of reference files")


class Reference(BaseModel):
    """Versioned transcriptome reference and annotation specification (legacy alias)."""
    organism: str = Field(..., description="Target organism scientific name")
    transcriptome_fasta: str = Field(..., description="Path to reference transcriptome FASTA")
    gtf_annotation: Optional[str] = Field(None, description="Optional path to GTF annotation file")
    tx2gene_csv: str = Field(..., description="Path to transcript-to-gene mapping CSV")
    salmon_index_dir: str = Field(..., description="Path to pre-computed or generated Salmon index directory")
    version_build: str = Field("TAIR10", description="Reference version build identifier")
    sha256_checksum: Optional[str] = Field(None, description="SHA-256 checksum of reference FASTA")


class ToolExecutionStep(BaseModel):
    """Structured execution step record for agent tool call provenance and UX drawers."""
    step_id: str = Field(..., description="Unique step identifier (e.g. step_001)")
    tool_name: str = Field(..., description="Tool name executed")
    timestamp: str = Field(..., description="ISO timestamp of execution")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Input arguments passed to tool")
    status: str = Field("SUCCESS", description="SUCCESS, FAILED, or SKIPPED")
    output_summary: str = Field("", description="Human-readable summary of step result")
    artifact_paths: List[str] = Field(default_factory=list, description="Paths of artifacts generated by step")
    provenance_hash: Optional[str] = Field(None, description="SHA-256 provenance hash for step execution")


class WorkspaceState(BaseModel):
    """Analytical readiness state of the project workspace."""
    readiness_stage: str = Field("UNINITIALIZED", description="UNINITIALIZED, FASTQ_UPLOADED, QUANTIFIED, ANALYZED, REPORT_GENERATED")
    has_counts_matrix: bool = Field(False, description="Whether counts_matrix.csv is present")
    has_de_results: bool = Field(False, description="Whether DE results CSV is present")
    active_contrast_id: Optional[str] = Field(None, description="Active contrast identifier")
    total_samples: int = Field(0, description="Total sample count")
    replicate_status: str = Field("INFERENTIAL", description="INFERENTIAL or EXPLORATORY")
    is_ready_for_deseq2: Optional[bool] = Field(True, description="Whether biological experimental design is fully resolved for DESeq2")
    unresolved_reason: Optional[str] = Field(None, description="Reason if biological metadata or experimental design requires resolution")


class AnalysisRun(BaseModel):
    """Status and timing tracking for an analysis execution run."""
    run_id: str = Field(..., description="Unique run execution identifier")
    project_id: str = Field(..., description="Target project identifier")
    status: str = Field("QUEUED", description="QUEUED, RUNNING, COMPLETED, or FAILED")
    execution_engine: str = Field("Nextflow+Salmon+PyDESeq2", description="Engine identifier")
    start_time: str = Field(..., description="ISO-formatted start timestamp")
    end_time: Optional[str] = Field(None, description="ISO-formatted completion timestamp")
    error_message: Optional[str] = Field(None, description="Failure details if status is FAILED")


class Artifact(BaseModel):
    """Machine-readable artifact produced by workflow execution."""
    artifact_id: str = Field(..., description="Unique artifact identifier")
    artifact_type: str = Field(..., description="counts_matrix, vst_matrix, de_csv, volcano_plot, etc.")
    file_path: str = Field(..., description="Path to file on disk")
    format: str = Field("csv", description="File format extension")
    file_size_bytes: int = Field(0, description="Size in bytes")


class Provenance(BaseModel):
    """Execution provenance manifest."""
    project_id: str = Field(..., description="Target project identifier")
    origin: DataOrigin = Field(..., description="Data source origin")
    engine_versions: Dict[str, str] = Field(default_factory=dict, description="Tool version map")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Analysis parameter map")
    input_files_sha256: Dict[str, str] = Field(default_factory=dict, description="File checksum map")
    reference_sha256: Dict[str, str] = Field(default_factory=dict, description="Reference genome/transcriptome checksum map")


class Project(BaseModel):
    """Canonical dataset-agnostic RNA-seq project representation."""
    project_id: str = Field(..., description="Unique project identifier (slug)")
    name: str = Field(..., description="Human-readable project title")
    origin: DataOrigin = Field(..., description="Data origin type")
    organism: str = Field(..., description="Target organism scientific name")
    manifest: SampleManifest = Field(..., description="Sample manifest and layout")
    design: ExperimentalDesign = Field(..., description="Experimental design specification")
    reference: Optional[Reference] = Field(None, description="Reference transcriptome specification")
    reference_spec: Optional[ReferenceSpec] = Field(None, description="First-class reference provenance specification")
    workspace_state: WorkspaceState = Field(default_factory=WorkspaceState, description="Analytical readiness workspace state")
    execution_history: List[ToolExecutionStep] = Field(default_factory=list, description="Persistent step-by-step tool execution trace history")
    active_run: Optional[AnalysisRun] = Field(None, description="Active or latest analysis run")
    artifacts: List[Artifact] = Field(default_factory=list, description="Output artifact list")
    provenance: Optional[Provenance] = Field(None, description="Execution provenance manifest")

    @validator("project_id")
    def validate_project_id_slug(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("project_id must be a non-empty string.")
        clean = v.strip().upper()
        if " " in clean:
            raise ValueError("project_id must not contain spaces.")
        return clean
