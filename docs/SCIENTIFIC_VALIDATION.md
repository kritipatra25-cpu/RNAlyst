# RNAlyst Scientific MVP Acceptance Test Report

## 1. Executive Summary

This report documents the verification of the **RNAlyst Real Scientific MVP Acceptance Test Suite**. All tests were executed deterministically against the canonical repository using real local data (`OSD-120`) without synthetic data fallbacks or mock biological results.

- **Overall Result**: **17 / 17 Scientific Acceptance Checks Passed (100% Pass Rate)**
- **Test Date**: September 12, 2026
- **Test Runner Script**: `scripts/run_scientific_acceptance_test.py`

---

## 2. Acceptance Dataset Identification

The test suite utilized the local `OSD-120` bulk RNA-seq dataset (*Arabidopsis thaliana* root tissue spaceflight experiment):

- **Dataset / Project ID**: `OSD-120`
- **Organism**: *Arabidopsis thaliana*
- **Total Biological Samples**: 6
  - **Ground Control ($N=3$)**: `Atha_Col-0_root_GC_Alight_Rep1_GSM2493759`, `Atha_Col-0_root_GC_Alight_Rep2_GSM2493760`, `Atha_Col-0_root_GC_Alight_Rep3_GSM2493761`
  - **Space Flight ($N=3$)**: `Atha_Col-0_root_FLT_Alight_Rep1_GSM2493777`, `Atha_Col-0_root_FLT_Alight_Rep2_GSM2493778`, `Atha_Col-0_root_FLT_Alight_Rep3_GSM2493779`
- **Count Matrix File**: `data/osd120_execution/counts_matrix.csv` (32,835 genes x 6 samples)
- **Metadata File**: `data/osd120_execution/sample_table.csv`
- **Experimental Design Formula**: `~ condition`
- **Contrast**: `Space Flight` vs `Ground Control`
- **Biological Replication Status**: Sufficient ($N=3 \ge 2$ per group)
- **PCA Status**: Valid ($N=6 \ge 2$ samples)

---

## 3. Comprehensive 17-Item Acceptance Status Matrix

| # | Criterion | Category | Status | Verified Evidence & Test Output Details |
|---|-----------|----------|--------|-----------------------------------------|
| 1 | **FASTQ / Sample Semantics** | Ingestion | **PASS** | `scientific_guardrails/replicate_rules.py` treats R1/R2 paired FASTQs as 1 biological sample. |
| 2 | **Count Matrix Validation** | Ingestion | **PASS** | Validated 32,835 genes and 6 sample columns in `counts_matrix.csv`. |
| 3 | **Normalization / VST** | Computation | **PASS** | Computed log2/VST matrix saved to `results/osd120_acceptance/vst_counts.csv`. |
| 4 | **2D PCA Decomposition** | Visualization | **PASS** | Rendered PCA scatter plot to `results/osd120_acceptance/pca_plot.png` with provenance `project_id: OSD-120`. |
| 5 | **Experimental Design Validation** | Guardrail | **PASS** | Validated design formula `~ condition` for Control ($N=3$) vs Flight ($N=3$). |
| 6 | **Differential Expression** | Computation | **PASS** | Executed DESeq2 statistics saving 32,833 gene results to `results/osd120_acceptance/deseq2_results.csv`. |
| 7 | **Volcano Plot** | Visualization | **PASS** | Rendered publication volcano plot (`volcano_plot.png`) from active DE results. |
| 8 | **Heatmap Plot** | Visualization | **PASS** | Rendered top DEG expression heatmap (`heatmap_plot.png`). |
| 9 | **Enrichment / DEG Extraction** | RAG / Stats | **PASS** | Extracted 8 significant DEGs (FDR $< 0.05$, $\|LFC\| > 1.0$) strictly from active OSD-120 data. |
| 10 | **Literature Grounding** | RAG | **PASS** | Queried RAG index for *Arabidopsis thaliana*, returning 6 grounded snippets. |
| 11 | **Project Isolation** | Provenance | **PASS** | Enforced strict project workspace isolation for `OSD-120`. |
| 12 | **Artifact Provenance** | Provenance | **PASS** | All generated artifacts contain immutable provenance metadata (`project_id`, `analysis_id`, `source_artifact`, `parameters`). |
| 13 | **Interpretation Grounding Contract** | LLM Safety | **PASS** | Structured LLM payload contains actual OSD-120 stats with zero benchmark text. |
| 14 | **Insufficient-Replicate Refusal** | Refusal Guardrail | **PASS** | Refused DE on $N=1$ per group with structured `InsufficientReplicatesError`. |
| 15 | **Missing-Metadata Refusal** | Refusal Guardrail | **PASS** | Refused DE on missing metadata file with structured `MissingPrerequisitesError`. |
| 16 | **Missing-DE Visualization Refusal** | Refusal Guardrail | **PASS** | Refused Volcano plot on missing DE results with `MissingPrerequisitesError`. |
| 17 | **Benchmark Contamination Protection** | RAG Safety | **PASS** | Verified zero Arabidopsis/OSD-678 benchmark data injected into non-Arabidopsis project query. |

---

## 4. Negative Guardrail Refusal Verification

### 4.1 Insufficient Replicates Refusal ($N=1$)
- **Action**: Injected single-replicate dataset ($N=1$ Control, $N=1$ Treatment).
- **Result**: `PrerequisiteEngine` threw `InsufficientReplicatesError`. Downstream PyDESeq2 execution was blocked. No DE artifact was produced.

### 4.2 Missing Metadata Refusal
- **Action**: Attempted DE analysis with non-existent metadata file path.
- **Result**: Threw `MissingPrerequisitesError`. Pipeline halted cleanly.

### 4.3 Missing DE Visualization Refusal
- **Action**: Invoked `VolcanoPlotTool` pointing to a missing DE results CSV.
- **Result**: `VolcanoPlotTool` returned `ToolResult.error_result` with `MissingPrerequisitesError`. No plot image was generated.

### 4.4 Benchmark Contamination Protection
- **Action**: Submitted a research query specifying *Homo sapiens*.
- **Result**: RAG literature engine filtered candidate snippets strictly by *Homo sapiens*, confirming zero fallback injection of default *Arabidopsis thaliana* benchmark data.

---

## 5. Scope & Disclaimer

The RNAlyst platform is designed exclusively as a **research support tool** for basic and computational biological research. It is **not** intended for clinical diagnostic use, therapeutic decision-making, or automated medical diagnosis.
