"""
Quantification Bridge & tximport Engine Module.

Bridges transcript quantification (Salmon quant.sf files) with gene-level
count matrix generation required by PyDESeq2 / DESeq2Tool.
Supports programmatically parsing Salmon quant.sf outputs, applying tx2gene
mappings, and producing counts_matrix.csv for arbitrary projects.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class QuantificationError(Exception):
    """Raised when transcript quantification or count aggregation fails."""


class QuantificationRunner:
    """Engine for processing Salmon quant outputs into gene count matrices."""

    @staticmethod
    def parse_quant_sf(quant_sf_path: Path) -> pd.DataFrame:
        """Parse Salmon transcript-level quant.sf file into DataFrame.

        Expected columns in quant.sf: Name, Length, EffectiveLength, TPM, NumReads
        """
        quant_sf_path = Path(quant_sf_path)
        if not quant_sf_path.exists():
            raise FileNotFoundError(f"quant.sf file not found at: {quant_sf_path}")

        try:
            df = pd.read_csv(quant_sf_path, sep="\t")
            req_cols = ["Name", "NumReads"]
            for col in req_cols:
                if col not in df.columns:
                    raise ValueError(f"quant.sf missing mandatory column '{col}'. Available: {list(df.columns)}")
            return df
        except Exception as e:
            raise QuantificationError(f"Failed to parse {quant_sf_path}: {e}") from e

    @classmethod
    def aggregate_salmon_quants_to_counts(
        cls,
        quant_dir_map: Dict[str, Path],
        tx2gene_path: Optional[Path] = None
    ) -> pd.DataFrame:
        """Aggregate multiple sample quant.sf files into a unified gene-level count matrix DataFrame.

        Args:
            quant_dir_map: Mapping of sample_id -> Path to quant directory or quant.sf file.
            tx2gene_path: Optional Path to tx2gene mapping CSV (columns: transcript_id, gene_id).
                          If None, attempts auto-extraction of gene_id from transcript_id.

        Returns:
            pd.DataFrame indexed by gene_id with sample_id count columns.
        """
        if not quant_dir_map:
            raise ValueError("quant_dir_map must not be empty.")

        # 1. Load tx2gene mapping if provided
        tx2gene_dict = {}
        if tx2gene_path and Path(tx2gene_path).exists():
            try:
                tx_df = pd.read_csv(tx2gene_path)
                # Flexible column detection
                tx_col = tx_df.columns[0]
                gene_col = tx_df.columns[1] if len(tx_df.columns) > 1 else tx_df.columns[0]
                tx2gene_dict = dict(zip(tx_df[tx_col].astype(str), tx_df[gene_col].astype(str)))
            except Exception as e:
                logger.warning("Failed reading tx2gene CSV %s: %s. Falling back to ID splitting.", tx2gene_path, e)

        sample_gene_counts: Dict[str, pd.Series] = {}

        for sample_id, raw_path in quant_dir_map.items():
            path = Path(raw_path)
            sf_file = path if path.is_file() and path.name == "quant.sf" else path / "quant.sf"

            df_quant = cls.parse_quant_sf(sf_file)

            # Map transcript ID -> gene ID
            if tx2gene_dict:
                df_quant["gene_id"] = df_quant["Name"].map(lambda t: tx2gene_dict.get(str(t), str(t)))
            else:
                # Default mapping: strip isoform extension (e.g. AT1G01010.1 -> AT1G01010, ENST... -> ENSG...)
                df_quant["gene_id"] = df_quant["Name"].astype(str).apply(lambda t: t.split(".")[0] if "." in t else t)

            # Aggregate transcript NumReads to gene-level counts
            gene_series = df_quant.groupby("gene_id")["NumReads"].sum()
            sample_gene_counts[sample_id] = gene_series

        # Combine sample series into single count matrix DataFrame
        df_counts = pd.DataFrame(sample_gene_counts).fillna(0.0)

        # Ensure rounded integer counts for DESeq2 compatibility
        df_counts = df_counts.round().astype(int)
        df_counts.index.name = "gene_id"

        return df_counts

    @classmethod
    def generate_counts_matrix_file(
        cls,
        quant_dir_map: Dict[str, Path],
        output_csv_path: Path,
        tx2gene_path: Optional[Path] = None
    ) -> Path:
        """Generate and write final counts_matrix.csv to destination path."""
        output_csv_path = Path(output_csv_path)
        output_csv_path.parent.mkdir(parents=True, exist_ok=True)

        df_counts = cls.aggregate_salmon_quants_to_counts(quant_dir_map, tx2gene_path)
        df_counts.reset_index(inplace=True)
        df_counts.to_csv(output_csv_path, index=False)

        logger.info("Generated counts_matrix.csv at %s (%d genes, %d samples)",
                    output_csv_path, len(df_counts), len(quant_dir_map))
        return output_csv_path
