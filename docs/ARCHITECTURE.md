# RNAlyst Architecture & Technical Specification

## Overview

RNAlyst is built around a **3-Layer Decoupled Architecture** that strictly isolates natural-language reasoning from deterministic bioinformatics computation and statistical inference.

```
+-------------------------------------------------------------------------+
|                         USER INTERFACE & API GATEWAY                   |
|                   FastAPI REST API / Web Application Interface          |
+------------------------------------┬------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  LAYER C: AI ORCHESTRATION & REASONING                  |
|    - Intent Recognition & Workflow Planning                             |
|    - Structured Tool Invocation Generation                              |
|    - Evidence-Grounded Scientific Interpretation Synthesis              |
+------------------------------------┬------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                 LAYER A: DETERMINISTIC SCIENTIFIC ENGINE                |
|    - Prerequisite Engine (Operation-Specific Rules & Refusals)           |
|    - FastQC & Salmon Pseudo-Alignment Engine                            |
|    - PyDESeq2 / SciPy Differential Expression Engine                    |
|    - PCA, Volcano Plot & Heatmap Figure Rendering Engines               |
|    - Biological Replication Guardrails (N >= 2 check)                  |
+------------------------------------┬------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|               LAYER B: PROVENANCE & LITERATURE KNOWLEDGE                |
|    - Project Isolation & Workspace Storage                              |
|    - Artifact Provenance Manifest Generation (JSON Metadata)            |
|    - Organism-Restricted Literature RAG Engine                              |
+-------------------------------------------------------------------------+
```

---

## 1. Core Component Breakdown

### 1.1 Frontend Web Interface (`web/`)
- **Technology**: Vanilla JavaScript (ES6+), HTML5, CSS3 Editorial Design Tokens.
- **Role**: Provides a clean, publication-grade workspace for:
  - Drag-and-drop multi-file FASTQ upload with automatic R1/R2 pairing.
  - Count Matrix (`counts_matrix.csv`) direct upload.
  - Interactive research query composer.
  - Real-time display of execution status, generated plots, DEG tables, and evidence-grounded literature snippets.

### 1.2 FastAPI REST API Gateway (`api/`)
- **Key Modules**: `api/main.py`, `api/routes/upload.py`, `api/routes/qc.py`, `api/routes/agent_query.py`.
- **Role**:
  - Exposes OpenAPI REST endpoints (`/api/v1/projects`, `/api/v1/qc`, `/api/v1/analyses`, `/api/v1/query`).
  - Handles multipart/form-data file streams for paired FASTQ files.
  - Enforces request validation schemas using Pydantic v2.

### 1.3 Project Management & Isolation (`pipeline/project_manager.py`)
- **Role**:
  - Manages isolated workspace directories per project (`projects/{PROJECT_ID}/`).
  - Maintains structured subdirectories: `data/uploads/`, `qc/`, `results/`.
  - Tracks metadata and active project configs in standard YAML/JSON formats.

### 1.4 Agent Orchestrator (`agent/orchestrator/agent_runner.py`)
- **Role**:
  - Parses user intent from conversational research queries.
  - Maps requested actions to deterministic tool executions registered in `ToolRegistry`.
  - Generates the **Interpretation Input Contract Payload** for the LLM provider, guaranteeing that Gemini receives pre-computed statistical outputs and never computes raw math.

### 1.5 Prerequisite Engine (`agent/tools/prerequisite_engine.py`)
- **Role**:
  - Enforces explicit, operation-specific prerequisite checks before any scientific computation or plotting begins.
  - Operations covered: QC, Quantification, Count Validation, PCA, Differential Expression, Volcano Plot, Heatmap, Enrichment, Literature Grounding.
  - Returns structured `ToolResult.error_result` (`MissingPrerequisitesError`, `InsufficientReplicatesError`) upon failure, blocking downstream execution without fallbacks.

### 1.6 Scientific Guardrails (`scientific_guardrails/replicate_rules.py`)
- **Role**:
  - Enforces the biological replication guardrail ($N \ge 2$ biological samples per condition) for inferential differential expression.
  - Rejects single-replicate contrasts ($N=1$) safely with `InsufficientReplicatesError`.

### 1.7 Deterministic Tool Registry (`agent/tools/base_tool.py` & `visualization_tools.py`)
- **Contract**: All scientific tools extend `BaseTool` and return strongly-typed `ToolResult` objects containing:
  - `status`: `"success"` or `"error"`
  - `result`: Dictionary of numerical statistics and outputs.
  - `artifacts`: List of generated image/data file paths.
  - `provenance`: Dictionary tracking `project_id`, `analysis_id`, parameters, and timestamps.
  - `error`: Structured `ToolError` object.

### 1.8 Plot Rendering Engine (`visualization/plots_engine.py`)
- **Role**:
  - Renders publication-ready 2D PCA scatter plots, Volcano plots, and Sample Expression Heatmaps using Matplotlib and Seaborn.
  - Incorporates color-palette aesthetics tailored for scientific publication.

### 1.9 Literature & RAG Engine (`agent/tools/literature_tool.py`)
- **Role**:
  - Queries local PubMed/Ensembl literature indices filtered strictly by the target organism (`Arabidopsis thaliana`, `Homo sapiens`, `Mus musculus`).
  - Prevents cross-species benchmark knowledge injection into user analysis queries.

---

## 2. Decoupling Guarantee Matrix

| Operation | Executed By | LLM Role |
|-----------|-------------|----------|
| **FASTQ QC Parsing** | FastQC / Python | None (receives summary metrics) |
| **Quantification** | Salmon / Nextflow | None (receives count matrix) |
| **Count Normalization** | PyDESeq2 / SciPy | None (receives VST matrix) |
| **PCA Decomposition** | SciPy PCA / Scikit-Learn | None (receives 2D coordinates) |
| **Wald Test DE & FDR** | PyDESeq2 / Statsmodels | None (receives DEG table) |
| **Plot Rendering** | Matplotlib / Seaborn | None (receives PNG file path) |
| **Literature Search** | Local RAG Index | None (receives text snippets) |
| **Result Synthesis** | None | **Synthesizes grounded text narrative from pre-computed artifacts** |

---

## 3. Data Flow Diagram

```
User FASTQ / Counts
       │
       ▼
Upload Endpoint ──► Project Directory Isolation
                          │
                          ▼
                  Prerequisite Check ──► [Fail: Return InsufficientReplicatesError]
                          │
                   [Pass] ▼
                 FastQC / Salmon Engine
                          │
                          ▼
                    Counts Matrix
                          │
                          ▼
                 PyDESeq2 Statistical Core
               ┌──────────┴──────────┐
               ▼                     ▼
          VST Matrix            DE Results CSV
               │                     │
        ┌──────┴──────┐       ┌──────┴──────┐
        ▼             ▼       ▼             ▼
     PCA Plot      Heatmap  Volcano Plot  Enrichment
        │             │       │             │
        └─────────────┼───────┴─────────────┘
                      │
                      ▼
            Artifact Provenance Engine
                      │
                      ▼
         Structured Context Contract Payload
                      │
                      ▼
           Gemini LLM Synthesis Engine
                      │
                      ▼
          Grounded User Narrative & Figures
```
