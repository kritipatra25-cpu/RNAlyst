"""
Gene Identity Verifier for Phase 2 Interpretation Layer.
Ensures every gene symbol or AGI identifier is traceable to Phase 1 data or verified TAIR10 annotations.
"""

from typing import Set, Tuple, List, Optional, Dict, Any
import pandas as pd

class GeneIdentityVerifier:
    """Validates gene identifiers against Phase 1 datasets and TAIR10 annotation records."""

    def __init__(self, phase1_gene_ids: Set[str], external_gene_map: Dict[str, str] = None):
        self.phase1_gene_ids = set(phase1_gene_ids)
        self.external_gene_map = external_gene_map if external_gene_map else {}

    def is_valid_gene(self, gene_id: str) -> bool:
        """Check if gene ID is present in Phase 1 results or external TAIR10 records."""
        if not gene_id or not isinstance(gene_id, str):
            return False
        clean_id = gene_id.strip()
        return (clean_id in self.phase1_gene_ids) or (clean_id in self.external_gene_map)

    def verify_gene(self, gene_id: str) -> Tuple[bool, str, Optional[str], str]:
        """
        Verify gene ID and return (is_verified, gene_id, symbol, annotation_source).
        Missing symbol does NOT mark the gene as invalid.
        """
        clean_id = gene_id.strip() if gene_id else ""
        if self.is_valid_gene(clean_id):
            symbol = self.external_gene_map.get(clean_id, None)
            return True, clean_id, symbol, "TAIR10"
        return False, clean_id, None, "UNVERIFIED"

    def filter_valid_genes(self, gene_ids: List[str]) -> List[str]:
        """Filter list of gene IDs and retain only valid items."""
        return [g for g in gene_ids if self.is_valid_gene(g)]
