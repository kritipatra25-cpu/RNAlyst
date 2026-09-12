"""
AI Agent Orchestrator managing evidence-grounded interpretation, RAG literature synthesis,
and programmatic RNASeqBackendAPI execution through an iterative tool-calling agent loop.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from pipeline.backend_api import (
    RNASeqBackendAPI,
    AnalysisRequest,
    AnalysisResult,
    PreflightValidationResult,
    AnalysisErrorResult,
    DatasetMetadata,
    ContrastMetadata,
)
from pipeline.schemas.results_schemas import AIInterpretationClaim
from scientific_guardrails.claim_guardrails import validate_ai_claim_text

from agent.orchestrator.intent_parser import NaturalLanguageIntentParser, AnalysisIntent
from agent.orchestrator.analysis_plan import PlanValidator, AnalysisPlan
from agent.orchestrator.conversational_manager import ConversationalManager, ConversationalSession, ConversationalTurn
from agent.rag.literature_engine import LiteratureRAGEngine, LiteratureSnippet
from agent.reasoning.scientific_synthesizer import ScientificSynthesizer, ScientificReport
from analysis.annotation.gene_annotator import GeneAnnotator

from agent.tools.base_tool import ToolResult
from agent.tools.deseq2_tool import DESeq2Tool
from agent.tools.literature_tool import LiteratureTool
from agent.tools.gene_annotation_tool import GeneAnnotationTool
from agent.tools.visualization_tools import VolcanoPlotTool, PCAPlotTool, HeatmapTool, QCPlotTool
from agent.tools.candidate_prioritization_tool import CandidatePrioritizationTool
from agent.tools.registry import ToolRegistry
from agent.llm.client import LLMClient, BaseLLMProvider, LLMMessage, LLMResponse, ToolCallRequest
from agent.llm.dispatcher import ToolCallDispatcher
from agent.llm.providers import MockLLMProvider

logger = logging.getLogger(__name__)


class AgentResponse(BaseModel):
    """Structured response returned by the AI Orchestrator Gateway to caller/user."""
    success: bool
    operation: str
    message: str
    session_id: Optional[str] = None
    dataset_id: Optional[str] = None
    intent: Optional[AnalysisIntent] = None
    plan: Optional[AnalysisPlan] = None
    preflight_result: Optional[PreflightValidationResult] = None
    analysis_result: Optional[AnalysisResult] = None
    error_result: Optional[AnalysisErrorResult] = None
    scientific_report: Optional[ScientificReport] = None
    literature_snippets: Optional[List[LiteratureSnippet]] = None
    datasets: Optional[List[DatasetMetadata]] = None
    contrasts: Optional[List[ContrastMetadata]] = None
    claims: Optional[List[AIInterpretationClaim]] = None
    tool_results: Optional[List[ToolResult]] = Field(default_factory=list, description="Executed tool outputs during agent loop")
    iterations_count: int = Field(0, description="Total agentic loop iterations executed")


class AgentOrchestrator:
    """AI Agent Orchestrator acting as evidence-grounded gateway to RNASeqBackendAPI."""

    def __init__(
        self,
        backend_api: Optional[RNASeqBackendAPI] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        tool_registry: Optional[ToolRegistry] = None,
        model_name: str = "gemini-3.6-flash"
    ):
        self.api = backend_api or RNASeqBackendAPI()
        self.model_name = model_name
        self.parser = NaturalLanguageIntentParser()
        self.plan_validator = PlanValidator(backend_api=self.api)
        self.conversational_manager = ConversationalManager(backend_api=self.api)
        from pipeline.project_manager import ProjectManager
        self.project_manager = ProjectManager()
        self.rag_engine = LiteratureRAGEngine()
        self.annotator = GeneAnnotator()
        self.synthesizer = ScientificSynthesizer(
            rag_engine=self.rag_engine,
            annotator=self.annotator
        )

        # Step 1-7 Tool & LLM Integration (All BaseTool contracts)
        self.tool_registry = tool_registry or ToolRegistry()
        if not self.tool_registry.get("run_differential_expression"):
            self.tool_registry.register(DESeq2Tool(backend_api=self.api))
        if not self.tool_registry.get("search_literature"):
            self.tool_registry.register(LiteratureTool(rag_engine=self.rag_engine))
        if not self.tool_registry.get("annotate_gene"):
            self.tool_registry.register(GeneAnnotationTool(annotator=self.annotator))
        if not self.tool_registry.get("generate_volcano_plot"):
            self.tool_registry.register(VolcanoPlotTool())
        if not self.tool_registry.get("generate_pca_plot"):
            self.tool_registry.register(PCAPlotTool())
        if not self.tool_registry.get("generate_heatmap"):
            self.tool_registry.register(HeatmapTool())
        if not self.tool_registry.get("generate_qc_plot"):
            self.tool_registry.register(QCPlotTool())
        if not self.tool_registry.get("evaluate_candidate_genes"):
            self.tool_registry.register(CandidatePrioritizationTool())

        self.dispatcher = ToolCallDispatcher(registry=self.tool_registry)
        if llm_provider:
            self.provider = llm_provider
        else:
            try:
                from agent.llm.providers import GeminiLLMProvider
                self.provider = GeminiLLMProvider(model_name=self.model_name)
            except Exception as err:
                from agent.llm.providers import UnavailableLLMProvider
                self.provider = UnavailableLLMProvider(str(err))
        self.llm_client = LLMClient(provider=self.provider, tool_registry=self.tool_registry)


    def list_datasets(self) -> AgentResponse:
        """Query available dataset configurations from deterministic backend."""
        datasets = self.api.list_available_datasets()
        return AgentResponse(
            success=True,
            operation="LIST_DATASETS",
            message=f"Discovered {len(datasets)} configured dataset(s).",
            datasets=datasets
        )

    def list_contrasts(self, dataset_id: str) -> AgentResponse:
        """Query available contrasts for a specified dataset."""
        try:
            contrasts = self.api.list_available_contrasts(dataset_id)
            return AgentResponse(
                success=True,
                operation="LIST_CONTRASTS",
                dataset_id=dataset_id,
                message=f"Retrieved {len(contrasts)} contrast(s) for dataset {dataset_id}.",
                contrasts=contrasts
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                operation="LIST_CONTRASTS",
                dataset_id=dataset_id,
                message=f"Backend rejected contrast query: {e}",
                error_result=AnalysisErrorResult(
                    dataset_id=dataset_id,
                    error_type=type(e).__name__,
                    message=str(e),
                    rejected_by_backend=True
                )
            )

    def validate_dataset(self, dataset_id: str) -> AgentResponse:
        """Perform dry-run pre-flight validation on dataset input files and replicate rules."""
        pf_res = self.api.validate_preflight(dataset_id)
        return AgentResponse(
            success=pf_res.is_valid,
            operation="VALIDATE_DATASET",
            dataset_id=dataset_id,
            message=f"Pre-flight validation for {dataset_id}: status={pf_res.replicate_status}, min_replicates={pf_res.min_replicates}.",
            preflight_result=pf_res
        )

    def execute_analysis_plan(self, plan: AnalysisPlan) -> AgentResponse:
        """Execute multi-step AnalysisPlan through deterministic backend API and synthesis layer."""
        if not plan.is_validated:
            return AgentResponse(
                success=False,
                operation="EXECUTE_PLAN",
                dataset_id=plan.dataset_id,
                plan=plan,
                message=f"Analysis plan rejected during validation: {'; '.join(plan.validation_errors)}",
                error_result=AnalysisErrorResult(
                    dataset_id=plan.dataset_id,
                    error_type="PlanValidationError",
                    message="; ".join(plan.validation_errors),
                    rejected_by_backend=True
                )
            )

        # Execute DE step
        req = AnalysisRequest(
            dataset_id=plan.dataset_id,
            contrast_id=plan.intent.contrast_id,
            fdr_cutoff=plan.intent.fdr_cutoff,
            lfc_cutoff=plan.intent.lfc_cutoff
        )

        success, result, error = self.api.run_analysis_safe(req)
        if not success:
            return AgentResponse(
                success=False,
                operation="EXECUTE_PLAN",
                dataset_id=plan.dataset_id,
                plan=plan,
                message=f"Deterministic backend rejected analysis execution: {error.message}",
                error_result=error
            )

        # Retrieve RAG literature snippets
        lit_snippets = []
        if plan.intent.candidate_genes:
            for g in plan.intent.candidate_genes:
                lit_snippets.extend(self.rag_engine.search_gene_literature(g))
        else:
            lit_snippets = self.rag_engine.get_all_snippets()[:3]

        # Generate scientific synthesis report
        report = self.synthesizer.synthesize(
            analysis_result=result,
            query_text=plan.intent.raw_user_query
        )

        return AgentResponse(
            success=True,
            operation="EXECUTE_PLAN",
            dataset_id=plan.dataset_id,
            intent=plan.intent,
            plan=plan,
            message=f"Successfully executed multi-step analysis plan for {plan.dataset_id}.",
            analysis_result=result,
            scientific_report=report,
            literature_snippets=lit_snippets
        )

    def query(
        self,
        user_query: str,
        session_id: Optional[str] = None,
        dataset_id: Optional[str] = None
    ) -> AgentResponse:
        """Full natural-language query handler (delegates to agentic tool loop)."""
        return self.agentic_query(user_query=user_query, session_id=session_id, dataset_id=dataset_id)

    def agentic_query(
        self,
        user_query: str,
        session_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        max_iterations: int = 5
    ) -> AgentResponse:
        """
        Iterative Agentic Tool-Calling Loop: Plan -> Execute -> Observe -> Synthesize.
        Uses LLM tool calling via LLMClient and validates execution through ToolCallDispatcher.
        """
        session = self.conversational_manager.get_or_create_session(session_id)
        if dataset_id:
            session.active_dataset_id = dataset_id

        messages: List[LLMMessage] = []

        # Reconstruct session conversation history for multi-turn continuity
        for prev_turn in session.turns:
            messages.append(LLMMessage(role="user", content=prev_turn.user_query))
            if prev_turn.response_text:
                messages.append(LLMMessage(role="assistant", content=prev_turn.response_text))

        # Inject Active Experiment Context into prompt if active dataset ID is set
        active_id = session.active_dataset_id or getattr(self.api, "active_dataset_id", None)
        if active_id:
            try:
                proj = self.project_manager.get_project(active_id)
                if proj and hasattr(proj, "manifest") and proj.manifest.samples:
                    samples_desc = []
                    for s in proj.manifest.samples:
                        lay = getattr(s, "layout", "SINGLE")
                        cond = getattr(s, "condition", "UNRESOLVED")
                        samples_desc.append(f"  - Sample '{s.sample_id}': layout={lay}, condition={cond}")

                    ready = getattr(proj.workspace_state, "is_ready_for_deseq2", True)
                    reason = getattr(proj.workspace_state, "unresolved_reason", None)

                    samples_str = "\n".join(samples_desc)
                    exp_context = (
                        "[ACTIVE EXPERIMENT CONTEXT]\n"
                        f"Project ID: {proj.project_id}\n"
                        f"Organism: {proj.organism}\n"
                        f"Total Biological Samples: {len(proj.manifest.samples)}\n"
                        f"Biological Samples List:\n{samples_str}\n"
                        f"Ready for DESeq2 Differential Expression: {ready}\n"
                    )
                    if reason:
                        exp_context += f"Unresolved Metadata/Design Notice: {reason}\n"

                    # Collect real FASTQ QC metrics for project files if present
                    try:
                        from pathlib import Path
                        from api.routes.qc import find_uploaded_file, calculate_fastq_qc
                        uploaded_f = find_uploaded_file(active_id)
                        qc_data = calculate_fastq_qc(uploaded_f)
                        exp_context += (
                            f"FASTQ Quality Control Metrics ({uploaded_f.name}):\n"
                            f"  - Total Reads Sampled: {qc_data.get('total_reads')}\n"
                            f"  - Total Bases: {qc_data.get('total_bases')}\n"
                            f"  - Mean Read Length: {qc_data.get('mean_read_length')} bp\n"
                            f"  - Mean Phred Quality Score: {qc_data.get('mean_phred_quality')}\n"
                            f"  - GC Content: {qc_data.get('gc_content_percent')}%\n"
                        )
                    except Exception as qc_ctx_err:
                        logger.debug("QC context retrieval notice for %s: %s", active_id, qc_ctx_err)

                    exp_context += (
                        "\nCRITICAL GROUNDING RULES FOR SYNTHESIS:\n"
                        f"- You are analyzing Project ID '{active_id}'. Operate STRICTLY on this project's actual data.\n"
                        "- NEVER mention pre-packaged benchmark datasets (e.g. spaceflight/Arabidopsis benchmarks) or static DEG numbers "
                        "UNLESS the user explicitly asks about them or those exact terms exist in current tool execution outputs.\n"
                        "- If differential expression or p-values have not been run/computed for this dataset, state clearly that "
                        "differential expression analysis has not been performed / is unavailable, rather than fabricating DEG numbers.\n"
                        "- VISUALIZATION REQUEST INSTRUCTIONS:\n"
                        "  * If the user requests specific plot types (e.g. PCA plot, volcano plot, heatmap, QC plot), execute ONLY the requested visualization tools.\n"
                        "  * Do NOT execute or generate unrequested plot figures.\n"
                        "  * If prerequisites (e.g., DE results for volcano or heatmap) are missing or incomplete, report the missing prerequisites clearly rather than fabricating data.\n"
                        "- Base your response ONLY on the provided active experiment context and the actual outputs of executed tools.\n"
                    )
                    messages.insert(0, LLMMessage(role="user", content=exp_context))
            except Exception as ctx_err:
                logger.warning("Failed to inject active experiment context for %s: %s", active_id, ctx_err)

        messages.append(LLMMessage(role="user", content=user_query))

        executed_tool_results: List[ToolResult] = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # 1. Plan / Decide Next Step
            response: LLMResponse = self.llm_client.generate(messages=messages, include_tools=True)

            if response.finish_reason == "error":
                err_msg = (response.raw_response.get("error") if isinstance(response.raw_response, dict) else None) or "LLM synthesis provider unavailable."
                return AgentResponse(
                    success=False,
                    operation="AGENTIC_QUERY",
                    message=f"LLM synthesis error: {err_msg}",
                    session_id=session.session_id,
                    dataset_id=session.active_dataset_id,
                    iterations_count=iteration
                )

            # 2. Check if LLM reached final synthesis response
            if response.content and not response.has_tool_calls:
                turn = ConversationalTurn(
                    turn_id=f"turn_{len(session.turns) + 1:03d}",
                    user_query=user_query,
                    intent=self.parser.parse(user_query, active_dataset_id=session.active_dataset_id),
                    response_text=response.content,
                    is_validated=True
                )
                session.turns.append(turn)

                return AgentResponse(
                    success=True,
                    operation="AGENTIC_QUERY",
                    message=response.content,
                    session_id=session.session_id,
                    dataset_id=session.active_dataset_id,
                    tool_results=executed_tool_results,
                    iterations_count=iteration
                )

            # 3. Handle Tool Calls
            if response.has_tool_calls:
                # Add assistant message with tool calls to memory
                messages.append(LLMMessage(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls
                ))

                for tool_call in response.tool_calls:
                    # Execute tool via dispatcher
                    tool_res = self.dispatcher.dispatch(tool_call)
                    executed_tool_results.append(tool_res)

                    # Update session active metadata if dataset/contrast returned
                    if tool_res.status == "success" and "dataset_id" in tool_res.result:
                        session.active_dataset_id = tool_res.result["dataset_id"]

                    # Record execution step trace into project workspace history
                    cur_dataset_id = session.active_dataset_id or (tool_call.arguments.get("dataset_id") if isinstance(tool_call.arguments, dict) else None)
                    if cur_dataset_id:
                        try:
                            from datetime import datetime
                            from pipeline.schemas.project_schemas import ToolExecutionStep
                            artifact_paths = []
                            if isinstance(tool_res.result, dict):
                                for k, v in tool_res.result.items():
                                    if k.endswith("_path") or k.endswith("_file") or k.endswith("_dir"):
                                        if isinstance(v, str):
                                            artifact_paths.append(v)
                            step = ToolExecutionStep(
                                step_id=f"step_{len(executed_tool_results):03d}",
                                tool_name=tool_call.tool_name,
                                timestamp=datetime.utcnow().isoformat(),
                                arguments=tool_call.arguments if isinstance(tool_call.arguments, dict) else {},
                                status="SUCCESS" if tool_res.status == "success" else "FAILED",
                                output_summary=f"Executed {tool_call.tool_name}: {tool_res.status}",
                                artifact_paths=artifact_paths,
                                provenance_hash=tool_res.provenance.get("sha256") if isinstance(tool_res.provenance, dict) else None
                            )
                            self.project_manager.record_execution_step(cur_dataset_id, step)
                        except Exception as trace_err:
                            logger.warning("Failed to record workspace execution step for %s: %s", cur_dataset_id, trace_err)

                    # Append tool result back to message context for LLM observation
                    messages.append(LLMMessage(
                        role="tool",
                        content=tool_res.model_dump_json(),
                        tool_call_id=tool_call.call_id
                    ))
            else:
                # Fallback if no content and no tool calls returned
                break

        # Max iterations reached without final synthesis
        return AgentResponse(
            success=False,
            operation="AGENTIC_QUERY",
            message=f"Agent loop reached maximum iteration limit ({max_iterations}) without producing a final answer.",
            session_id=session.session_id,
            dataset_id=session.active_dataset_id,
            tool_results=executed_tool_results,
            iterations_count=iteration,
            error_result=AnalysisErrorResult(
                dataset_id=session.active_dataset_id or "UNKNOWN",
                error_type="MaxIterationsReachedError",
                message=f"Agent reached limit of {max_iterations} iterations.",
                rejected_by_backend=False
            )
        )

    def process_natural_language_intent(self, intent_dict: Dict[str, Any]) -> AgentResponse:
        """Processes structured intent dictionary for gateway routing (backward compatible)."""
        action = intent_dict.get("action", "")
        dataset_id = intent_dict.get("dataset_id")
        contrast_id = intent_dict.get("contrast_id")
        fdr_cutoff = intent_dict.get("fdr_cutoff", 0.05)
        lfc_cutoff = intent_dict.get("lfc_cutoff", 1.0)

        active_ds = dataset_id or getattr(self.api, "active_dataset_id", None)
        if action == "list_datasets":
            return self.list_datasets()
        elif action == "list_contrasts":
            return self.list_contrasts(active_ds or "UNKNOWN")
        elif action == "validate":
            return self.validate_dataset(active_ds or "UNKNOWN")
        elif action == "run_analysis":
            intent = AnalysisIntent(
                dataset_id=active_ds or "UNKNOWN",
                action="run_analysis",
                contrast_id=contrast_id,
                fdr_cutoff=fdr_cutoff,
                lfc_cutoff=lfc_cutoff
            )
            plan = self.plan_validator.build_plan(intent)
            return self.execute_analysis_plan(plan)
        else:
            return AgentResponse(
                success=False,
                operation="UNKNOWN_ACTION",
                dataset_id=dataset_id,
                message=f"Unsupported intent action '{action}'.",
                error_result=AnalysisErrorResult(
                    dataset_id=dataset_id or "UNKNOWN",
                    error_type="UnsupportedIntentError",
                    message=f"Action '{action}' is not supported by AI Gateway API.",
                    rejected_by_backend=True
                )
            )

    def interpret_de_results(
        self,
        de_summary: Dict[str, Any],
        top_genes: List[Dict[str, Any]],
        enrichment_summary: Dict[str, Any]
    ) -> List[AIInterpretationClaim]:
        """Generates evidence-classified claims while validating through scientific guardrails."""
        raw_claims = []
        for idx, gene in enumerate(top_genes[:5], 1):
            gid = gene.get("gene_id") or gene.get("symbol") or f"GENE_{idx}"
            lfc = gene.get("log2FoldChange") or gene.get("shrunk_log2FoldChange") or 0.0
            p = gene.get("padj") or gene.get("pvalue") or 0.05
            direction = "increased" if lfc > 0 else "decreased"
            raw_claims.append({
                "claim_id": f"claim_{idx:03d}",
                "text": f"{gid} expression {direction} with log2FC = {lfc:.2f} (padj = {p:.4e}) in condition relative to control.",
                "evidence_type": "OBSERVATION",
                "supporting_gene_ids": [gid]
            })

        validated_claims = []
        for claim_dict in raw_claims:
            is_valid, rejections = validate_ai_claim_text(claim_dict["text"])
            claim = AIInterpretationClaim(
                claim_id=claim_dict["claim_id"],
                text=claim_dict["text"],
                evidence_type=claim_dict["evidence_type"],
                supporting_gene_ids=claim_dict["supporting_gene_ids"],
                guardrail_passed=is_valid,
                rejection_reason="; ".join(rejections) if rejections else None
            )
            validated_claims.append(claim)

        return validated_claims