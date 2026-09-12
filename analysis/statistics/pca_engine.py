"""
Deterministic Principal Component Analysis (PCA) Engine for RNA-seq Expression Data.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA


def load_expression_matrix(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads an expression / count matrix from CSV or TSV file.
    Rows = genes/features, Columns = samples.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Expression matrix file not found: {file_path}")

    sep = "\t" if path.suffix in [".tsv", ".txt"] or ".tsv" in path.name else ","
    df = pd.read_csv(path, sep=sep)

    if df.empty:
        raise ValueError("Expression matrix is empty.")

    # Identify gene identifier column
    gene_col = None
    for col in ["gene_id", "gene", "ensembl_id", "Gene", "GeneID", "ID"]:
        if col in df.columns:
            gene_col = col
            break

    if gene_col:
        df = df.set_index(gene_col)
    else:
        # If first column is string/non-numeric, set as index
        first_col = df.columns[0]
        if not pd.api.types.is_numeric_dtype(df[first_col]):
            df = df.set_index(first_col)

    # Keep only numeric sample columns
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty or numeric_df.shape[1] < 2:
        raise ValueError(
            f"Expression matrix requires at least 2 numeric sample columns; found {numeric_df.shape[1]}"
        )

    return numeric_df


def perform_pca(
    expression_data: Union[pd.DataFrame, str, Path],
    sample_metadata: Optional[Dict[str, str]] = None,
    n_components: int = 2,
    log_transform: bool = True
) -> Dict[str, Any]:
    """
    Computes PCA on a gene-by-sample expression matrix.
    Rows = genes, Columns = samples.
    """
    if isinstance(expression_data, (str, Path)):
        expression_df = load_expression_matrix(expression_data)
    elif isinstance(expression_data, pd.DataFrame):
        expression_df = expression_data.select_dtypes(include=[np.number])
    else:
        raise TypeError("expression_data must be a pandas DataFrame or file path.")

    if expression_df.empty or expression_df.shape[1] < 2:
        raise ValueError(
            f"PCA requires at least 2 samples (columns); matrix shape is {expression_df.shape}"
        )

    # Log2-transformation log2(x + 1) for RNA-seq variance stabilization if requested
    matrix = expression_df.values.T  # Shape: (n_samples, n_genes)
    if log_transform:
        matrix = np.log2(np.maximum(matrix, 0) + 1.0)

    n_samples, n_genes = matrix.shape
    max_components = min(n_samples, n_genes, n_components)
    if max_components < 1:
        raise ValueError("Insufficient data dimensions for PCA.")

    pca = PCA(n_components=max_components)
    coords = pca.fit_transform(matrix)

    samples = list(expression_df.columns)
    sample_metadata = sample_metadata or {}

    coordinates_list = []
    for i, sample_name in enumerate(samples):
        item = {
            "sample_id": sample_name,
            "PC1": float(round(coords[i, 0], 4)),
            "PC2": float(round(coords[i, 1], 4)) if max_components > 1 else 0.0,
            "group": sample_metadata.get(sample_name, "default")
        }
        coordinates_list.append(item)

    explained_var_ratio = pca.explained_variance_ratio_
    explained_var_dict = {
        f"PC{i+1}": float(round(ratio, 4)) for i, ratio in enumerate(explained_var_ratio)
    }
    explained_var_pct = {
        f"PC{i+1}": float(round(ratio * 100, 2)) for i, ratio in enumerate(explained_var_ratio)
    }

    return {
        "samples": samples,
        "coordinates": coordinates_list,
        "explained_variance_ratio": explained_var_dict,
        "explained_variance_percentage": explained_var_pct,
        "total_explained_variance": float(round(sum(explained_var_ratio) * 100, 2)),
        "n_samples": n_samples,
        "n_genes": n_genes
    }
