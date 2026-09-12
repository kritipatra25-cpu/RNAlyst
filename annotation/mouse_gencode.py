"""
Mouse GENCODE M34 Gene Annotation Lookup Engine for Mus musculus.

Provides mapping from ENSEMBL gene IDs (e.g. ENSMUSG00000000001) to gene symbols,
descriptions, and biotypes.
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

# Sample Mouse GENCODE M34 reference dictionary for primary spaceflight candidate genes
MOUSE_GENCODE_BUILTIN = {
    "ENSMUSG00000000001": {"symbol": "Gai2", "name": "G protein subunit alpha i2", "biotype": "protein_coding"},
    "ENSMUSG00000000028": {"symbol": "Ccdc158", "name": "coiled-coil domain containing 158", "biotype": "protein_coding"},
    "ENSMUSG00000020167": {"symbol": "Cd44", "name": "CD44 antigen", "biotype": "protein_coding"},
    "ENSMUSG00000029304": {"symbol": "Hsp90aa1", "name": "heat shock protein 90 alpha family class A member 1", "biotype": "protein_coding"},
    "ENSMUSG00000025902": {"symbol": "Cyp2e1", "name": "cytochrome P450 family 2 subfamily e member 1", "biotype": "protein_coding"},
}

class MouseGENCODEAnnotator:
    """Annotator for Mus musculus GENCODE M34 gene IDs."""

    def __init__(self, annotation_file: Optional[str] = None):
        self.annotations = MOUSE_GENCODE_BUILTIN.copy()
        if annotation_file:
            self.load_annotation_table(annotation_file)

    def load_annotation_table(self, file_path: str):
        """Load external annotation table into memory."""
        try:
            df = pd.read_csv(file_path, sep="\t" if file_path.endswith(".tsv") else ",")
            for _, row in df.iterrows():
                gene_id = str(row.get("gene_id", "")).strip()
                if gene_id:
                    self.annotations[gene_id] = {
                        "symbol": str(row.get("symbol", gene_id)),
                        "name": str(row.get("description", "")),
                        "biotype": str(row.get("biotype", "protein_coding")),
                    }
            logger.info("Loaded %d mouse gene annotations from %s", len(self.annotations), file_path)
        except Exception as e:
            logger.error("Failed loading mouse annotation table %s: %s", file_path, e)

    def annotate_gene(self, gene_id: str) -> Dict[str, Any]:
        """Annotate single gene ID."""
        gid_clean = str(gene_id).strip()
        # Remove version suffix if present (e.g. ENSMUSG00000000001.4 -> ENSMUSG00000000001)
        gid_base = gid_clean.split(".")[0]

        if gid_base in self.annotations:
            ann = self.annotations[gid_base].copy()
            ann["gene_id"] = gid_clean
            return ann

        return {
            "gene_id": gid_clean,
            "symbol": gid_base,
            "name": "Uncharacterized Mouse transcript",
            "biotype": "unknown",
        }

    def annotate_dataframe(self, df: pd.DataFrame, gene_col: str = "gene_id") -> pd.DataFrame:
        """Annotate pandas DataFrame containing a gene ID column."""
        if gene_col not in df.columns:
            return df

        annotated_df = df.copy()
        symbols, names, biotypes = [], [], []

        for gid in annotated_df[gene_col]:
            ann = self.annotate_gene(gid)
            symbols.append(ann["symbol"])
            names.append(ann["name"])
            biotypes.append(ann["biotype"])

        annotated_df["symbol"] = symbols
        annotated_df["gene_name"] = names
        annotated_df["biotype"] = biotypes
        return annotated_df
