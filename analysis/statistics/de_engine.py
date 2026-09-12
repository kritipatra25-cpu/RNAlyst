"""
Deterministic Differential Expression (DE) Analysis Engine for RNA-seq Count Data.
"""
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

logger = logging.getLogger(__name__)


def load_sample_metadata(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads sample metadata from CSV or TSV file.
    Must contain a sample column and an experimental condition/group column.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Sample metadata file not found: {file_path}")

    sep = "\t" if path.suffix in [".tsv", ".txt"] or ".tsv" in path.name else ","
    df = pd.read_csv(path, sep=sep)

    if df.empty:
        raise ValueError("Sample metadata file is empty.")

    # Identify sample column
    sample_col = None
    for col in ["sample", "sample_id", "sample_name", "Sample", "SampleID"]:
        if col in df.columns:
            sample_col = col
            break
    if not sample_col:
        sample_col = df.columns[0]

    # Identify condition/group column
    condition_col = None
    for col in ["condition", "group", "treatment", "Condition", "Group", "Treatment"]:
        if col in df.columns and col != sample_col:
            condition_col = col
            break
    if not condition_col:
        if len(df.columns) > 1:
            condition_col = df.columns[1]
        else:
            raise ValueError("Sample metadata requires at least two columns: 'sample' and 'condition'.")

    df = df.set_index(sample_col)
    df.index = df.index.astype(str).str.strip()
    df[condition_col] = df[condition_col].astype(str).str.strip()

    # Validate distinct conditions
    distinct_conditions = df[condition_col].unique()
    if len(distinct_conditions) < 2:
        raise ValueError(
            f"Differential expression requires at least 2 distinct experimental groups; found {len(distinct_conditions)} ({distinct_conditions})"
        )

    # Validate replicate counts per condition
    counts_per_cond = df[condition_col].value_counts()
    min_replicates = counts_per_cond.min()
    if min_replicates < 2:
        insufficient = counts_per_cond[counts_per_cond < 2].index.tolist()
        raise ValueError(
            f"Differential expression requires at least 2 replicates per condition; group(s) {insufficient} have < 2 replicates."
        )

    # Rename condition column to 'condition' for internal uniformity
    df = df.rename(columns={condition_col: "condition"})
    return df[["condition"]]


def load_count_matrix(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads a gene-by-sample count matrix from CSV or TSV file.
    Rows = genes, Columns = samples.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Count matrix file not found: {file_path}")

    sep = "\t" if path.suffix in [".tsv", ".txt"] or ".tsv" in path.name else ","
    df = pd.read_csv(path, sep=sep)

    if df.empty:
        raise ValueError("Count matrix file is empty.")

    # Identify gene identifier column
    gene_col = None
    for col in ["gene_id", "gene", "ensembl_id", "Gene", "GeneID", "ID"]:
        if col in df.columns:
            gene_col = col
            break

    if gene_col:
        df = df.set_index(gene_col)
    else:
        first_col = df.columns[0]
        if not pd.api.types.is_numeric_dtype(df[first_col]):
            df = df.set_index(first_col)

    df.index = df.index.astype(str).str.strip()
    # Keep numeric columns
    numeric_df = df.select_dtypes(include=[np.number])
    numeric_df.columns = numeric_df.columns.astype(str).str.strip()

    if numeric_df.empty or numeric_df.shape[1] < 2:
        raise ValueError(
            f"Count matrix requires at least 2 numeric sample columns; found {numeric_df.shape[1]}"
        )

    return numeric_df


def perform_differential_expression(
    count_matrix_input: Union[str, Path, pd.DataFrame],
    metadata_input: Union[str, Path, pd.DataFrame],
    reference_level: Optional[str] = None,
    alpha: float = 0.05,
    lfc_threshold: float = 1.0
) -> Dict[str, Any]:
    """
    Performs deterministic Differential Expression analysis on raw/normalized RNA-seq count data.
    """
    # 1. Load inputs
    if isinstance(count_matrix_input, (str, Path)):
        counts_df = load_count_matrix(count_matrix_input)
    elif isinstance(count_matrix_input, pd.DataFrame):
        counts_df = count_matrix_input.copy()
    else:
        raise TypeError("count_matrix_input must be a DataFrame or file path.")

    if isinstance(metadata_input, (str, Path)):
        metadata_df = load_sample_metadata(metadata_input)
    elif isinstance(metadata_input, pd.DataFrame):
        metadata_df = metadata_input.copy()
    else:
        raise TypeError("metadata_input must be a DataFrame or file path.")

    # 2. Align samples between count matrix and metadata
    common_samples = [s for s in counts_df.columns if s in metadata_df.index]
    if len(common_samples) < 4:
        raise ValueError(
            f"Fewer than 4 matching samples between count matrix and metadata; found {len(common_samples)} matching: {common_samples}"
        )

    counts_df = counts_df[common_samples]
    metadata_df = metadata_df.loc[common_samples]

    conditions = list(metadata_df["condition"].unique())
    if len(conditions) < 2:
        raise ValueError(f"Fewer than 2 experimental conditions among matched samples: {conditions}")

    # Determine reference and test levels
    if reference_level and reference_level in conditions:
        ref_grp = reference_level
        test_grp = [c for c in conditions if c != ref_grp][0]
    else:
        # Default: first condition as reference, second as test
        ref_grp = conditions[0]
        test_grp = conditions[1]

    contrast = ["condition", test_grp, ref_grp]

    test_samples = metadata_df[metadata_df["condition"] == test_grp].index.tolist()
    ref_samples = metadata_df[metadata_df["condition"] == ref_grp].index.tolist()

    if len(test_samples) < 2 or len(ref_samples) < 2:
        raise ValueError(
            f"DE testing requires >= 2 replicates per group. Found {test_grp}: {len(test_samples)}, {ref_grp}: {len(ref_samples)}"
        )

    # 3. Statistical Analysis using PyDESeq2 if available, else Welch's t-test + FDR
    use_pydeseq2 = False
    pydeseq2_df = None

    try:
        from pydeseq2.dds import DeseqDataSet
        from pydeseq2.ds import DeseqStats

        # PyDESeq2 expects samples as rows and genes as columns
        counts_t = counts_df.T.astype(int)
        # Ensure non-negative integers
        counts_t = np.clip(counts_t, 0, None)

        dds = DeseqDataSet(
            counts=counts_t,
            metadata=metadata_df,
            design_factors="condition",
            ref_level=["condition", ref_grp],
            quiet=True
        )
        dds.deseq2()

        stat_res = DeseqStats(dds, contrast=contrast, quiet=True)
        stat_res.summary()
        pydeseq2_df = stat_res.results_df
        use_pydeseq2 = True
    except Exception as e:
        logger.info("PyDESeq2 execution skipped/fallback used (%s); using statistical Welch t-test engine.", e)
        use_pydeseq2 = False

    results_list = []
    gene_ids = list(counts_df.index)

    if use_pydeseq2 and pydeseq2_df is not None:
        for gene_id in gene_ids:
            if gene_id in pydeseq2_df.index:
                row = pydeseq2_df.loc[gene_id]
                bm = float(row.get("baseMean", 0.0))
                lfc = float(row.get("log2FoldChange", 0.0))
                st = float(row.get("stat", 0.0))
                pval = float(row.get("pvalue", 1.0))
                padj = float(row.get("padj", 1.0))
            else:
                bm, lfc, st, pval, padj = 0.0, 0.0, 0.0, 1.0, 1.0

            if np.isnan(pval): pval = 1.0
            if np.isnan(padj): padj = 1.0
            if np.isnan(lfc): lfc = 0.0

            is_sig = bool((padj <= alpha) and (abs(lfc) >= lfc_threshold))
            results_list.append({
                "gene_id": str(gene_id),
                "baseMean": float(round(bm, 4)),
                "log2FoldChange": float(round(lfc, 4)),
                "stat": float(round(st, 4)),
                "pvalue": float(pval),
                "padj": float(padj),
                "significant": is_sig
            })
    else:
        # Standardized Welch's t-test with log2(x + 1) variance-stabilization
        test_vals = counts_df[test_samples].values  # (n_genes, n_test)
        ref_vals = counts_df[ref_samples].values    # (n_genes, n_ref)

        # Log2 counts
        test_log = np.log2(np.maximum(test_vals, 0) + 1.0)
        ref_log = np.log2(np.maximum(ref_vals, 0) + 1.0)

        mean_test = np.mean(test_log, axis=1)
        mean_ref = np.mean(ref_log, axis=1)
        base_means = np.mean(counts_df.values, axis=1)

        lfcs = mean_test - mean_ref

        # Welch's t-test per gene
        t_stats, p_values = stats.ttest_ind(test_log, ref_log, axis=1, equal_var=False)

        # Clean NaN p-values
        p_values = np.nan_to_num(p_values, nan=1.0)
        t_stats = np.nan_to_num(t_stats, nan=0.0)

        # Benjamini-Hochberg FDR correction
        _, padjs, _, _ = multipletests(p_values, alpha=alpha, method="fdr_bh")

        for i, gene_id in enumerate(gene_ids):
            bm = float(base_means[i])
            lfc = float(lfcs[i])
            st = float(t_stats[i])
            pval = float(p_values[i])
            padj = float(padjs[i])
            is_sig = bool((padj <= alpha) and (abs(lfc) >= lfc_threshold))

            results_list.append({
                "gene_id": str(gene_id),
                "baseMean": float(round(bm, 4)),
                "log2FoldChange": float(round(lfc, 4)),
                "stat": float(round(st, 4)),
                "pvalue": float(pval),
                "padj": float(padj),
                "significant": is_sig
            })

    # Summary metrics
    df_res = pd.DataFrame(results_list)
    total_genes = len(df_res)
    sig_df = df_res[df_res["significant"] == True]
    sig_count = len(sig_df)
    up_count = len(sig_df[sig_df["log2FoldChange"] > 0])
    down_count = len(sig_df[sig_df["log2FoldChange"] < 0])

    summary = {
        "total_genes": total_genes,
        "significant_genes": sig_count,
        "upregulated_genes": up_count,
        "downregulated_genes": down_count,
        "alpha": alpha,
        "lfc_threshold": lfc_threshold,
        "contrast": contrast,
        "statistical_method": "PyDESeq2" if use_pydeseq2 else "Welch_t_test_FDR_BH"
    }

    return {
        "summary": summary,
        "contrast": contrast,
        "results": results_list,
        "dataframe": df_res
    }
