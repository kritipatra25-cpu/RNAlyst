# Reproducibility & Provenance Policy

## 1. Deterministic Execution Rules
To guarantee 100% computational reproducibility across compute environments:
- **Pinned Software Environments**: All bioinformatics tools (FastQC v0.12.1, fastp v0.23.4, Salmon v1.10.2, STAR v2.7.11a) are bundled in immutable Docker/Apptainer containers.
- **Pinned R Packages**: R 4.3.2 with DESeq2 v1.42.0, tximport v1.30.0, apeglm v1.24.0.
- **Pinned Reference Genomes**: Fixed genome assemblies (TAIR10, GRCh38.p14, GRCm39) with SHA-256 validation. Dynamic retrieval of "latest" references is prohibited.
- **Random Seed Locking**: Statistical functions requiring random seeds (e.g. GSEA permutations, PCA SVD solvers) use locked explicit seeds (`seed = 42`).

## 2. Analysis Manifest Schema
Every analysis generates a `provenance_manifest.json` containing:
- Unique Analysis GUID & Parent GUID
- Input file checksums (SHA-256)
- Container image digest
- Workflow engine version & execution parameters
- Reference genome & annotation release version + checksum
- Design formula, reference level, contrast specification
- Exact R environment session info
- Complete log of all user/LLM actions
