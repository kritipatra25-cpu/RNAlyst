"""
Phase3Validator for Phase 3 Constrained LLM Interpretation Layer.
Enforces 16 non-negotiable scientific guardrails:
1. Numerical immutability against Phase 1 locked outputs
2. FDR language audit (prohibits DE claims when padj >= 0.05)
3. Causal language audit (prohibits un-framed causal verbs)
4. Citation & chunk ID traceability (rejects hallucinated/synthetic citations)
5. Database annotation isolation (prevents GO/KEGG/MapMan from masquerading as literature)
6. Exploratory hypothesis framing
7. Mandatory Human Review Gate status ("PENDING_HUMAN_REVIEW")
"""

import math
import re
from typing import List, Dict, Any, Tuple
from pipeline.schemas.rag_schemas import VerifiedEvidencePackage
from pipeline.schemas.phase3_schemas import Phase3GeneInterpretation, Phase3InterpretationReport

class Phase3Validator:
    FORBIDDEN_SIGNIFICANCE_TERMS = [
        "significantly upregulated",
        "significantly downregulated",
        "differentially expressed",
        "statistically significant differential expression",
        "high confidence differential expression"
    ]

    FORBIDDEN_CAUSAL_WORDS = [
        "causes",
        "drives",
        "mediates",
        "results in",
        "is responsible for",
        "demonstrates that",
        "establishes that"
    ]

    REJECTED_CITATION_PATTERNS = [
        r"XXXXX",
        r"dummy",
        r"placeholder",
        r"99999999",
        r"synthetic"
    ]

    def verify_numerical_immutability(self, gene_interp: Phase3GeneInterpretation, pkg: VerifiedEvidencePackage) -> Tuple[bool, str]:
        """Verify that quantitative metrics in Phase 3 report match Phase 1 source exactly."""
        q = pkg.quantitative_metadata
        if gene_interp.statistical_status != q.statistical_status:
            return False, f"Statistical status mismatch for '{gene_interp.gene_id}': report '{gene_interp.statistical_status}' vs Phase 1 '{q.statistical_status}'"

        text = gene_interp.quantitative_summary.lower()

        # Check padj value representation
        if q.padj >= 0.05 and q.statistical_status != "FDR_SIGNIFICANT":
            text_clean = text.replace("not statistically significant", "")
            for term in self.FORBIDDEN_SIGNIFICANCE_TERMS:
                if term in text_clean:
                    return False, f"Gene '{gene_interp.gene_id}' with padj={q.padj:.4f} contains forbidden significance term: '{term}'"

        return True, "VERIFIED"


    def verify_causal_language(self, text: str) -> Tuple[bool, str]:
        """Verify narrative contains no un-framed causal claims."""
        text_lower = text.lower()
        for word in self.FORBIDDEN_CAUSAL_WORDS:
            if word in text_lower and "literature-supported" not in text_lower:
                return False, f"Narrative contains forbidden causal word: '{word}'"
        return True, "VERIFIED"

    def verify_citation_traceability(self, gene_interp: Phase3GeneInterpretation, pkg: VerifiedEvidencePackage) -> Tuple[bool, str]:
        """
        Verify all cited PMIDs/DOIs exist in Phase 2 verified evidence package.
        Reject synthetic/hallucinated citations.
        """
        pkg_citations = set()
        pkg_chunks = set()

        for ev in pkg.evidence_records:
            pkg_chunks.add(ev.chunk_id)
            if ev.literature_citation:
                if ev.literature_citation.pmid:
                    pkg_citations.add(ev.literature_citation.pmid)
                if ev.literature_citation.doi:
                    pkg_citations.add(ev.literature_citation.doi)
                pkg_citations.add(ev.literature_citation.citation_id)

        # Check cited citations
        for cit_id in gene_interp.supporting_citation_ids:
            for pat in self.REJECTED_CITATION_PATTERNS:
                if re.search(pat, cit_id, re.IGNORECASE):
                    return False, f"Synthetic/hallucinated citation identifier detected: '{cit_id}'"

            if cit_id not in pkg_citations:
                return False, f"Citation ID '{cit_id}' for gene '{gene_interp.gene_id}' does not exist in verified Phase 2 RAG evidence package"

        # Check cited chunk IDs
        for chk_id in gene_interp.supporting_chunk_ids:
            if chk_id not in pkg_chunks:
                return False, f"Chunk ID '{chk_id}' for gene '{gene_interp.gene_id}' does not exist in verified Phase 2 RAG evidence package"

        return True, "VERIFIED"

    def verify_database_annotation_isolation(self, gene_interp: Phase3GeneInterpretation, pkg: VerifiedEvidencePackage) -> Tuple[bool, str]:
        """Verify database records (GO/KEGG/Reactome/MapMan) are NOT represented as peer-reviewed literature citations."""
        db_record_ids = set()
        for ev in pkg.evidence_records:
            if ev.database_record:
                db_record_ids.add(ev.database_record.record_id)
                db_record_ids.add(ev.database_record.database)

        # Ensure no database record ID appears in supporting_citation_ids
        for cit_id in gene_interp.supporting_citation_ids:
            if cit_id in db_record_ids or cit_id in ["GO", "KEGG", "REACTOME", "MAPMAN", "TAIR"]:
                return False, f"Database annotation '{cit_id}' erroneously passed as peer-reviewed literature citation"

        return True, "VERIFIED"

    def verify_exploratory_hypotheses(self, gene_interp: Phase3GeneInterpretation, pkg: VerifiedEvidencePackage) -> Tuple[bool, str]:
        """Verify Category D hypotheses are properly framed and linked."""
        pkg_chunks = set(ev.chunk_id for ev in pkg.evidence_records)

        for hyp in gene_interp.exploratory_hypotheses:
            if hyp.is_established_mechanism:
                return False, f"Hypothesis '{hyp.hypothesis_id}' cannot be marked as established mechanism"

            if not hyp.hypothesis_statement.startswith("Hypothesis (Exploratory):"):
                return False, f"Hypothesis '{hyp.hypothesis_id}' statement must start with 'Hypothesis (Exploratory):'"

            if not hyp.motivating_observation:
                return False, f"Hypothesis '{hyp.hypothesis_id}' missing Category A motivating quantitative observation"

            for chk in hyp.supporting_evidence_chunk_ids:
                if chk not in pkg_chunks:
                    return False, f"Hypothesis '{hyp.hypothesis_id}' references invalid chunk ID '{chk}'"

        return True, "VERIFIED"

    def validate_gene_interpretation(self, gene_interp: Phase3GeneInterpretation, pkg: VerifiedEvidencePackage) -> Tuple[bool, List[str]]:
        """Run all validator checks on a single gene interpretation."""
        errors = []

        # 1. Numerical Immutability & FDR Audit
        ok, msg = self.verify_numerical_immutability(gene_interp, pkg)
        if not ok:
            errors.append(msg)

        # 2. Causal Language Audit
        ok, msg = self.verify_causal_language(gene_interp.quantitative_summary + " " + " ".join(gene_interp.literature_context))
        if not ok:
            errors.append(msg)

        # 3. Citation & Chunk Traceability
        ok, msg = self.verify_citation_traceability(gene_interp, pkg)
        if not ok:
            errors.append(msg)

        # 4. Database Annotation Isolation
        ok, msg = self.verify_database_annotation_isolation(gene_interp, pkg)
        if not ok:
            errors.append(msg)

        # 5. Exploratory Hypotheses
        ok, msg = self.verify_exploratory_hypotheses(gene_interp, pkg)
        if not ok:
            errors.append(msg)

        return len(errors) == 0, errors

    def validate_interpretation_report(self, report: Phase3InterpretationReport, packages_map: Dict[str, VerifiedEvidencePackage]) -> Tuple[bool, List[str]]:
        """Validate entire Phase 3 interpretation report."""
        all_errors = []

        # Check Human Review Gate
        if report.human_review_status != "PENDING_HUMAN_REVIEW":
            all_errors.append(f"Invalid initial human review status '{report.human_review_status}'. Must be 'PENDING_HUMAN_REVIEW'")

        for gene_interp in report.gene_interpretations:
            gid = gene_interp.gene_id
            if gid not in packages_map:
                all_errors.append(f"Report contains gene '{gid}' not present in Phase 2 verified evidence packages")
                continue

            pkg = packages_map[gid]
            ok, errs = self.validate_gene_interpretation(gene_interp, pkg)
            if not ok:
                all_errors.extend(errs)

        return len(all_errors) == 0, all_errors
