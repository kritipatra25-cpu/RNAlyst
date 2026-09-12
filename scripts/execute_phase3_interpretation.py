"""
End-to-End Execution Script for Phase 3 LLM Interpretation Layer.
Reads Phase 2 RAG retrieval report, synthesizes Phase 3 evidence-bound interpretations,
validates output against 16 scientific guardrails, and exports JSON & Markdown reports.
"""

import os
import json
import logging
from pipeline.schemas.rag_schemas import RAGRetrievalReport
from analysis.interpretation.phase3_llm_adapter import Phase3LLMAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def run_phase3_interpretation():
    rag_json_path = os.path.join("results", "osd120_phase2_interpretation", "rag_retrieval_report.json")
    output_dir = os.path.join("results", "osd120_phase3_interpretation")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(rag_json_path):
        raise FileNotFoundError(f"Required Phase 2 RAG report missing at: {rag_json_path}")

    logger.info("=== PHASE 3 LLM INTERPRETATION LAYER EXECUTION ===")
    logger.info(f"Loading Phase 2 RAG evidence package from: {rag_json_path}")

    with open(rag_json_path, "r", encoding="utf-8") as f:
        rag_data = json.load(f)

    rag_report = RAGRetrievalReport(**rag_data)
    logger.info(f"Loaded RAG report with {len(rag_report.evidence_packages)} candidate gene evidence packages.")

    adapter = Phase3LLMAdapter(provider_name="DETERMINISTIC_MOCK_LLM_V1")
    logger.info("Synthesizing Phase 3 constrained interpretation report...")
    phase3_report = adapter.generate_report(rag_report)

    # 1. Export JSON Report
    json_path = os.path.join(output_dir, "phase3_interpretation_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(phase3_report.model_dump(), f, indent=2)
    logger.info(f"Saved Phase 3 Interpretation Report JSON to: {json_path}")

    # 2. Export Markdown Report
    md_path = os.path.join(output_dir, "phase3_interpretation_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Phase 3 LLM Interpretation Report — {phase3_report.study_id}\n\n")
        f.write(f"**Contrast**: {phase3_report.contrast}\n")
        f.write(f"**Human Review Status**: `{phase3_report.human_review_status}`\n")
        f.write(f"**Execution Timestamp**: `{phase3_report.provenance_manifest.get('execution_timestamp')}`\n\n")
        f.write(f"> [!WARNING]\n> **STUDY-LEVEL WARNING**: {phase3_report.sample_size_warning}\n\n")
        f.write("---\n\n")

        for interp in phase3_report.gene_interpretations:
            f.write(f"## Candidate Gene: `{interp.gene_id}` (Symbol: {interp.symbol or 'Unassigned'})\n\n")
            f.write(f"- **Statistical Classification**: `{interp.statistical_status}`\n")
            f.write(f"- **Category A (Quantitative Summary)**:\n  > {interp.quantitative_summary}\n\n")

            if interp.literature_context:
                f.write("- **Category B (Literature-Supported Context)**:\n")
                for lit in interp.literature_context:
                    f.write(f"  - {lit}\n")
                f.write("\n")

            if interp.database_annotations:
                f.write("- **Category C (Database / Pathway Annotations)**:\n")
                for db in interp.database_annotations:
                    f.write(f"  - {db}\n")
                f.write("\n")

            if interp.exploratory_hypotheses:
                f.write("- **Category D (Exploratory Hypotheses)**:\n")
                for hyp in interp.exploratory_hypotheses:
                    f.write(f"  - **{hyp.hypothesis_id}** (`{hyp.hypothesis_label}`):\n")
                    f.write(f"    - *Statement*: {hyp.hypothesis_statement}\n")
                    f.write(f"    - *Motivating Observation*: {hyp.motivating_observation}\n")
                    f.write(f"    - *Supporting Chunk IDs*: `{', '.join(hyp.supporting_evidence_chunk_ids)}`\n")
                    f.write(f"    - *Supporting Citations*: `{', '.join(hyp.supporting_citation_ids)}`\n")
                f.write("\n")

            f.write("- **Uncertainty & Methodological Notes**:\n")
            for unc in interp.uncertainty_notes:
                f.write(f"  - {unc}\n")
            f.write("\n")

            f.write(f"> [!CAUTION]\n> **MANDATORY CAUSAL GUARDRAIL**: {interp.causal_guardrail_statement}\n\n")
            f.write("---\n\n")

    logger.info(f"Saved Phase 3 Interpretation Report Markdown to: {md_path}")
    logger.info("=== PHASE 3 LLM INTERPRETATION LAYER EXECUTION COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_phase3_interpretation()
