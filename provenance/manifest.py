"""Manager for creating and updating immutable analysis provenance manifests."""
import json
import os
from typing import Dict, Any
from provenance.schemas import ProvenanceManifest


class ProvenanceManager:
    def __init__(self, provenance_dir: str):
        self.provenance_dir = provenance_dir
        os.makedirs(self.provenance_dir, exist_ok=True)

    def save_manifest(self, manifest: ProvenanceManifest) -> str:
        filepath = os.path.join(self.provenance_dir, f"{manifest.analysis_id}_provenance.json")
        with open(filepath, "w") as f:
            f.write(manifest.model_dump_json(indent=2))
        return filepath

    def load_manifest(self, analysis_id: str) -> ProvenanceManifest:
        filepath = os.path.join(self.provenance_dir, f"{analysis_id}_provenance.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Provenance manifest for {analysis_id} not found.")
        with open(filepath, "r") as f:
            data = json.load(f)
        return ProvenanceManifest(**data)
