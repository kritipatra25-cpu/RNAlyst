"""Validation module enforcing biological and technical replicate constraints."""
from typing import Tuple, List
from pipeline.schemas.input_schemas import SampleSheetInput


def validate_biological_replicates(sample_sheet: SampleSheetInput) -> Tuple[str, List[str]]:
    """Evaluates biological replicate counts per condition.

    Replicate Rules:
    - N = 1 per group: NOT_VALID for inferential DE (EXPLORATORY only)
    - N = 2 per group: EXPLORATORY with warning (limited power)
    - N >= 3 per group: VALID
    """
    warnings: List[str] = []
    condition_counts = {}

    for sample in sample_sheet.samples:
        if sample.is_technical_replicate:
            # Technical replicates do NOT count as independent biological replicates
            continue
        cond = sample.condition
        condition_counts[cond] = condition_counts.get(cond, 0) + 1

    min_reps = min(condition_counts.values()) if condition_counts else 0

    if len(condition_counts) < 2:
        return "INVALID", ["Differential expression requires at least two distinct experimental groups."]

    if min_reps < 2:
        insufficient = [cond for cond, count in condition_counts.items() if count < 2]
        warnings.append(
            f"WARNING (N=1): Condition(s) {insufficient} have N < 2 biological replicates. "
            "Inferential differential expression requires at least N=2 biological replicates per group."
        )
        return "EXPLORATORY", warnings

    elif min_reps == 2:
        warnings.append(
            "WARNING: One or more conditions has N=2 biological replicates. "
            "Statistical power to detect differential expression is limited."
        )
        return "VALID", warnings

    return "VALID", warnings
