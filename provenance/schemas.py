"""Data schemas for analysis manifests, checksums, and execution provenance."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class InputFileChecksum(BaseModel):
    file_name: str
    file_path: str
    sha256: str
    size_bytes: int


class ReferenceGenomeProvenance(BaseModel):
    organism: str
    common_name: str
    genome_assembly: str
    annotation_source: str
    annotation_release: str
    gene_id_namespace: str
    reference_checksum_sha256: str
    transcriptome_version: str


class StatisticalDesignProvenance(BaseModel):
    design_formula: str
    reference_group: str
    comparison_group: str
    experimental_factor: str
    batch_factor: Optional[str] = None
    shrinkage_method: str = "apeglm"
    statistical_test: str = "Wald"
    fdr_threshold: float = 0.05
    log2fc_threshold: float = 1.0


class ProvenanceManifest(BaseModel):
    analysis_id: str
    parent_analysis_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    pipeline_version: str = "0.1.0"
    container_digest: Optional[str] = None
    input_files: List[InputFileChecksum]
    reference: ReferenceGenomeProvenance
    statistical_design: StatisticalDesignProvenance
    validity_status: str  # VALID | VALID_WITH_WARNINGS | EXPLORATORY | NOT_VALID
    status_reasons: List[str] = []
    software_versions: Dict[str, str] = {}
    manual_decisions: List[Dict[str, Any]] = []
