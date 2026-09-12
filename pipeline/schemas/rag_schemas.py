"""
Pydantic schemas for Phase 2 RAG / Knowledge Retrieval Layer.
Strictly separates peer-reviewed Literature Citations from Database Records,
enforces contextual relevance tier assignment (Tiers 1, 2, 3), and provides
frozen read-only Phase 1 quantitative metadata wrappers.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class VerifiedLiteratureCitation(BaseModel):
    model_config = ConfigDict(frozen=True)
    citation_id: str
    pmid: Optional[str] = None
    doi: Optional[str] = None
    title: str
    authors: str
    year: int
    source_database: str = "PubMed"
    retrieval_timestamp: str
    retrieved_chunk_text: str
    verification_status: str = "VERIFIED_EXTERNAL_RECORD"

class VerifiedDatabaseRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    database: str  # TAIR, GO, KEGG, REACTOME, MAPMAN, OSDR
    record_id: str  # GO ID, KEGG ID, Reactome ID, etc.
    record_version: Optional[str] = "v1.0"
    annotation_text: str
    association_type: str = "DIRECT_ANNOTATION"  # DIRECT_ANNOTATION, PATHWAY_ASSOCIATION, LITERATURE_BASED_MECHANISTIC_ASSOCIATION
    verification_status: str = "VERIFIED_DATABASE_ENTRY"

class VerifiedEvidenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    gene_id: str
    evidence_type: str  # LITERATURE, GO, KEGG, REACTOME, MAPMAN, OSDR
    evidence_tier: int = Field(..., ge=1, le=3, description="Contextual relevance to OSD-120: 1=Direct OSD-120 study, 2=Arabidopsis spaceflight/root, 3=General plant process")
    literature_citation: Optional[VerifiedLiteratureCitation] = None
    database_record: Optional[VerifiedDatabaseRecord] = None
    chunk_id: str
    claim_text: str
    verification_status: str = "VERIFIED"

class ReadonlyQuantitativeMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)
    gene_id: str
    baseMean: float
    log2FoldChange: float
    shrunk_log2FoldChange: float
    lfcSE: float
    pvalue: float
    padj: float
    statistical_status: str  # FDR_SIGNIFICANT, RAW_P_ONLY, NON_SIGNIFICANT

class VerifiedEvidencePackage(BaseModel):
    model_config = ConfigDict(frozen=True)
    gene_id: str
    symbol: Optional[str] = None
    annotation_source: str = "TAIR10"
    quantitative_metadata: ReadonlyQuantitativeMetadata
    evidence_records: List[VerifiedEvidenceRecord]
    unresolved_gene_status: bool = False

class RAGRetrievalReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    study_id: str = "OSD-120"
    contrast: str = "Space Flight vs Ground Control"
    candidates_queried: List[str]
    sources_searched: List[str]
    evidence_packages: List[VerifiedEvidencePackage]
    verified_literature_count: int
    verified_database_count: int
    tier_counts: Dict[str, int]
    unresolved_genes: List[str]
    retrieval_failures: List[Dict[str, Any]]
