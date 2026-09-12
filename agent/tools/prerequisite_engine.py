"""
Scientific Prerequisite Engine for RNAlyst Platform.

Defines and enforces operation-specific scientific prerequisites for every bioinformatics tool:
1. QC: FASTQ files uploaded
2. Quantification: FASTQ files + reference index / Salmon binary (bypassed if count matrix exists)
3. Count Validation: counts_matrix.csv present and valid
4. Normalization / VST: count matrix present and >= 2 samples
5. PCA: expression matrix present and >= 2 samples
6. Differential Expression: count matrix + sample metadata + valid contrast + N >= 2 biological replicates per group
7. Volcano Plot: DE results CSV present
8. Heatmap: DE results CSV or expression matrix present
9. Enrichment: DEG list present (padj < cutoff)
10. Literature Grounding: active project organism and query terms

Missing prerequisites return structured error metadata with clear remediation instructions.
Zero synthetic, mock, or static fallbacks are permitted.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class ScientificPrerequisiteError(Exception):
    """Base exception for missing or unsatisfied scientific prerequisites."""
    def __init__(self, error_type: str, message: str, missing_prerequisites: List[str], recommendation: str):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.missing_prerequisites = missing_prerequisites
        self.recommendation = recommendation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "missing_prerequisites": self.missing_prerequisites,
            "recommendation": self.recommendation
        }


class MissingPrerequisitesError(ScientificPrerequisiteError):
    def __init__(self, message: str, missing_prerequisites: List[str], recommendation: str):
        super().__init__("MissingPrerequisitesError", message, missing_prerequisites, recommendation)


class InsufficientReplicatesError(ScientificPrerequisiteError):
    def __init__(self, message: str, missing_prerequisites: List[str], recommendation: str):
        super().__init__("InsufficientReplicatesError", message, missing_prerequisites, recommendation)


class PrerequisiteEngine:
    """Authoritative scientific prerequisite validation engine."""

    def __init__(self, projects_dir: str = "projects"):
        self.projects_dir = Path(projects_dir).resolve()

    def get_project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id.strip().upper()

    def validate_qc_prerequisites(self, project_id: str, fastq_files: Optional[List[Path]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate prerequisites for Quality Control (QC)."""
        proj_dir = self.get_project_dir(project_id)
        uploads_dir = proj_dir / "data" / "uploads"

        has_files = False
        if fastq_files and len(fastq_files) > 0:
            has_files = True
        elif uploads_dir.exists():
            found = list(uploads_dir.glob("*.fastq*")) + list(uploads_dir.glob("*.fq*"))
            has_files = len(found) > 0

        if not has_files:
            err = MissingPrerequisitesError(
                message=f"No FASTQ files found for project '{project_id}'. FASTQ files must be uploaded before running QC.",
                missing_prerequisites=["fastq_files"],
                recommendation="Upload paired-end or single-end FASTQ files via POST /api/v1/qc."
            )
            return False, err.to_dict()

        return True, None

    def validate_quantification_prerequisites(
        self,
        project_id: str,
        has_salmon_binary: bool,
        reference_fasta: Optional[Path] = None,
        has_direct_counts: bool = False
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate prerequisites for FASTQ Quantification (Salmon). Bypassed if direct counts matrix exists."""
        if has_direct_counts:
            return True, None

        proj_dir = self.get_project_dir(project_id)
        uploads_dir = proj_dir / "data" / "uploads"

        has_fastqs = uploads_dir.exists() and len(list(uploads_dir.glob("*.fastq*")) + list(uploads_dir.glob("*.fq*"))) > 0

        missing = []
        if not has_fastqs:
            missing.append("fastq_files")
        if not has_salmon_binary:
            missing.append("salmon_executable")
        if reference_fasta and not Path(reference_fasta).exists():
            missing.append("reference_transcriptome_fasta")

        if missing:
            err = MissingPrerequisitesError(
                message=f"Cannot execute transcript quantification for project '{project_id}': missing {', '.join(missing)}.",
                missing_prerequisites=missing,
                recommendation="Upload FASTQ files and ensure Salmon binary / reference transcriptome is available, OR upload a pre-computed counts_matrix.csv directly."
            )
            return False, err.to_dict()

        return True, None

    def validate_pca_prerequisites(self, project_id: str, counts_matrix_path: Optional[Path] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate prerequisites for 2D Principal Component Analysis (PCA)."""
        proj_dir = self.get_project_dir(project_id)
        matrix_path = counts_matrix_path or (proj_dir / "data" / "counts_matrix.csv")

        if not matrix_path.exists() or matrix_path.stat().st_size < 10:
            err = MissingPrerequisitesError(
                message=f"Counts matrix missing for project '{project_id}'. Quantified expression data is required to perform PCA.",
                missing_prerequisites=["counts_matrix"],
                recommendation="Upload a counts_matrix.csv or execute FASTQ quantification first."
            )
            return False, err.to_dict()

        try:
            df = pd.read_csv(matrix_path)
            sample_cols = [c for c in df.columns if str(c).lower() not in ("gene_id", "transcript_id", "id", "name", "unnamed: 0")]
            if len(sample_cols) < 2:
                err = MissingPrerequisitesError(
                    message=f"PCA requires at least 2 biological samples to calculate principal components. Project '{project_id}' contains only {len(sample_cols)} sample(s).",
                    missing_prerequisites=["multiple_biological_samples"],
                    recommendation="Upload FASTQ files or expression data for at least 2 distinct biological samples."
                )
                return False, err.to_dict()
        except Exception as e:
            err = MissingPrerequisitesError(
                message=f"Failed to parse counts matrix at {matrix_path}: {e}",
                missing_prerequisites=["valid_counts_matrix"],
                recommendation="Verify that counts_matrix.csv contains valid numerical gene expression counts."
            )
            return False, err.to_dict()

        return True, None

    def validate_de_prerequisites(
        self,
        project_id: str,
        counts_matrix_path: Optional[Path] = None,
        sample_metadata_path: Optional[Path] = None,
        condition_col: str = "condition"
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate prerequisites for Inferential Differential Expression (DE). Strictly enforces N >= 2 biological replicates per group."""
        proj_dir = self.get_project_dir(project_id)
        c_path = counts_matrix_path or (proj_dir / "data" / "counts_matrix.csv")
        m_path = sample_metadata_path or (proj_dir / "data" / "sample_metadata.csv")

        if not c_path.exists() or c_path.stat().st_size < 10:
            err = MissingPrerequisitesError(
                message=f"Counts matrix missing for project '{project_id}'. Cannot execute differential expression.",
                missing_prerequisites=["counts_matrix"],
                recommendation="Provide a valid counts_matrix.csv for project."
            )
            return False, err.to_dict()

        if not m_path.exists() or m_path.stat().st_size < 10:
            err = MissingPrerequisitesError(
                message=f"Sample metadata file missing for project '{project_id}'. Differential expression requires experimental condition assignments.",
                missing_prerequisites=["sample_metadata"],
                recommendation="Assign experimental conditions/groups for each sample via sample_metadata.csv."
            )
            return False, err.to_dict()

        try:
            df_meta = pd.read_csv(m_path)
            if condition_col not in df_meta.columns:
                err = MissingPrerequisitesError(
                    message=f"Sample metadata is missing condition column '{condition_col}'. Available columns: {list(df_meta.columns)}",
                    missing_prerequisites=["condition_column"],
                    recommendation=f"Include a '{condition_col}' column in sample_metadata.csv specifying control vs treatment groups."
                )
                return False, err.to_dict()

            conds = [str(c).strip() for c in df_meta[condition_col] if pd.notna(c) and str(c).strip().upper() != "UNRESOLVED"]
            unique_groups = set(conds)

            if len(unique_groups) < 2:
                err = MissingPrerequisitesError(
                    message=f"Differential expression requires at least 2 distinct experimental groups (e.g. control vs treatment). Found: {list(unique_groups)}",
                    missing_prerequisites=["experimental_contrast_groups"],
                    recommendation="Assign at least two distinct experimental groups (e.g., control and treatment) to samples."
                )
                return False, err.to_dict()

            # Count biological replicates per group
            group_counts = {}
            for c in conds:
                group_counts[c] = group_counts.get(c, 0) + 1

            insufficient_groups = [grp for grp, count in group_counts.items() if count < 2]

            if insufficient_groups:
                err = InsufficientReplicatesError(
                    message=f"Inferential differential expression cannot be performed: group(s) {insufficient_groups} have N < 2 biological replicates. Replicate breakdown: {group_counts}.",
                    missing_prerequisites=["biological_replicates_ge_2"],
                    recommendation="Upload additional biological replicate samples so that every experimental group has N >= 2 biological replicates."
                )
                return False, err.to_dict()

        except Exception as e:
            if isinstance(e, ScientificPrerequisiteError):
                raise
            err = MissingPrerequisitesError(
                message=f"Error validating DE metadata for project '{project_id}': {e}",
                missing_prerequisites=["valid_metadata"],
                recommendation="Check sample_metadata.csv formatting."
            )
            return False, err.to_dict()

        return True, None

    def validate_volcano_prerequisites(self, project_id: str, de_csv_path: Optional[Path] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate prerequisites for Volcano Plot."""
        proj_dir = self.get_project_dir(project_id)
        if de_csv_path:
            target = Path(de_csv_path)
        else:
            results_dir = proj_dir / "results"
            de_files = list(results_dir.glob("*_deseq2_results.csv")) if results_dir.exists() else []
            target = de_files[0] if de_files else (proj_dir / "data" / "differential_expression.csv")

        if not target.exists() or target.stat().st_size < 10:
            err = MissingPrerequisitesError(
                message=f"Differential expression results missing for project '{project_id}'. Cannot generate volcano plot.",
                missing_prerequisites=["de_results"],
                recommendation="Run differential expression analysis prior to requested volcano plot generation."
            )
            return False, err.to_dict()

        return True, None
