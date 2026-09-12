"""
Programmatic API Gateway for Bulk RNA-seq AI Agent Platform.

Provides a strongly-validated, deterministic interface between external AI/LLM orchestrators
and the reusable core RNA-seq computational pipeline.

Usage:
    from pipeline.backend_api import RNASeqBackendAPI, AnalysisRequest

    api = RNASeqBackendAPI()
    datasets = api.list_available_datasets()
    request = AnalysisRequest(dataset_id="OSD-678")
    result = api.run_analysis(request)
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator

import pandas as pd

from pipeline.config_parser import load_dataset_config, DatasetConfig
from pipeline.input_validation import MetadataValidator
from pipeline.cli import run_pipeline

logger = logging.getLogger("pipeline.backend_api")

class AnalysisRequest(BaseModel):
    """Structured, validated analysis request from external AI orchestrator."""
    dataset_id: str = Field(..., description="Target dataset identifier (e.g. OSD-678, OSD-120)")
    contrast_id: Optional[str] = Field(None, description="Optional specific contrast ID to filter execution/summary")
    analysis_type: str = Field("DIFFERENTIAL_EXPRESSION", description="Analysis type string")
    fdr_cutoff: float = Field(0.05, description="False Discovery Rate significance threshold")
    lfc_cutoff: float = Field(1.0, description="Absolute log2 fold-change significance threshold")
    candidate_selection_mode: str = Field("SPECIFIED_LIST", description="Candidate gene selection mode")
    specified_candidates: Optional[List[str]] = Field(None, description="Optional custom candidate TAIR/gene IDs")

    @validator("dataset_id")
    def validate_dataset_id(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("dataset_id must be a non-empty string.")
        return v.strip().upper()

    @validator("analysis_type")
    def validate_analysis_type(cls, v):
        allowed = ["DIFFERENTIAL_EXPRESSION", "FACTORIAL_DESEQ2", "META_ANALYSIS"]
        if v not in allowed:
            raise ValueError(f"Unsupported analysis_type '{v}'. Must be one of {allowed}.")
        return v

    @validator("fdr_cutoff")
    def validate_fdr_cutoff(cls, v):
        if v <= 0.0 or v >= 1.0:
            raise ValueError(f"fdr_cutoff must be between 0.0 and 1.0 strictly. Got: {v}")
        return v

    @validator("lfc_cutoff")
    def validate_lfc_cutoff(cls, v):
        if v < 0.0:
            raise ValueError(f"lfc_cutoff must be non-negative. Got: {v}")
        return v

class DatasetMetadata(BaseModel):
    """Metadata summary of an available dataset configuration."""
    dataset_id: str
    organism: str
    config_path: str
    description: Optional[str] = None
    samples_count: int = 0
    factors: Dict[str, List[str]]
    reference_levels: Dict[str, str]
    contrast_ids: List[str]
    interaction_contrast_ids: List[str]
    candidate_count: int

class ContrastMetadata(BaseModel):
    """Metadata of a valid contrast defined in a dataset config."""
    id: str
    factor: str
    numerator: str
    denominator: str
    description: str

class PreflightValidationResult(BaseModel):
    """Structured result from dry-run pre-flight validation."""
    dataset_id: str
    is_valid: bool
    sample_count: int
    gene_count: int
    min_replicates: int
    replicate_status: str
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

class AnalysisErrorResult(BaseModel):
    """Machine-readable error/rejection result returned when validation or backend fails."""
    dataset_id: str
    error_type: str
    message: str
    details: List[str] = Field(default_factory=list)
    rejected_by_backend: bool = True

class AnalysisResult(BaseModel):
    """Machine-readable execution result returned by the backend API."""
    dataset_id: str
    execution_status: str
    output_dir: str
    analysis_summary_path: str
    candidate_comparison_csv_path: str
    provenance_manifest_path: str
    contrast_count: int
    candidate_count: int
    summary_metrics: Dict[str, Any]

class RNASeqBackendAPI:
    """Canonical programmatic API gateway for deterministic RNA-seq backend execution."""

    def __init__(self, configs_dir: str = "configs"):
        self.configs_dir = Path(configs_dir).resolve()
        self._dataset_config_map: Dict[str, Path] = {}
        self._refresh_dataset_cache()

    def _refresh_dataset_cache(self):
        """Discover all valid dataset YAML configurations in configs_dir."""
        self._dataset_config_map.clear()
        if not self.configs_dir.exists():
            logger.warning(f"Configs directory missing: {self.configs_dir}")
            return

        for yaml_file in self.configs_dir.glob("*.yaml"):
            try:
                config = load_dataset_config(str(yaml_file))
                self._dataset_config_map[config.dataset_id.upper()] = yaml_file
            except Exception as e:
                logger.warning(f"Failed to parse config file {yaml_file}: {e}")

    def list_available_datasets(self) -> List[DatasetMetadata]:
        """Discover and return metadata for all configured datasets."""
        self._refresh_dataset_cache()
        datasets = []
        for dataset_id, yaml_path in sorted(self._dataset_config_map.items()):
            config = load_dataset_config(str(yaml_path))
            c_ids = [c.id for c in config.contrasts]
            ic_ids = [ic.id for ic in config.interaction_contrasts]
            cand_count = len(config.candidate_selection.specified_genes)
            
            # Calculate samples_count from sample metadata file
            samples_count = 0
            try:
                sample_df = pd.read_csv(config.sample_metadata_path)
                samples_count = len(sample_df)
            except Exception as e:
                logger.warning(f"Failed to read sample metadata for {dataset_id}: {e}")
            
            # Extract description from first contrast if available
            description = None
            if config.contrasts and len(config.contrasts) > 0:
                description = config.contrasts[0].description
            
            datasets.append(DatasetMetadata(
                dataset_id=config.dataset_id,
                organism=config.organism,
                config_path=str(yaml_path),
                description=description,
                samples_count=samples_count,
                factors=config.factors,
                reference_levels=config.reference_levels,
                contrast_ids=c_ids,
                interaction_contrast_ids=ic_ids,
                candidate_count=cand_count
            ))
        return datasets

    def list_available_contrasts(self, dataset_id: str) -> List[ContrastMetadata]:
        """Return list of valid contrasts for a specified dataset."""
        dataset_key = dataset_id.strip().upper()
        if dataset_key not in self._dataset_config_map:
            raise ValueError(f"Unknown dataset_id '{dataset_id}'. Available: {list(self._dataset_config_map.keys())}")
        
        config = load_dataset_config(str(self._dataset_config_map[dataset_key]))
        contrasts = []
        for c in config.contrasts:
            contrasts.append(ContrastMetadata(
                id=c.id,
                factor=c.factor,
                numerator=c.numerator,
                denominator=c.denominator,
                description=c.description
            ))
        return contrasts

    def validate_request(self, request: AnalysisRequest) -> bool:
        """Validate request against available dataset configurations and constraints."""
        dataset_key = request.dataset_id.strip().upper()
        if dataset_key not in self._dataset_config_map:
            raise ValueError(f"Unknown dataset_id '{request.dataset_id}'. Available: {list(self._dataset_config_map.keys())}")
            
        config = load_dataset_config(str(self._dataset_config_map[dataset_key]))
        
        if request.contrast_id:
            valid_c_ids = [c.id for c in config.contrasts] + [ic.id for ic in config.interaction_contrasts]
            if request.contrast_id not in valid_c_ids:
                raise ValueError(f"Invalid contrast_id '{request.contrast_id}' for dataset {dataset_key}. Valid contrasts: {valid_c_ids}")
                
        return True

    def validate_preflight(self, dataset_id: str) -> PreflightValidationResult:
        """Perform dry-run pre-flight validation of input metadata and replicate rules."""
        dataset_key = dataset_id.strip().upper()
        if dataset_key not in self._dataset_config_map:
            return PreflightValidationResult(
                dataset_id=dataset_id,
                is_valid=False,
                sample_count=0,
                gene_count=0,
                min_replicates=0,
                replicate_status="INVALID",
                errors=[f"Unknown dataset_id '{dataset_id}'. Available: {list(self._dataset_config_map.keys())}"]
            )

        config = load_dataset_config(str(self._dataset_config_map[dataset_key]))
        df_counts = pd.read_csv(config.counts_matrix_path)
        metadata = pd.read_csv(config.sample_metadata_path)

        is_valid_meta, meta_errs = MetadataValidator.validate_sample_sheet(metadata)
        
        group_col = config.combined_group_column or list(config.factors.keys())[0]
        if config.combined_group_column and config.combined_group_column not in metadata.columns:
            group_cols = list(config.factors.keys())
            metadata[config.combined_group_column] = metadata[group_cols[0]].astype(str)
            for col in group_cols[1:]:
                metadata[config.combined_group_column] += "_" + metadata[col].astype(str)

        rep_audit = MetadataValidator.audit_replicates(metadata, group_col)

        return PreflightValidationResult(
            dataset_id=config.dataset_id,
            is_valid=is_valid_meta and (rep_audit["min_replicates"] >= 1),
            sample_count=len(metadata),
            gene_count=len(df_counts),
            min_replicates=rep_audit["min_replicates"],
            replicate_status=rep_audit["status"],
            warnings=rep_audit.get("warnings", []),
            errors=meta_errs if not is_valid_meta else []
        )

    def run_analysis_safe(self, request: AnalysisRequest) -> Any:
        """Safe wrapper returning (success: bool, result: Optional[AnalysisResult], error: Optional[AnalysisErrorResult])."""
        try:
            result = self.run_analysis(request)
            return True, result, None
        except Exception as e:
            logger.error("Backend execution rejected: %s", e)
            err_res = AnalysisErrorResult(
                dataset_id=request.dataset_id,
                error_type=type(e).__name__,
                message=str(e),
                details=[str(e)],
                rejected_by_backend=True
            )
            return False, None, err_res

    def run_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        """Execute deterministic pipeline for request and return machine-readable AnalysisResult."""
        self.validate_request(request)
        dataset_key = request.dataset_id.strip().upper()
        config_path = str(self._dataset_config_map[dataset_key])
        
        # Check if pre-computed results already exist to avoid unnecessary expensive re-computation
        try:
            return self.get_result(dataset_key)
        except FileNotFoundError:
            # Execute existing deterministic Phase 5C CLI pipeline runner
            run_pipeline(config_path)
            return self.get_result(dataset_key)

    def get_result(self, dataset_id: str) -> AnalysisResult:
        """Retrieve structured AnalysisResult for a previously executed dataset."""
        dataset_key = dataset_id.strip().upper()
        if dataset_key not in self._dataset_config_map:
            raise ValueError(f"Unknown dataset_id '{dataset_id}'. Available: {list(self._dataset_config_map.keys())}")
            
        config = load_dataset_config(str(self._dataset_config_map[dataset_key]))
        out_dir = Path(config.output_dir).resolve()
        
        clean_id = dataset_key.lower().replace("-", "")
        summary_json_path = out_dir / f"{clean_id}_analysis_summary.json"
        cand_csv_path = out_dir / "candidate_validation" / f"{clean_id}_candidate_comparison.csv"
        prov_json_path = out_dir / f"{clean_id}_provenance_manifest.json"
        
        if not summary_json_path.exists():
            raise FileNotFoundError(f"Analysis summary file missing for {dataset_id} at {summary_json_path}. Run analysis first.")
            
        with open(summary_json_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
            
        c_count = len(config.contrasts) + len(config.interaction_contrasts)
        cand_count = len(summary_data.get("candidate_gene_outcomes", []))
        
        return AnalysisResult(
            dataset_id=config.dataset_id,
            execution_status="SUCCESS",
            output_dir=str(out_dir),
            analysis_summary_path=str(summary_json_path),
            candidate_comparison_csv_path=str(cand_csv_path),
            provenance_manifest_path=str(prov_json_path),
            contrast_count=c_count,
            candidate_count=cand_count,
            summary_metrics=summary_data.get("contrast_summary_metrics", {})
        )

    def get_provenance(self, dataset_id: str) -> Dict[str, Any]:
        """Retrieve execution provenance manifest dictionary for a dataset."""
        dataset_key = dataset_id.strip().upper()
        if dataset_key not in self._dataset_config_map:
            raise ValueError(f"Unknown dataset_id '{dataset_id}'. Available: {list(self._dataset_config_map.keys())}")
            
        config = load_dataset_config(str(self._dataset_config_map[dataset_key]))
        out_dir = Path(config.output_dir).resolve()
        clean_id = dataset_key.lower().replace("-", "")
        prov_json_path = out_dir / f"{clean_id}_provenance_manifest.json"
        
        if not prov_json_path.exists():
            raise FileNotFoundError(f"Provenance manifest missing for {dataset_id} at {prov_json_path}. Run analysis first.")
            
        with open(prov_json_path, "r", encoding="utf-8") as f:
            return json.load(f)
