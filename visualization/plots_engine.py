"""
Visualization Engine for Bulk RNA-seq Analysis.

Generates publication-ready figures:
1. 2D PCA Scatter Plot (PC1 vs PC2 with variance explained %)
2. MA Plot (baseMean vs LFC)
3. Volcano Plot (-log10 padj vs shrunken LFC)
4. Expression Heatmap (Row Z-score normalized VST values for top DEGs)
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)

# Set global publication styling
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
plt.rcParams["axes.edgecolor"] = "#333333"
plt.rcParams["axes.linewidth"] = 0.8

class VisualizationEngine:
    """Engine for generating RNA-seq plots."""

    @staticmethod
    def plot_pca(
        pca_data: Union[pd.DataFrame, Dict[str, Any]],
        output_path: Union[str, Path],
        sample_meta: Optional[pd.DataFrame] = None,
        group_col: str = "condition",
        top_n_genes: int = 500
    ) -> Dict[str, Any]:
        """Generate 2D PCA scatter plot from VST count matrix or PCA results dict."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(pca_data, dict) and "coordinates" in pca_data:
            coords = pca_data["coordinates"]
            pca_df = pd.DataFrame(coords) if isinstance(coords, list) else pd.DataFrame.from_dict(coords, orient="index")
            exp_pct = pca_data.get("explained_variance_percentage", {})
            pc1_var = exp_pct.get("PC1", 0.0)
            pc2_var = exp_pct.get("PC2", 0.0)

            fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
            hue_col = "group" if "group" in pca_df.columns else group_col
            if hue_col not in pca_df.columns:
                pca_df[hue_col] = "Sample"

            sns.scatterplot(
                data=pca_df,
                x="PC1",
                y="PC2",
                hue=hue_col,
                s=100,
                palette="Set1",
                ax=ax
            )

            for _, row in pca_df.iterrows():
                sid = str(row.get("sample_id", row.name))
                ax.annotate(
                    sid.split("_")[0],
                    (row["PC1"], row["PC2"]),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=7,
                    alpha=0.8
                )

            ax.set_xlabel(f"PC1 ({pc1_var:.1f}% Variance)", fontsize=11, fontweight="bold")
            ax.set_ylabel(f"PC2 ({pc2_var:.1f}% Variance)", fontsize=11, fontweight="bold")
            ax.set_title("Principal Component Analysis (PCA)", fontsize=13, fontweight="bold", pad=12)
            plt.tight_layout()
            plt.savefig(output_path, bbox_inches="tight")
            plt.close()
            return {"pc1_var": pc1_var, "pc2_var": pc2_var}

        if isinstance(pca_data, (str, Path)):
            vst_df = pd.read_csv(pca_data, index_col=0)
        else:
            vst_df = pca_data

        gene_vars = vst_df.var(axis=1)
        top_genes = gene_vars.nlargest(top_n_genes).index
        sub_vst = vst_df.loc[top_genes].T

        pca = PCA(n_components=2, random_state=42)
        pcs = pca.fit_transform(sub_vst)
        var_explained = pca.explained_variance_ratio_ * 100

        pca_df = pd.DataFrame(pcs, index=sub_vst.index, columns=["PC1", "PC2"])
        
        if sample_meta is not None and isinstance(sample_meta, pd.DataFrame) and group_col in sample_meta.columns:
            pca_df[group_col] = sample_meta.loc[pca_df.index, group_col].values
        else:
            pca_df[group_col] = "Sample"

        fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
        sns.scatterplot(
            data=pca_df,
            x="PC1",
            y="PC2",
            hue=group_col,
            style=group_col,
            s=100,
            palette="Set1",
            ax=ax
        )

        for sample_id, row in pca_df.iterrows():
            ax.annotate(
                str(sample_id).split("_")[0],
                (row["PC1"], row["PC2"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=7,
                alpha=0.8
            )

        ax.set_xlabel(f"PC1 ({var_explained[0]:.1f}% Variance)", fontsize=11, fontweight="bold")
        ax.set_ylabel(f"PC2 ({var_explained[1]:.1f}% Variance)", fontsize=11, fontweight="bold")
        ax.set_title("Principal Component Analysis (PCA)", fontsize=13, fontweight="bold", pad=12)
        ax.legend(title=group_col, bbox_to_anchor=(1.05, 1), loc="upper left", frameon=True)
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches="tight")
        plt.close()

        logger.info("Saved PCA plot to %s", output_path)

        return {
            "pc1_var": float(var_explained[0]),
            "pc2_var": float(var_explained[1]),
            "coordinates": pca_df.to_dict(orient="index")
        }

    @staticmethod
    def plot_volcano(
        de_data: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]],
        output_path: Path,
        fdr_thresh: float = 0.05,
        lfc_thresh: float = 1.0,
        title: str = "Volcano Plot (Differential Expression)"
    ) -> Path:
        """Generate Volcano plot (-log10 padj vs shrunken LFC)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(de_data, (str, Path)):
            de_df = pd.read_csv(de_data)
        elif isinstance(de_data, (list, dict)):
            de_df = pd.DataFrame(de_data)
        else:
            de_df = de_data

        lfc_col = "shrunk_log2FoldChange" if "shrunk_log2FoldChange" in de_df.columns else "log2FoldChange"
        p_col = "padj" if "padj" in de_df.columns else "pvalue"

        if lfc_col not in de_df.columns or p_col not in de_df.columns:
            logger.warning("Required columns missing for volcano plot.")
            return output_path

        df = de_df.copy().dropna(subset=[p_col, lfc_col])
        df["minus_log10_padj"] = -np.log10(np.clip(df[p_col], 1e-300, 1.0))

        conditions = [
            (df[p_col] < fdr_thresh) & (df[lfc_col] >= lfc_thresh),
            (df[p_col] < fdr_thresh) & (df[lfc_col] <= -lfc_thresh),
        ]
        choices = ["Upregulated", "Downregulated"]
        df["Significance"] = np.select(conditions, choices, default="Not Significant")

        palette = {"Upregulated": "#D95F02", "Downregulated": "#7570B3", "Not Significant": "#B3B3B3"}

        fig, ax = plt.subplots(figsize=(7, 6), dpi=300)
        sns.scatterplot(
            data=df,
            x=lfc_col,
            y="minus_log10_padj",
            hue="Significance",
            palette=palette,
            alpha=0.7,
            s=25,
            ax=ax
        )

        ax.axvline(x=lfc_thresh, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.axvline(x=-lfc_thresh, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.axhline(y=-np.log10(fdr_thresh), color="black", linestyle="--", linewidth=0.8, alpha=0.7)

        top_degs = df[df["Significance"] != "Not Significant"].nsmallest(5, p_col)
        for _, row in top_degs.iterrows():
            sym = str(row.get("symbol", row.get("gene_id", "")))
            ax.annotate(
                sym,
                (row[lfc_col], row["minus_log10_padj"]),
                xytext=(6, 6),
                textcoords="offset points",
                fontsize=8,
                fontweight="bold"
            )

        ax.set_xlabel("Log2 Fold Change", fontsize=11, fontweight="bold")
        ax.set_ylabel("-Log10 Adjusted P-value (FDR)", fontsize=11, fontweight="bold")
        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
        ax.legend(title="Significance", frameon=True)
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches="tight")
        plt.close()

        logger.info("Saved Volcano plot to %s", output_path)
        return output_path

    @staticmethod
    def plot_heatmap(
        vst_df: Union[pd.DataFrame, str, Path],
        de_data: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any], str, Path],
        sample_meta: Optional[Union[pd.DataFrame, str, Path]] = None,
        output_path: Optional[Path] = None,
        top_n: int = 40
    ) -> Path:
        """Generate Row Z-score Normalized Heatmap for top DEGs."""
        if output_path is None:
            output_path = Path("heatmap.png")
        else:
            output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(vst_df, (str, Path)):
            vst_df = pd.read_csv(vst_df, index_col=0)

        if isinstance(de_data, (str, Path)):
            de_df = pd.read_csv(de_data)
        elif isinstance(de_data, (list, dict)):
            de_df = pd.DataFrame(de_data)
        else:
            de_df = de_data

        p_col = "padj" if "padj" in de_df.columns else "pvalue"
        if p_col not in de_df.columns or "gene_id" not in de_df.columns:
            logger.warning("Required columns missing for heatmap plot.")
            return output_path

        sig_genes = de_df.dropna(subset=[p_col]).nsmallest(top_n, p_col)["gene_id"].tolist()
        sub_vst = vst_df.loc[vst_df.index.isin(sig_genes)]

        if sub_vst.empty:
            logger.warning("No significant genes found to plot heatmap.")
            return output_path

        # Keep only numeric columns
        sub_vst = sub_vst.select_dtypes(include=[np.number])
        if sub_vst.empty:
            logger.warning("No numeric columns found in expression matrix for heatmap.")
            return output_path

        z_scores = sub_vst.sub(sub_vst.mean(axis=1), axis=0).div(sub_vst.std(axis=1), axis=0).fillna(0)

        symbol_map = dict(zip(de_df["gene_id"], de_df.get("symbol", de_df["gene_id"])))
        z_scores.index = [symbol_map.get(g, g) for g in z_scores.index]

        fig, ax = plt.subplots(figsize=(8, 10), dpi=300)
        sns.heatmap(
            z_scores,
            cmap="vlag",
            center=0,
            linewidths=0.5,
            cbar_kws={"label": "Expression Z-score"},
            ax=ax
        )

        ax.set_title(f"Top {len(z_scores)} Differentially Expressed Genes", fontsize=13, fontweight="bold", pad=12)
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches="tight")
        plt.close()

        logger.info("Saved Heatmap plot to %s", output_path)
        return output_path

    @staticmethod
    def plot_qc(qc_metrics: Dict[str, Any], output_path: Union[str, Path]) -> Path:
        """Generate Quality Control summary bar plot."""
        return generate_qc_plot(qc_metrics, output_path)


def generate_pca_plot(pca_data, output_path, sample_meta=None, group_col="condition", top_n_genes=500):
    return VisualizationEngine.plot_pca(pca_data, output_path, sample_meta, group_col, top_n_genes)

def generate_volcano_plot(de_data=None, output_path=None, fdr_thresh=0.05, lfc_thresh=1.0, title="Volcano Plot (Differential Expression)", de_results_input=None):
    de_input = de_data if de_data is not None else de_results_input
    return VisualizationEngine.plot_volcano(de_input, output_path, fdr_thresh, lfc_thresh, title)

def generate_heatmap_plot(vst_df=None, de_data=None, sample_meta=None, output_path=None, top_n=40, count_matrix_input=None, de_results_input=None, metadata_input=None):
    vst_input = vst_df if vst_df is not None else count_matrix_input
    de_input = de_data if de_data is not None else de_results_input
    meta_input = sample_meta if sample_meta is not None else metadata_input
    return VisualizationEngine.plot_heatmap(vst_input, de_input, meta_input, output_path, top_n)

def generate_qc_plot(qc_metrics, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4), dpi=300)
    metrics = ["total_reads", "gc_content_percent", "mean_phred_quality"]
    vals = [qc_metrics.get(m, 0) if isinstance(qc_metrics, dict) else 0 for m in metrics]
    ax.bar(metrics, vals, color="#3182bd")
    ax.set_title("QC Summary Metrics")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    return output_path
