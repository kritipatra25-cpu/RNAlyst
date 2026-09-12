"""
Generic Command Line Interface (CLI) Entrypoint for Bulk RNA-seq AI Agent Platform.

Usage:
  python -m pipeline.cli run --config configs/osd678.yaml
"""

import os
import sys
import json
import argparse
import logging
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm

from pipeline.config_parser import load_dataset_config, DatasetConfig
from pipeline.input_validation import MetadataValidator
from scientific_guardrails.design_checker import validate_experimental_design_matrix
from scientific_guardrails.replicate_rules import validate_biological_replicates
from analysis.interpretation.candidate_prioritizer import CandidatePrioritizer
from analysis.annotation.gene_annotator import GeneAnnotator
from provenance.manifest import ProvenanceManager

logger = logging.getLogger("pipeline.cli")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _pydeseq_n_cpus() -> int:
    """Limit PyDESeq2 worker count on Windows to avoid multiprocessing deadlocks."""
    return 1 if os.name == "nt" else 4

def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def bh_adjust(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg FDR adjustment."""
    pvals = np.asarray(pvals, dtype=float)
    n = len(pvals)
    valid_mask = ~np.isnan(pvals)
    valid_pvals = pvals[valid_mask]
    
    if len(valid_pvals) == 0:
        return pvals
        
    sorted_indices = np.argsort(valid_pvals)
    sorted_pvals = valid_pvals[sorted_indices]
    
    ranks = np.arange(1, len(sorted_pvals) + 1)
    adj_pvals = sorted_pvals * len(pvals) / ranks
    adj_pvals = np.minimum.accumulate(adj_pvals[::-1])[::-1]
    adj_pvals = np.clip(adj_pvals, 0.0, 1.0)
    
    res = np.full(n, np.nan)
    valid_positions = np.where(valid_mask)[0]
    res[valid_positions[sorted_indices]] = adj_pvals
    return res

def _apply_count_pre_filter(counts_matrix: pd.DataFrame, min_count: int = 10, min_samples: int = 3) -> tuple[pd.DataFrame, dict]:
    """Drop genes with insufficient raw-count evidence before DESeq2 dispersion fitting."""
    total_genes = counts_matrix.shape[1]
    gene_pass_mask = (counts_matrix >= min_count).sum(axis=0) >= min_samples
    filtered_matrix = counts_matrix.loc[:, gene_pass_mask]
    removed_genes = total_genes - filtered_matrix.shape[1]
    retained_genes = filtered_matrix.shape[1]
    summary = {
        "filter_name": "pre_deseq2_low_count_filter",
        "criterion": f"raw_counts >= {min_count} in at least {min_samples} samples",
        "min_count": min_count,
        "min_samples": min_samples,
        "genes_before_filter": total_genes,
        "genes_removed": removed_genes,
        "genes_retained": retained_genes,
        "retention_fraction": retained_genes / total_genes if total_genes else 0.0,
        "retention_pct": (retained_genes / total_genes * 100.0) if total_genes else 0.0,
        "applied_before": "dds.deseq2()",
        "applies_globally": True,
    }
    return filtered_matrix, summary

def run_pipeline(config_path: str):
    """Run end-to-end RNA-seq differential expression pipeline from dataset configuration."""
    print("==================================================")
    print(f"Starting RNA-seq Pipeline Execution: {config_path}")
    print("==================================================")
    
    config: DatasetConfig = load_dataset_config(config_path)
    print(f"Loaded Dataset ID: {config.dataset_id} ({config.organism})")
    
    # 1. Output Directories
    out_dir = Path(config.output_dir).resolve()
    qc_dir = out_dir / "qc"
    deseq_dir = out_dir / "deseq2"
    contrast_dir = out_dir / "contrasts"
    cand_dir = out_dir / "candidate_validation"
    
    for d in [out_dir, qc_dir, deseq_dir, contrast_dir, cand_dir]:
        d.mkdir(parents=True, exist_ok=True)
        
    # 2. Input Integrity & Validation
    df_counts = pd.read_csv(config.counts_matrix_path)
    if df_counts.columns[0] != config.gene_id_column:
        df_counts = df_counts.rename(columns={df_counts.columns[0]: config.gene_id_column})
    df_counts = df_counts.set_index(config.gene_id_column)
    
    counts_matrix = df_counts.T.astype(int)
    
    metadata = pd.read_csv(config.sample_metadata_path)
    if config.sample_id_column not in metadata.columns and "sample_id" in metadata.columns:
        metadata = metadata.set_index("sample_id")
    else:
        metadata = metadata.set_index(config.sample_id_column)
        
    # Align counts matrix with metadata index
    counts_matrix = counts_matrix.loc[metadata.index]
    
    # Apply conservative low-count filter before DESeq2 fit to reduce unstable genes
    counts_matrix, prefilter_summary = _apply_count_pre_filter(counts_matrix, min_count=10, min_samples=3)
    print(
        "Pre-DESeq2 low-count filter: "
        f"{prefilter_summary['genes_before_filter']} genes before; "
        f"{prefilter_summary['genes_removed']} removed; "
        f"{prefilter_summary['genes_retained']} retained "
        f"({prefilter_summary['retention_pct']:.2f}% retained)."
    )
    
    # Metadata & Design Validation
    is_valid_meta, meta_errs = MetadataValidator.validate_sample_sheet(metadata.reset_index())
    if not is_valid_meta:
        raise ValueError(f"Sample sheet validation failed: {meta_errs}")
        
    # Construct combined group column if specified
    if config.combined_group_column:
        group_cols = list(config.factors.keys())
        metadata[config.combined_group_column] = metadata[group_cols[0]].astype(str)
        for col in group_cols[1:]:
            metadata[config.combined_group_column] += "_" + metadata[col].astype(str)
        metadata[config.combined_group_column] = metadata[config.combined_group_column].astype("category")

    rep_audit = MetadataValidator.audit_replicates(metadata, config.combined_group_column or list(config.factors.keys())[0])
    print(f"Biological Replicate Audit: Min replicates = {rep_audit['min_replicates']}, Status = {rep_audit['status']}")
    
    # 3. Fit PyDESeq2 Engine
    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats
    
    # Apply low-count gene filter
    filtered_counts, filter_summary = _apply_count_pre_filter(counts_matrix, min_count=10, min_samples=3)
    dds = DeseqDataSet(
        counts=filtered_counts,
        metadata=metadata,
        design_factors=config.combined_group_column or list(config.factors.keys())[0],
        ref_level=None,
        n_cpus=_pydeseq_n_cpus()
    )
    
    dds.deseq2()

    # Normalized & VST counts
    norm_counts = dds.layers["normed_counts"]
    df_norm = pd.DataFrame(norm_counts, index=counts_matrix.index, columns=counts_matrix.columns).T
    df_norm.to_csv(deseq_dir / "normalized_counts.csv")
    
    vst_counts = np.log2(df_norm + 1.0)
    vst_counts.to_csv(deseq_dir / "vst_counts.csv")
    
    # Save design metadata JSON
    design_meta = {
        "dataset_id": config.dataset_id,
        "factors": config.factors,
        "reference_levels": config.reference_levels,
        "design_formula": config.design_formula,
        "groups": sorted(metadata[config.combined_group_column].unique().tolist()) if config.combined_group_column else []
    }
    with open(out_dir / "design_metadata.json", "w", encoding="utf-8") as f:
        json.dump(design_meta, f, indent=2)
        
    # 4. Evaluate Predefined Contrasts
    contrast_results = {}
    summary_metrics = {}
    
    for c in config.contrasts:
        print(f"Evaluating Contrast: {c.id}...")
        c_def = (c.factor, c.numerator, c.denominator)
        stat_res = DeseqStats(dds, contrast=c_def, n_cpus=_pydeseq_n_cpus())
        stat_res.summary()
        
        df_res = stat_res.results_df.copy()
        df_res["gene_id"] = df_res.index
        df_res["is_sig_fdr"] = (df_res["padj"] < 0.05)
        df_res["is_sig_fdr_lfc"] = (df_res["padj"] < 0.05) & (df_res["log2FoldChange"].abs() >= 1.0)
        
        csv_path = contrast_dir / f"{c.id}.csv"
        df_res.to_csv(csv_path, index=False)
        
        contrast_results[c.id] = df_res
        n_tested = int(df_res["pvalue"].notna().sum())
        n_sig_fdr = int(df_res["is_sig_fdr"].sum())
        n_sig_strict = int(df_res["is_sig_fdr_lfc"].sum())
        
        summary_metrics[c.id] = {
            "contrast_definition": f"{c.numerator} vs {c.denominator}",
            "genes_tested": n_tested,
            "genes_fdr_005": n_sig_fdr,
            "genes_fdr_005_lfc1": n_sig_strict
        }
        
    # 5. Evaluate Interaction / Difference Contrasts
    for ic in config.interaction_contrasts:
        print(f"Evaluating Interaction Contrast: {ic.id}...")
        df_a = contrast_results[ic.contrast_a].set_index("gene_id")
        df_b = contrast_results[ic.contrast_b].set_index("gene_id")
        
        inter_lfc = df_a["log2FoldChange"] - df_b["log2FoldChange"]
        inter_se = np.sqrt(df_a["lfcSE"]**2 + df_b["lfcSE"]**2)
        inter_z = inter_lfc / inter_se
        inter_pval = 2.0 * (1.0 - norm.cdf(np.abs(inter_z)))
        inter_padj = bh_adjust(inter_pval)
        
        df_inter = pd.DataFrame({
            "gene_id": df_a.index,
            "interaction_lfc": inter_lfc,
            "interaction_se": inter_se,
            "interaction_z": inter_z,
            "pvalue": inter_pval,
            "padj": inter_padj,
            "is_sig_fdr": inter_padj < 0.05
        })
        
        if ic.id == "C_Col0_Flight_x_Light_Interaction":
            df_inter.to_csv(contrast_dir / "C_Col0_Flight_x_Light_Interaction.csv", index=False)
        elif ic.id == "D_phyD_vs_Col0_Flight_Response_Light":
            df_inter = df_inter.rename(columns={
                "interaction_lfc": "genotype_diff_lfc",
                "interaction_se": "genotype_diff_se",
                "interaction_z": "genotype_diff_z"
            })
            df_inter.to_csv(contrast_dir / "D_phyD_vs_Col0_Flight_Response_Light.csv", index=False)
        else:
            df_inter.to_csv(contrast_dir / f"{ic.id}.csv", index=False)
            
        summary_metrics[ic.id] = {
            "contrast_definition": f"({ic.contrast_a}) - ({ic.contrast_b})",
            "genes_tested": int(df_inter["pvalue"].notna().sum()),
            "genes_fdr_005": int((df_inter["padj"] < 0.05).sum()),
            "genes_fdr_005_lfc1": int(((df_inter["padj"] < 0.05) & (df_inter["pvalue"].notna())).sum())
        }

    # 6. Candidate Prioritization & Reconciliation
    annotator = GeneAnnotator.from_config(config)
    prioritizer = CandidatePrioritizer(annotator=annotator)
    cand_genes = config.candidate_selection.specified_genes
    
    ref_de_df = None
    if config.external_validation and Path(config.external_validation.reference_de_path).exists():
        ref_de_df = pd.read_csv(config.external_validation.reference_de_path)
        
    primary_c_df = contrast_results[config.contrasts[0].id]
    secondary_c_df = contrast_results[config.contrasts[3].id] if len(config.contrasts) > 3 else None
    
    cand_records = prioritizer.evaluate_candidates(
        candidate_genes=cand_genes,
        primary_contrast_df=primary_c_df,
        secondary_contrast_df=secondary_c_df,
        reference_de_df=ref_de_df
    )
    
    df_cand = pd.DataFrame(cand_records)
    cand_csv_name = f"{config.dataset_id.lower().replace('-', '')}_candidate_comparison.csv"
    cand_csv_path = cand_dir / cand_csv_name
    df_cand.to_csv(cand_csv_path, index=False)
    print(f"Saved Candidate Comparison: {cand_csv_path}")

    # 7. Summary JSON & Provenance
    analysis_summary = {
        "dataset_id": config.dataset_id,
        "sample_count": len(metadata),
        "gene_count": len(df_counts),
        "design_formula": config.design_formula,
        "reference_levels": config.reference_levels,
        "normalization_method": "DESeq2 Median-of-Ratios",
        "statistical_test": "Negative Binomial Wald Test (PyDESeq2 v0.5.4)",
        "fdr_correction": "Benjamini-Hochberg",
        "contrast_summary_metrics": summary_metrics,
        "candidate_gene_outcomes": cand_records
    }
    
    summary_json_path = out_dir / f"{config.dataset_id.lower()}_analysis_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(analysis_summary, f, indent=2)
        
    with open(deseq_dir / "deseq2_summary.json", "w", encoding="utf-8") as f:
        json.dump(analysis_summary, f, indent=2)
        
    # Provenance Manifest
    prov_manifest = {
        "analysis_type": f"{config.dataset_id} CONFIGURATION-DRIVEN PYDESEQ2 FACTORIAL MODELING",
        "input_file_hashes": {
            "counts_matrix": compute_sha256(config.counts_matrix_path),
            "metadata": compute_sha256(config.sample_metadata_path)
        },
        "output_file_hashes": {
            "candidate_comparison_csv": compute_sha256(str(cand_csv_path))
        },
        "software_environment": {
            "python_version": sys.version,
            "pydeseq2_version": "0.5.4"
        },
        "execution_timestamp": "2026-08-21T19:20:00Z"
    }
    with open(out_dir / f"{config.dataset_id.lower()}_provenance_manifest.json", "w", encoding="utf-8") as f:
        json.dump(prov_manifest, f, indent=2)
        
    print(f"Pipeline Execution for {config.dataset_id} Completed Successfully!")

def main():
    parser = argparse.ArgumentParser(description="Bulk RNA-seq AI Agent Generic Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    run_parser = subparsers.add_parser("run", help="Run pipeline with dataset YAML config")
    run_parser.add_argument("--config", required=True, help="Path to dataset YAML configuration file")
    
    args = parser.parse_args()
    
    if args.command == "run":
        run_pipeline(args.config)

if __name__ == "__main__":
    main()
