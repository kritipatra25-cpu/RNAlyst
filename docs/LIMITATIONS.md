# RNAlyst System Scope & Known Limitations

This document explicitly outlines the operational boundaries, technical constraints, and scope limitations of the current RNAlyst MVP release.

---

## 1. LLM Provider API Quota & Live Verification

- **Current Status**: The core LLM orchestration and Gemini integration modules (`agent/orchestrator/agent_runner.py`) are fully implemented. However, live API verification during automated test execution was temporarily paused due to **upstream Gemini API quota exhaustion**.
- **Mitigation & Safety Guarantee**: All deterministic scientific computation, prerequisite engine checks, PyDESeq2 statistical modeling, PCA, volcano plot, and heatmap renderings execute **100% independently of the LLM**. The structured context payload contract ensures that once API quota refreshes, Gemini receives verified statistical inputs.

---

## 2. Supported Workflows & Experimental Designs

- **Assay Scope**: Designed specifically for **bulk short-read RNA-sequencing**. Single-cell RNA-seq (scRNA-seq), long-read direct RNA sequencing, and small RNA/miRNA assays are currently out of scope.
- **Experimental Design Formulas**: The MVP supports standard two-group comparison models (`~ condition`) and batch-adjusted models (`~ batch + condition`). Complex multi-level interactions and non-linear time series require custom script preparation.

---

## 3. Biological Replication Constraints

- **Replication Guardrail ($N \ge 2$)**: Inferential differential expression requires a minimum of $N=2$ biological replicates per group.
- **Single-Sample Datasets ($N=1$)**: Datasets with a single biological sample per condition are restricted to FASTQ quality control, pseudo-alignment, and raw expression quantification. They are rejected for differential expression with an explicit `InsufficientReplicatesError`.

---

## 4. Reference Genomes & Organism Coverage

- **Primary Supported Organisms**:
  - *Arabidopsis thaliana* (TAIR10)
  - *Homo sapiens* (GRCh38 / Ensembl)
  - *Mus musculus* (GRCm39 / Ensembl)
- **Custom Organisms**: Additional non-model organisms require pre-computed Salmon index paths and matching Ensembl annotation mapping files.

---

## 5. Deployment Environment

- **Current Architecture**: Validated as a local desktop/workstation research prototype under Linux / WSL2 (Ubuntu 22.04).
- **Multi-Tenancy & Security**: Production features such as multi-user authentication, tenant data isolation in cloud databases, and automated billing are scheduled for Phase 2.

---

## 6. Regulatory & Clinical Disclaimer

RNAlyst is a **computational biology research tool**. It is **not** intended for clinical diagnostic procedures, therapeutic guidance, or direct patient care. All generated scientific insights and literature interpretations must be validated by qualified research personnel.
