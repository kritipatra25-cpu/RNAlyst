"""
Dataset Configuration Schema and Parser for Bulk RNA-seq Analysis Platform.

Validates dataset YAML configurations deterministically before analysis execution.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator

class ContrastConfig(BaseModel):
    id: str
    factor: str
    numerator: str
    denominator: str
    description: Optional[str] = None

class InteractionContrastConfig(BaseModel):
    id: str
    contrast_a: str
    contrast_b: str
    operation: str = "DIFFERENCE"

class CandidateSelectionConfig(BaseModel):
    mode: str = "FDR_THRESHOLD"  # FDR_THRESHOLD, TOP_N, or SPECIFIED_LIST
    fdr_cutoff: float = 0.05
    lfc_cutoff: float = 1.0
    specified_genes: List[str] = Field(default_factory=list)

class ExternalValidationConfig(BaseModel):
    reference_dataset_id: str
    reference_de_path: str

class DatasetConfig(BaseModel):
    dataset_id: str
    organism: str = "Arabidopsis thaliana"
    annotation_source: str = "TAIR10"
    
    counts_matrix_path: str
    sample_metadata_path: str
    sample_id_column: str = "sample_id"
    gene_id_column: str = "gene_id"
    
    design_formula: str = "~ group"
    combined_group_column: Optional[str] = "group"
    factors: Dict[str, List[str]]
    reference_levels: Dict[str, str]
    
    contrasts: List[ContrastConfig]
    interaction_contrasts: List[InteractionContrastConfig] = Field(default_factory=list)
    candidate_selection: CandidateSelectionConfig = Field(default_factory=CandidateSelectionConfig)
    external_validation: Optional[ExternalValidationConfig] = None
    custom_symbol_map: Optional[Dict[str, str]] = None
    annotation_file: Optional[str] = None
    output_dir: Optional[str] = None

    @validator("counts_matrix_path", "sample_metadata_path")
    def validate_path_exists(cls, v):
        path = Path(v)
        if not path.exists():
            raise FileNotFoundError(f"Configured dataset file path does not exist: {v}")
        return v

    @validator("factors", "reference_levels")
    def validate_factor_consistency(cls, v, values):
        return v

def load_dataset_config(config_path: str) -> DatasetConfig:
    """Load, parse, and validate a dataset YAML configuration file."""
    config_path = Path(config_path).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Dataset configuration file not found: {config_path}")
        
    with open(config_path, "r", encoding="utf-8") as f:
        raw_dict = yaml.safe_load(f)
        
    if not isinstance(raw_dict, dict):
        raise ValueError(f"Invalid YAML content in {config_path}: expected a dictionary.")
        
    # Resolve relative paths relative to repository root if needed
    repo_root = Path(os.getcwd())
    if "counts_matrix_path" in raw_dict:
        p = Path(raw_dict["counts_matrix_path"])
        if not p.is_absolute() and (repo_root / p).exists():
            raw_dict["counts_matrix_path"] = str(repo_root / p)
            
    if "sample_metadata_path" in raw_dict:
        p = Path(raw_dict["sample_metadata_path"])
        if not p.is_absolute() and (repo_root / p).exists():
            raw_dict["sample_metadata_path"] = str(repo_root / p)
            
    if "external_validation" in raw_dict and raw_dict["external_validation"] and "reference_de_path" in raw_dict["external_validation"]:
        p = Path(raw_dict["external_validation"]["reference_de_path"])
        if not p.is_absolute() and (repo_root / p).exists():
            raw_dict["external_validation"]["reference_de_path"] = str(repo_root / p)
            
    config = DatasetConfig(**raw_dict)
    
    if not config.output_dir:
        config.output_dir = f"results/{config.dataset_id.lower()}_analysis"
        
    return config
