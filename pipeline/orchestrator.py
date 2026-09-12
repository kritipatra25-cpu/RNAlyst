"""
Deterministic Analysis Orchestration Layer.
"""
import os
import json
import uuid
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from pipeline.job_models import (
    AnalysisJob, JobStatus, StepStatus, StepExecutionTrace,
    AnalysisArtifact, ArtifactType, AnalysisStepType
)
from pipeline.llm_provider import BaseLLMProvider
from pipeline.planner import AnalysisPlanner
from api.routes.qc import find_uploaded_file, find_all_uploaded_files, calculate_fastq_qc, calculate_project_qc
from analysis.statistics.pca_engine import perform_pca, load_expression_matrix
from analysis.statistics.de_engine import perform_differential_expression, load_sample_metadata
from visualization.plots_engine import (
    generate_pca_plot, generate_volcano_plot, generate_heatmap_plot, generate_qc_plot
)

logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOBS_DIR = PROJECT_ROOT / "data" / "jobs"
ARTIFACTS_DIR = PROJECT_ROOT / "data" / "artifacts"
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"

JOBS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class AnalysisOrchestrator:
    """
    Manages creation, persistence, execution, and step tracing of AnalysisJobs.
    """

    def __init__(
        self,
        jobs_dir: Optional[Path] = None,
        artifacts_dir: Optional[Path] = None,
        uploads_dir: Optional[Path] = None,
        llm_provider: Optional[BaseLLMProvider] = None
    ):
        self.jobs_dir = jobs_dir or JOBS_DIR
        self.artifacts_dir = artifacts_dir or ARTIFACTS_DIR
        self.uploads_dir = uploads_dir or UPLOADS_DIR
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.llm_provider = llm_provider
        self.planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=self.llm_provider)

    def _job_file_path(self, analysis_id: str) -> Path:
        return self.jobs_dir / f"{analysis_id}.json"

    def save_job(self, job: AnalysisJob) -> None:
        job.updated_at = datetime.now(timezone.utc).isoformat()
        filepath = self._job_file_path(job.analysis_id)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(job.model_dump_json(indent=2))

    def get_job(self, analysis_id: str) -> Optional[AnalysisJob]:
        filepath = self._job_file_path(analysis_id)
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AnalysisJob.model_validate(data)
        except Exception as e:
            logger.error("Failed to load job %s: %s", analysis_id, e)
            return None

    def list_jobs(self) -> List[AnalysisJob]:
        jobs = []
        for path in self.jobs_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                jobs.append(AnalysisJob.model_validate(data))
            except Exception as e:
                logger.warning("Failed to parse job at %s: %s", path, e)
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def _find_expression_matrix(self, file_id: str) -> Optional[Path]:
        requested_id = str(file_id).strip().lower()
        direct = Path(file_id)
        if direct.is_file() and direct.suffix in [".csv", ".tsv", ".txt"]:
            return direct

        for path in self.uploads_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in [".csv", ".tsv", ".txt"]:
                continue
            filename = path.name.strip().lower()
            if "metadata" in filename or "design" in filename or "samples" in filename:
                continue
            if filename.startswith(requested_id + "_") or filename.startswith(requested_id) or requested_id in filename:
                return path

        return None

    def _find_sample_metadata(self, file_id: str) -> Optional[Path]:
        requested_id = str(file_id).strip().lower()

        for path in self.uploads_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in [".csv", ".tsv", ".txt"]:
                continue
            filename = path.name.strip().lower()
            if ("metadata" in filename or "design" in filename or "samples" in filename) and (filename.startswith(requested_id + "_") or filename.startswith(requested_id) or requested_id in filename):
                return path

        return None

    def create_job(
        self,
        file_id: str,
        user_question: Optional[str] = None,
        organism: Optional[str] = None,
        dataset_id: Optional[str] = None,
        plan: Optional[List[str]] = None,
        llm_provider: Optional[BaseLLMProvider] = None
    ) -> AnalysisJob:
        analysis_id = f"analysis_{uuid.uuid4().hex[:12]}"

        effective_planner = self.planner
        if llm_provider is not None:
            effective_planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=llm_provider)

        structured_plan = effective_planner.create_analysis_plan(
            file_id=file_id,
            user_question=user_question,
            requested_plan=plan
        )

        selected_plan = structured_plan.selected_steps

        step_traces = [
            StepExecutionTrace(step=step_name, status=StepStatus.PENDING)
            for step_name in selected_plan
        ]

        provenance = {
            "platform": sys.platform,
            "python_version": sys.version.split()[0],
            "orchestrator_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        job = AnalysisJob(
            analysis_id=analysis_id,
            file_id=file_id,
            user_question=user_question,
            organism=organism,
            dataset_id=dataset_id,
            status=JobStatus.QUEUED,
            current_step=None,
            plan=selected_plan,
            structured_plan=structured_plan,
            steps=step_traces,
            artifacts=[],
            errors=list(structured_plan.validation_errors),
            provenance=provenance
        )

        self.save_job(job)
        return job

    def execute_job(self, analysis_id: str) -> AnalysisJob:
        job = self.get_job(analysis_id)
        if not job:
            raise ValueError(f"AnalysisJob '{analysis_id}' not found.")

        job.status = JobStatus.RUNNING
        self.save_job(job)

        if job.structured_plan and not job.structured_plan.is_valid:
            first_step = job.plan[0] if job.plan else "unknown"
            trace = next((s for s in job.steps if s.step == first_step), None)
            if not trace:
                trace = StepExecutionTrace(step=first_step, status=StepStatus.PENDING)
                job.steps.append(trace)

            err_msg = job.structured_plan.validation_errors[0] if job.structured_plan.validation_errors else "Invalid analysis plan."
            trace.status = StepStatus.FAILED
            trace.message = err_msg
            trace.completed_at = datetime.now(timezone.utc).isoformat()

            if err_msg not in job.errors:
                job.errors.append(err_msg)
            job.status = JobStatus.FAILED
            job.current_step = first_step
            self.save_job(job)
            return job

        for step_name in job.plan:
            trace = next((s for s in job.steps if s.step == step_name), None)
            if not trace:
                trace = StepExecutionTrace(step=step_name, status=StepStatus.PENDING)
                job.steps.append(trace)

            trace.status = StepStatus.RUNNING
            trace.started_at = datetime.now(timezone.utc).isoformat()
            job.current_step = step_name
            self.save_job(job)

            try:
                if step_name in ["qc", "validating_dataset"]:
                    all_files = find_all_uploaded_files(job.file_id)
                    if not all_files:
                        all_files = [find_uploaded_file(job.file_id)]
                    qc_results = calculate_project_qc(all_files)


                    artifact_filename = f"{job.analysis_id}_{step_name}_summary.json"
                    artifact_path = self.artifacts_dir / artifact_filename
                    with open(artifact_path, "w", encoding="utf-8") as f:
                        json.dump(qc_results, f, indent=2)

                    json_artifact = AnalysisArtifact(
                        artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                        type=ArtifactType.QC_SUMMARY,
                        name=artifact_filename,
                        path=str(artifact_path),
                        step=step_name,
                        metadata={
                            "total_reads": qc_results.get("total_reads"),
                            "gc_content_percent": qc_results.get("gc_content_percent")
                        }
                    )

                    qc_plot_filename = f"{job.analysis_id}_{step_name}_plot.png"
                    qc_plot_path = self.artifacts_dir / qc_plot_filename
                    generate_qc_plot(qc_results, qc_plot_path)

                    plot_artifact = AnalysisArtifact(
                        artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                        type=ArtifactType.PLOT,
                        name=qc_plot_filename,
                        path=str(qc_plot_path),
                        step=step_name,
                        metadata={
                            "format": "png",
                            "dpi": 300,
                            "parent_artifact_id": json_artifact.artifact_id,
                            "source_file": json_artifact.name
                        }
                    )

                    trace.artifacts.extend([json_artifact, plot_artifact])
                    job.artifacts.extend([json_artifact, plot_artifact])
                    trace.status = StepStatus.COMPLETED
                    trace.message = f"Step '{step_name}' executed successfully."
                    trace.completed_at = datetime.now(timezone.utc).isoformat()

                elif step_name == "pca":
                    matrix_path = self._find_expression_matrix(job.file_id)
                    if not matrix_path:
                        err_msg = "PCA requires a gene-by-sample expression/count matrix; FASTQ quantification is not yet implemented."
                        logger.warning(err_msg)
                        trace.status = StepStatus.FAILED
                        trace.message = err_msg
                        trace.completed_at = datetime.now(timezone.utc).isoformat()
                        job.errors.append(err_msg)
                        job.status = JobStatus.FAILED
                        job.current_step = step_name
                        self.save_job(job)
                        return job

                    pca_results = perform_pca(matrix_path)

                    json_filename = f"{job.analysis_id}_pca_results.json"
                    json_path = self.artifacts_dir / json_filename
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(pca_results, f, indent=2)

                    json_artifact = AnalysisArtifact(
                        artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                        type=ArtifactType.JSON_DATA,
                        name=json_filename,
                        path=str(json_path),
                        step=step_name,
                        metadata={
                            "n_samples": pca_results.get("n_samples"),
                            "n_genes": pca_results.get("n_genes"),
                            "total_explained_variance": pca_results.get("total_explained_variance")
                        }
                    )

                    plot_filename = f"{job.analysis_id}_pca_plot.png"
                    plot_path = self.artifacts_dir / plot_filename
                    generate_pca_plot(pca_results, plot_path)

                    plot_artifact = AnalysisArtifact(
                        artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                        type=ArtifactType.PLOT,
                        name=plot_filename,
                        path=str(plot_path),
                        step=step_name,
                        metadata={
                            "format": "png",
                            "dpi": 300,
                            "parent_artifact_id": json_artifact.artifact_id,
                            "source_file": json_artifact.name
                        }
                    )

                    trace.artifacts.extend([json_artifact, plot_artifact])
                    job.artifacts.extend([json_artifact, plot_artifact])
                    trace.status = StepStatus.COMPLETED
                    trace.message = "PCA analysis and plot generation completed successfully."
                    trace.completed_at = datetime.now(timezone.utc).isoformat()

                elif step_name in ["differential_expression", "de"]:
                    matrix_path = self._find_expression_matrix(job.file_id)
                    metadata_path = self._find_sample_metadata(job.file_id)

                    if not matrix_path or not metadata_path:
                        err_msg = "Differential expression requires a gene-by-sample count matrix and sample metadata defining experimental conditions."
                        logger.warning(err_msg)
                        trace.status = StepStatus.FAILED
                        trace.message = err_msg
                        trace.completed_at = datetime.now(timezone.utc).isoformat()
                        job.errors.append(err_msg)
                        job.status = JobStatus.FAILED
                        job.current_step = step_name
                        self.save_job(job)
                        return job

                    de_results = perform_differential_expression(matrix_path, metadata_path)

                    json_filename = f"{job.analysis_id}_de_summary.json"
                    json_path = self.artifacts_dir / json_filename
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(de_results["summary"], f, indent=2)

                    json_artifact = AnalysisArtifact(
                        artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                        type=ArtifactType.JSON_DATA,
                        name=json_filename,
                        path=str(json_path),
                        step=step_name,
                        metadata=de_results["summary"]
                    )

                    csv_filename = f"{job.analysis_id}_de_results.csv"
                    csv_path = self.artifacts_dir / csv_filename
                    de_results["dataframe"].to_csv(csv_path, index=False)

                    csv_artifact = AnalysisArtifact(
                        artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                        type=ArtifactType.DE_TABLE,
                        name=csv_filename,
                        path=str(csv_path),
                        step=step_name,
                        metadata={
                            "total_genes": de_results["summary"]["total_genes"],
                            "significant_genes": de_results["summary"]["significant_genes"],
                            "contrast": de_results["summary"]["contrast"]
                        }
                    )

                    trace.artifacts.extend([json_artifact, csv_artifact])
                    job.artifacts.extend([json_artifact, csv_artifact])

                    volcano_filename = f"{job.analysis_id}_volcano_plot.png"
                    volcano_path = self.artifacts_dir / volcano_filename
                    generate_volcano_plot(de_results["results"], volcano_path)

                    volcano_artifact = AnalysisArtifact(
                        artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                        type=ArtifactType.PLOT,
                        name=volcano_filename,
                        path=str(volcano_path),
                        step=step_name,
                        metadata={
                            "format": "png",
                            "dpi": 300,
                            "parent_artifact_id": csv_artifact.artifact_id,
                            "source_file": csv_artifact.name
                        }
                    )
                    trace.artifacts.append(volcano_artifact)
                    job.artifacts.append(volcano_artifact)

                    heatmap_filename = f"{job.analysis_id}_heatmap_plot.png"
                    heatmap_path = self.artifacts_dir / heatmap_filename
                    hm_result = generate_heatmap_plot(
                        count_matrix_input=matrix_path,
                        de_results_input=de_results["results"],
                        metadata_input=metadata_path,
                        output_path=heatmap_path
                    )

                    if hm_result:
                        heatmap_artifact = AnalysisArtifact(
                            artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                            type=ArtifactType.PLOT,
                            name=heatmap_filename,
                            path=str(heatmap_path),
                            step=step_name,
                            metadata={
                                "format": "png",
                                "dpi": 300,
                                "parent_artifact_id": csv_artifact.artifact_id,
                                "source_file": csv_artifact.name
                            }
                        )
                        trace.artifacts.append(heatmap_artifact)
                        job.artifacts.append(heatmap_artifact)
                    else:
                        logger.info("No significant DE genes meet threshold; heatmap generation skipped.")

                    trace.status = StepStatus.COMPLETED
                    trace.message = "Differential expression analysis and plot generation completed successfully."
                    trace.completed_at = datetime.now(timezone.utc).isoformat()

                else:
                    trace.status = StepStatus.FAILED
                    trace.message = f"Step '{step_name}' is currently not implemented."
                    trace.completed_at = datetime.now(timezone.utc).isoformat()
                    job.errors.append(trace.message)
                    job.status = JobStatus.FAILED
                    job.current_step = step_name
                    self.save_job(job)
                    return job

            except Exception as e:
                err_msg = f"Step '{step_name}' failed: {str(e)}"
                logger.exception(err_msg)
                trace.status = StepStatus.FAILED
                trace.message = err_msg
                trace.completed_at = datetime.now(timezone.utc).isoformat()
                job.errors.append(err_msg)
                job.status = JobStatus.FAILED
                job.current_step = step_name
                self.save_job(job)
                return job

            self.save_job(job)

        job.status = JobStatus.COMPLETED
        job.current_step = None
        self.save_job(job)
        return job
