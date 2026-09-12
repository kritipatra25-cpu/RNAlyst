# AnalysisJob & Analysis Orchestration Architecture

## Overview
This document specifies the design and implementation of the **AnalysisJob** model and **AnalysisOrchestrator** engine in the `RNA-seq AI Agent` platform located at `/home/kriti/rna-seq-ai-agent`.

The orchestration layer acts as the deterministic backend backbone connecting high-level user questions and FASTQ datasets to validated, reproducible bioinformatics tool executions, structured artifact registrations, and transparent execution traces.

---

## Architectural Principles

1. **Deterministic Execution Boundary**:
   - The LLM / Agent acts as a planner, tool caller, and scientific interpreter.
   - All statistical, QC, and bioinformatic computations are executed deterministically by Python/R backend tools (e.g. `calculate_fastq_qc`, Salmon, DESeq2).
   - The LLM **never** fabricates statistical results or bypasses deterministic tools.

2. **Explicit Plan Representation**:
   - The `AnalysisJob.plan` represents only the explicitly requested analysis steps for that job (e.g., `["validating_dataset", "qc"]`).
   - Unimplemented or unrequested future steps do NOT automatically populate into every job or mark as skipped.
   - If an un-implemented step is explicitly requested in a job plan, the orchestrator sets the step status to `failed` with an explicit message (`"Step 'X' is currently not implemented for raw FASTQ inputs"`) and halts execution cleanly.

3. **Transparent Execution Trace**:
   - The system maintains a transparent history of execution steps (`StepExecutionTrace`) recording action status, start/completion timestamps, user-facing progress messages, and registered artifacts.
   - Internal LLM chain-of-thought is kept private; only tool actions, execution state, and structured outputs are exposed to the user.

---

## Data Models (`pipeline/job_models.py`)

### 1. Enums
- **`JobStatus`**: `queued`, `planning`, `running`, `completed`, `failed`
- **`StepStatus`**: `pending`, `running`, `completed`, `failed`, `skipped`
- **`AnalysisStepType`**: `understanding_question`, `planning_analysis`, `validating_dataset`, `qc`, `differential_expression`, `pca`, `volcano`, `heatmap`, `enrichment`, `literature_search`, `synthesize_results`
- **`ArtifactType`**: `qc_summary`, `counts_table`, `de_table`, `plot`, `report`, `json_data`

### 2. `AnalysisArtifact`
```json
{
  "artifact_id": "art_1b9c04a2",
  "type": "qc_summary",
  "name": "analysis_2f42a1d7_qc_summary.json",
  "path": "/home/kriti/rna-seq-ai-agent/data/artifacts/analysis_2f42a1d7_qc_summary.json",
  "step": "qc",
  "metadata": {
    "total_reads": 200,
    "gc_content_percent": 48.5
  },
  "created_at": "2026-08-30T14:11:26.818025+00:00"
}
```

### 3. `StepExecutionTrace`
```json
{
  "step": "qc",
  "status": "completed",
  "started_at": "2026-08-30T14:11:26.818319+00:00",
  "completed_at": "2026-08-30T14:11:26.820368+00:00",
  "message": "Step 'qc' executed successfully.",
  "artifacts": [...]
}
```

### 4. `AnalysisJob`
```json
{
  "analysis_id": "analysis_2f42a1d7a5b3",
  "file_id": "fc5fc9f0-65ce-40a4-b4c8-7a8605776859",
  "user_question": "Perform FASTQ QC analysis",
  "organism": "Arabidopsis thaliana",
  "dataset_id": null,
  "status": "completed",
  "current_step": null,
  "plan": ["validating_dataset", "qc"],
  "steps": [...],
  "artifacts": [...],
  "errors": [],
  "provenance": {
    "platform": "linux",
    "python_version": "3.10.12",
    "orchestrator_version": "1.0.0"
  },
  "created_at": "2026-08-30T14:11:26.800000+00:00",
  "updated_at": "2026-08-30T14:11:26.820000+00:00"
}
```

---

## Orchestration Layer (`pipeline/orchestrator.py`)

The `AnalysisOrchestrator` manages job creation, state persistence, step execution, and artifact registration:

- **Persistence**: Jobs are persisted as JSON files under `/home/kriti/rna-seq-ai-agent/data/jobs/{analysis_id}.json`. Artifacts are stored under `/home/kriti/rna-seq-ai-agent/data/artifacts/`.
- **`create_job(...)`**: Initializes a new job in state `queued` with pending step traces matching `plan`.
- **`get_job(analysis_id)`**: Loads stored job JSON.
- **`execute_job(analysis_id)`**: Iterates sequentially through `job.plan`:
  1. Updates `job.status` to `running` and active `step.status` to `running`.
  2. For `validating_dataset` or `qc`: calls `find_uploaded_file(file_id)` and `calculate_fastq_qc(file_path)`, writes JSON artifact, and marks step `completed`.
  3. For unimplemented steps: marks step `failed` with message `"Step 'X' is currently not implemented for raw FASTQ inputs."` and halts job execution in `failed` state.

---

## API Layer (`api/routes/analyses.py` & `api/main.py`)

All endpoints are exposed under both root (`/analyses`) and versioned (`/api/v1/analyses`) prefixes:

- **`POST /analyses`** (or `/api/v1/analyses`):
  - Request body: `{ "file_id": "...", "user_question": "...", "plan": ["validating_dataset", "qc"] }`
  - Returns `201 Created` with initialized `AnalysisJob`.

- **`GET /analyses/{analysis_id}`** (or `/api/v1/analyses/{analysis_id}`):
  - Returns full `AnalysisJob` object.
  - Fallback: Returns upload status if queried with a `file_id` (maintaining backwards compatibility).

- **`POST /analyses/{analysis_id}/run`** (or `/api/v1/analyses/{analysis_id}/run`):
  - Triggers execution of the orchestrator and returns updated `AnalysisJob`.

- **`GET /analyses/{analysis_id}/status`**:
  - Returns concise status, current step, step trace, artifact count, and errors.

- **`GET /analyses/{analysis_id}/artifacts`**:
  - Returns array of registered `AnalysisArtifact` objects for the job.

---

## Verification & Testing (`tests/test_analysis_job.py`)

A 10-test suite validates:
1. `AnalysisJob` API creation.
2. `AnalysisJob` retrieval via API.
3. Correct initial state (`queued`).
4. QC step execution through orchestrator.
5. Step state transitions (`pending` -> `running` -> `completed`).
6. Unimplemented step state failure handling.
7. Artifact registration.
8. Non-existent `file_id` 404 error handling.
9. Existing `GET /qc/{file_id}` endpoint compatibility.
10. Existing `POST /ingestion/upload` endpoint compatibility.

All 10 tests passed with 100% success rate in the production WSL environment.

---

## What is Intentionally NOT Implemented Yet

- **Fake / Mock DE Results**: Differential expression (DESeq2), PCA, volcano plots, and heatmaps require aligned count matrices and design matrices; they are NOT mocked.
- **Frontend UI Integration**: Web interface components remain un-modified in this phase.
- **Literature Agent / RAG Search**: Retrieval and PDF generation remain in downstream modular phases.
