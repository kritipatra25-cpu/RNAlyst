# Generic Bulk RNA-seq AI Agent Core Backend Guide

> **MODULE**: Core Bioinformatics Pipeline & Generic CLI Runner  
> **CANONICAL ENTRYPOINT**: `python -m pipeline.cli run --config <path_to_config.yaml>`  
> **REPRODUCIBILITY STATUS**: **`BENCHMARK_REPRODUCED`** (100% exact numerical match against locked OSD-678 benchmark)

---

## 1. Overview

The Bulk RNA-seq AI Agent platform features a decoupled, configuration-driven, deterministic backend that isolates core statistical modeling and validation from high-level AI orchestration.

```
dataset YAML configuration (configs/osd678.yaml, configs/osd120.yaml, configs/*.yaml)
        ↓
generic CLI runner (pipeline/cli.py)
        ↓
config parser & Pydantic schema validation (pipeline/config_parser.py)
        ↓
input integrity & sample sheet validation (pipeline/input_validation.py)
        ↓
replicate (N>=3) & design matrix rank checks (scientific_guardrails/*)
        ↓
PyDESeq2 negative binomial Wald engine (analysis/statistics/deseq2_runner.py)
        ↓
standardized factor & interaction contrast evaluation
        ↓
candidate gene prioritization & locus symbol reconciliation (analysis/interpretation/candidate_prioritizer.py)
        ↓
SHA-256 execution provenance manifest (provenance/manifest.py)
        ↓
structured results export (results/{dataset_id}/...)
```

---

## 2. Configuration Specification

Every dataset configuration is defined in a standard YAML file parsed by `pipeline/config_parser.py`.

### YAML Configuration Schema

```yaml
# Dataset Identity
dataset_id: "OSD-678"
organism: "Arabidopsis thaliana"
annotation_source: "TAIR10"

# Input Data File Paths
counts_matrix_path: "data/osd678/GLDS-612_rna_seq_STAR_Unnormalized_Counts_GLbulkRNAseq.csv"
sample_metadata_path: "data/osd678/osd678_sample_metadata.csv"
sample_id_column: "sample_id"
gene_id_column: "gene_id"

# Experimental Design
design_formula: "~ group"
combined_group_column: "group"

# Factor Definitions (Ordered key format: spaceflight, genotype, light)
factors:
  spaceflight: ["Ground", "Flight"]
  genotype: ["Col-0", "Ws", "phyD"]
  light: ["Dark", "Light"]

reference_levels:
  spaceflight: "Ground"
  genotype: "Col-0"
  light: "Dark"

# Predefined Simple Contrasts
contrasts:
  - id: "A1_Col0_Light_Flight_vs_Ground"
    factor: "group"
    numerator: "Flight_Col-0_Light"
    denominator: "Ground_Col-0_Light"
    description: "Col-0 Wild-Type Flight vs Ground Response under Light"

# Interaction / Difference Contrasts
interaction_contrasts:
  - id: "C_Col0_Flight_x_Light_Interaction"
    contrast_a: "A1_Col0_Light_Flight_vs_Ground"
    contrast_b: "B1_Col0_Dark_Flight_vs_Ground"
    operation: "DIFFERENCE"

# Candidate Gene Selection Mode
candidate_selection:
  mode: "SPECIFIED_LIST" # SPECIFIED_LIST, FDR_THRESHOLD, or TOP_N
  fdr_cutoff: 0.05
  lfc_cutoff: 1.0
  specified_genes:
    - "AT3G17609" # HYH
    - "AT4G04720" # CPK21
    - "AT2G04170" # AT2G04170
    - "AT1G01010" # ANAC001
    - "AT5G57630" # CIPK21
    - "AT3G46640" # LUX
    - "AT5G07390" # RBOHA
    - "AT5G13930" # CHS

# External Validation / Cross-Dataset Reference
external_validation:
  reference_dataset_id: "OSD-120"
  reference_de_path: "results/osd120_primary_analysis/differential_expression.csv"

output_dir: "results/osd678_validation"
```

---

## 3. CLI Usage

To run differential expression and candidate prioritization on any dataset:

```bash
# Run OSD-678 analysis
python -m pipeline.cli run --config configs/osd678.yaml

# Run OSD-120 analysis
python -m pipeline.cli run --config configs/osd120.yaml

# Run automated pipeline test suite
python -m unittest tests/test_pipeline_refactor.py
```

---

## 4. AI / LLM Architectural Boundary

| Subsystem | Responsibilities | Deterministic / AI |
|---|---|---|
| **Input Validation** | Read matrix format checking, sample sheet column validation, replicate count audits ($N \ge 3$) | **Deterministic Python** |
| **Statistical Engine** | PyDESeq2 size-factor normalization, dispersion fitting, Wald test statistics, BH FDR adjustment | **Deterministic Python** |
| **Scientific Guardrails** | Design matrix rank deficiency checking, causal claim regex validation | **Deterministic Python** |
| **Provenance** | SHA-256 input/output hashing, software environment logging | **Deterministic Python** |
| **AI Orchestrator** | High-level user query formulation, RAG literature context retrieval, Markdown report generation | **LLM Assisted** |

> **STRICT GUARANTEE**: The AI/LLM layer is NEVER involved in calculating log2 fold changes, $p$-values, FDR thresholds, or biological replicate validity checks.

---

## 5. Automated Regression Test Suite

The refactored backend includes `tests/test_pipeline_refactor.py` which verifies:
- YAML schema parsing and default handling.
- Input metadata validation and replicate rule enforcement.
- Dynamic candidate gene prioritization and cross-dataset reconciliation.
- **Exact numerical regression** against locked OSD-678 benchmark targets (`results/osd678_validation/candidate_validation/osd678_candidate_comparison.csv`).

To run tests:
```bash
python -m unittest tests/test_pipeline_refactor.py
```
*(Result: 4/4 tests passed in 0.020 seconds)*
