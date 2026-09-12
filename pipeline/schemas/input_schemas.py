"""Input schemas for FASTQ, sample sheet, and metadata validation."""
from enum import Enum
from typing import List, Optional, Dict
from dataclasses import dataclass, field

class LayoutType(str, Enum):
    SINGLE = "SINGLE"
    PAIRED = "PAIRED"

@dataclass
class SampleMetadata:
    sample_id: str
    biological_unit_id: str
    condition: str
    batch: Optional[str] = None
    genotype: Optional[str] = None
    tissue: Optional[str] = None
    sex: Optional[str] = None
    timepoint: Optional[str] = None
    is_technical_replicate: bool = False
    technical_replicate_group: Optional[str] = None

@dataclass
class SampleSheetInput:
    organism: str
    layout: LayoutType
    samples: List[SampleMetadata]
    fastq_files: Dict[str, List[str]]
    reference_group: str
    comparison_group: str
    design_formula: Optional[str] = None

    def __post_init__(self):
        supported = ["Arabidopsis thaliana", "Homo sapiens", "Mus musculus"]
        if self.organism not in supported:
            raise ValueError(f"Unsupported organism: {self.organism}. Must be one of {supported}")
