"""
NASA OSDR (Open Science Data Repository) API Client Module.

Provides robust access to NASA OSDR metadata, sample factor matrices,
file inventories, candidate contrast discovery, and file downloads.
"""

import json
import logging
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

OSDR_BASE_URL = "https://osdr.nasa.gov/geode-py/ws"

class NASAOSDRClient:
    """Client for interacting with the NASA OSDR REST API."""

    def __init__(self, base_url: str = OSDR_BASE_URL, user_agent: str = "Antigravity-RNASeq-Engine/1.0"):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent

    def _make_request(self, endpoint: str) -> Dict[str, Any]:
        """Make an HTTP GET request to the OSDR API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except Exception as e:
            logger.error("OSDR API request failed for URL %s: %s", url, e)
            raise RuntimeError(f"OSDR API request failed: {e}") from e

    def fetch_study_metadata(self, accession: str) -> Dict[str, Any]:
        """Fetch complete study metadata for a given OSDR accession (e.g. OSD-120 or OSD-379)."""
        acc_clean = accession.strip().upper()
        if not (acc_clean.startswith("OSD-") or acc_clean.startswith("GLDS-")):
            raise ValueError(f"Invalid OSDR accession format: {accession}. Expected 'OSD-XXX' or 'GLDS-XXX'.")
        
        endpoint = f"repo/studies/{acc_clean}"
        data = self._make_request(endpoint)
        if not data:
            raise ValueError(f"No metadata returned for accession {acc_clean}")
        return data

    def parse_sample_table(self, study_metadata: Dict[str, Any]) -> pd.DataFrame:
        """Extract and normalize the sample metadata table into a pandas DataFrame."""
        samples_node = study_metadata.get("samples", {})
        table_rows = samples_node.get("table", []) if isinstance(samples_node, dict) else []
        
        if not table_rows:
            logger.warning("No sample table rows found in study metadata.")
            return pd.DataFrame()

        df = pd.DataFrame(table_rows)
        return df

    def parse_assay_metadata(self, study_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract assay specifications including sequencing platform, layout, strandedness, and files."""
        assays = study_metadata.get("assays", [])
        parsed_assays = []

        for idx, assay in enumerate(assays):
            if not isinstance(assay, dict):
                continue
            
            assay_info = {
                "assay_index": idx + 1,
                "measurement_type": assay.get("measurementType"),
                "technology_type": assay.get("technologyType"),
                "technology_platform": assay.get("technologyPlatform"),
                "file_name": assay.get("filename"),
                "total_records": assay.get("totalRecords", 0),
                "data_files": assay.get("dataFiles", []),
            }
            
            # Extract sample-level assay parameters from inner table
            inner_table = assay.get("table", {}).get("table", []) if isinstance(assay.get("table"), dict) else []
            if inner_table:
                r0 = inner_table[0]
                assay_info["library_layout"] = r0.get("Parameter Value[library layout]") or r0.get("Parameter Value[Library Layout]")
                assay_info["strandedness"] = r0.get("Parameter Value[stranded]") or r0.get("Parameter Value[Stranded]")
                assay_info["read_length"] = r0.get("Parameter Value[Read Length]")
                assay_info["sequencing_instrument"] = r0.get("Parameter Value[sequencing instrument]") or r0.get("Parameter Value[Sequencing Instrument]")
            
            parsed_assays.append(assay_info)

        return parsed_assays

    def audit_file_inventory(self, study_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Audit all data files associated with the study, classifying them into raw FASTQ and processed tables."""
        assays = study_metadata.get("assays", [])
        inventory = {
            "raw_fastq_files": [],
            "count_matrices": [],
            "deseq2_tables": [],
            "contrast_tables": [],
            "other_files": [],
            "total_raw_size_bytes": 0,
        }

        for assay in assays:
            if not isinstance(assay, dict):
                continue
            dfiles = assay.get("dataFiles", [])
            for f in dfiles:
                if not isinstance(f, dict):
                    continue
                name = f.get("name", "")
                ftype = f.get("type", "")
                url = f.get("remoteUrl") or f.get("url") or f.get("link")
                size = f.get("size") or f.get("file_size") or 0
                
                file_obj = {"name": name, "type": ftype, "url": url, "size": size}
                name_lower = name.lower()

                if "fastq" in name_lower or "raw" in ftype.lower() or name_lower.endswith(".tar"):
                    inventory["raw_fastq_files"].append(file_obj)
                    if isinstance(size, (int, float)):
                        inventory["total_raw_size_bytes"] += size
                elif "contrast" in name_lower:
                    inventory["contrast_tables"].append(file_obj)
                elif "deseq" in name_lower or "differential" in name_lower:
                    inventory["deseq2_tables"].append(file_obj)
                elif "count" in name_lower or "quant" in name_lower or "normalized" in name_lower:
                    inventory["count_matrices"].append(file_obj)
                else:
                    inventory["other_files"].append(file_obj)

        return inventory

    def download_file(self, file_url: str, dest_path: Path, expected_sha256: Optional[str] = None) -> Path:
        """Download a file from NASA OSDR with SHA-256 checksum verification."""
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        req = urllib.request.Request(file_url, headers={"User-Agent": self.user_agent})
        logger.info("Downloading file from %s to %s", file_url, dest_path)

        with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as f_out:
            hasher = hashlib.sha256()
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f_out.write(chunk)
                hasher.update(chunk)

        calculated_hash = hasher.hexdigest()
        if expected_sha256 and calculated_hash.lower() != expected_sha256.lower():
            dest_path.unlink(missing_ok=True)
            raise ValueError(f"Checksum mismatch for {dest_path.name}! Calculated: {calculated_hash}, Expected: {expected_sha256}")

        logger.info("Download completed for %s (SHA-256: %s)", dest_path.name, calculated_hash)
        return dest_path
