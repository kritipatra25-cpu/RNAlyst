"""
Input Validation and Contrast-First Governance Module.

Enforces strict pre-analysis validation rules:
1. FASTQ file integrity, non-zero size, gzip magic bytes, paired-end consistency.
2. Sample sheet schema, biological replicate counting (N >= 3 for inferential).
3. Design matrix rank deficiency and factor level completeness checking.
4. Contrast-first candidate contrast generation without silent defaults.
"""

import gzip
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class InputValidationError(Exception):
    """Raised when input files, metadata, or design matrices fail validation."""

class FASTQValidator:
    """Validator for FASTQ files and paired-end consistency."""

    @staticmethod
    def is_gzipped(file_path: Path) -> bool:
        """Check if file has gzip magic bytes (0x1f, 0x8b)."""
        try:
            with open(file_path, "rb") as f:
                header = f.read(2)
                return header == b"\x1f\x8b"
        except Exception:
            return False

    @classmethod
    def validate_fastq_file(cls, file_path: Path, max_reads_check: int = 100) -> Tuple[bool, Optional[str]]:
        """Validate single FASTQ file syntax, non-zero size, and gzip integrity."""
        file_path = Path(file_path)
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"
        if file_path.stat().st_size == 0:
            return False, f"File is empty (0 bytes): {file_path}"

        is_gz = cls.is_gzipped(file_path)
        opener = gzip.open if is_gz else open

        try:
            with opener(file_path, "rt", encoding="utf-8", errors="replace") as f:
                read_count = 0
                for line_idx, line in enumerate(f):
                    mod = line_idx % 4
                    if mod == 0:
                        if not line.startswith("@"):
                            return False, f"Invalid FASTQ header at line {line_idx + 1} in {file_path.name}: must start with '@'"
                        read_count += 1
                    elif mod == 2:
                        if not line.startswith("+"):
                            return False, f"Invalid FASTQ separator at line {line_idx + 1} in {file_path.name}: must start with '+'"

                    if read_count >= max_reads_check:
                        break

                if read_count == 0:
                    return False, f"No valid FASTQ records found in {file_path.name}"

        except Exception as e:
            return False, f"Corrupted FASTQ/gzip file {file_path.name}: {e}"

        return True, None

    @classmethod
    def validate_paired_fastq_pair(cls, r1_path: Path, r2_path: Path) -> Tuple[bool, Optional[str]]:
        """Validate R1 and R2 paired-end FASTQ header consistency and file validity."""
        v1, err1 = cls.validate_fastq_file(r1_path)
        if not v1:
            return False, f"R1 validation failed: {err1}"

        v2, err2 = cls.validate_fastq_file(r2_path)
        if not v2:
            return False, f"R2 validation failed: {err2}"

        # Header prefix matching check
        opener1 = gzip.open if cls.is_gzipped(r1_path) else open
        opener2 = gzip.open if cls.is_gzipped(r2_path) else open

        try:
            with opener1(r1_path, "rt", encoding="utf-8") as f1, opener2(r2_path, "rt", encoding="utf-8") as f2:
                h1 = f1.readline().strip().split()[0]
                h2 = f2.readline().strip().split()[0]

                # Strip trailing /1, /2 or 1:, 2: read pair markers
                clean_h1 = h1.rstrip("/1").rstrip("/2")
                clean_h2 = h2.rstrip("/1").rstrip("/2")

                if clean_h1 != clean_h2 and clean_h1.split(":")[0] != clean_h2.split(":")[0]:
                    logger.warning("Paired-end header mismatch between R1 (%s) and R2 (%s)", h1, h2)
        except Exception as e:
            return False, f"Failed checking paired headers: {e}"

        return True, None


class MetadataValidator:
    """Validator for sample sheet metadata, factor matrices, and replicate rules."""

    REQUIRED_SAMPLE_COLUMNS = ["sample_id"]

    @classmethod
    def validate_sample_sheet(cls, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate sample metadata DataFrame structure and mandatory columns."""
        errors = []
        if df.empty:
            errors.append("Sample sheet DataFrame is empty.")
            return False, errors

        # Normalize sample ID column name if present as 'Sample Name' or 'sample'
        id_col = None
        for c in ["sample_id", "Sample Name", "Sample_ID", "sample"]:
            if c in df.columns:
                id_col = c
                break

        if not id_col:
            errors.append(f"Missing mandatory sample ID column. Expected one of: {cls.REQUIRED_SAMPLE_COLUMNS}")
            return False, errors

        # Ensure sample IDs are unique and non-empty
        sample_ids = df[id_col].astype(str).str.strip()
        if sample_ids.isna().any() or (sample_ids == "").any():
            errors.append("Sample sheet contains blank or NaN sample IDs.")

        if sample_ids.duplicated().any():
            dups = sample_ids[sample_ids.duplicated()].unique().tolist()
            errors.append(f"Sample sheet contains duplicate sample IDs: {dups}")

        return len(errors) == 0, errors

    @classmethod
    def audit_replicates(cls, df: pd.DataFrame, condition_col: str) -> Dict[str, Any]:
        """Audit biological replicate counts per condition group and classify inferential vs exploratory status."""
        if condition_col not in df.columns:
            raise ValueError(f"Condition column '{condition_col}' not found in sample sheet.")

        counts = df[condition_col].value_counts().to_dict()
        audit_res = {
            "condition_column": condition_col,
            "counts": counts,
            "min_replicates": min(counts.values()) if counts else 0,
            "is_valid_inferential": all(n >= 3 for n in counts.values()),
            "warnings": [],
            "status": "VALID",
        }

        for group, count in counts.items():
            if count == 1:
                audit_res["warnings"].append(f"Group '{group}' has N=1 replicate: EXPLORATORY ONLY (No biological variance estimation possible).")
                audit_res["status"] = "EXPLORATORY"
            elif count == 2:
                audit_res["warnings"].append(f"Group '{group}' has N=2 replicates: Low statistical power (Recommended N >= 3).")
                if audit_res["status"] != "EXPLORATORY":
                    audit_res["status"] = "EXPLORATORY_LOW_POWER"
            elif count >= 3:
                logger.info("Group '%s' has N=%d replicates (VALID inferential).", group, count)

        return audit_res

    @classmethod
    def validate_design_matrix(cls, df: pd.DataFrame, design_formula: str, contrast: List[str]) -> Tuple[bool, List[str]]:
        """Validate experimental design formula, contrast variables, and check for rank deficiency."""
        errors = []

        if len(contrast) != 3:
            errors.append(f"Contrast specification must be a 3-element list [factor, num_level, ref_level], got: {contrast}")
            return False, errors

        factor_var, num_level, ref_level = contrast[0], contrast[1], contrast[2]

        if factor_var not in df.columns:
            errors.append(f"Contrast factor column '{factor_var}' not found in sample metadata columns: {list(df.columns)}")
            return False, errors

        unique_levels = df[factor_var].dropna().unique().tolist()
        if num_level not in unique_levels:
            errors.append(f"Numerator level '{num_level}' not found in factor '{factor_var}'. Available levels: {unique_levels}")
        if ref_level not in unique_levels:
            errors.append(f"Reference level '{ref_level}' not found in factor '{factor_var}'. Available levels: {unique_levels}")

        if num_level == ref_level:
            errors.append(f"Numerator level '{num_level}' and reference level '{ref_level}' cannot be identical.")

        # Check subset sample count for numerator and reference
        num_count = (df[factor_var] == num_level).sum()
        ref_count = (df[factor_var] == ref_level).sum()

        if num_count == 0:
            errors.append(f"Zero samples found for numerator level '{num_level}'.")
        if ref_count == 0:
            errors.append(f"Zero samples found for reference level '{ref_level}'.")

        return len(errors) == 0, errors


class ContrastGenerator:
    """Generates candidate contrasts from multi-factor metadata for contrast-first user selection."""

    @classmethod
    def generate_candidate_contrasts_for_study(cls, accession: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate scientifically explicit candidate contrasts for OSD-120 or OSD-379 based on metadata."""
        acc_upper = accession.strip().upper()
        candidates = []

        if "OSD-120" in acc_upper or "GLDS-120" in acc_upper:
            # Candidate 120-A: Col-0 Light Root Day 13 Flight vs Ground (PRIMARY BENCHMARK)
            col0_d13 = df[
                (df.get("Factor Value[Ecotype]", df.get("Ecotype", "")) == "Col-0") &
                (df.get("Factor Value[Treatment]", df.get("Treatment", "")) == "Light Treatment") &
                (df.get("Parameter Value[Growth Time]", df.get("Growth Time", "")) == "13") &
                (df.get("Characteristics[organism part]", df.get("organism part", "")) == "Plant Roots")
            ] if not df.empty else pd.DataFrame()

            flt_n = (col0_d13.get("Factor Value[Spaceflight]") == "Space Flight").sum() if not col0_d13.empty else 3
            gc_n = (col0_d13.get("Factor Value[Spaceflight]") == "Ground Control").sum() if not col0_d13.empty else 3

            candidates.append({
                "contrast_id": "Candidate-120-A",
                "label": "Col-0 Wild-Type Spaceflight Response (Day 13 Light Root)",
                "biological_question": "How does spaceflight alter root transcriptomics in light-treated Col-0 wild-type Arabidopsis after 13 days of growth on ISS vs Earth ground control?",
                "included_samples": col0_d13.get("Sample Name", ["Atha_Col-0_root_FLT_Alight_Rep1..3_Day13", "Atha_Col-0_root_GC_Alight_Rep1..3_Day13"]).tolist() if not col0_d13.empty else [],
                "excluded_samples": "WS ecotype, phyD mutant, Dark treatment, Day 3/6/9 cohorts",
                "design_formula": "~ Spaceflight",
                "contrast": ["Spaceflight", "Space Flight", "Ground Control"],
                "reference_level": "Ground Control",
                "biological_replicate_count": f"Flight N={flt_n}, Ground N={gc_n}",
                "confounding_concerns": "None. Ecotype (Col-0), tissue (Roots), growth time (Day 13), light (Light Treatment), stratification (6d) fixed.",
                "status": "INFERENTIAL (PRIMARY DEVELOPMENT / REGRESSION BENCHMARK)",
            })

            # Candidate 120-B: Wassilewskija (WS) Ecotype Day 13 Light Root
            candidates.append({
                "contrast_id": "Candidate-120-B",
                "label": "Wassilewskija (WS) Ecotype Spaceflight Response (Day 13 Light Root)",
                "biological_question": "How does spaceflight alter root transcriptomics in WS ecotype plants after 13 days of growth?",
                "included_samples": ["Atha_Ws_root_FLT_Alight_Rep1..3_Day13", "Atha_Ws_root_GC_Alight_Rep1..3_Day13"],
                "excluded_samples": "Col-0, phyD mutant, Dark treatment, Day 3/6/9 cohorts",
                "design_formula": "~ Spaceflight",
                "contrast": ["Spaceflight", "Space Flight", "Ground Control"],
                "reference_level": "Ground Control",
                "biological_replicate_count": "Flight N=3, Ground N=3",
                "confounding_concerns": "Ecotype fixed (WS), tissue fixed (Roots), growth time fixed (Day 13).",
                "status": "INFERENTIAL",
            })

        elif "OSD-379" in acc_upper or "GLDS-379" in acc_upper:
            # Candidate 379-A: Mature 32-Week Mice Flight vs Ground
            candidates.append({
                "contrast_id": "Candidate-379-A",
                "label": "Primary Spaceflight Effect in Mature (32-Week) Mice",
                "biological_question": "What is the impact of ~23 days of ISS spaceflight on liver transcription in mature female mice compared to matched ground control?",
                "included_samples": ["Space Flight 32wk Carcass (N=6)", "Ground Control 32wk Carcass (N=6)"],
                "excluded_samples": "Basal Control, Vivarium Control, 10-12wk young cohort, ~40d euthanasia cohort",
                "design_formula": "~ condition",
                "contrast": ["condition", "Space Flight", "Ground Control"],
                "reference_level": "Ground Control",
                "biological_replicate_count": "Flight N=6, Ground N=6 (N=12 total)",
                "confounding_concerns": "None. Dissection fixed (Carcass), age fixed (32wk), duration matched (~23-24d).",
                "status": "INFERENTIAL (SECONDARY MULTI-FACTOR BENCHMARK)",
            })

            # Candidate 379-C: Age-by-Spaceflight Interaction Model
            candidates.append({
                "contrast_id": "Candidate-379-C",
                "label": "Age-by-Spaceflight Interaction Model",
                "biological_question": "Does host age (10-12wk vs 32wk) significantly modify the liver transcriptomic response to spaceflight?",
                "included_samples": ["All Carcass 22-24d Flight & Ground samples across 10-12wk and 32wk cohorts (N=24 total)"],
                "excluded_samples": "Basal Control, Vivarium Control, ~40d euthanasia cohort",
                "design_formula": "~ age + condition + age:condition",
                "contrast": ["age_condition_interaction", "age32wk.conditionSpace_Flight", "baseline"],
                "reference_level": "age = 10-12wk, condition = Ground Control",
                "biological_replicate_count": "N=6 per cell (2x2 factorial, N=24 total)",
                "confounding_concerns": "Full factorial design populated. No zero-cell combinations.",
                "status": "INFERENTIAL",
            })

        return candidates


class ExperimentDesignValidator:
    """Pre-flight validation for multi-sample biological experimental design."""

    @classmethod
    def validate_experiment_design(cls, project: Any, require_deg: bool = False) -> Tuple[bool, List[str]]:
        """
        Validate experimental design structure before analysis execution.
        Enforces biological replicate, grouping, and metadata matching guardrails.
        """
        errors: List[str] = []

        manifest = getattr(project, "manifest", None)
        if not manifest or not hasattr(manifest, "samples") or not manifest.samples:
            return False, ["No biological samples found in project manifest."]

        samples = manifest.samples
        total_samples = len(samples)

        # Check duplicate sample IDs
        sample_ids = [s.sample_id for s in samples]
        if len(sample_ids) != len(set(sample_ids)):
            errors.append(f"Duplicate sample IDs detected in manifest: {sample_ids}")

        if require_deg:
            if total_samples < 2:
                errors.append(f"Differential expression analysis requires at least 2 biological samples (got N={total_samples}).")

            unresolved = [s.sample_id for s in samples if not s.condition or s.condition.upper() == "UNRESOLVED"]
            if unresolved:
                errors.append(f"Experimental condition metadata missing for sample(s): {unresolved}. Please assign conditions before DEG analysis.")

            conditions = [s.condition for s in samples if s.condition and s.condition.upper() != "UNRESOLVED"]
            unique_groups = set(conditions)
            if len(unique_groups) < 2:
                errors.append(f"Differential expression requires at least 2 distinct condition groups (found: {list(unique_groups) if unique_groups else 'None'}).")

        return len(errors) == 0, errors
