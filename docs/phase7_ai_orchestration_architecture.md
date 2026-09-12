# Phase 7 — AI Orchestration & Scientific Reasoning Architecture

## 1. Overview
The Phase 7 AI Orchestration and Scientific Reasoning Layer establishes a clean, evidence-grounded gateway between natural-language user queries and the deterministic bulk RNA-seq backend API (`RNASeqBackendAPI`).

```
USER
  ↓
NATURAL-LANGUAGE SCIENTIFIC QUESTION
  ↓
NATURAL LANGUAGE INTENT PARSER (agent/orchestrator/intent_parser.py)
  ↓
STRUCTURED ANALYSIS INTENT & MACHINE-READABLE ANALYSIS PLAN (agent/orchestrator/analysis_plan.py)
  ↓
PLAN VALIDATOR & BACKEND GUARDRAILS
  ↓
RNASeqBackendAPI (pipeline/backend_api.py)
  ↓
DETERMINISTIC PyDESeq2 STATISTICAL COMPUTATION
  ↓
STRUCTURED ANALYSIS RESULTS & CANDIDATE RECONCILIATION
  ↓
LITERATURE RAG RETRIEVAL (agent/rag/literature_engine.py)
  ↓
EVIDENCE HIERARCHY CLASSIFICATION (agent/reasoning/evidence_classifier.py)
  ↓
STRUCTURED 7-QUESTION SCIENTIFIC SYNTHESIS (agent/reasoning/scientific_synthesizer.py)
  ↓
HUMAN-READABLE REPORT
```

## 2. Core Components

### A. Natural-Language Intent Parser (`agent/orchestrator/intent_parser.py`)
- **Purpose**: Translates free-form queries (e.g. *"What genes are significantly different between spaceflight and ground under light in OSD-678?"*) into structured `AnalysisIntent` models.
- **Fields**: `dataset_id`, `action`, `contrast_id`, `fdr_cutoff`, `lfc_cutoff`, `candidate_genes`, `require_interpretation`, `require_literature`.

### B. Machine-Readable Analysis Plan & Validator (`agent/orchestrator/analysis_plan.py`)
- **Purpose**: Converts `AnalysisIntent` into explicit, step-by-step `AnalysisPlan` objects (`VALIDATE_METADATA`, `EXECUTE_DE`, `ANNOTATE_GENES`, `SEARCH_LITERATURE`, `SYNTHESIZE_REPORT`).
- **Validation**: `PlanValidator` checks plans against `RNASeqBackendAPI` before execution. Invalid dataset IDs, contrast IDs, or out-of-bound parameters are rejected prior to statistical execution.

### C. Conversational State Manager (`agent/orchestrator/conversational_manager.py`)
- **Purpose**: Preserves active dataset, contrast, and candidate gene context across multi-turn user conversations without allowing conversation history to bypass backend validation boundaries.

### D. Literature RAG Engine (`agent/rag/literature_engine.py`)
- **Purpose**: Local, deterministic RAG retrieval index containing verified peer-reviewed spaceflight and plant transcriptomics literature snippets with exact source provenance (journal, year, DOI, provenance ID). Prevents citation fabrication.

### E. Evidence Hierarchy Classifier (`agent/reasoning/evidence_classifier.py`)
- **Enforces 5 explicit evidence badges**:
  - `[OBSERVED]`: Raw or normalized count observations.
  - `[STATISTICAL]`: PyDESeq2 differential expression metrics (LFC, p-value, padj).
  - `[LITERATURE-SUPPORTED]`: Verified peer-reviewed literature snippets & citations.
  - `[INTERPRETATION]`: Grounded biological pathway interpretation.
  - `[HYPOTHESIS]`: Speculative cellular or physiological mechanisms.
- **Guardrails**: Over-assertive hypotheses (e.g., claiming speculative mechanisms as "proven facts") are rejected.

### F. Scientific Synthesizer (`agent/reasoning/scientific_synthesizer.py`)
- **Purpose**: Transforms structured `AnalysisResult`, gene annotations, and literature snippets into a 7-question Markdown report (`ScientificReport`):
  1. What was tested? `[OBSERVED]`
  2. What was observed? `[OBSERVED]`
  3. What was statistically significant? `[STATISTICAL]`
  4. Which genes and pathways are most relevant? `[STATISTICAL]` / `[INTERPRETATION]`
  5. What evidence supports their biological interpretation? `[LITERATURE-SUPPORTED]`
  6. What remains uncertain? `[INTERPRETATION]`
  7. What hypotheses could be tested next? `[HYPOTHESIS]`

## 3. Boundary & Guardrail Rules
1. **Deterministic Isolation**: Zero statistical calculation occurs in the LLM or orchestration layer.
2. **Rejection Parity**: Backend rejections (e.g. unknown dataset ID, invalid FDR bound) are passed directly back to the caller without override.
3. **No Causal Conversion**: Statistical correlation or association is never presented as direct causation.
