"""
Citation Integrity Verifier for Phase 2 Interpretation Layer.
Strictly validates citation metadata and rejects fabricated/synthetic identifiers like XXXXX.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from pipeline.schemas.phase2_schemas import VerifiedCitation

class CitationVerifier:
    """Verifies that all citations originate from external retrieval databases."""

    REJECTED_PATTERNS = [
        r"XXXXX",
        r"dummy",
        r"placeholder",
        r"10\.1038/XXXXX",
        r"00000000",
        r"synthetic",
    ]

    def __init__(self, verified_records: List[Dict[str, Any]]):
        self.verified_database = {}
        for rec in verified_records:
            cid = rec.get("citation_id")
            if cid:
                self.verified_database[cid] = rec

    def is_synthetic_placeholder(self, text: str) -> bool:
        """Check if any field contains synthetic placeholder strings."""
        if not text:
            return False
        for pat in self.REJECTED_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return True
        return False

    def verify_citation(self, citation: VerifiedCitation) -> Tuple[bool, str]:
        """Verify citation integrity and reject hallucinated metadata."""
        # 1. Check for synthetic placeholders in any field
        fields_to_check = [
            citation.citation_id,
            citation.doi or "",
            citation.pmid or "",
            citation.title,
            citation.authors,
        ]
        for fld in fields_to_check:
            if self.is_synthetic_placeholder(fld):
                return False, f"Citation contains rejected synthetic placeholder: '{fld}'"

        # 2. Verify citation exists in verified retrieval database
        if citation.citation_id not in self.verified_database:
            return False, f"Citation ID '{citation.citation_id}' not found in verified retrieval records"

        record = self.verified_database[citation.citation_id]
        if citation.title != record.get("title"):
            return False, f"Citation title mismatch for '{citation.citation_id}'"

        return True, "VERIFIED"

    def verify_citation_dict(self, rec: Dict[str, Any]) -> Tuple[bool, Optional[VerifiedCitation], str]:
        """Verify citation dictionary record and return (is_valid, VerifiedCitation, message)."""
        cid = rec.get("citation_id", "")
        pmid = rec.get("pmid")
        doi = rec.get("doi")
        title = rec.get("title", "")
        authors = rec.get("authors", "")
        year = rec.get("year", 0)

        # Check synthetic placeholders
        for fld in [cid, doi or "", pmid or "", title, authors]:
            if self.is_synthetic_placeholder(fld):
                return False, None, f"Citation contains rejected synthetic placeholder: '{fld}'"

        # Check pmid format if present
        if pmid and (len(pmid) > 10 or not pmid.isdigit()):
            return False, None, f"Invalid or synthetic PMID format: '{pmid}'"

        # Check doi format if present
        if doi and not doi.startswith("10."):
            return False, None, f"Invalid or malformed DOI format: '{doi}'"

        if cid not in self.verified_database:
            return False, None, f"PMID not found in verified external database: '{cid}'"

        cit_obj = VerifiedCitation(
            citation_id=cid,
            source_type=rec.get("source_type", "PEER_REVIEWED_PAPER"),
            pmid=pmid,
            doi=doi,
            title=title,
            authors=authors,
            year=year,
            retrieved_chunk_text=rec.get("retrieved_chunk_text", ""),
            verification_status="VERIFIED_EXTERNAL_RECORD"
        )

        return True, cit_obj, "VERIFIED"

    def filter_and_validate_citations(self, citations: List[VerifiedCitation]) -> List[VerifiedCitation]:
        """Filter list of citations and return only verified items."""
        valid_citations = []
        for cit in citations:
            is_valid, msg = self.verify_citation(cit)
            if is_valid:
                valid_citations.append(cit)
            else:
                print(f"[CITATION VERIFIER REJECTED]: {msg}")
        return valid_citations

