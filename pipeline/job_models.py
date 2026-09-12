"""
Canonical Job and Artifact Models for Analysis Job Orchestration.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AnalysisStepType(str, Enum):
    UNDERSTANDING_QUESTION = "understanding_question"
    PLANNING_ANALYSIS = "planning_analysis"
    VALIDATING_DATASET = "validating_dataset"
    QC = "qc"
    DIFFERENTIAL_EXPRESSION = "differential_expression"
    PCA = "pca"
    VOLCANO = "volcano"
    HEATMAP = "heatmap"
    ENRICHMENT = "enrichment"
    LITERATURE_SEARCH = "literature_search"
    SYNTHESIZE_RESULTS = "synthesize_results"


class ArtifactType(str, Enum):
    QC_SUMMARY = "qc_summary"
    COUNTS_TABLE = "counts_table"
    DE_TABLE = "de_table"
    PLOT = "plot"
    REPORT = "report"
    JSON_DATA = "json_data"


class AnalysisArtifact(BaseModel):
    artifact_id: str
    type: ArtifactType
    name: str
    path: str
    step: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StepExecutionTrace(BaseModel):
    step: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    message: Optional[str] = None
    artifacts: List[AnalysisArtifact] = Field(default_factory=list)


class RequiredInputSpec(BaseModel):
    input_type: str  # "fastq", "count_matrix", "sample_metadata"
    required_for_steps: List[str] = Field(default_factory=list)
    is_available: bool = False
    resolved_path: Optional[str] = None
    resolution_message: str = ""


class ExpectedOutputArtifact(BaseModel):
    artifact_type: str  # "qc_summary", "qc_plot", "pca_results", "pca_plot", "de_table", "volcano_plot", "heatmap_plot"
    step: str
    description: str


class StepRationale(BaseModel):
    step: str
    rationale: str
    required_inputs: List[str] = Field(default_factory=list)
    expected_outputs: List[str] = Field(default_factory=list)


class StructuredAnalysisPlan(BaseModel):
    user_question: str
    interpreted_intent: str
    analysis_goal: str
    is_valid: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    required_inputs: List[RequiredInputSpec] = Field(default_factory=list)
    selected_steps: List[str] = Field(default_factory=list)
    step_rationales: List[StepRationale] = Field(default_factory=list)
    expected_artifacts: List[ExpectedOutputArtifact] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AnalysisJob(BaseModel):
    analysis_id: str
    file_id: str
    user_question: Optional[str] = None
    organism: Optional[str] = None
    dataset_id: Optional[str] = None
    status: JobStatus = JobStatus.QUEUED
    current_step: Optional[str] = None
    plan: List[str] = Field(default_factory=lambda: ["validating_dataset", "qc"])
    structured_plan: Optional[StructuredAnalysisPlan] = None
    steps: List[StepExecutionTrace] = Field(default_factory=list)
    artifacts: List[AnalysisArtifact] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
