# Scientific Specification v1: AI-Assisted RNA-seq Research Agent

## 1. Executive Summary
This document establishes the scientific principles, mathematical foundations, and strict guardrails governing the AI-Assisted RNA-seq Analysis Platform. The platform provides automated end-to-end bulk short-read gene-level differential expression analysis while guaranteeing strict computational determinism and evidence-grounded AI reasoning.

## 2. Core Architectural Separation Rules

```
+-----------------------------------------------------------------------+
| LAYER A: Deterministic Bioinformatics & Statistical Engine (Authorized)|
| FastQC -> fastp -> Salmon/STAR -> DESeq2 -> LRT/Wald -> apeglm        |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| LAYER B: Versioned Biological Knowledge & Literature Retrieval        |
| Ensembl, GENCODE, TAIR10, GO, Reactome, PubMed, Europe PMC            |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| LAYER C: Guardrailed AI Orchestration & Scientific Interpretation      |
| Experimental context, literature synthesis, evidence taxonomy        |
+-----------------------------------------------------------------------+
```

### Mandatory Non-Negotiable Rule
**The LLM MUST NEVER be the source of truth for numerical, statistical, or bioinformatics results.**
- Numerical calculations, p-values, log2 fold changes, read counts, PCA coordinates, and enrichment statistics are derived strictly by Layer A software.
- Biological knowledge (gene identity, pathways, publication citations) is retrieved strictly by Layer B APIs/databases.
- The LLM (Layer C) synthesizes, explains, and connects evidence under strict scientific guardrails.

## 3. Supported Initial Scope
- **Assays**: Bulk short-read RNA-seq (gene-level differential expression).
- **Excluded Assays**: Single-cell RNA-seq (scRNA-seq), single-nucleus (snRNA-seq), 3' RNA-seq, long-read (PacBio/ONT), small RNA-seq, transcript-level DE / isoform switching, alternative splicing, fusion detection, novel transcript discovery. Excluded assays MUST trigger hard refusal gates.
- **Organisms**:
  1. *Arabidopsis thaliana* (Reference: TAIR10, Ensembl Release 58)
  2. *Homo sapiens* (Reference: GRCh38, GENCODE v45)
  3. *Mus musculus* (Reference: GRCm39, GENCODE vM34)

## 4. Statistical Models & Replicate Governance

### Replicate Thresholds
- **N = 1 per group**: Inferential differential expression **PROHIBITED**. Output labeled `EXPLORATORY — NO BIOLOGICAL VARIANCE ESTIMATION`.
- **N = 2 per group**: Labeled `EXPLORATORY — LIMITED STATISTICAL POWER WITH WARNING`.
- **N >= 3 per group**: Minimum standard for biological inference.

### Experimental Design Models
- Simple Two-Group: `~ condition` (Wald Test)
- Additive Batch-Adjusted: `~ batch + condition` (Wald Test)
- Multi-factor / Interactions: `~ batch + genotype + treatment + genotype:treatment` (LRT)

### Batch Confounding Rule
If `batch` and `condition` are completely confounded (rank deficiency), the pipeline MUST halt affected contrasts and emit:
`TREATMENT EFFECT NOT IDENTIFIABLE FROM THIS EXPERIMENTAL DESIGN`. No ComBat or PCA filtering may be applied to force identifiability.

## 5. Scientific Language Conventions
- Use "statistically supported as differentially expressed (FDR < 0.05, |shrunken log2FC| >= 1.0)" instead of "gene is activated".
- Use "genes associated with pathway X were overrepresented among upregulated genes" instead of "pathway X is activated".
- Use "consistent with literature" instead of "proves".
