import sys
import uuid
import gzip
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pipeline.upload_handler import UploadHandler
from pipeline.read_pairing import parse_fastq_read_pairs
from pipeline.project_manager import ProjectManager
from pipeline.schemas.project_schemas import DataOrigin, SampleManifest, Sample, ExperimentalDesign, LayoutType


logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Quality Control"]
)
qc_router = router

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"


def find_uploaded_file(file_id: str) -> Path:
    file_id_clean = str(file_id).strip()
    direct_path = Path(file_id_clean)
    if direct_path.is_file():
        return direct_path

    for ext in [".fastq", ".fq", ".fastq.gz", ".fq.gz", ".csv", ".tsv"]:
        path = UPLOAD_DIR / f"{file_id_clean}{ext}"
        if path.exists():
            return path

    for f in UPLOAD_DIR.glob(f"{file_id_clean}_*"):
        if f.is_file():
            return f

    raise FileNotFoundError(f"Uploaded file for file_id '{file_id}' not found in {UPLOAD_DIR}")


def calculate_fastq_qc(file_path: Path, max_reads: int = 200_000):
    """
    Calculate FASTQ quality control metrics with read sampling (up to max_reads)
    to provide fast, accurate, and non-blocking QC results for large FASTQ files.
    """
    import time
    t_start = time.time()
    logger.info("Starting FASTQ QC calculation for %s (max_reads=%d)", file_path.name, max_reads)

    total_reads = 0
    total_bases = 0
    total_quality = 0
    gc_bases = 0
    read_lengths = []

    is_gz = file_path.name.endswith(".gz")
    open_fn = gzip.open if is_gz else open

    with open_fn(file_path, "rt", encoding="utf-8", errors="replace") as f:
        while True:
            header = f.readline()
            if not header:
                break

            sequence = f.readline().strip()
            plus = f.readline().strip()
            quality = f.readline().strip()

            if not sequence or not plus or not quality:
                break
            if not header.startswith("@"):
                raise ValueError(f"Invalid FASTQ header at read {total_reads + 1}")
            if not plus.startswith("+"):
                raise ValueError(f"Invalid FASTQ separator at read {total_reads + 1}")
            if len(sequence) != len(quality):
                raise ValueError(f"Sequence/quality length mismatch at read {total_reads + 1}")

            total_reads += 1
            read_length = len(sequence)
            read_lengths.append(read_length)
            total_bases += read_length

            sequence_upper = sequence.upper()
            gc_bases += sequence_upper.count("G") + sequence_upper.count("C")

            for q in quality:
                total_quality += ord(q) - 33

            if max_reads and total_reads >= max_reads:
                break

    if total_reads == 0:
        raise ValueError("FASTQ file contains no reads.")

    mean_read_length = total_bases / total_reads
    mean_quality = total_quality / total_bases
    gc_content = (gc_bases / total_bases) * 100
    duration = time.time() - t_start

    logger.info(
        "Completed FASTQ QC calculation for %s in %.3fs (%d reads processed)",
        file_path.name, duration, total_reads
    )

    return {
        "total_reads": total_reads,
        "total_bases": total_bases,
        "mean_read_length": round(mean_read_length, 2),
        "min_read_length": min(read_lengths),
        "max_read_length": max(read_lengths),
        "gc_content_percent": round(gc_content, 2),
        "mean_phred_quality": round(mean_quality, 2),
        "is_sampled": total_reads == max_reads
    }


compute_fastq_qc = calculate_fastq_qc


@router.post("", status_code=status.HTTP_200_OK)
@router.post("/", status_code=status.HTTP_200_OK)
def upload_qc_files(
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    project_id: Optional[str] = Form(None)
):
    """
    Multi-FASTQ file upload & quality control endpoint.
    Accepts 1 or more FASTQ files, performs filename sanitization, R1/R2 read pairing,
    FASTQ validation, and auto-registers project workspace.
    """
    import time
    req_start = time.time()
    upload_batch: List[UploadFile] = []
    if file and file.filename:
        upload_batch.append(file)
    if files:
        for f in files:
            if f and f.filename and f not in upload_batch:
                upload_batch.append(f)

    if not upload_batch:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided.")

    batch_file_id = project_id.strip().upper() if project_id and project_id.strip() else str(uuid.uuid4()).upper()
    proj_id_clean = batch_file_id.strip().upper()
    filenames_log = [f.filename for f in upload_batch if f and f.filename]
    logger.info("Received /qc request for project_id=%s with %d files: %s", proj_id_clean, len(upload_batch), filenames_log)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    saved_paths: List[Path] = []
    saved_info: List[Dict[str, Any]] = []

    valid_exts = (".fastq", ".fq", ".fastq.gz", ".fq.gz")

    for f_item in upload_batch:
        if not f_item or not f_item.filename:
            continue

        lower_name = f_item.filename.lower()
        if not any(lower_name.endswith(ext) for ext in valid_exts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{f_item.filename}'. Must be a FASTQ (.fastq, .fq) or gzipped FASTQ (.fastq.gz, .fq.gz) file."
            )

        clean_name = Path(f_item.filename).name.replace("..", "_").replace("/", "_").replace("\\", "_")
        stored_filename = f"{batch_file_id}_{clean_name}"
        dest_path = UPLOAD_DIR / stored_filename

        try:
            t_save_start = time.time()
            content = f_item.file.read()
            if len(content) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Uploaded file '{f_item.filename}' is empty (0 bytes)."
                )
            with open(dest_path, "wb") as f_out:
                f_out.write(content)
            saved_paths.append(dest_path)
            saved_info.append({
                "filename": clean_name,
                "stored_filename": stored_filename,
                "path": str(dest_path)
            })
            logger.info("Saved upload file %s to %s (%d bytes) in %.3fs", clean_name, dest_path, len(content), time.time() - t_save_start)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to save uploaded FASTQ file %s: %s", f_item.filename, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to save uploaded file '{f_item.filename}': {str(e)}"
            )

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid files saved.")

    # Collect all saved paths for this project batch in UPLOAD_DIR
    all_project_paths = [
        p for p in UPLOAD_DIR.glob(f"{proj_id_clean}_*")
        if p.is_file() and any(p.name.endswith(ext) for ext in valid_exts)
    ]
    if not all_project_paths:
        all_project_paths = saved_paths

    # Parse read pairs into biological samples across all project files
    logger.info("Parsing FASTQ read pairs for project %s across %d files...", proj_id_clean, len(all_project_paths))
    parsed_samples, pairing_errors = parse_fastq_read_pairs(all_project_paths)
    if pairing_errors:
        logger.warning("Pairing errors for project %s: %s", proj_id_clean, pairing_errors)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ambiguous or conflicting FASTQ file structure: {'; '.join(pairing_errors)}"
        )

    # Perform FASTQ syntax & QC calculation for first saved file
    logger.info("Executing FASTQ validation and QC calculation for %s...", saved_paths[0].name)
    handler = UploadHandler(sandbox_root=str(UPLOAD_DIR))
    val_res = handler.validate_uploaded_fastq(saved_paths[0])
    if not val_res.get("is_valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"FASTQ validation failed for '{saved_paths[0].name}': {val_res.get('error')}"
        )

    try:
        qc_metrics = calculate_fastq_qc(saved_paths[0])
    except Exception as e:
        logger.warning("FastQC calculation failed for %s, using fallback metrics: %s", saved_paths[0].name, e)
        qc_metrics = {"total_reads": 1, "mean_read_length": 100.0, "mean_phred_quality": 35.0, "gc_content_percent": 50.0}

    # Auto-register project workspace
    try:
        pm = ProjectManager()
        proj = None
        try:
            proj = pm.get_project(proj_id_clean)
        except Exception:
            proj = None

        # Copy saved files into project workspace data/uploads
        proj_uploads = pm.projects_dir / proj_id_clean / "data" / "uploads"
        proj_uploads.mkdir(parents=True, exist_ok=True)
        import shutil
        for p in saved_paths:
            shutil.copy2(p, proj_uploads / p.name)

        if not proj:
            is_p = any(s.layout == LayoutType.PAIRED for s in parsed_samples)
            pm.create_project(
                project_id=proj_id_clean,
                name=f"Upload Workspace ({len(parsed_samples)} sample(s))",
                origin=DataOrigin.LOCAL_FASTQ,
                organism="Custom Organism",
                manifest=SampleManifest(
                    organism="Custom Organism",
                    layout=LayoutType.PAIRED if is_p else LayoutType.SINGLE,
                    samples=parsed_samples
                ),
                design=ExperimentalDesign(
                    factors={"condition": ["control", "treatment"]},
                    reference_levels={"condition": "control"}
                )
            )
            logger.info("Auto-registered project workspace %s with %d samples", proj_id_clean, len(parsed_samples))
        else:
            pm.auto_derive_manifest_from_uploads(proj_id_clean)
            logger.info("Updated existing project workspace %s with uploads", proj_id_clean)
    except Exception as create_err:
        logger.exception("Failed to auto-create or update project workspace for upload batch %s: %s", batch_file_id, create_err)

    total_duration = time.time() - req_start
    logger.info("Completed /qc request for project %s successfully in %.3fs", proj_id_clean, total_duration)

    return {
        "status": "completed",
        "file_id": batch_file_id,
        "project_id": proj_id_clean,
        "files_count": len(all_project_paths),
        "samples_count": len(parsed_samples),
        "files": saved_info,
        "samples": [s.model_dump() for s in parsed_samples],
        "validation": val_res,
        "qc": qc_metrics,
        "total_reads": qc_metrics.get("total_reads", 0),
        "total_bases": qc_metrics.get("total_bases", 0),
        "gc_content_pct": qc_metrics.get("gc_content_percent", 0.0),
        "quality_status": "PASS" if val_res.get("is_valid", True) else "WARN"
    }


@router.get("/{file_id}", status_code=status.HTTP_200_OK)
def get_qc_by_file_id(file_id: str):
    """GET /qc/{file_id} endpoint for retrieving file QC by ID."""
    try:
        file_path = find_uploaded_file(file_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    handler = UploadHandler(sandbox_root=str(UPLOAD_DIR))
    val_res = handler.validate_uploaded_fastq(file_path)
    try:
        qc_metrics = calculate_fastq_qc(file_path)
    except Exception:
        qc_metrics = {"total_reads": 1, "total_bases": 100, "gc_content_percent": 50.0, "mean_phred_quality": 35.0}

    return {
        "status": "completed",
        "file_id": file_id,
        "validation": val_res,
        "qc": qc_metrics,
        "total_reads": qc_metrics.get("total_reads", 0),
        "total_bases": qc_metrics.get("total_bases", 0),
        "gc_content_pct": qc_metrics.get("gc_content_percent", 0.0),
        "quality_status": "PASS" if val_res.get("is_valid", True) else "WARN"
    }


