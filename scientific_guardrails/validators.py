"""Master scientific validation gate enforcing statistical and bioinformatics guardrails."""
from typing import List, Tuple
from pipeline.schemas.input_schemas import SampleSheetInput
from scientific_guardrails.replicate_rules import validate_biological_replicates
from scientific_guardrails.design_checker import validate_experimental_design_matrix


class ScientificGuardrailError(Exception):
    """Raised when a hard scientific failure gate is triggered."""
    pass


def run_pre_analysis_guardrails(sample_sheet: SampleSheetInput) -> Tuple[str, List[str]]:
    """Runs all pre-analysis scientific validation checks.

    Returns:
        (validity_status, warnings)
        where validity_status is VALID | VALID_WITH_WARNINGS | EXPLORATORY | NOT_VALID
    """
    warnings: List[str] = []

    # 1. Validate Replicate Rules
    rep_status, rep_warnings = validate_biological_replicates(sample_sheet)
    warnings.extend(rep_warnings)

    if rep_status == "NOT_VALID":
        raise ScientificGuardrailError(
            "Inferential differential expression is scientifically invalid without biological replicates. "
            "Execution halted."
        )

    # 2. Validate Experimental Design & Confounding Matrix
    design_status, design_warnings = validate_experimental_design_matrix(sample_sheet)
    warnings.extend(design_warnings)

    if design_status == "NOT_VALID":
        raise ScientificGuardrailError(
            "Rank deficiency or total batch confounding detected. "
            "Treatment effect not identifiable from this experimental design."
        )

    # Determine aggregated status
    if rep_status == "EXPLORATORY" or design_status == "EXPLORATORY":
        aggregated_status = "EXPLORATORY"
    elif warnings:
        aggregated_status = "VALID_WITH_WARNINGS"
    else:
        aggregated_status = "VALID"

    return aggregated_status, warnings
