"""
Execution Runner for Phase 2 LLM Interpretation & Knowledge Retrieval Layer.
Consumes Phase 1 locked outputs, synthesizes verified biological interpretation, and outputs audit manifests.
"""

import json
import logging
from pathlib import Path

from analysis.interpretation.data_loader import Phase1DataLoader
from analysis.interpretation.llm_interpreter import LLMInterpretationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    base_dir = Path(r"c:\Users\USER\.gemini\antigravity\scratch\rna-seq-ai-agent").resolve()
    phase1_dir = base_dir / "results" / "osd120_primary_analysis"
    out_dir = base_dir / "results" / "osd120_phase2_interpretation"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== PHASE 2 LLM INTERPRETATION LAYER EXECUTION ===")
    logger.info("Reading Phase 1 output files from: %s", phase1_dir)

    # 1. Load Phase 1 data
    loader = Phase1DataLoader(phase1_dir)
    data_bundle, file_hashes = loader.load_phase1_data()

    logger.info("Phase 1 input files loaded successfully. File Hashes:")
    for k, v in file_hashes.items():
        logger.info("  %s: %s", k, v[:12])

    # 2. Instantiate Interpretation Engine
    engine = LLMInterpretationEngine(data_bundle, file_hashes)

    # 3. Generate Interpretation Report
    report = engine.generate_deterministic_interpretation()

    # 4. Verify Report Integrity
    is_valid, errors = engine.verify_interpretation_report(report)
    if not is_valid:
        logger.error("Phase 2 Report Verification FAILED:")
        for err in errors:
            logger.error("  - %s", err)
        raise RuntimeError("Interpretation report verification failed!")

    logger.info("Phase 2 Report Verification PASSED! All 6 scientific safeguards satisfied.")

    # 5. Write Output Artifacts
    report_dict = report.model_dump()

    report_path = out_dir / "interpretation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    prov_path = out_dir / "phase2_provenance_manifest.json"
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(report_dict["provenance_manifest"], f, indent=2)

    logger.info("Saved Phase 2 Interpretation Report to: %s", report_path)
    logger.info("Saved Phase 2 Provenance Manifest to:   %s", prov_path)
    logger.info("=== PHASE 2 EXECUTION SUCCESSFULLY COMPLETED ===")

if __name__ == "__main__":
    main()
