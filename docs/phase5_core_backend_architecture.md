# Phase 5 — Core Backend Architecture Mapping

> **DOCUMENT TYPE**: Read-Only Architectural Audit & Generalization Specification
> **EVALUATED ARTIFACTS**: `docs/phase4_backend_reproducibility_audit.md`, `results/phase4_backend/*`, `pipeline/`, `analysis/`, `scientific_guardrails/`, `provenance/`
> **GOAL**: Map actual reusable core backend components, isolate OSD-specific logic, define component contracts, and evaluate generalization readiness for non-OSD bulk RNA-seq datasets.
> **FINAL ARCHITECTURAL VERDICT**: **`B. READY AFTER REFACTORING`**

---

## 1. System Component Inventory

| Component Name | Location | Input | Processing | Output | Deterministic? | Reusable? |
|---|---|---|---|---|---|---|
| **MetadataValidator** | `pipeline/input_validation.py` | CSV Sample sheet, design formula | Validates column names, non-empty IDs, duplicate check, replicate count audit | Validation Boolean, error list, replicate summary | YES | YES |
| **DesignChecker** | `scientific_guardrails/design_checker.py` | Metadata DataFrame, design formula, contrast | Checks factor availability, level existence, rank deficiency | Validation Boolean, error list | YES | YES |
| **ReplicateChecker** | `scientific_guardrails/replicate_rules.py` | Sample sheet DataFrame, condition column | Verifies $N \ge 3$ for inferential classification | Audit result dict (Inferential vs Exploratory) | YES | YES |
| **DESeq2Runner** | `analysis/statistics/deseq2_runner.py` | Count matrix, sample metadata, design formula | PyDESeq2 differential expression fitting, contrast extraction | DE stats DataFrame (LFC, p-value, padj, lfcSE) | YES | YES |
| **MetaAnalysisEngine** | `analysis/statistics/meta_analysis_engine.py` | Multiple DE summary statistics DataFrames | Fixed-effects inverse-variance meta-analysis, Cochran's Q | Summary LFC, meta $p$-value, heterogeneity statistics | YES | YES |
| **GeneIdentityVerifier** | `analysis/interpretation/gene_identity_verifier.py` | Gene IDs, locus mapping table | Reconciles gene symbols against TAIR10 reference annotations | Standardized TAIR Locus / Symbol dict | YES | PARTIAL (Arabidopsis specific) |
| **ExtensibleRAGEngine** | `analysis/interpretation/rag_engine.py` | Query string, top-$K$ parameter | Local vector/text retrieval over literature JSON/vector DB | List of retrieved verified publication chunks | YES | YES |
| **CitationVerifier** | `analysis/interpretation/citation_verifier.py` | Citation IDs, literature chunks | Compares claimed citations against retrieved database records | Verification Boolean, verified citation list | YES | YES |
| **ClaimGuardrails** | `scientific_guardrails/claim_guardrails.py` | Narrative text string | Regex & keyword scanning for forbidden causal overreach terms | Compliance Boolean, flagged terms list | YES | YES |
| **Phase1DataLoader** | `analysis/interpretation/data_loader.py` | Directory path containing Phase 1 outputs | Reads DE CSV, VST CSV, JSON summary, computes SHA-256 | Data dictionary & SHA-256 hash dictionary | YES | YES |
| **ProvenanceManager** | `provenance/manifest.py` | Artifact file paths, execution parameters | SHA-256 hashing, provenance manifest construction | JSON Provenance Manifest | YES | YES |
| **OSD678DESeq2Runner** | `scripts/osd678_deseq2_runner.py` | OSD-678 raw counts & metadata CSVs | Hard-coded 8-contrast PyDESeq2 runner for OSD-678 | Contrast CSVs, summary JSON, candidate comparison | YES | NO (OSD-678 specific) |
| **InterpretationBuilder** | `scripts/osd120_osd678_interpretation_builder.py` | Validated candidate DE statistics | Hard-coded candidate comparison dictionary generator | `biological_interpretation_summary.json` | YES | NO (OSD-120/678 candidate specific) |

---

## 2. Core Backend Identification

Components are categorised into 6 functional architectural tiers:

### A. CORE REUSABLE BACKEND
- `pipeline.input_validation.MetadataValidator`: Validates general sample sheets regardless of organism or experiment.
- `analysis.statistics.deseq2_runner.DESeq2Runner`: General wrapper around PyDESeq2 for arbitrary count matrices and design formulas.
- `analysis.statistics.meta_analysis_engine.run_meta_analysis`: General statistical inverse-variance meta-analysis engine.
- `provenance.manifest.ProvenanceManager`: Generic SHA-256 hash provenance calculator.

### B. DATASET-SPECIFIC LOGIC
- `scripts.osd678_deseq2_runner`: Hard-coded sample sheet parsing and contrast specifications for OSD-678.
- `scripts.osd120_osd678_interpretation_builder`: Hard-coded candidate lookup table for OSD-120 vs OSD-678 candidate genes.

### C. SCIENTIFIC-DOMAIN-SPECIFIC LOGIC
- `analysis.interpretation.gene_identity_verifier`: Contains TAIR10 locus mappings specific to *Arabidopsis thaliana*. (Needs abstraction for mouse/human).

### D. AI / LLM ORCHESTRATION
- `analysis.interpretation.phase3_llm_adapter.Phase3LLMAdapter`: Formats quantitative stats into structured LLM prompts.
- Antigravity Prompts (`Prompt 2.5`, `Prompt 3`, `Prompt 3.5`): High-level task orchestration prompts.

### E. VALIDATION / SAFETY GUARDRAILS
- `scientific_guardrails.design_checker`: Prevents rank-deficient linear models.
- `scientific_guardrails.replicate_rules`: Enforces minimum sample size rules ($N \ge 3$).
- `scientific_guardrails.claim_guardrails`: Prevents LLM causal overreach in markdown text.
- `analysis.interpretation.citation_verifier`: Prevents fabricated literature citations.

### F. REPORTING / PRESENTATION
- `docs/osd120_osd678_biological_interpretation.md`: Final human-readable Markdown report.
- `docs/phase4_backend_reproducibility_audit.md`: Audit report.

---

## 3. OSD-Specific Dependencies

Identification of dataset assumptions requiring refactoring:

| Dependency Item | Location in Codebase | Proposed Architectural Treatment |
|---|---|---|
| `OSD-120` / `OSD-678` accessions | `scripts/osd678_deseq2_runner.py`, `pipeline/input_validation.py` | **1. Remain dataset configuration** |
| `TAIR10` gene locus IDs (`AT1G01010`, etc.) | `analysis/interpretation/gene_identity_verifier.py` | **2. Become a plugin/module** (`GeneAnnotationPlugin`) |
| Factorial contrasts ($3 \times 2 \times 2$) | `scripts/osd678_deseq2_runner.py` | **3. Become a user-provided parameter** (`config.yaml`) |
| BRIC-23 / APEX hardware contexts | `docs/osd678_contrast_plan.md` | **4. Remain domain-specific** |
| Hard-coded 8 candidates (`ANAC001`, `LUX`, etc.) | `scripts/osd120_osd678_interpretation_builder.py` | **3. Become a user-provided parameter** (Dynamic selection by FDR threshold) |

---

## 4. General RNA-seq Agent Abstraction

Generalized 12-stage RNA-seq analysis pipeline mapping:

```
Stage 1: DATASET ACQUISITION       ──────> Existing (pipeline.osdr_client / manual download)
Stage 2: INPUT VALIDATION         ──────> Reusable (pipeline.input_validation.MetadataValidator)
Stage 3: METADATA RECONCILIATION   ──────> Reusable (scientific_guardrails.design_checker)
Stage 4: EXPERIMENT DESIGN        ──────> Reusable (pipeline.input_validation.ContrastGenerator)
Stage 5: STATISTICAL MODEL        ──────> Reusable (analysis.statistics.deseq2_runner.DESeq2Runner)
Stage 6: DIFFERENTIAL EXPRESSION  ──────> Reusable (PyDESeq2 core)
Stage 7: CANDIDATE SELECTION      ──────> Needs Abstraction (Dynamic FDR threshold filter vs hard-coded list)
Stage 8: EXTERNAL VALIDATION      ──────> Reusable (analysis.statistics.meta_analysis_engine)
Stage 9: LITERATURE RETRIEVAL     ──────> Reusable (analysis.interpretation.rag_engine.ExtensibleRAGEngine)
Stage 10: SCIENTIFIC INTERPRETATION ────> Reusable (analysis.interpretation.phase3_llm_adapter)
Stage 11: EVIDENCE GRADING        ──────> Reusable (scientific_guardrails.claim_guardrails)
Stage 12: REPORT EXPORT           ──────> Reusable (provenance.manifest.ProvenanceManager)
```

---

## 5. Core Backend Contract (Component Schemas)

### Stage 1: Input Validation Contract
- **Input Schema**: Raw Count Matrix CSV/TSV, Sample Sheet CSV (`sample_id`, factor columns), Design Formula String (e.g. `~ genotype + spaceflight`).
- **Output Schema**: `ValidationResult(is_valid: bool, errors: List[str], sample_count: int, factor_levels: Dict[str, List[str]])`.
- **Responsibility**: Enforce non-zero counts, non-empty metadata, duplicate checking, and factor availability.

### Stage 2: Differential Expression Contract
- **Input Schema**: Validated Count DataFrame, Validated Metadata DataFrame, Design Formula, Contrast List `[factor, num_level, ref_level]`.
- **Output Schema**: `DEResults(stats_df: DataFrame[gene_id, log2FC, pvalue, padj, lfcSE], summary_json: Dict[str, Any])`.
- **Responsibility**: Fit negative binomial GLM, extract contrast, apply Benjamini-Hochberg FDR correction.

### Stage 3: Knowledge Retrieval Contract
- **Input Schema**: Candidate Gene List `[gene_id, symbol]`, Domain Query Strings, Top-$K$ limit.
- **Output Schema**: `RetrievedContext(chunks: List[VerifiedCitation], query_metadata: Dict[str, Any])`.
- **Responsibility**: Fetch relevant literature excerpts without altering statistical values.

---

## 6. AI Agent Boundary

```
+-------------------------------------------------------------------------+
|                        DETERMINISTIC COMPUTATION                        |
|  (Count Parsing, PyDESeq2 Fitting, FDR Correction, Meta-Analysis,       |
|   SHA-256 Hashing, Replicate Rule Checks, Rank Deficiency Checks)        |
+-------------------------------------------------------------------------+
                                     │ (Machine-Readable Stats JSON)
                                     ▼
+-------------------------------------------------------------------------+
|                            AI ORCHESTRATION                             |
|  (Task Boundary Planning, Pipeline Stage Triggering, RAG Querying)      |
+-------------------------------------------------------------------------+
                                     │ (Retrieved Chunks + Stats)
                                     ▼
+-------------------------------------------------------------------------+
|                        SCIENTIFIC INTERPRETATION                        |
|  (Drafting Narrative Summaries, Evidence-Graded Tagging, Hypotheses)    |
+-------------------------------------------------------------------------+
                                     │ (Draft Markdown Text)
                                     ▼
+-------------------------------------------------------------------------+
|                         VALIDATION & GUARDRAILS                         |
|  (Python Regex Scanning for Forbidden Causal Overreach Terms)           |
+-------------------------------------------------------------------------+
                                     │ (Audited Text)
                                     ▼
+-------------------------------------------------------------------------+
|                              HUMAN REVIEW                               |
|  (Reviewing Implementation Plans, Feasibility Audits, Final Reports)    |
+-------------------------------------------------------------------------+
```

---

## 7. Evidence / Guardrail Architecture

Mapping of evidence labels (`[OBSERVED]`, `[LITERATURE]`, `[INFERENCE]`, `[HYPOTHESIS]`):

- **Origin**: Established in Prompt 2.5 Audit and Prompt 3.5 Evidence-Graph Audit.
- **Enforcement Mechanism**: Dual-layer (Enforced at prompt level during generation, and audited by executable Python code `scientific_guardrails.claim_guardrails.validate_ai_claim_text`).
- **Downstream Trust**: High. Machine-readable summaries stored in `biological_interpretation_summary.json` preserve `evidence_level` and `mechanistic_status` metadata fields.

---

## 8. Provenance Architecture

Tracing data transformations from source to report:

`Raw STAR Counts (SHA-256)`
$\rightarrow$ `PyDESeq2 Contrast Execution (SHA-256)`
$\rightarrow$ `Candidate Summary JSON (SHA-256)`
$\rightarrow$ `Evidence-Graded Markdown Report (SHA-256)`

- **Traceability Status**: Fully traceable via `provenance/manifest.py`.
- **Execution Distinction**: Phase 4 established **`PROVENANCE DEMONSTRATED`** (all computational outputs traceable to verified count matrices), but **`FULL PIPELINE RERUN`** from raw FASTQ reads was not performed (pre-quantified counts used).

---

## 9. Target Architecture

```
                 USER / CLINICAL SCIENTIST
                             │
                             ▼
                      AI ORCHESTRATOR
               (agent.orchestrator.agent_runner)
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
     DATA QC             ANALYSIS              EVIDENCE
(pipeline.input_val)  (analysis.stats)    (analysis.interp.rag)
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
                      INTERPRETATION
                (Phase3LLMAdapter / Prompts)
                             │
                             ▼
                  VALIDATION / GUARDRAILS
               (scientific_guardrails)
                             │
                             ▼
                        HUMAN REVIEW
               (notify_user / Release Gates)
                             │
                             ▼
                         FINAL REPORT
            (docs/osd120_osd678_biological_interpretation.md)
```

---

## 10. Gap Analysis

### ALREADY EXISTS
- Core PyDESeq2 runner (`analysis/statistics/deseq2_runner.py`).
- Input & Metadata validators (`pipeline/input_validation.py`).
- Design matrix & replicate checkers (`scientific_guardrails/`).
- Inverse-variance meta-analysis engine (`analysis/statistics/meta_analysis_engine.py`).
- Extensible RAGEngine (`analysis/interpretation/rag_engine.py`).
- SHA-256 Provenance manager (`provenance/manifest.py`).

### NEEDS REFACTORING
- Hard-coded runner scripts (`scripts/osd678_deseq2_runner.py`) into a configuration-driven CLI runner.
- Hard-coded candidate selection script (`scripts/osd120_osd678_interpretation_builder.py`) into a dynamic FDR threshold filter.
- `GeneIdentityVerifier` to support species-agnostic annotation plugins (mouse, human, Arabidopsis).

### MUST BE BUILT
- Unified Command Line Interface (`python -m pipeline.cli run --config config.yaml`).
- Config file parser (`yaml` / `json` experimental configuration reader).

---

## 11. Most Important Output & Final Verdict

### Summary Categorization Lists

```yaml
CORE_BACKEND_COMPONENTS:
  - pipeline.input_validation.MetadataValidator
  - analysis.statistics.deseq2_runner.DESeq2Runner
  - analysis.statistics.meta_analysis_engine.run_meta_analysis
  - provenance.manifest.ProvenanceManager

DATASET_SPECIFIC_COMPONENTS:
  - scripts.osd678_deseq2_runner
  - scripts.osd120_osd678_interpretation_builder
  - data.osd120
  - data.osd678

AI_ORCHESTRATION_COMPONENTS:
  - agent.orchestrator.agent_runner
  - analysis.interpretation.phase3_llm_adapter
  - Prompt_2.5_Boundary_Audit
  - Prompt_3.0_Biological_Interpretation
  - Prompt_3.5_Evidence_Graph_Audit

VALIDATION_COMPONENTS:
  - scientific_guardrails.design_checker
  - scientific_guardrails.replicate_rules
  - scientific_guardrails.claim_guardrails
  - analysis.interpretation.citation_verifier

MISSING_ABSTRACTIONS:
  - Unified_CLI_Entrypoint (pipeline.cli)
  - YAML_Configuration_Parser
  - Species_Agnostic_Gene_Annotation_Plugin
```

---

### Final Architectural Verdict

### **B. READY AFTER REFACTORING**

### Verdict Explanation
The core backend functionality—including input validation, PyDESeq2 differential expression modeling, meta-analysis, SHA-256 provenance tracking, and scientific guardrail enforcement—is fully implemented in Python and has been proven 100% executable and reproducible in Phase 4. However, the current execution workflow relies on dataset-specific runner scripts (`scripts/osd678_deseq2_runner.py` and `scripts/osd120_osd678_interpretation_builder.py`) containing hard-coded OSD-678 contrasts and OSD-120 candidate gene lists. To accept a completely new, arbitrary RNA-seq dataset, these hard-coded scripts must be refactored into a configuration-driven pipeline powered by a unified CLI entrypoint and dynamic FDR-based candidate selection. The core algorithms, mathematical engines, and validation safety checks require no architectural redesign and are ready for reuse immediately upon refactoring.

---

PHASE_5_ARCHITECTURE_AUDIT_COMPLETE
