"""
Phase3LLMAdapter for Phase 3 Constrained LLM Interpretation Layer.
Transforms Phase 2 VerifiedEvidencePackage objects into structured Phase 3 reports
without making uncontrolled API calls or fabricating claims/citations.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from pipeline.schemas.rag_schemas import VerifiedEvidencePackage, RAGRetrievalReport
from pipeline.schemas.phase3_schemas import (
    Phase3ExploratoryHypothesis,
    Phase3GeneInterpretation,
    Phase3InterpretationReport
)
from analysis.interpretation.phase3_validator import Phase3Validator

CAUSAL_GUARDRAIL_VERBATIM = (
    "The analysis and interpretation describe spaceflight-associated transcriptional differences "
    "relative to ground control under light-treated root conditions at Day 13. "
    "They do NOT establish pure microgravity causality or biological replication."
)

SAMPLE_SIZE_WARNING_VERBATIM = (
    "STATISTICAL POWER WARNING: OSD-120 utilizes N=3 spaceflight vs N=3 ground control samples. "
    "With 3 replicate pairs, DESeq2 has limited statistical power. Genes with unadjusted p < 0.05 "
    "but padj >= 0.05 (RAW_P_ONLY) are exploratory and require secondary orthogonal validation."
)

class Phase3LLMAdapter:
    """Constrained LLM Adapter for Phase 3 Evidence Synthesis."""

    def __init__(self, provider_name: str = "DETERMINISTIC_MOCK_LLM_V1"):
        self.provider_name = provider_name
        self.validator = Phase3Validator()

    def generate_gene_interpretation(self, pkg: VerifiedEvidencePackage) -> Phase3GeneInterpretation:
        """Synthesize a Phase3GeneInterpretation strictly from VerifiedEvidencePackage."""
        q = pkg.quantitative_metadata
        gid = pkg.gene_id

        # 1. Category A: Direct Quantitative Observation
        if q.statistical_status == "FDR_SIGNIFICANT":
            stat_desc = f"statistically significant under Benjamini-Hochberg FDR (padj = {q.padj:.4f} < 0.05)"
        elif q.statistical_status == "RAW_P_ONLY":
            stat_desc = f"raw p-value = {q.pvalue:.2e} < 0.05, but adjusted p-value = {q.padj:.4f} >= 0.05 (not statistically significant after FDR correction)"
        else:
            stat_desc = f"not statistically significant (p = {q.pvalue:.4f}, padj = {q.padj:.4f})"

        quant_summary = (
            f"In OSD-120 (spaceflight vs ground control in light-grown Arabidopsis roots), "
            f"gene {gid} exhibits shrunk log2FC = {q.shrunk_log2FoldChange:+.3f} (raw log2FC = {q.log2FoldChange:+.3f}, "
            f"lfcSE = {q.lfcSE:.3f}, baseMean = {q.baseMean:.1f}). "
            f"The response is {stat_desc}."
        )

        # 2. Category B: Literature Context & Category C: Database Annotations
        lit_context = []
        db_annotations = []
        supporting_cits = []
        supporting_chunks = []

        lit_chunk_map = []

        for rec in pkg.evidence_records:
            supporting_chunks.append(rec.chunk_id)
            if rec.literature_citation:
                cit = rec.literature_citation
                cit_id = cit.pmid or cit.doi or cit.citation_id
                supporting_cits.append(cit_id)
                lit_stmt = (
                    f"Literature record [{cit_id}] (Tier {rec.evidence_tier}, chunk {rec.chunk_id}): "
                    f"\"{rec.claim_text}\""
                )
                lit_context.append(lit_stmt)
                lit_chunk_map.append((rec.chunk_id, cit_id, rec.claim_text))

            elif rec.database_record:
                db = rec.database_record
                db_stmt = (
                    f"Database annotation ({db.database}:{db.record_id}, {db.association_type}, chunk {rec.chunk_id}): "
                    f"\"{db.annotation_text}\""
                )
                db_annotations.append(db_stmt)

        # Deduplicate
        supporting_cits = sorted(list(set(supporting_cits)))
        supporting_chunks = sorted(list(set(supporting_chunks)))

        # 3. Category D: Exploratory Hypotheses
        hypotheses = []
        if lit_chunk_map:
            for i, (chk_id, cit_id, claim) in enumerate(lit_chunk_map, 1):
                hyp = Phase3ExploratoryHypothesis(
                    hypothesis_id=f"HYP_{gid}_{i:02d}",
                    hypothesis_label="Hypothesis (Exploratory)",
                    motivating_observation=f"OSD-120 shrunk log2FC = {q.shrunk_log2FoldChange:+.3f}, padj = {q.padj:.4f}",
                    supporting_evidence_chunk_ids=[chk_id],
                    supporting_citation_ids=[cit_id],
                    hypothesis_statement=f"Hypothesis (Exploratory): Observed transcript alterations in {gid} may reflect contextual cell wall or stress responses as noted in prior study literature [{cit_id}].",
                    is_established_mechanism=False
                )
                hypotheses.append(hyp)

        # 4. Uncertainty Notes
        uncertainty = [SAMPLE_SIZE_WARNING_VERBATIM]
        if q.statistical_status == "RAW_P_ONLY":
            uncertainty.append(
                f"UNCERTAINTY: Gene {gid} has raw p = {q.pvalue:.2e} < 0.05 but padj = {q.padj:.4f} >= 0.05. "
                "Must be treated as exploratory hypothesis, NOT confirmed differential expression."
            )
        if not lit_context:
            uncertainty.append(f"UNCERTAINTY: No peer-reviewed literature evidence was retrieved for {gid}.")

        return Phase3GeneInterpretation(
            gene_id=gid,
            symbol=pkg.symbol,
            statistical_status=q.statistical_status,
            quantitative_summary=quant_summary,
            literature_context=lit_context,
            database_annotations=db_annotations,
            exploratory_hypotheses=hypotheses,
            supporting_citation_ids=supporting_cits,
            supporting_chunk_ids=supporting_chunks,
            uncertainty_notes=uncertainty,
            causal_guardrail_statement=CAUSAL_GUARDRAIL_VERBATIM
        )

    def generate_report(self, rag_report: RAGRetrievalReport) -> Phase3InterpretationReport:
        """Synthesize complete Phase 3 Interpretation Report."""
        gene_interps = []
        packages_map = {}

        for pkg in rag_report.evidence_packages:
            packages_map[pkg.gene_id] = pkg
            interp = self.generate_gene_interpretation(pkg)
            gene_interps.append(interp)

        timestamp = datetime.now(timezone.utc).isoformat()

        # Compute provenance hash
        payload_str = json.dumps([g.model_dump() for g in gene_interps], sort_keys=True)
        prov_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()[:16]

        provenance = {
            "execution_timestamp": timestamp,
            "provider_name": self.provider_name,
            "rag_report_candidates_count": len(rag_report.candidates_queried),
            "provenance_hash": prov_hash,
            "phase1_locked_reference": "results/osd120_primary_analysis/differential_expression.csv",
            "phase2_rag_reference": "results/osd120_phase2_interpretation/rag_retrieval_report.json"
        }

        report = Phase3InterpretationReport(
            study_id=rag_report.study_id,
            contrast=rag_report.contrast,
            gene_interpretations=gene_interps,
            sample_size_warning=SAMPLE_SIZE_WARNING_VERBATIM,
            provenance_manifest=provenance,
            human_review_status="PENDING_HUMAN_REVIEW"
        )

        # Validate generated report
        ok, errors = self.validator.validate_interpretation_report(report, packages_map)
        if not ok:
            raise ValueError(f"Phase 3 Validator rejected generated report: {errors}")

        return report
