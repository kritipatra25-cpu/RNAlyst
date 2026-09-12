# Supported Data & Input Specifications

## 1. Supported Raw Inputs
- **File Formats**: `.fastq`, `.fastq.gz`, `.fq`, `.fq.gz`
- **Read Types**: Single-End (SE), Paired-End (PE)
- **Public Accessions**: NASA OSDR (GeneLab) accessions, NCBI SRA (`SRR`/`ERR`/`DRR`), ENA accessions, GEO accessions (`GSE`).

## 2. Supported Processed Inputs (Explicit Limitations)
When raw FASTQ files are unavailable, the platform accepts:
- Un-normalized raw read count matrices (Gene x Sample).
- Salmon / Kallisto transcript quantification directories (`quant.sf`).

> **CRITICAL WARNING**: Supplying count matrices skips raw FASTQ QC, adapter contamination checking, and alignment mapping validation. The output report will explicitly state that raw read QC stages were skipped.
