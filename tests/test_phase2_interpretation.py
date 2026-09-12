"""
Unit Test Suite for Phase 2 LLM Interpretation & Knowledge Retrieval Layer.
Validates all 6 scientific safeguards and core system components.
"""

import pytest
import pandas as pd
from pipeline.schemas.phase2_schemas import (
    VerifiedCitation,
    DecomposedConfidence,
    GeneEvidence,
    InterpretationReport
)
from analysis.interpretation.citation_verifier import CitationVerifier
from analysis.interpretation.gene_identity_verifier import GeneIdentityVerifier
from analysis.interpretation.rag_engine import ExtensibleRAGEngine
from analysis.interpretation.llm_interpreter import LLMInterpretationEngine

@pytest.fixture
def mock_verified_record():
    return {
        "citation_id": "CIT_PUBMED_29122345",
        "source_type": "PEER_REVIEWED_PAPER",
        "title": "Transcriptomic analysis of Arabidopsis thaliana root orientation",
        "authors": "Kruse CPS, et al.",
        "year": 2017,
        "pmid": "29122345",
        "doi": "10.1038/s41598-017-16441-x",
        "retrieved_chunk_text": "Light-grown Arabidopsis roots in spaceflight display upregulation of cell wall enzymes."
    }

@pytest.fixture
def mock_data_bundle():
    de_df = pd.DataFrame({
        "gene_id": ["AT2G30210", "AT5G49440", "AT1G73500"],
        "baseMean": [100.0, 500.0, 20.0],
        "log2FoldChange": [1.0, 1.2, -0.8],
        "shrunk_log2FoldChange": [0.95, 1.15, -0.75],
        "lfcSE": [0.2, 0.25, 0.3],
        "pvalue": [0.0001, 0.0002, 0.001],
        "padj": [0.05, 0.06, 0.15]
    })
    return {
        "differential_expression": de_df,
        "vst_counts": pd.DataFrame(),
        "summary": {"total_genes": 32833},
        "provenance": {"contrast": "Space Flight vs Ground Control"},
        "concordance": {"primary_metrics": {"directional_concordance_rate_pct": 85.99}}
    }

def test_citation_verifier_rejects_synthetic_placeholder(mock_verified_record):
    verifier = CitationVerifier([mock_verified_record])

    # Valid citation
    valid_cit = VerifiedCitation(
        citation_id="CIT_PUBMED_29122345",
        source_type="PEER_REVIEWED_PAPER",
        title="Transcriptomic analysis of Arabidopsis thaliana root orientation",
        authors="Kruse CPS, et al.",
        year=2017,
        pmid="29122345",
        doi="10.1038/s41598-017-16441-x",
        retrieved_chunk_text="Light-grown Arabidopsis roots in spaceflight display upregulation of cell wall enzymes."
    )
    is_valid, _ = verifier.verify_citation(valid_cit)
    assert is_valid is True

    # Invalid citation with synthetic placeholder XXXXX
    invalid_cit = VerifiedCitation(
        citation_id="CIT_PUBMED_29122345",
        source_type="PEER_REVIEWED_PAPER",
        title="Transcriptomic analysis of Arabidopsis thaliana root orientation",
        authors="Kruse CPS, et al.",
        year=2017,
        pmid="29122345",
        doi="10.1038/XXXXX",  # Synthetic DOI!
        retrieved_chunk_text="Light-grown Arabidopsis roots in spaceflight display upregulation of cell wall enzymes."
    )
    is_valid_inv, msg = verifier.verify_citation(invalid_cit)
    assert is_valid_inv is False
    assert "synthetic placeholder" in msg.lower()

def test_gene_identity_verifier():
    phase1_genes = {"AT2G30210", "AT5G49440", "AT1G73500"}
    verifier = GeneIdentityVerifier(phase1_genes)

    assert verifier.is_valid_gene("AT2G30210") is True
    assert verifier.is_valid_gene("AT5G49440") is True
    assert verifier.is_valid_gene("INVALID_GENE_123") is False
    assert verifier.is_valid_gene("AT99G99999") is False

def test_extensible_rag_engine():
    rag = ExtensibleRAGEngine()
    citations = rag.query_knowledge_base(["auxin", "cell wall", "root"], top_k=3)

    assert len(citations) > 0
    assert any(c.citation_id == "CIT_PUBMED_29122345" for c in citations)
    assert any("PATHWAY" in c.source_type for c in citations)

def test_llm_interpreter_guardrails(mock_data_bundle):
    file_hashes = {"de_csv": "abc123hash"}
    engine = LLMInterpretationEngine(mock_data_bundle, file_hashes)
    report = engine.generate_deterministic_interpretation()

    # 1. Causal guardrail statement presence
    assert "spaceflight-associated transcriptional differences relative to ground control" in report.causal_guardrail_statement

    # 2. Verify report integrity
    is_valid, errors = engine.verify_interpretation_report(report)
    assert is_valid is True
    assert len(errors) == 0

    # 3. Hypothesis traceability check
    class_d_items = [ev for ev in report.gene_interpretations if "Class D" in ev.evidence_class]
    for item in class_d_items:
        assert len(item.derived_from_class_a_gene_ids) > 0 or len(item.derived_from_class_c_citation_ids) > 0
