"""
Deterministic Agent Planning & Execution Contract Layer.
Converts natural language user questions into validated StructuredAnalysisPlans,
optionally ingesting untrusted proposals from a provider-agnostic BaseLLMProvider.
"""
import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from pipeline.job_models import (
    StructuredAnalysisPlan, RequiredInputSpec, ExpectedOutputArtifact, StepRationale
)
from pipeline.llm_provider import BaseLLMProvider, LLMIntentProposal

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"


class AnalysisPlanner:
    """
    Deterministic planner that ingests non-authoritative LLM proposals (if provided),
    independently validates user question scope, resolves workspace input files,
    builds step execution rationales, and generates an authoritative StructuredAnalysisPlan.
    """

    def __init__(self, uploads_dir: Optional[Path] = None, llm_provider: Optional[BaseLLMProvider] = None):
        self.uploads_dir = uploads_dir or UPLOADS_DIR
        self.llm_provider = llm_provider

    def parse_question_intent(self, user_question: Optional[str]) -> Tuple[str, str, List[str]]:
        """
        Deterministic fallback intent parser mapping natural language user questions
        to an interpreted intent, analysis goal, and candidate steps.
        """
        if not user_question or not user_question.strip():
            return "GENERAL_RNA_SEQ_ANALYSIS", "Perform dataset discovery and standard workflow", ["validating_dataset", "pca", "differential_expression"]

        q = user_question.strip().lower()

        # Check for Differential Expression keywords
        is_de = any(k in q for k in [
            "differential", "differentially", "de", "deseq", "fold change", "log2fc",
            "treated vs control", "control vs treated", "significantly different",
            "upregulated", "downregulated", "significant genes", "volcano", "heatmap"
        ])

        # Check for PCA / Clustering keywords
        is_pca = any(k in q for k in [
            "pca", "principal component", "clustering", "variance", "dimensionality",
            "sample relationship", "grouping", "overview plot"
        ])

        # Check for QC keywords
        is_qc = any(k in q for k in [
            "qc", "quality control", "fastq", "reads", "phred", "gc content",
            "read count", "per base quality", "trimming"
        ])

        # General RNA-Seq analysis request fallback
        is_general_rnaseq = any(k in q for k in [
            "rna-seq", "rnaseq", "transcriptome", "expression", "counts", "gene expression",
            "pipeline", "analysis", "workflow", "run all", "full analysis"
        ])

        candidate_steps = []
        intents = []

        if is_qc or ("fastq" in q and not is_de and not is_pca):
            candidate_steps.append("validating_dataset")
            intents.append("QC")

        if is_pca:
            candidate_steps.append("pca")
            intents.append("PCA")

        if is_de:
            if "pca" not in candidate_steps:
                candidate_steps.append("pca")
            candidate_steps.append("differential_expression")
            intents.append("DIFFERENTIAL_EXPRESSION")

        if not candidate_steps:
            if is_general_rnaseq:
                candidate_steps = ["validating_dataset", "pca", "differential_expression"]
                intents = ["GENERAL_DISCOVERY"]
            else:
                # Unsupported or out of scope question
                return (
                    "UNSUPPORTED_QUESTION",
                    f"Question '{user_question.strip()}' is out of scope or unsupported for RNA-seq analysis.",
                    []
                )

        interpreted_intent = "_AND_".join(intents)
        analysis_goal = f"Execute {' + '.join(intents)} pipeline based on user query: '{user_question.strip()}'"

        return interpreted_intent, analysis_goal, candidate_steps

    def _resolve_file(self, file_id: str, file_kind: str) -> Optional[Path]:
        req_id = str(file_id).strip().lower()

        if file_kind == "fastq":
            for path in self.uploads_dir.rglob("*"):
                if not path.is_file():
                    continue
                name = path.name.lower()
                if name.endswith((".fastq", ".fq", ".fastq.gz", ".fq.gz")):
                    if name.startswith(req_id + "_") or name.startswith(req_id) or req_id in name:
                        return path
            return None

        elif file_kind == "count_matrix":
            for path in self.uploads_dir.rglob("*"):
                if not path.is_file() or path.suffix not in [".csv", ".tsv", ".txt"]:
                    continue
                name = path.name.lower()
                if "metadata" in name or "design" in name or "samples" in name:
                    continue
                if name.startswith(req_id + "_") or name.startswith(req_id) or req_id in name:
                    return path
            return None

        elif file_kind == "sample_metadata":
            for path in self.uploads_dir.rglob("*"):
                if not path.is_file() or path.suffix not in [".csv", ".tsv", ".txt"]:
                    continue
                name = path.name.lower()
                if ("metadata" in name or "design" in name or "samples" in name) and (name.startswith(req_id + "_") or name.startswith(req_id) or req_id in name):
                    return path
            return None

        return None

    def validate_inputs_for_steps(
        self, file_id: str, candidate_steps: List[str]
    ) -> Tuple[List[RequiredInputSpec], bool, List[str]]:
        """
        Determines input specs required for selected steps, checks file existence ONLY
        in trusted uploads_dir, and generates validation errors if required files are missing.
        """
        specs = []
        validation_errors = []
        is_valid = True

        if not candidate_steps:
            return [], False, ["No valid execution steps selected for this query."]

        needs_qc = any(s in candidate_steps for s in ["validating_dataset", "qc"])
        needs_count_matrix = any(s in candidate_steps for s in ["pca", "differential_expression", "de"])
        needs_metadata = any(s in candidate_steps for s in ["differential_expression", "de"])

        # 1. FASTQ spec
        if needs_qc:
            fq_path = self._resolve_file(file_id, "fastq")
            is_avail = fq_path is not None and fq_path.exists()
            msg = f"FASTQ file resolved at {fq_path}" if is_avail else f"No FASTQ file found matching ID '{file_id}'."
            specs.append(RequiredInputSpec(
                input_type="fastq",
                required_for_steps=[s for s in candidate_steps if s in ["validating_dataset", "qc"]],
                is_available=is_avail,
                resolved_path=str(fq_path) if is_avail else None,
                resolution_message=msg
            ))
            if not is_avail and not needs_count_matrix:
                is_valid = False
                validation_errors.append(f"FASTQ Quality Control requires an uploaded FASTQ file for ID '{file_id}'.")

        # 2. Count Matrix spec
        if needs_count_matrix:
            cm_path = self._resolve_file(file_id, "count_matrix")
            is_avail = cm_path is not None and cm_path.exists()
            msg = f"Gene count matrix resolved at {cm_path}" if is_avail else f"No expression/count matrix CSV/TSV found matching ID '{file_id}'."
            specs.append(RequiredInputSpec(
                input_type="count_matrix",
                required_for_steps=[s for s in candidate_steps if s in ["pca", "differential_expression", "de"]],
                is_available=is_avail,
                resolved_path=str(cm_path) if is_avail else None,
                resolution_message=msg
            ))
            if not is_avail:
                is_valid = False
                validation_errors.append(f"PCA requires a gene-by-sample expression/count matrix CSV/TSV for ID '{file_id}'.")

        # 3. Sample Metadata spec
        if needs_metadata:
            meta_path = self._resolve_file(file_id, "sample_metadata")
            is_avail = meta_path is not None and meta_path.exists()
            msg = f"Sample metadata resolved at {meta_path}" if is_avail else f"No sample metadata CSV/TSV found matching ID '{file_id}'."
            specs.append(RequiredInputSpec(
                input_type="sample_metadata",
                required_for_steps=[s for s in candidate_steps if s in ["differential_expression", "de"]],
                is_available=is_avail,
                resolved_path=str(meta_path) if is_avail else None,
                resolution_message=msg
            ))
            if not is_avail and is_valid:
                is_valid = False
                validation_errors.append(f"Differential expression requires a gene-by-sample count matrix and sample metadata defining experimental conditions for ID '{file_id}'.")

        return specs, is_valid, validation_errors

    def create_analysis_plan(
        self,
        file_id: str,
        user_question: Optional[str] = None,
        requested_plan: Optional[List[str]] = None
    ) -> StructuredAnalysisPlan:
        """
        Assembles an authoritative, validated StructuredAnalysisPlan.
        If an LLM provider is present, ingests its proposal as non-authoritative suggestions.
        Deterministically validates question scope, workspace input files, and step execution.
        """
        # 1. Independent Scope Check: Determine if user_question is supported
        det_intent, det_goal, det_steps = self.parse_question_intent(user_question)
        if det_intent == "UNSUPPORTED_QUESTION":
            return StructuredAnalysisPlan(
                user_question=user_question or "Unspecified query",
                interpreted_intent="UNSUPPORTED_QUESTION",
                analysis_goal=det_goal,
                is_valid=False,
                validation_errors=[f"User question '{user_question}' is not a recognized RNA-seq analysis request (supported: QC, PCA, Differential Expression, Heatmap/Volcano plots)."],
                required_inputs=[],
                selected_steps=[],
                step_rationales=[],
                expected_artifacts=[]
            )

        selected_steps = []
        analysis_goal = det_goal
        interpreted_intent = det_intent

        # 2. Ingest LLM Proposal if available
        if self.llm_provider is not None:
            try:
                llm_proposal = self.llm_provider.generate_intent_proposal(user_question)
                if llm_proposal.proposed_steps:
                    valid_known_steps = ["validating_dataset", "qc", "pca", "differential_expression", "de"]
                    proposed = [s for s in llm_proposal.proposed_steps if s in valid_known_steps]
                    
                    if proposed:
                        selected_steps = proposed
                        if "differential_expression" in selected_steps or "de" in selected_steps:
                            if "pca" not in selected_steps:
                                selected_steps.insert(0, "pca")
                    if llm_proposal.proposed_goal:
                        analysis_goal = llm_proposal.proposed_goal
            except Exception as e:
                logger.warning("LLM provider proposal failed or malformed (%s); falling back to deterministic parser.", e)
                selected_steps = det_steps

        if not selected_steps:
            if requested_plan:
                selected_steps = requested_plan
            else:
                selected_steps = det_steps

        # 3. Deterministic Input Resolution & Validation (Ignore any LLM path claims)
        input_specs, is_valid, validation_errors = self.validate_inputs_for_steps(file_id, selected_steps)

        rationales = []
        expected_artifacts = []

        for step in selected_steps:
            if step in ["validating_dataset", "qc"]:
                rationales.append(StepRationale(
                    step=step,
                    rationale="Evaluates sequence quality, read count, GC content, and Phred quality scores.",
                    required_inputs=["fastq"],
                    expected_outputs=["qc_summary.json", "qc_plot.png"]
                ))
                expected_artifacts.extend([
                    ExpectedOutputArtifact(artifact_type="qc_summary", step=step, description="FASTQ quality metrics summary JSON"),
                    ExpectedOutputArtifact(artifact_type="qc_plot", step=step, description="Multi-panel FASTQ quality overview PNG plot")
                ])
            elif step == "pca":
                rationales.append(StepRationale(
                    step=step,
                    rationale="Computes Principal Component Analysis on variance-stabilized log2 counts to evaluate sample grouping.",
                    required_inputs=["count_matrix"],
                    expected_outputs=["pca_results.json", "pca_plot.png"]
                ))
                expected_artifacts.extend([
                    ExpectedOutputArtifact(artifact_type="pca_results", step=step, description="PCA coordinates and variance summary JSON"),
                    ExpectedOutputArtifact(artifact_type="pca_plot", step=step, description="Publication-quality 300 DPI PCA scatter plot PNG")
                ])
            elif step in ["differential_expression", "de"]:
                rationales.append(StepRationale(
                    step=step,
                    rationale="Performs PyDESeq2 / Welch DE analysis comparing experimental conditions to identify significant genes.",
                    required_inputs=["count_matrix", "sample_metadata"],
                    expected_outputs=["de_summary.json", "de_results.csv", "volcano_plot.png", "heatmap_plot.png"]
                ))
                expected_artifacts.extend([
                    ExpectedOutputArtifact(artifact_type="de_summary", step=step, description="Differential expression statistics summary JSON"),
                    ExpectedOutputArtifact(artifact_type="de_table", step=step, description="Full gene-level differential expression results CSV"),
                    ExpectedOutputArtifact(artifact_type="volcano_plot", step=step, description="Differential expression volcano plot PNG"),
                    ExpectedOutputArtifact(artifact_type="heatmap_plot", step=step, description="Top DE genes expression z-score heatmap PNG")
                ])

        # 4. Canonical Intent Determination
        intents = []
        if any(s in selected_steps for s in ["validating_dataset", "qc"]):
            intents.append("QC")
        if any(s in selected_steps for s in ["pca"]):
            intents.append("PCA")
        if any(s in selected_steps for s in ["differential_expression", "de"]):
            intents.append("DIFFERENTIAL_EXPRESSION")

        if intents:
            interpreted_intent = "_AND_".join(intents)

        plan = StructuredAnalysisPlan(
            user_question=user_question or "Unspecified user query",
            interpreted_intent=interpreted_intent,
            analysis_goal=analysis_goal,
            is_valid=is_valid,
            validation_errors=validation_errors,
            required_inputs=input_specs,
            selected_steps=selected_steps,
            step_rationales=rationales,
            expected_artifacts=expected_artifacts
        )

        return plan
