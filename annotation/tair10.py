"""
TAIR10 Gene Annotation Lookup Engine for Arabidopsis thaliana.

Provides mapping from AGI locus IDs (e.g. AT1G01010) to gene symbols,
functional descriptions, and Gene Ontology (GO) categories.
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

# Sample TAIR10 reference dictionary for primary spaceflight candidate genes
TAIR10_BUILTIN_ANNOTATIONS = {
    "AT1G01010": {"symbol": "ANAC001", "name": "NAC domain-containing protein 1", "biotype": "protein_coding", "go_process": "GO:0006355 (regulation of transcription)"},
    "AT3G24650": {"symbol": "ABI3", "name": "ABSCISIC ACID-INSENSITIVE 3", "biotype": "protein_coding", "go_process": "GO:0009737 (response to abscisic acid)"},
    "AT5G66170": {"symbol": "WRKY33", "name": "WRKY DNA-binding protein 33", "biotype": "protein_coding", "go_process": "GO:0009611 (response to wounding)"},
    "AT1G22710": {"symbol": "PR1", "name": "PATHOGENESIS-RELATED GENE 1", "biotype": "protein_coding", "go_process": "GO:0009607 (response to biotic stimulus)"},
    "AT4G12420": {"symbol": "EXPA1", "name": "EXPANSIEN A1", "biotype": "protein_coding", "go_process": "GO:0009832 (plant organ morphogenesis)"},
    "AT2G46370": {"symbol": "HEAT SHOCK PROTEIN 70", "name": "HSP70-1", "biotype": "protein_coding", "go_process": "GO:0009408 (response to heat)"},
}

class TAIR10Annotator:
    """Annotator for Arabidopsis thaliana TAIR10 locus IDs."""

    def __init__(self, annotation_file: Optional[str] = None):
        self.annotations = TAIR10_BUILTIN_ANNOTATIONS.copy()
        if annotation_file:
            self.load_annotation_table(annotation_file)

    def load_annotation_table(self, file_path: str):
        """Load external annotation table (TSV/CSV) into memory."""
        try:
            df = pd.read_csv(file_path, sep="\t" if file_path.endswith(".tsv") else ",")
            for _, row in df.iterrows():
                gene_id = str(row.get("gene_id", "")).strip().upper()
                if gene_id:
                    self.annotations[gene_id] = {
                        "symbol": str(row.get("symbol", gene_id)),
                        "name": str(row.get("description", "")),
                        "biotype": str(row.get("biotype", "protein_coding")),
                        "go_process": str(row.get("go_process", "")),
                    }
            logger.info("Loaded %d gene annotations from %s", len(self.annotations), file_path)
        except Exception as e:
            logger.error("Failed loading annotation table %s: %s", file_path, e)

    def annotate_gene(self, gene_id: str) -> Dict[str, Any]:
        """Annotate single gene ID."""
        gid_clean = str(gene_id).strip().upper()
        if gid_clean in self.annotations:
            ann = self.annotations[gid_clean].copy()
            ann["gene_id"] = gid_clean
            return ann

        return {
            "gene_id": gid_clean,
            "symbol": gid_clean,
            "name": "Uncharacterized Arabidopsis transcript",
            "biotype": "unknown",
            "go_process": "",
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
