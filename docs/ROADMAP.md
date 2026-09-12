# RNAlyst Product & Technical Roadmap

This document outlines the development milestones for RNAlyst as it transitions from a validated scientific MVP prototype to a scalable production platform for academic and incubation deployment.

---

## Phase 1: Validated Scientific MVP (Current Status)

- [x] **Decoupled 3-Layer Architecture**: Isolate LLM reasoning from PyDESeq2 / SciPy statistical engines.
- [x] **Operation-Specific Prerequisite Engine**: Strict validation for FASTQ, Count Matrices, PCA, DE, Volcano, Heatmaps, and Literature.
- [x] **Biological Replication Guardrail**: Enforce $N \ge 2$ biological samples per group for inferential DE.
- [x] **Paired-End Semantics**: Group R1/R2 reads into single sample units.
- [x] **Direct Count-Matrix Ingestion**: Bypass Salmon when pre-computed CSV counts are provided.
- [x] **Dynamic Publication Graphics**: Render PCA, Volcano, and Heatmap plots with provenance tracking.
- [x] **Organism-Restricted RAG**: Filter literature retrieval by active project organism.
- [x] **Scientific Acceptance Suite**: 17/17 checks verified on local `OSD-120` dataset.

---

## Phase 2: Production Deployment & Platform Hardening (Near-Term)

- [ ] **Docker Containerization**: Package FastAPI, Salmon, R/PyDESeq2 dependencies into unified OCI-compliant container images.
- [ ] **PostgreSQL & Redis Storage**: Replace file-system project storage with persistent relational models and asynchronous task queues (Celery/Redis).
- [ ] **Multi-Tenant Authentication & RBAC**: Implement JWT authentication and project-level sharing permissions.
- [ ] **Live LLM Quota & Fallback Management**: Add streaming token support, multi-provider fallbacks (Anthropic Claude, OpenAI GPT-4o), and usage quota monitoring.

---

## Phase 3: Expanded Bioinformatics Capabilities (Medium-Term)

- [ ] **Multi-Organism Genome Index Expansion**: Add pre-built Salmon indexes for *Homo sapiens* (GRCh38), *Mus musculus* (GRCm39), *Drosophila melanogaster*, and *Saccharomyces cerevisiae*.
- [ ] **Complex Experimental Designs**: Support multi-factor ANOVA, interaction terms (`~ batch + treatment + genotype:treatment`), and time-course design formulas.
- [ ] **Functional Pathway Enrichment**: Integrate automated GSEA and Over-Representation Analysis (ORA) against KEGG, Reactome, and Gene Ontology (GO) databases.
- [ ] **Isoform & Splicing Analysis**: Support transcript-level differential expression and alternative splicing visualization.

---

## Phase 4: Enterprise & Incubation Release (Long-Term)

- [ ] **Cloud Distributed Execution**: Integrate Nextflow Tower / AWS Batch / GCP Life Sciences for scaling large FASTQ cohorts.
- [ ] **Interactive Web Graphics**: Transition static PNG renderings to interactive Plotly/D3 graphics with hover-over gene annotations.
- [ ] **Multi-Agent Research Synthesis**: Introduce specialized sub-agents for comparative meta-analysis, ortholog mapping, and automated manuscript section drafting.
- [ ] **Clinical & Diagnostic Compliance Tracking**: Add rigorous audit logging for data provenance required in regulatory submissions.
