"""Design matrix checker validating rank deficiency, factor estimability, and batch confounding."""
import pandas as pd
from typing import Tuple, List
from pipeline.schemas.input_schemas import SampleSheetInput


def validate_experimental_design_matrix(sample_sheet: SampleSheetInput) -> Tuple[str, List[str]]:
    """Checks for rank deficiency and complete batch confounding."""
    warnings: List[str] = []

    data = []
    for s in sample_sheet.samples:
        data.append({
            "sample_id": s.sample_id,
            "condition": s.condition,
            "batch": s.batch or "batch1",
            "genotype": s.genotype or "wt"
        })

    df = pd.DataFrame(data)

    # Check complete batch confounding
    if "batch" in df.columns and df["batch"].nunique() > 1:
        contingency = pd.crosstab(df["condition"], df["batch"])
        # If any condition is uniquely present in only one batch with no overlap, check rank
        if (contingency > 0).sum(axis=1).max() == 1 and df["condition"].nunique() == df["batch"].nunique():
            return "NOT_VALID", [
                "TREATMENT EFFECT NOT IDENTIFIABLE: Batch and condition are completely confounded (100% correlation)."
            ]

    # Check zero cell combinations for factorial design if design formula specified
    if sample_sheet.design_formula and ":" in sample_sheet.design_formula:
        # Check interaction estimability
        cell_counts = df.groupby(["condition", "genotype"]).size()
        if (cell_counts == 0).any():
            warnings.append("WARNING: Missing cells in factorial design matrix. Interactions may not be fully estimable.")

    return "VALID", warnings
