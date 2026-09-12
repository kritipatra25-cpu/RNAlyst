"""Schemas for differential expression, enrichment, and AI results."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class DEGeneResult(BaseModel):
    gene_id: str
    gene_symbol: Optional[str] = None
    base_mean: float
    log2_fold_change: float
    shrunken_log2_fc: float
    lfc_se: float
    p_value: float
    padj: float
    status: str  # UPREGULATED | DOWNREGULATED | NOT_SIGNIFICANT | NOT_ESTIMABLE
    annotation: Optional[Dict[str, Any]] = None


class EnrichmentResultItem(BaseModel):
    term_id: str
    term_name: str
    category: str
    p_value: float
    adjusted_p_value: float
    odds_ratio: Optional[float] = None
    combined_score: Optional[float] = None
    genes: List[str]
    leading_edge_genes: Optional[List[str]] = None


class EvidenceClassification(str):
    OBSERATION = "OBSERVATION"
    INFERENCE = "INFERENCE"
    LITERATURE_SUPPORTED = "LITERATURE_SUPPORTED_MECHANISM"
    HYPOTHESIS = "HYPOTHESIS"


class AIInterpretationClaim(BaseModel):
    claim_id: str
    text: str
    evidence_type: str  # OBSERVATION | INFERENCE | LITERATURE_SUPPORTED_MECHANISM | HYPOTHESIS
    supporting_gene_ids: List[str] = []
    citation_pmid_doi: Optional[str] = None
    guardrail_passed: bool = True
    rejection_reason: Optional[str] = None
