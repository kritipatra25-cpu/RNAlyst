"""
Candidate Gene Prioritizer and Cross-Dataset Reconciliation Engine.

Extracts, prioritizes, and classifies candidate genes from differential expression statistical results
in a configuration-driven, species-reconciled manner.
"""

import logging
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from analysis.annotation.gene_annotator import GeneAnnotator, TAIR10_BENCHMARK_SYMBOL_MAP

# Retain backward-compatible symbol map reference
TAIR10_SYMBOL_MAP = TAIR10_BENCHMARK_SYMBOL_MAP

class CandidatePrioritizer:
    """Prioritizes and classifies candidate genes across differential expression contrasts."""

    def __init__(
        self,
        symbol_map: Optional[Dict[str, str]] = None,
        annotator: Optional[GeneAnnotator] = None
    ):
        if annotator is not None:
            self.annotator = annotator
        else:
            self.annotator = GeneAnnotator(custom_symbol_map=symbol_map)
        # Keep symbol_map property accessible for legacy code
        self.symbol_map = symbol_map or TAIR10_SYMBOL_MAP

    def get_symbol(self, gene_id: str) -> str:
        """Resolve gene ID to symbol or return fallback."""
        return self.annotator.get_symbol(gene_id)

    def evaluate_candidates(
        self,
        candidate_genes: List[str],
        primary_contrast_df: pd.DataFrame,
        secondary_contrast_df: Optional[pd.DataFrame] = None,
        reference_de_df: Optional[pd.DataFrame] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate candidate gene list against DE contrasts and optional cross-dataset reference.
        """
        df_p = primary_contrast_df.set_index("gene_id") if "gene_id" in primary_contrast_df.columns else primary_contrast_df
        df_s = secondary_contrast_df.set_index("gene_id") if secondary_contrast_df is not None and "gene_id" in secondary_contrast_df.columns else secondary_contrast_df
        df_ref = reference_de_df.set_index("gene_id") if reference_de_df is not None and "gene_id" in reference_de_df.columns else reference_de_df

        results = []

        for g in candidate_genes:
            # Primary contrast (e.g. OSD-678 Light Flight vs Ground)
            lfc_p = float(df_p.loc[g, "log2FoldChange"]) if g in df_p.index and pd.notna(df_p.loc[g, "log2FoldChange"]) else None
            se_p = float(df_p.loc[g, "lfcSE"]) if g in df_p.index and "lfcSE" in df_p.columns and pd.notna(df_p.loc[g, "lfcSE"]) else None
            pval_p = float(df_p.loc[g, "pvalue"]) if g in df_p.index and pd.notna(df_p.loc[g, "pvalue"]) else None
            padj_p = float(df_p.loc[g, "padj"]) if g in df_p.index and pd.notna(df_p.loc[g, "padj"]) else None

            # Secondary contrast (e.g. OSD-678 Dark Flight vs Ground)
            lfc_s = float(df_s.loc[g, "log2FoldChange"]) if df_s is not None and g in df_s.index and pd.notna(df_s.loc[g, "log2FoldChange"]) else None
            padj_s = float(df_s.loc[g, "padj"]) if df_s is not None and g in df_s.index and pd.notna(df_s.loc[g, "padj"]) else None

            # Reference DE dataset (e.g. OSD-120 Primary DE)
            lfc_ref = float(df_ref.loc[g, "log2FoldChange"]) if df_ref is not None and g in df_ref.index and pd.notna(df_ref.loc[g, "log2FoldChange"]) else None
            shrunk_ref = float(df_ref.loc[g, "shrunk_log2FoldChange"]) if df_ref is not None and g in df_ref.index and "shrunk_log2FoldChange" in df_ref.columns and pd.notna(df_ref.loc[g, "shrunk_log2FoldChange"]) else None
            padj_ref = float(df_ref.loc[g, "padj"]) if df_ref is not None and g in df_ref.index and pd.notna(df_ref.loc[g, "padj"]) else None

            # Directional concordance evaluation
            if lfc_ref is None or lfc_p is None:
                concordance = "NOT_TESTABLE"
            elif lfc_ref * lfc_p > 0:
                concordance = "CONCORDANT"
            else:
                concordance = "DISCORDANT"

            pass_fdr = bool(padj_p < 0.05) if padj_p is not None else False

            # Evidence classification rules
            if concordance == "CONCORDANT" and pass_fdr:
                evidence_classification = "CROSS_TISSUE_REPLICATION_CONCORDANT"
            elif concordance == "CONCORDANT" and not pass_fdr:
                evidence_classification = "DIRECTIONAL_CONVERGENCE_FAIL_FDR"
            elif concordance == "DISCORDANT":
                evidence_classification = "TISSUE_SPECIFIC_OR_DISCORDANT"
            else:
                evidence_classification = "INSUFFICIENT_EVIDENCE"

            record = {
                "gene_id": g,
                "symbol": self.get_symbol(g),
                "osd120_lfc": lfc_ref,
                "osd120_shrunk_lfc": shrunk_ref,
                "osd120_padj": padj_ref,
                "osd678_light_lfc": lfc_p,
                "osd678_light_se": se_p,
                "osd678_light_pval": pval_p,
                "osd678_light_padj": padj_p,
                "osd678_dark_lfc": lfc_s,
                "osd678_dark_padj": padj_s,
                "direction_concordance": concordance,
                "passes_osd678_fdr_005": pass_fdr,
                "evidence_classification": evidence_classification,
            }
            results.append(record)

        return results
