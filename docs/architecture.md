# Architecture Overview: AI-Assisted RNA-seq Research Agent

## System Topography

```
[ FASTQ / Accession ] ---> [ Nextflow Pipeline ] ---> [ DESeq2 Engine ]
                                                             |
                                                             v
[ User UI (Lovable) ] <---> [ FastAPI Gateway ] <---> [ Structured Results ]
                                                             |
                                                             v
                                                  [ AI Agent Orchestrator ]
                                                  /          |          \
                                       [ Guardrails ] [ Tool Calling ] [ Literature API ]
```

## Layer Architecture & Data Flow

1. **Input & Validation Gate (`pipeline/input_validation`)**: Checks SHA-256 checksums, paired-end read consistency, FASTQ syntax, sample metadata completeness, reference incompatibility.
2. **Deterministic Workflow (`workflows/rnaseq.nf`)**: Executes FastQC, fastp, Salmon quantification, gene count matrix generation via `tximport`.
3. **Statistical Analysis Engine (`analysis/`)**: Executes R DESeq2 script to estimate dispersions, fit GLM, shrink LFC (`apeglm`), perform independent filtering, and calculate Benjamini-Hochberg FDR.
4. **Annotation & Enrichment (`annotation/`, `enrichment/`)**: Map gene identifiers against versioned SQLite/GFF/GTF annotations. Execute Over-Representation Analysis (ORA) and GSEA against pinned Gene Ontology and Reactome gene sets.
5. **Visualization Engine (`visualization/`)**: Generate publication-ready PNG/SVG assets for PCA, sample-distance heatmaps, volcano plots, expression heatmaps, and MA plots.
6. **Literature & Retrieval (`literature/`)**: Fetch paper metadata and abstracts via PubMed E-utilities, Europe PMC REST API, Crossref API. Verify citations before LLM ingestion.
7. **Guardrailed AI Agent (`agent/`, `scientific_guardrails/`)**: LLM tool calling agent operating under deterministic guardrail validators.
8. **Provenance Manager (`provenance/`)**: Stores immutable JSON analysis manifest containing complete parameter state, environment hashes, and execution logs.
