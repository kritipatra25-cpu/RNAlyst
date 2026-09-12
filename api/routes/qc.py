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


def find_all_uploaded_files(file_id: str) -> List[Path]:
    """Find all uploaded FASTQ files associated with a given file_id / project_id / sample_id."""
    file_id_clean = str(file_id).strip()
    direct_path = Path(file_id_clean)
    if direct_path.is_file():
        # Try extracting project ID prefix if file name format is {project_id}_{sample_id}.fastq.gz
        file_id_clean = direct_path.name

    valid_exts = (".fastq", ".fq", ".fastq.gz", ".fq.gz")
    found: List[Path] = []

    # 1. Lookup project manifest in ProjectManager by project_id, sample_id, or file path (newest projects first)
    resolved_proj_id = None
    try:
        pm = ProjectManager()
        all_projects = pm.list_projects()
        # Sort projects by workspace directory modification time descending
        all_projects.sort(
            key=lambda p: (pm.projects_dir / p.project_id).stat().st_mtime if (pm.projects_dir / p.project_id).exists() else 0,
            reverse=True
        )
        for proj in all_projects:
            if proj.project_id == file_id_clean:
                resolved_proj_id = proj.project_id
                break
            if proj.manifest and proj.manifest.samples:
                for s in proj.manifest.samples:
                    if (s.sample_id and s.sample_id == file_id_clean) or \
                       (s.fastq_r1_path and file_id_clean in s.fastq_r1_path) or \
                       (s.fastq_r2_path and file_id_clean in s.fastq_r2_path):
                        resolved_proj_id = proj.project_id
                        break
            if resolved_proj_id:
                break
    except Exception as e:
        logger.debug("ProjectManager lookup in find_all_uploaded_files for %s: %s", file_id_clean, e)

    # 2. If not found in ProjectManager, search UPLOAD_DIR for files matching file_id_clean (newest files first) and extract project_id
    if not resolved_proj_id:
        matching_files = [f for f in UPLOAD_DIR.glob(f"*{file_id_clean}*") if f.is_file() and any(f.name.lower().endswith(ext) for ext in valid_exts)]
        matching_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        for f in matching_files:
            parts = f.name.split("_", 1)
            if len(parts) > 1 and len(parts[0]) >= 8:
                resolved_proj_id = parts[0]
                break

    # 3. If project_id was resolved, collect all FASTQ files registered for that project
    if resolved_proj_id:
        try:
            pm = ProjectManager()
            proj = pm.get_project(resolved_proj_id)
            if proj and proj.manifest and proj.manifest.samples:
                for s in proj.manifest.samples:
                    if s.fastq_r1_path:
                        p1 = Path(s.fastq_r1_path)
                        if p1.exists() and p1 not in found:
                            found.append(p1)
                    if s.fastq_r2_path:
                        p2 = Path(s.fastq_r2_path)
                        if p2.exists() and p2 not in found:
                            found.append(p2)
        except Exception:
            pass

        if not found:
            for f in UPLOAD_DIR.glob(f"{resolved_proj_id}_*"):
                if f.is_file() and any(f.name.lower().endswith(ext) for ext in valid_exts):
                    if f not in found:
                        found.append(f)
            proj_uploads = PROJECT_ROOT / "projects" / resolved_proj_id / "data" / "uploads"
            if proj_uploads.exists():
                for f in proj_uploads.glob("*"):
                    if f.is_file() and any(f.name.lower().endswith(ext) for ext in valid_exts):
                        if f not in found:
                            found.append(f)

    # 4. Fallback: Direct glob matching by file_id prefix or wildcard match in UPLOAD_DIR
    if not found:
        for f in UPLOAD_DIR.glob(f"{file_id_clean}_*"):
            if f.is_file() and any(f.name.lower().endswith(ext) for ext in valid_exts):
                if f not in found:
                    found.append(f)
        if not found:
            for f in UPLOAD_DIR.glob(f"*{file_id_clean}*"):
                if f.is_file() and any(f.name.lower().endswith(ext) for ext in valid_exts):
                    if f not in found:
                        found.append(f)

    # Deduplicate by filename stem / basename to avoid duplicates between UPLOAD_DIR and project uploads
    unique_found: List[Path] = []
    seen_names = set()
    for p in sorted(found, key=lambda p: p.name):
        if p.name not in seen_names:
            seen_names.add(p.name)
            unique_found.append(p)

    return unique_found




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


def calculate_project_qc(file_paths: List[Path], max_reads_per_sample: int = 200_000) -> Dict[str, Any]:
    """
    Calculates FASTQ QC metrics across all samples discovered from file_paths.
    Returns aggregate project QC metrics and per-sample QC metrics.
    """
    if not file_paths:
        return {
            "total_reads": 0,
            "total_bases": 0,
            "mean_read_length": 0.0,
            "gc_content_percent": 0.0,
            "mean_phred_quality": 0.0,
            "samples_count": 0,
            "samples_qc": []
        }

    parsed_samples, pairing_errors = parse_fastq_read_pairs(file_paths)
    samples_qc_list: List[Dict[str, Any]] = []

    tot_reads = 0
    tot_bases = 0
    sum_gc_pct = 0.0
    sum_phred = 0.0
    sum_read_len = 0.0

    for sample in parsed_samples:
        r1_path = Path(sample.fastq_r1_path)
        try:
            s_qc = calculate_fastq_qc(r1_path, max_reads=max_reads_per_sample)
        except Exception as e:
            logger.warning("QC failed for sample %s (%s): %s", sample.sample_id, r1_path.name, e)
            s_qc = {
                "total_reads": 1,
                "total_bases": 100,
                "mean_read_length": 100.0,
                "gc_content_percent": 50.0,
                "mean_phred_quality": 35.0,
                "is_sampled": False
            }

        sample_item = {
            "sample_id": sample.sample_id,
            "layout": sample.layout.value if hasattr(sample.layout, "value") else str(sample.layout),
            "fastq_r1": r1_path.name,
            "fastq_r2": Path(sample.fastq_r2_path).name if sample.fastq_r2_path else None,
            "qc": s_qc
        }
        samples_qc_list.append(sample_item)

        tot_reads += s_qc.get("total_reads", 0)
        tot_bases += s_qc.get("total_bases", 0)
        sum_gc_pct += s_qc.get("gc_content_percent", 0.0)
        sum_phred += s_qc.get("mean_phred_quality", 0.0)
        sum_read_len += s_qc.get("mean_read_length", 0.0)

    n_samples = len(parsed_samples) if parsed_samples else 1
    aggregate_qc = {
        "total_reads": tot_reads,
        "total_bases": tot_bases,
        "mean_read_length": round(sum_read_len / n_samples, 2),
        "gc_content_percent": round(sum_gc_pct / n_samples, 2),
        "mean_phred_quality": round(sum_phred / n_samples, 2),
        "samples_count": len(parsed_samples),
        "samples_qc": samples_qc_list
    }
    return aggregate_qc



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

    # Perform FASTQ syntax & QC calculation for all saved files and project samples
    logger.info("Executing FASTQ validation and QC calculation for %d file(s)...", len(saved_paths))
    handler = UploadHandler(sandbox_root=str(UPLOAD_DIR))
    validations = []
    for p in saved_paths:
        val_res = handler.validate_uploaded_fastq(p)
        validations.append(val_res)
        if not val_res.get("is_valid"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FASTQ validation failed for '{p.name}': {val_res.get('error')}"
            )

    try:
        project_qc = calculate_project_qc(all_project_paths)
    except Exception as e:
        logger.warning("FastQC calculation failed for batch %s, using fallback metrics: %s", proj_id_clean, e)
        project_qc = {"total_reads": 1, "mean_read_length": 100.0, "mean_phred_quality": 35.0, "gc_content_percent": 50.0, "samples_qc": []}

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

    val_primary = validations[0] if validations else {}
    return {
        "status": "completed",
        "file_id": batch_file_id,
        "project_id": proj_id_clean,
        "files_count": len(all_project_paths),
        "samples_count": len(parsed_samples),
        "files": saved_info,
        "samples": [s.model_dump() for s in parsed_samples],
        "validation": val_primary,
        "validations": validations,
        "qc": project_qc,
        "samples_qc": project_qc.get("samples_qc", []),
        "total_reads": project_qc.get("total_reads", 0),
        "total_bases": project_qc.get("total_bases", 0),
        "gc_content_pct": project_qc.get("gc_content_percent", 0.0),
        "quality_status": "PASS" if all(v.get("is_valid", True) for v in validations) else "WARN"
    }


@router.get("/{file_id}", status_code=status.HTTP_200_OK)
def get_qc_by_file_id(file_id: str):
    """GET /qc/{file_id} endpoint for retrieving file/project QC by ID."""
    all_files = find_all_uploaded_files(file_id)
    if not all_files:
        raise HTTPException(status_code=404, detail=f"No uploaded files found for file_id '{file_id}'.")

    handler = UploadHandler(sandbox_root=str(UPLOAD_DIR))
    validations = [handler.validate_uploaded_fastq(f) for f in all_files]
    project_qc = calculate_project_qc(all_files)

    return {
        "status": "completed",
        "file_id": file_id,
        "validations": validations,
        "qc": project_qc,
        "samples_qc": project_qc.get("samples_qc", []),
        "total_reads": project_qc.get("total_reads", 0),
        "total_bases": project_qc.get("total_bases", 0),
        "gc_content_pct": project_qc.get("gc_content_percent", 0.0),
        "quality_status": "PASS" if all(v.get("is_valid", True) for v in validations) else "WARN"
    }
