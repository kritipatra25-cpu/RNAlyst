"""
Sandboxed FASTQ Upload & File Validation Handler.

Handles secure file upload routing into project sandbox directories,
filename sanitization (path traversal protection), and validation
via FASTQValidator and MetadataValidator.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

from pipeline.input_validation import FASTQValidator, MetadataValidator, InputValidationError

logger = logging.getLogger(__name__)


class UploadHandler:
    """Manager for secure file uploads and pre-analysis validation within sandbox directories."""

    def __init__(self, sandbox_root: str = "data/uploads"):
        self.sandbox_root = Path(sandbox_root).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def get_project_sandbox(self, project_id: str) -> Path:
        """Get or create sanitized project sandbox directory path."""
        clean_id = project_id.strip().upper()
        if " " in clean_id or ".." in clean_id or "/" in clean_id or "\\" in clean_id:
            raise ValueError(f"Invalid project_id '{project_id}': path traversal or invalid characters detected.")

        sandbox_dir = self.sandbox_root / clean_id
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        return sandbox_dir

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize uploaded filename to prevent directory traversal attacks."""
        clean_name = Path(filename.replace("\\", "/")).name
        # Remove dangerous characters
        clean_name = clean_name.replace("..", "_").replace("/", "_").replace("\\", "_")
        if not clean_name:
            raise ValueError("Filename is invalid or empty after sanitization.")
        return clean_name



    def save_uploaded_file(self, project_id: str, filename: str, content_bytes: bytes) -> Path:
        """Save raw bytes into project sandbox directory with filename sanitization."""
        sandbox_dir = self.get_project_sandbox(project_id)
        clean_filename = self.sanitize_filename(filename)
        dest_path = sandbox_dir / clean_filename

        with open(dest_path, "wb") as f:
            f.write(content_bytes)

        logger.info("Saved uploaded file %s for project %s (%d bytes)", clean_filename, project_id, len(content_bytes))
        return dest_path

    def validate_uploaded_fastq(self, file_path: Path) -> Dict[str, Any]:
        """Validate a single uploaded FASTQ file using FASTQValidator."""
        is_valid, err = FASTQValidator.validate_fastq_file(file_path)
        return {
            "file_name": file_path.name,
            "is_valid": is_valid,
            "error": err,
            "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
            "is_gzipped": FASTQValidator.is_gzipped(file_path) if file_path.exists() else False
        }

    def validate_uploaded_fastq_pair(self, r1_path: Path, r2_path: Path) -> Dict[str, Any]:
        """Validate paired-end R1 and R2 FASTQ headers and syntax."""
        is_valid, err = FASTQValidator.validate_paired_fastq_pair(r1_path, r2_path)
        return {
            "r1_name": r1_path.name,
            "r2_name": r2_path.name,
            "is_valid": is_valid,
            "error": err
        }

    def validate_uploaded_sample_sheet(self, sample_sheet_path: Path) -> Dict[str, Any]:
        """Validate CSV sample metadata sheet."""
        if not sample_sheet_path.exists():
            return {"is_valid": False, "errors": [f"File not found: {sample_sheet_path}"]}

        try:
            df = pd.read_csv(sample_sheet_path)
            is_valid, errors = MetadataValidator.validate_sample_sheet(df)
            return {
                "file_name": sample_sheet_path.name,
                "is_valid": is_valid,
                "sample_count": len(df) if not df.empty else 0,
                "columns": list(df.columns),
                "errors": errors
            }
        except Exception as e:
            return {"is_valid": False, "errors": [f"Failed to parse CSV sample sheet: {e}"]}
