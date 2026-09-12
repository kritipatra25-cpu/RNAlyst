"""
Directional Benchmark Validation Framework for Bulk RNA-seq Engine.

Validates pipeline output against published reference DE results (e.g. NASA GeneLab reference tables):
1. Sample identity correspondence
2. Gene ID universe mapping statistics
3. Shared-gene log2FC Spearman rank correlation (rho)
4. Directional agreement matrix (UP/UP, DOWN/DOWN, UP/DOWN, DOWN/UP)
5. DEG Jaccard overlap index (FDR < 0.05, |LFC| >= 1.0)
6. Top-50 candidate DEG overlap %
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

class DirectionalBenchmarkValidator:
    """Validator for comparing pipeline DE output against reference benchmark tables."""

    @staticmethod
    def calculate_directional_metrics(
        pipeline_de: pd.DataFrame,
        reference_de: pd.DataFrame,
        gene_col: str = "gene_id",
        lfc_col_pipeline: str = "shrunk_log2FoldChange",
        lfc_col_ref: str = "log2FoldChange",
        padj_col_pipeline: str = "padj",
        padj_col_ref: str = "padj",
        fdr_thresh: float = 0.05,
        lfc_thresh: float = 1.0
    ) -> Dict[str, Any]:
        """Calculate complete directional agreement metrics between pipeline and reference."""

        pipe_clean = pipeline_de.dropna(subset=[gene_col, lfc_col_pipeline]).copy()
        ref_clean = reference_de.dropna(subset=[gene_col, lfc_col_ref]).copy()

        pipe_clean[gene_col] = pipe_clean[gene_col].astype(str).str.strip()
        ref_clean[gene_col] = ref_clean[gene_col].astype(str).str.strip()

        merged = pd.merge(
            pipe_clean,
            ref_clean,
            on=gene_col,
            suffixes=("_pipeline", "_reference")
        )

        if merged.empty:
            raise ValueError("Zero overlapping gene IDs found between pipeline output and reference table!")

        total_shared_genes = len(merged)

        # Resolve merged column names
        pipe_lfc_key = f"{lfc_col_pipeline}_pipeline" if f"{lfc_col_pipeline}_pipeline" in merged.columns else lfc_col_pipeline
        ref_lfc_key = f"{lfc_col_ref}_reference" if f"{lfc_col_ref}_reference" in merged.columns else lfc_col_ref

        pipe_padj_key = f"{padj_col_pipeline}_pipeline" if f"{padj_col_pipeline}_pipeline" in merged.columns else padj_col_pipeline
        ref_padj_key = f"{padj_col_ref}_reference" if f"{padj_col_ref}_reference" in merged.columns else padj_col_ref

        # 1. Spearman Rank Correlation (rho)
        pipe_lfc = merged[pipe_lfc_key].values
        ref_lfc = merged[ref_lfc_key].values

        spearman_rho, spearman_p = stats.spearmanr(pipe_lfc, ref_lfc)

        # 2. Directional Agreement Matrix
        up_up = int(((pipe_lfc > 0) & (ref_lfc > 0)).sum())
        down_down = int(((pipe_lfc < 0) & (ref_lfc < 0)).sum())
        up_down = int(((pipe_lfc > 0) & (ref_lfc < 0)).sum())
        down_up = int(((pipe_lfc < 0) & (ref_lfc > 0)).sum())

        concordant_count = up_up + down_down
        directional_concordance_rate = float(concordant_count / total_shared_genes) if total_shared_genes > 0 else 0.0

        # 3. DEG Overlap (Jaccard Index)
        pipe_deg = set(
            merged[
                (merged[pipe_padj_key] < fdr_thresh) &
                (merged[pipe_lfc_key].abs() >= lfc_thresh)
            ][gene_col]
        )
        ref_deg = set(
            merged[
                (merged[ref_padj_key] < fdr_thresh) &
                (merged[ref_lfc_key].abs() >= lfc_thresh)
            ][gene_col]
        )

        intersection_deg = pipe_deg.intersection(ref_deg)
        union_deg = pipe_deg.union(ref_deg)
        deg_jaccard = float(len(intersection_deg) / len(union_deg)) if union_deg else 1.0

        # 4. Top-50 DEG Overlap
        pipe_top50 = set(merged.nsmallest(50, pipe_padj_key)[gene_col])
        ref_top50 = set(merged.nsmallest(50, ref_padj_key)[gene_col])
        top50_overlap_count = len(pipe_top50.intersection(ref_top50))
        top50_overlap_rate = float(top50_overlap_count / 50.0)

        results = {
            "total_pipeline_genes": len(pipe_clean),
            "total_reference_genes": len(ref_clean),
            "shared_gene_count": total_shared_genes,
            "spearman_log2fc_rho": float(spearman_rho),
            "spearman_pvalue": float(spearman_p),
            "directional_matrix": {
                "UP_UP": up_up,
                "DOWN_DOWN": down_down,
                "UP_DOWN": up_down,
                "DOWN_UP": down_up,
                "total_concordant": concordant_count,
                "concordance_rate": directional_concordance_rate
            },
            "deg_statistics": {
                "pipeline_deg_count": len(pipe_deg),
                "reference_deg_count": len(ref_deg),
                "deg_intersection_count": len(intersection_deg),
                "deg_jaccard_index": deg_jaccard,
            },
            "top50_deg_agreement_pct": top50_overlap_rate * 100.0,
            "is_benchmark_passed": bool(spearman_rho >= 0.85 and directional_concordance_rate >= 0.80)
        }

        logger.info(
            "Benchmark Comparison: Spearman rho=%.4f, Concordance Rate=%.2f%%, DEG Jaccard=%.4f",
            spearman_rho, directional_concordance_rate * 100.0, deg_jaccard
        )

        return results
