"""
Read-Only Data Loader for Phase 1 Output Artifacts.
Loads DE tables, VST matrices, and provenance manifests with SHA-256 hashing.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

class Phase1DataLoader:
    """Loads Phase 1 outputs in strictly read-only mode."""

    def __init__(self, phase1_dir: Path):
        self.phase1_dir = Path(phase1_dir).resolve()
        if not self.phase1_dir.exists():
            raise FileNotFoundError(f"Phase 1 directory does not exist: {self.phase1_dir}")

    def _compute_hash(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def load_phase1_data(self) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Load Phase 1 output datasets and compute file hashes."""
        de_csv = self.phase1_dir / "differential_expression.csv"
        vst_csv = self.phase1_dir / "vst_counts.csv"
        summary_json = self.phase1_dir / "deseq2_summary.json"
        prov_json = self.phase1_dir / "provenance_manifest.json"
        concordance_json = self.phase1_dir / "tier_c_concordance_report.json"

        hashes = {}
        for path, key in [
            (de_csv, "differential_expression_csv"),
            (vst_csv, "vst_counts_csv"),
            (summary_json, "deseq2_summary_json"),
            (prov_json, "provenance_manifest_json"),
            (concordance_json, "tier_c_concordance_report_json"),
        ]:
            if path.exists():
                hashes[key] = self._compute_hash(path)
            else:
                logger.warning("Optional Phase 1 file missing: %s", path)

        de_df = pd.read_csv(de_csv) if de_csv.exists() else pd.DataFrame()
        vst_df = pd.read_csv(vst_csv).set_index("gene_id") if vst_csv.exists() else pd.DataFrame()

        with open(summary_json, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        with open(prov_json, "r", encoding="utf-8") as f:
            prov_data = json.load(f)

        concordance_data = {}
        if concordance_json.exists():
            with open(concordance_json, "r", encoding="utf-8") as f:
                concordance_data = json.load(f)

        data_bundle = {
            "differential_expression": de_df,
            "vst_counts": vst_df,
            "summary": summary_data,
            "provenance": prov_data,
            "concordance": concordance_data,
        }

        return data_bundle, hashes
