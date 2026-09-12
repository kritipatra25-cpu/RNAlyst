"""
Pydantic schemas for Phase 3 Constrained LLM Interpretation Layer.
Enforces 5 evidence-bound output categories, citation/chunk traceability,
frozen quantitative metadata references, and human-review gate metadata.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class Phase3ExploratoryHypothesis(BaseModel):
    model_config = ConfigDict(frozen=True)
    hypothesis_id: str
    hypothesis_label: str = "Hypothesis (Exploratory)"
    motivating_observation: str  # Category A reference
    supporting_evidence_chunk_ids: List[str]  # Category B/C chunk IDs
    supporting_citation_ids: List[str]  # Verified PMIDs/DOIs
    hypothesis_statement: str  # Must start with "Hypothesis (Exploratory):"
    is_established_mechanism: bool = False  # MUST ALWAYS BE FALSE

class Phase3GeneInterpretation(BaseModel):
    model_config = ConfigDict(frozen=True)
    gene_id: str
    symbol: Optional[str] = None
    statistical_status: str  # FDR_SIGNIFICANT, RAW_P_ONLY, NON_SIGNIFICANT
    quantitative_summary: str  # Category A
    literature_context: List[str]  # Category B
    database_annotations: List[str]  # Category C
    exploratory_hypotheses: List[Phase3ExploratoryHypothesis]  # Category D
    supporting_citation_ids: List[str]
    supporting_chunk_ids: List[str]
    uncertainty_notes: List[str]
    causal_guardrail_statement: str

class Phase3InterpretationReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    study_id: str = "OSD-120"
    contrast: str = "Space Flight vs Ground Control"
    gene_interpretations: List[Phase3GeneInterpretation]
    sample_size_warning: str
    provenance_manifest: Dict[str, Any]
    human_review_status: str = "PENDING_HUMAN_REVIEW"  # PENDING_HUMAN_REVIEW vs HUMAN_APPROVED
