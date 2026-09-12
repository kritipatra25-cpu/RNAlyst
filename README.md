# RNAlyst: AI-Assisted Bulk RNA-seq Analysis & Interpretation Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](pyproject.toml)
[![Framework: FastAPI](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![LLM: Gemini / Groq](https://img.shields.io/badge/LLM-Gemini%20%2F%20Groq-orange.svg)](.env.example)

**RNAlyst** is an open-source, scientifically defensible AI research assistant for bulk RNA-sequencing (RNA-seq) analysis. It pairs an agentic natural-language interface with deterministic bioinformatics tooling, operation-specific prerequisite enforcement, and evidence-grounded scientific synthesis.

> **CORE SCIENTIFIC PRINCIPLE**: *The LLM does not compute, estimate, or fabricate numerical bioinformatics statistics.*
> All statistical calculations (QC, pseudo-alignment, DESeq2 differential expression, PCA, volcano plots, and heatmaps) are executed deterministically by Python/R bioinformatics packages. Configurable LLM providers (Google Gemini, Groq) act strictly as high-level planners, tool orchestrators, and evidence-grounded scientific interpreters.

---

## Table of Contents

- [Overview](#overview)
- [Current Capabilities](#current-capabilities)
- [Workflow Architecture](#workflow-architecture)
- [Real-Data Validation (GSE135618)](#real-data-validation-gse135618)
- [AI / LLM Integration](#ai--llm-integration)
- [Scientific Safeguards & Provenance](#scientific-safeguards--provenance)
- [Installation & Quick Start](#installation--quick-start)
- [Configuration](#configuration)
- [Automated Test Suite](#automated-test-suite)
- [Current Limitations](#current-limitations)
- [Roadmap](#roadmap)
- [Citation & Data Sources](#citation--data-sources)
- [License](#license)

---

## Overview

Bulk RNA-seq is standard practice in biological research, but domain experts frequently encounter:

1. **Workflow Fragmentation**: Navigating separate tools for quality control, pseudo-alignment, count matrix parsing, DESeq2 modeling, PCA, enrichment analysis, and literature retrieval.
2. **Prerequisite & Guardrail Complexity**: Biological replication requirements ($N \ge 2$ per experimental group) and experimental design matrices require explicit configuration to avoid invalid statistical inferences.
3. **Synthesis Overhead**: Connecting quantitative output tables with organism-specific biological mechanisms requires manual literature cross-referencing.
4. **AI Hallucination Risks**: Unconstrained generic LLMs may invent $p$-values, substitute demo datasets, or fabricate plot outputs when data is missing.

RNAlyst solves these challenges by combining a natural-language workspace interface with a deterministic execution engine, strict project workspace isolation, and transparent artifact provenance.

---

## Current Capabilities

To maintain scientific integrity, RNAlyst explicitly categorizes features into three maturity tiers:

### 1. Validated on Real Data
- **Sampling-Based FASTQ QC**: Performs FASTQ quality control using up to 200,000 reads per file, extracting total read counts, GC percentage, mean read length, Phred quality scores, and sequence quality distributions.
- **Multi-Sample Discovery & Aggregation**: Discovers and processes all biological samples within a project directory, calculating both per-sample and project-aggregated quality metrics.
- **Strict Project Isolation**: Constrains file discovery and analysis execution strictly to the active project manifest, preventing cross-project file contamination.
- **Verified QC Visualization**: Generates publication-ready multi-panel QC summary plots saved directly to `projects/<project_id>/results/qc_plot.png` with 3-step post-generation validation (file existence, non-zero size, PNG magic header check).
- **AI Scientific Synthesis**: Synthesizes FASTQ quality metrics into evidence-grounded scientific summaries using configured LLM providers (Groq, Gemini).

### 2. Implemented / Under Ongoing Validation
- **Expression Quantification Engine**: Wraps Salmon pseudo-alignment and count aggregation for transcript- and gene-level expression quantification.
- **Direct Count Matrix Ingestion**: Accepts pre-computed count matrices (`counts_matrix.csv`) and sample metadata files (`sample_metadata.csv`) for direct downstream analysis.
- **2D PCA Decomposition**: Computes variance-stabilized transformations (VST) and 2D principal component analysis scatter plots. *(Requires user-supplied sample metadata design matrix)*.
- **PyDESeq2 Differential Expression**: Computes Wald statistics, log2 fold-change shrinkage, and Benjamini-Hochberg FDR adjustments for differential expression. *(Requires $N \ge 2$ biological replicates per group)*.
- **Dynamic Visualizations**: Render volcano plots and top DEG expression heatmaps from verified DE results artifacts.
- **Organism-Restricted RAG**: Keyword and vector-based literature retrieval filtered strictly by the target organism (*Arabidopsis thaliana*, *Mus musculus*, *Homo sapiens*).

### 3. Planned / Roadmap
- **Automated Experimental Design Inference**: Guided interactive prompt for user sample metadata assignment.
- **Multi-Study Meta-Analysis**: Cross-dataset concordance and meta-analysis plotting interface.
- **Containerized Execution Workflows**: Nextflow and Docker container runtime wrappers.

---

## Workflow Architecture

```
[ Researcher FASTQ Upload / Query ]
                 │
                 ▼
 ┌──────────────────────────────────────┐
 │  FastAPI REST Gateway / Router       │  <-- Route Ingestion & Project Manager
 └──────────────────┬───────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────┐
 │  Agent Orchestrator & Tool Registry  │  <-- Prerequisite Check & Intent Parsing
 └──────────────────┬───────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────┐
 │  Deterministic Bioinformatics Engine │  <-- FASTQ QC / Salmon / PyDESeq2 / SciPy
 │  (Computes Statistics & Visuals)     │      Saves to projects/<project_id>/results/
 └──────────────────┬───────────────────┘
                    │ Structured JSON Payload & Validated PNGs
                    ▼
 ┌──────────────────────────────────────┐
 │  LLM Provider Layer                  │  <-- Groq (openai/gpt-oss-120b)
 │  (Scientific Synthesis & RAG)        │      Google Gemini (gemini-2.5-flash)
 └──────────────────┬───────────────────┘
                    │ Grounded Scientific Response
                    ▼
 [ Web Frontend Editorial Interface ]
```

---

## Real-Data Validation (GSE135618)

RNAlyst has been verified end-to-end against real biological single-end bulk RNA-seq FASTQ files from NCBI GEO accession **GSE135618**:

- **Sample Identifiers**: `SRR9937483` (PBS), `SRR9937484` (PBS), `SRR9937486` (LPS), `SRR9937487` (LPS)
- **Biological Samples Discovered**: Exactly 4 main FASTQ samples.
- **Reads Sampled**: 200,000 reads per file (800,000 total sampled reads across the dataset).
- **Read Length**: 72 bp single-end.
- **GC Content**: ~41% across all samples.
- **Mean Quality Score**: ~30 Phred score.
- **QC Plot Artifact**: Saved to `projects/<project_id>/results/qc_plot.png` (verified non-empty valid PNG file).
- **Zero Synthetic Fallbacks**: Provenance checks confirm no demo or synthetic data fallback was triggered.

---

## AI / LLM Integration

RNAlyst supports modular LLM providers configured strictly via environment variables.

### Supported Providers
- **Groq API**: High-throughput inference using `openai/gpt-oss-120b`.
- **Google Gemini API**: Native Google GenAI integration using `gemini-2.5-flash`.

### Provider Configuration (`.env`)
```bash
# Set active LLM provider ('groq' or 'gemini')
LLM_PROVIDER=groq

# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

# Google Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

> [!CAUTION]
> NEVER commit actual API keys or credentials to Git. Use `.env.example` as a reference.

---

## Scientific Safeguards & Provenance

1. **Zero Synthetic / Mock Results**: Missing data triggers structured refusal errors (`MissingPrerequisitesError`) rather than synthetic mock generation.
2. **Biological Replication Guardrail ($N \ge 2$)**: Differential expression requires $\ge 2$ biological samples per experimental group. Single-replicate queries are safely rejected for DE while permitting QC.
3. **Explicit Design Requirement**: Design formulas (`~ condition`) require explicit user-provided sample metadata.
4. **Strict Directory Isolation**: Every upload receives a dedicated GUID project directory under `projects/<project_id>/`.
5. **Immutable Provenance**: Generated artifacts record creation timestamp, tool version, input paths, and parameter hash.

---

## Installation & Quick Start

### Prerequisites
- Linux OS or WSL2 (Ubuntu 22.04 recommended)
- Python 3.10+
- (Optional) `salmon` executable on system PATH for quantification

### Installation

```bash
# 1. Clone repository
git clone https://github.com/your-username/rna-seq-ai-agent.git
cd rna-seq-ai-agent

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -e .

# 4. Configure environment
cp .env.example .env
```

### Starting the Application

```bash
# Start FastAPI backend
PYTHONPATH=. uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

Open `web/index.html` in your browser to interact with the RNAlyst editorial web interface.

---

## Configuration

Refer to `.env.example` for all configurable environment variables:

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `LLM_PROVIDER` | `groq` | Active LLM provider (`groq` or `gemini`) |
| `GROQ_API_KEY` | *(Required if using Groq)* | Groq API key |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model identifier |
| `GEMINI_API_KEY` | *(Required if using Gemini)* | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model identifier |
| `HOST` | `127.0.0.1` | API server host interface |
| `PORT` | `8000` | API server port |

---

## Automated Test Suite

RNAlyst maintains a comprehensive automated unit and integration test suite covering FASTQ parsing, multi-sample project management, API routes, tool registration, and visualization generation.

```bash
# Run unit & pipeline test suite
PYTHONPATH=. .venv/bin/pytest tests/unit/ test_multi_sample_web_pipeline.py -v

# Run visualization tests
PYTHONPATH=. .venv/bin/pytest tests/test_visualization.py -v
```

**Current Test Metrics**: 196 / 202 tests passing (97.0% pass rate).

---

## Current Limitations

- **Sampling-Based FASTQ QC**: FASTQ quality control samples up to 200,000 reads per file for rapid analysis rather than streaming multi-gigabyte files entirely into memory.
- **Experimental Design Metadata**: Automated 2D PCA and PyDESeq2 differential expression require explicit sample metadata tables mapping sample IDs to biological conditions (`control` vs `treated`).
- **Single-End Focus**: Multi-sample ingestion is fully validated for single-end FASTQ datasets; paired-end R1/R2 manifest discovery is under active validation.

---

## Roadmap

- [ ] Interactive UI step for user metadata assignment and contrast definition
- [ ] Paired-end R1/R2 automatic pairing validation
- [ ] Nextflow workflow engine integration
- [ ] Multi-tenant project workspace authentication

---

## Citation & Data Sources

- **Validation Dataset**: NCBI GEO [GSE135618](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE135618) (*Bulk RNA-seq of mouse macrophages*).
- **Bioinformatics Tools**: Salmon (Patro et al., 2017), PyDESeq2 (Muzellec et al., 2023), FastQC (Andrews, 2010).

---

## License

This project is licensed under the [MIT License](LICENSE).
