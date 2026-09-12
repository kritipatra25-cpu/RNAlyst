# Phase 5B — Backend Refactoring Plan

> **DOCUMENT TYPE**: Read-Only Architectural Refactoring Specification  
> **TARGET SYSTEM**: Bulk RNA-seq AI Agent Core Backend  
> **SCOPE**: Modular extraction of dataset-specific logic into reusable configurations, generic CLI runner, and species-agnostic plugins.  
> **FINAL REFACTORING STATUS**: **`FINAL STATUS: A. SAFE TO IMPLEMENT`**

---

## 1. Refactoring Objective

The objective of Phase 5B is to transform the Bulk RNA-seq AI Agent architecture from a dataset-bound implementation into a configuration-driven, generic RNA-seq analysis platform.

### Current Architectural Pattern:
```
dataset-specific runner (scripts/osd678_deseq2_runner.py)
        ↓
hard-coded OSD-678 contrasts (6 simple + 2 interaction/genotype)
        ↓
hard-coded candidate genes (8 TAIR IDs in scripts/osd120_osd678_interpretation_builder.py)
        ↓
core analysis (PyDESeq2 + local vector RAG)
```

### Target Architectural Pattern:
```
dataset configuration (configs/osd120.yaml, configs/osd678.yaml, configs/new_dataset.yaml)
        ↓
generic analysis runner (pipeline/cli.py)
        ↓
reusable statistical backend (analysis/statistics/deseq2_runner.py)
        ↓
structured results (results/{dataset_id}/...)
        ↓
optional validation / interpretation (analysis/interpretation/* + scientific_guardrails)
```

The benchmark datasets (**OSD-120** and **OSD-678**) must become standardized external configuration files rather than special cases hard-coded inside execution scripts.

---

## 2. File-by-File Refactoring Map

| Existing File | Current Responsibility | OSD-Specific Logic | What Should Be Extracted | What Remains | Proposed Destination |
|---|---|---|---|---|---|
| `scripts/osd678_deseq2_runner.py` | Runs PyDESeq2 analysis for OSD-678 | Hard-coded file paths (`data/osd678/...`), 8 contrast definitions, 8 TAIR candidate IDs | OSD-678 file paths, factors, reference levels, predefined contrasts | Generic DESeq2 contrast evaluation logic | `configs/osd678.yaml` (Config) & `pipeline/cli.py` (Runner) |
| `scripts/osd120_osd678_interpretation_builder.py` | Builds biological interpretation JSON | Hard-coded list of 8 candidate genes (`AT1G01010`, `AT3G46640`, etc.), hard-coded literature text | Candidate gene list, observed effect text, literature descriptions | Generic candidate comparison & evidence aggregator | `configs/osd120_osd678_benchmark.yaml` & `analysis/interpretation/candidate_prioritizer.py` |
| `analysis/interpretation/gene_identity_verifier.py` | Reconciles gene locus IDs to symbols | Hard-coded TAIR10 locus mappings for *Arabidopsis thaliana* | Species-specific TAIR mapping tables | Generic locus-to-symbol reconciliation interface | `pipeline/plugins/tair10_annotation_plugin.py` |
| `analysis/interpretation/rag_engine.py` | Retrieves literature context | Hard-coded OSD-120/OSD-678 vector database search queries | Dataset-specific search strings | Generic `ExtensibleRAGEngine` vector search engine | `analysis/interpretation/rag_engine.py` (remains core code) |
| `analysis/interpretation/phase3_llm_adapter.py` | Prepares prompt payloads | Hard-coded OSD-120 spaceflight contrast titles | Specific contrast label strings | Generic structured JSON prompt formatter | `analysis/interpretation/phase3_llm_adapter.py` (remains core code) |

---

## 3. Hard-Coded Logic Audit

| File Path & Location | Hard-Coded Logic Description | Classification | Action / Destination |
|---|---|---|---|
| `scripts/osd678_deseq2_runner.py` (L50-51) | `counts_file = 'data/osd678/GLDS-612...'` | **A. MUST EXTRACT** | Extract to `configs/osd678.yaml` |
| `scripts/osd678_deseq2_runner.py` (L82-90) | `reference_levels = {'genotype': 'Col-0', ...}` | **A. MUST EXTRACT** | Extract to `configs/osd678.yaml` |
| `scripts/osd678_deseq2_runner.py` (L142-149) | `contrasts = {'A1_Col0_Light_Flight_vs_Ground': ...}` | **A. MUST EXTRACT** | Extract to `configs/osd678.yaml` |
| `scripts/osd678_deseq2_runner.py` (L253) | `candidate_genes = ['AT3G17609', 'AT4G04720', ...]` | **A. MUST EXTRACT** | Extract to `configs/osd678.yaml` |
| `scripts/osd120_osd678_interpretation_builder.py` (L8-113) | Array of 8 hard-coded gene dictionaries with text | **A. MUST EXTRACT** | Extract to `configs/osd120_osd678_benchmark.yaml` |
| `analysis/interpretation/gene_identity_verifier.py` (L45-60) | TAIR10 Arabidopsis Locus symbol dictionary | **B. SAFE TO KEEP AS DATASET CONFIG** | Move to `pipeline/plugins/tair10_annotation_plugin.py` |
| `pipeline/input_validation.py` (L214-253) | Candidate generator for OSD-120 / OSD-379 | **D. DOCUMENTATION / BENCHMARK ONLY** | Keep as optional benchmark helper |
| `analysis/statistics/deseq2_runner.py` (L1-200) | PyDESeq2 matrix transformation & Wald test | **C. CORE SCIENTIFIC LOGIC** | Untouched |
| `scientific_guardrails/claim_guardrails.py` (L1-150) | Causal overreach keyword scanner | **C. CORE SCIENTIFIC LOGIC** | Untouched |
| `provenance/manifest.py` (L1-100) | SHA-256 manifest builder | **C. CORE SCIENTIFIC LOGIC** | Untouched |

---

## 4. Dataset Configuration Design

To run any new RNA-seq dataset, the system requires a YAML configuration file.

### Required Fields vs Optional Fields Schema:

```yaml
# Dataset Identity (REQUIRED)
dataset_id: "OSD-678"
organism: "Arabidopsis thaliana" # Human, Mouse, Arabidopsis, etc.
annotation_source: "TAIR10" # Ensembl, RefSeq, TAIR10

# Input Data Paths (REQUIRED)
counts_matrix_path: "data/osd678/GLDS-612_rna_seq_STAR_Unnormalized_Counts_GLbulkRNAseq.csv"
sample_metadata_path: "data/osd678/osd678_sample_metadata.csv"
sample_id_column: "sample_id"
gene_id_column: "gene_id"

# Experimental Design (REQUIRED)
design_formula: "~ group"
combined_group_column: "group" # Column generated by concatenating factors
factors:
  spaceflight: ["Ground", "Flight"]
  genotype: ["Col-0", "Ws", "phyD"]
  light: ["Dark", "Light"]

reference_levels:
  spaceflight: "Ground"
  genotype: "Col-0"
  light: "Dark"

# Predefined Contrasts (REQUIRED - At least 1 primary contrast)
contrasts:
  - id: "A1_Col0_Light_Flight_vs_Ground"
    factor: "group"
    numerator: "Flight_Col-0_Light"
    denominator: "Ground_Col-0_Light"
    description: "Primary Spaceflight effect in Col-0 light seedlings"

# Interaction Contrasts (OPTIONAL)
interaction_contrasts:
  - id: "C_Col0_Flight_x_Light_Interaction"
    contrast_a: "A1_Col0_Light_Flight_vs_Ground"
    contrast_b: "B1_Col0_Dark_Flight_vs_Ground"
    operation: "DIFFERENCE"

# Candidate Gene Selection (OPTIONAL - Default: Top 50 by FDR)
candidate_selection:
  mode: "FDR_THRESHOLD" # FDR_THRESHOLD, TOP_N, or SPECIFIED_LIST
  fdr_cutoff: 0.05
  lfc_cutoff: 1.0
  specified_genes: ["AT3G17609", "AT4G04720", "AT2G04170", "AT1G01010"] # Optional benchmark list

# External Validation / Cross-Dataset Benchmark (OPTIONAL)
external_validation:
  reference_dataset_id: "OSD-120"
  reference_de_path: "results/osd120_primary/differential_expression.csv"
```

---

## 5. Contrast Abstraction

The statistical backend accepts contrasts represented in standardized dictionary structures:

```
                  CONTRAST CONFIGURATION (YAML)
                               │
                               ▼
               CONTRAST VALIDATOR & SCHEMA CHECKER
             (scientific_guardrails.design_checker)
                               │
                               ▼
                    PYDESEQ2 CONTRAST ENGINE
          (DeseqStats(dds, contrast=['group', num, ref]))
                               │
                               ▼
             STANDARDIZED CONTRAST RESULT DATAFRAME
         [gene_id, log2FoldChange, lfcSE, pvalue, padj]
```

### Supported Contrast Types:
1. **Simple Factor Contrast**: `('factor', 'numerator_level', 'reference_level')`.
2. **Interaction / Difference Contrast**: Delta-of-deltas computed deterministically as:
   $$\text{LFC}_{\text{interaction}} = \text{LFC}_A - \text{LFC}_B$$
   $$\text{SE}_{\text{interaction}} = \sqrt{\text{SE}_A^2 + \text{SE}_B^2}$$
   $$Z = \frac{\text{LFC}_{\text{interaction}}}{\text{SE}_{\text{interaction}}}$$
   $$p = 2 \times (1 - \Phi(|Z|))$$

---

## 6. Candidate Gene Abstraction

The candidate gene selection subsystem supports 4 modes:

1. **User-Specified Candidate List**: User supplies explicit array of gene IDs (e.g. OSD-120 benchmark candidates).
2. **Automated FDR Prioritization**: Filters genes passing $\text{padj} < 0.05$ and $|\log_2\text{FC}| \ge 1.0$, ranked by absolute log2 fold-change.
3. **Cross-Dataset Validated Candidates**: Intersects significant DE genes across two datasets (e.g. OSD-120 root DE vs OSD-678 seedling DE).
4. **Domain-Specific / Pathway Candidates**: Selects genes matching specific biological keywords (e.g. "ROS/Redox", "Circadian").

---

## 7. Runner Architecture

### Decision: Option C — Generic CLI Runner + Dataset Configuration Files
- **Rationale**: Provides maximum code reuse while maintaining complete reproducibility for OSD-120 and OSD-678 benchmarks via YAML configuration files.

### Execution Flow Map:

```
               python -m pipeline.cli run --config configs/osd678.yaml
                               │
                               ▼
                   1. CONFIG PARSER & VALIDATOR
                    (pipeline.config_parser)
                               │
                               ▼
                   2. INPUT INTEGRITY AUDIT
             (pipeline.input_validation.MetadataValidator)
                               │
                               ▼
               3. REPLICATE & RANK DEFICIENCY CHECK
             (scientific_guardrails.design_checker)
                               │
                               ▼
                   4. PYDESEQ2 MODEL FITTER
               (analysis.statistics.deseq2_runner)
                               │
                               ▼
                   5. CONTRAST EVALUATOR
                     (DeseqStats loop)
                               │
                               ▼
             6. CANDIDATE PRIORITIZATION & RECONCILIATION
            (analysis.interpretation.candidate_prioritizer)
                               │
                               ▼
                   7. PROVENANCE MANIFEST BUILDER
                    (provenance.manifest)
                               │
                               ▼
                   8. STRUCTURED RESULTS EXPORT
               (results/{dataset_id}/deseq2_summary.json)
```

---

## 8. AI / LLM Boundary

### Deterministic Subsystem (No LLM Decisions):
- Input metadata validation
- Biological replicate checking ($N \ge 3$)
- Design matrix rank deficiency checking
- Read count matrix processing and PyDESeq2 model fitting
- Log2 fold change, standard error, and $p$-value calculations
- Benjamini-Hochberg FDR adjustments
- Inverse-variance meta-analysis statistics
- SHA-256 file hashing and provenance manifest generation
- Causal overreach regex validation

### AI / LLM Orchestration Subsystem (LLM Assisted):
- natural language query processing
- RAG vector search query formulation
- Biological literature synthesis and context summarizing
- Text formatting of human-readable Markdown reports (`docs/`)

---

## 9. Backward Compatibility & Regression Checklist

After refactoring, running `python -m pipeline.cli run --config configs/osd678.yaml` must produce outputs identical to the existing Phase 4 benchmark outputs:

- [ ] **Gene Count Check**: Exactly 32,833 genes evaluated for OSD-678.
- [ ] **Sample Count Check**: Exactly 36 samples grouped into 12 factorial cells ($N=3$).
- [ ] **Numerical LFC Match**: `A1_Col0_Light_Flight_vs_Ground` LFC values match `results/osd678_validation/contrasts/A1_Col0_Light_Flight_vs_Ground.csv` to $\ge 6$ decimal places.
- [ ] **FDR Adjusted P-value Match**: `padj` values match to $\ge 6$ decimal places.
- [ ] **Candidate Classification Match**: 8 candidate genes classified into identical evidence groups (Group A: ANAC001, LUX, RBOHA, CHS; Group B: HYH; Group C: AT2G04170, CPK21, CIPK21).
- [ ] **SHA-256 Hash Auditing**: Provenance manifest verifies input file SHA-256 hashes match.

---

## 10. Proposed New Files / Modules

1. **`pipeline/config_parser.py`**: Reads, parses, and validates dataset YAML configuration files against Pydantic schemas.
2. **`pipeline/cli.py`**: Unified Command Line Interface entrypoint for running dataset pipelines.
3. **`configs/osd120.yaml`**: Configuration file defining OSD-120 counts, sample metadata, and contrasts.
4. **`configs/osd678.yaml`**: Configuration file defining OSD-678 counts, sample metadata, 8 factorial contrasts, and candidates.
5. **`analysis/interpretation/candidate_prioritizer.py`**: Reusable component for dynamic candidate gene selection and cross-dataset comparison.
6. **`pipeline/plugins/tair10_annotation_plugin.py`**: Isolated Arabidopsis TAIR10 locus annotation plugin.

---

## 11. Files That Must NOT Change

- `analysis/statistics/deseq2_runner.py`: Core PyDESeq2 integration engine.
- `analysis/statistics/meta_analysis_engine.py`: Fixed-effects inverse-variance meta-analysis engine.
- `scientific_guardrails/design_checker.py`: Rank deficiency and contrast validator.
- `scientific_guardrails/replicate_rules.py`: Biological replicate count auditor.
- `scientific_guardrails/claim_guardrails.py`: Causal claim regex engine.
- `provenance/manifest.py`: SHA-256 manifest calculator.
- All existing outputs under `results/osd120_primary/` and `results/osd678_validation/` (Locked benchmark artifacts).

---

## 12. Migration Order (10-Step Sequence)

1. **STEP 1**: Define Pydantic configuration schema in `pipeline/schemas/config_schemas.py`.
2. **STEP 2**: Implement YAML configuration parser in `pipeline/config_parser.py`.
3. **STEP 3**: Extract OSD-120 metadata, contrasts, and paths into `configs/osd120.yaml`.
4. **STEP 4**: Extract OSD-678 metadata, contrasts, and candidate lists into `configs/osd678.yaml`.
5. **STEP 5**: Build species annotation plugin in `pipeline/plugins/tair10_annotation_plugin.py`.
6. **STEP 6**: Create candidate gene prioritizer component in `analysis/interpretation/candidate_prioritizer.py`.
7. **STEP 7**: Implement generic CLI runner in `pipeline/cli.py`.
8. **STEP 8**: Execute regression verification against OSD-120 and OSD-678 benchmark outputs.
9. **STEP 9**: Verify SHA-256 provenance manifests and guardrail validation checks.
10. **STEP 10**: Expose generic CLI commands to high-level AI orchestrator.

---

## 13. Risk Register

| Risk Event | Impact | Mitigation Strategy |
|---|---|---|
| Refactored PyDESeq2 runner produces slightly different LFC values due to floating-point order | High | Lock `PyDESeq2` version (v0.5.4) and set explicit random seeds; verify diffs against locked CSVs. |
| Hard-coded candidate lookup table breaks when running non-Arabidopsis datasets | High | Implement species annotation plugins and fallback to TAIR/Ensembl locus IDs if symbol is missing. |
| Configuration file specifies invalid factor level names | Medium | Enforce strict pre-flight validation in `scientific_guardrails.design_checker` before PyDESeq2 initialization. |
| Over-generalizing pipeline breaks OSD-120/OSD-678 provenance traceability | High | Retain `data/` raw counts and locked `results/` artifacts as immutable regression targets. |

---

## 14. Final Refactoring Blueprint

```
                     CURRENT ARCHITECTURE
       (Hard-coded scripts: osd678_deseq2_runner.py)
                               │
                               ▼
                      TARGET ARCHITECTURE
  (pipeline/cli.py + configs/*.yaml + candidate_prioritizer.py)
                               │
                               ▼
                    FILES TO MODIFY & EXTRACT
   (scripts/osd678_deseq2_runner.py ──> configs/osd678.yaml)
                               │
                               ▼
                          FILES TO ADD
   (pipeline/cli.py, pipeline/config_parser.py, configs/*.yaml)
                               │
                               ▼
                        FILES TO PRESERVE
 (deseq2_runner.py, meta_analysis_engine.py, scientific_guardrails/*)
                               │
                               ▼
                   REGRESSION TESTS REQUIRED
  (Verify 32,833 genes, 36 samples, 8 candidates, exact LFC & padj)
                               │
                               ▼
                      IMPLEMENTATION ORDER
                   (10-Step Safe Sequence)
```

---

PHASE_5B_REFACTORING_PLAN_COMPLETE

FINAL STATUS: **A. SAFE TO IMPLEMENT**
