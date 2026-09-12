"""
Machine-Readable Analysis Plan and Intent Validation Engine.

Converts structured AnalysisIntent objects into explicit step-by-step AnalysisPlan objects
and validates them against the deterministic RNASeqBackendAPI.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from agent.orchestrator.intent_parser import AnalysisIntent
from pipeline.backend_api import RNASeqBackendAPI, AnalysisRequest

logger = logging.getLogger(__name__)


class PlanStep(BaseModel):
    """Single machine-readable step in an analysis plan."""
    step_number: int
    name: str
    operation: str  # RESOLVE_DATASET, VALIDATE_METADATA, EXECUTE_DE, ANNOTATE_GENES, SEARCH_LITERATURE, SYNTHESIZE_REPORT
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field("PENDING", description="PENDING, EXECUTED, REJECTED, SKIPPED")
    output_summary: Optional[str] = None


class AnalysisPlan(BaseModel):
    """Machine-readable multi-step execution plan for an AI-orchestrated query."""
    plan_id: str
    dataset_id: str
    intent: AnalysisIntent
    steps: List[PlanStep]
    is_validated: bool = False
    validation_errors: List[str] = Field(default_factory=list)


class PlanValidator:
    """Validates AnalysisPlan steps against RNASeqBackendAPI and scientific constraints."""

    def __init__(self, backend_api: Optional[RNASeqBackendAPI] = None):
        self.api = backend_api or RNASeqBackendAPI()

    def build_plan(self, intent: AnalysisIntent) -> AnalysisPlan:
        """Construct multi-step AnalysisPlan from AnalysisIntent."""
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        dataset_id = intent.dataset_id or "OSD-678"

        steps = []
        step_num = 1

        # Step 1: Resolve & Validate Dataset Metadata
        steps.append(PlanStep(
            step_number=step_num,
            name="Dataset Discovery & Pre-flight Validation",
            operation="VALIDATE_METADATA",
            parameters={"dataset_id": dataset_id}
        ))
        step_num += 1

        # Step 2: Execute Differential Expression
        if intent.action in ["run_analysis", "filter_candidates", "explain_pathways"]:
            steps.append(PlanStep(
                step_number=step_num,
                name="PyDESeq2 Differential Expression",
                operation="EXECUTE_DE",
                parameters={
                    "dataset_id": dataset_id,
                    "contrast_id": intent.contrast_id,
                    "fdr_cutoff": intent.fdr_cutoff,
                    "lfc_cutoff": intent.lfc_cutoff
                }
            ))
            step_num += 1

        # Step 3: Annotate Genes
        steps.append(PlanStep(
            step_number=step_num,
            name="Multi-Species Gene Annotation",
            operation="ANNOTATE_GENES",
            parameters={"dataset_id": dataset_id, "candidate_genes": intent.candidate_genes}
        ))
        step_num += 1

        # Step 4: Literature RAG Search
        if intent.require_literature or intent.action == "literature_search":
            steps.append(PlanStep(
                step_number=step_num,
                name="Literature RAG Evidence Retrieval",
                operation="SEARCH_LITERATURE",
                parameters={"dataset_id": dataset_id, "candidate_genes": intent.candidate_genes}
            ))
            step_num += 1

        # Step 5: Evidence-Grounded Scientific Synthesis
        steps.append(PlanStep(
            step_number=step_num,
            name="Evidence-Grounded Scientific Synthesis",
            operation="SYNTHESIZE_REPORT",
            parameters={"dataset_id": dataset_id}
        ))

        plan = AnalysisPlan(
            plan_id=plan_id,
            dataset_id=dataset_id,
            intent=intent,
            steps=steps,
            is_validated=False
        )

        return self.validate_plan(plan)

    def validate_plan(self, plan: AnalysisPlan) -> AnalysisPlan:
        """Validate AnalysisPlan against deterministic backend configuration and guardrails."""
        errors = []

        # 1. Validate dataset_id existence
        available_datasets = [d.dataset_id.upper() for d in self.api.list_available_datasets()]
        if plan.dataset_id.upper() not in available_datasets:
            errors.append(f"Invalid dataset_id '{plan.dataset_id}'. Available: {available_datasets}")

        # 2. Validate contrast_id if specified in EXECUTE_DE steps
        for step in plan.steps:
            if step.operation == "EXECUTE_DE":
                cid = step.parameters.get("contrast_id")
                if cid:
                    try:
                        valid_contrasts = [c.id for c in self.api.list_available_contrasts(plan.dataset_id)]
                        if cid not in valid_contrasts:
                            errors.append(f"Invalid contrast_id '{cid}' for dataset {plan.dataset_id}. Valid contrasts: {valid_contrasts}")
                    except Exception as e:
                        errors.append(f"Failed contrast lookup for dataset {plan.dataset_id}: {e}")

                # Validate FDR cutoff bounds
                fdr = step.parameters.get("fdr_cutoff", 0.05)
                if fdr <= 0.0 or fdr >= 1.0:
                    errors.append(f"fdr_cutoff must be between 0.0 and 1.0. Got: {fdr}")

        if errors:
            plan.is_validated = False
            plan.validation_errors = errors
            logger.warning("Plan %s validation REJECTED by backend: %s", plan.plan_id, errors)
        else:
            plan.is_validated = True
            plan.validation_errors = []
            logger.info("Plan %s validation PASSED.", plan.plan_id)

        return plan
