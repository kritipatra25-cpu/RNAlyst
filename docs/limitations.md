# Known Limitations & Non-Goals (v1 Scope)

## 1. Assay Scope Exclusions
The following sequencing modalities are strictly OUT OF SCOPE for the bulk RNA-seq pipeline:
- Single-cell / Single-nucleus RNA-seq (scRNA-seq/snRNA-seq)
- 3' Targeted RNA-seq / QuantSeq
- Long-read transcriptomics (PacBio ISO-Seq, ONT Direct RNA)
- Small RNA-seq / miRNA-seq
- Ribosome profiling (Ribo-seq)

## 2. Analytical Exclusions
- Novel isoform discovery & transcript assembly
- Alternative splicing / exon usage analysis
- Gene fusion detection (e.g. STAR-Fusion)
- Allele-specific expression / RNA editing
- Spatial transcriptomics deconvolution

## 3. AI & Clinical Exclusions
- The AI system will NOT offer medical diagnostics, therapeutic recommendations, or clinical interpretations.
- The AI system will NOT claim direct mechanistic causality based solely on differential gene expression metrics.
