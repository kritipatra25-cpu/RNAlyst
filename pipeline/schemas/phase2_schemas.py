"""
Phase 2 Pydantic Schemas for LLM Interpretation & Knowledge Retrieval Layer.
Enforces strict typing, multi-dimensional confidence decomposition, and citation verification.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class VerifiedCitation(BaseModel):
    citation_id: str
    source_type: str  # OSDR_PUBLICATION, PEER_REVIEWED_PAPER, PATHWAY_DATABASE
    osd_accession: Optional[str] = None
    gse_accession: Optional[str] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None
    title: str
    authors: str
    year: int
    retrieved_chunk_text: str
    verification_status: str = "VERIFIED_EXTERNAL_RECORD"

class DecomposedConfidence(BaseModel):
    statistical_status: str  # FDR_SIGNIFICANT, RAW_P_ONLY, NON_SIGNIFICANT
    confidence_label: str    # HIGH, MEDIUM, EXPLORATORY, UNSUBSTANTIATED
    statistical_significance: Dict[str, float]  # pvalue, padj
    effect_size_precision: Dict[str, Any]       # log2FC, shrunk_log2FC, lfcSE, effect_description
    directional_concordance: Dict[str, Any]      # sign_match_ref, concordance_pct
    literature_pathway_support: Dict[str, Any]  # chunk_count, verified_citation_ids

class GeneEvidence(BaseModel):
    gene_id: str
    symbol: Optional[str] = None
    annotation_source: str = "TAIR10"
    gene_id_verified: bool = True
    statistical_status: str  # FDR_SIGNIFICANT, RAW_P_ONLY, NON_SIGNIFICANT
    evidence_class: str = Field(..., description="Class A (Quantitative), Class B (Model), Class C (Literature/Pathway), Class D (Hypothesis), Class E (Causal Guardrail)")
    confidence_decomposition: DecomposedConfidence
    derived_from_class_a_gene_ids: List[str] = Field(default_factory=list)
    derived_from_class_c_citation_ids: List[str] = Field(default_factory=list)
    verified_citation_ids: List[str] = Field(default_factory=list)
    narrative_summary: str

class Phase2ProvenanceManifest(BaseModel):
    phase1_output_hashes: Dict[str, str]
    synthesis_mode: str = "DETERMINISTIC_REFERENCE"  # DETERMINISTIC_REFERENCE or LLM_SYNTHESIS
    provider_name: str = "DETERMINISTIC_TEMPLATE_GENERATOR"
    model_identifier: str = "rule_based_v1.0"
    api_version: str = "1.0.0"
    system_prompt_hash: str
    user_prompt_hash: str
    retrieval_query_string: str
    returned_chunk_ids: List[str]
    temperature: Optional[float] = None
    seed: Optional[int] = None
    input_payload_hash: str
    output_payload_hash: str
    execution_timestamp: str

class InterpretationReport(BaseModel):
    study_id: str = "OSD-120"
    contrast: str = "Space Flight vs Ground Control"
    causal_guardrail_statement: str = "The analysis and interpretation describe spaceflight-associated transcriptional differences relative to ground control under light-treated root conditions at Day 13. They do NOT establish pure microgravity causality or biological replication."
    sample_size_warning: str = "Study limitation: Small sample size (N=3 vs N=3) limits statistical power under strict Benjamini-Hochberg FDR control (padj < 0.05). Unadjusted p-value candidate genes are retained strictly for exploratory hypothesis generation and must NOT be reported as FDR-significant."
    verified_citations: List[VerifiedCitation]
    gene_interpretations: List[GeneEvidence]
    provenance_manifest: Phase2ProvenanceManifest
