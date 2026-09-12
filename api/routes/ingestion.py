"""
FastAPI Ingestion Router for Dataset-Agnostic Project Setup,
Sandboxed FASTQ File Uploads, and Read Quantification.
"""

import os
import shutil
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, Field

from pipeline.project_manager import ProjectManager
from pipeline.upload_handler import UploadHandler
from pipeline.quantification_runner import QuantificationRunner
from pipeline.nextflow_runner import NextflowRunner, DependencyNotFoundError
from agent.tools.ingestion_tools import CreateProjectTool, ValidateFASTQTool, QuantifyReadsTool

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateProjectRequest(BaseModel):
    project_id: str = Field(..., description="Unique dataset/project identifier (e.g. USER_STUDY_2026)")
    name: str = Field(..., description="Human-readable project title")
    origin: str = Field("LOCAL_FASTQ", description="Data origin (LOCAL_FASTQ or OSDR_ACCESSION)")
    organism: Optional[str] = Field(None, description="Organism species name (optional)")
    condition_column: Optional[str] = Field(None, description="Factor column name for differential comparison")
    sample_ids: Optional[List[str]] = Field(None, description="List of sample IDs (optional)")
    conditions: Optional[List[str]] = Field(None, description="Condition factor level for each sample (optional)")
    numerator_level: Optional[str] = Field(None, description="Numerator condition level (optional)")
    reference_level: Optional[str] = Field(None, description="Reference condition level (optional)")
    batch_column: Optional[str] = None


class QuantifyProjectRequest(BaseModel):
    reads_dir: Optional[str] = None
    transcriptome_fasta: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_project_endpoint(req: CreateProjectRequest):
    """Creates a new dataset-agnostic RNA-seq project and generates dataset YAML config."""
    try:
        tool = CreateProjectTool()
        res = tool.run(req.model_dump())
        if res.status != "success":
            raise HTTPException(status_code=400, detail=res.error or "Project creation failed.")
        return res.result
    except Exception as e:
        logger.exception("Failed to create project %s: %s", req.project_id, e)
        raise HTTPException(status_code=500, detail=f"Project creation failed: {str(e)}")


@router.post("/upload")
@router.post("/ingestion/upload")
async def upload_fastq_standalone(
    file: UploadFile = File(...),
    paired_file: Optional[UploadFile] = File(None),
    sample_id: Optional[str] = Form(None)
):
    """
    Standalone FASTQ upload endpoint.
    Generates a unique file_id (UUID), saves uploaded FASTQ file to data/uploads/{file_id}_{filename},
    validates the file, and returns file_id.
    """
    upload_dir = Path("data/uploads").resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    clean_name = Path(file.filename).name.replace("..", "_").replace("/", "_").replace("\\", "_")
    stored_filename = f"{file_id}_{clean_name}"
    dest_path = upload_dir / stored_filename

    try:
        content = file.file.read()
        with open(dest_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save uploaded file: {str(e)}")

    r2_dest = None
    if isinstance(paired_file, UploadFile) and paired_file.filename:
        clean_r2 = Path(paired_file.filename).name.replace("..", "_").replace("/", "_").replace("\\", "_")
        r2_dest = upload_dir / f"{file_id}_{clean_r2}"
        try:
            content_2 = paired_file.file.read()
            with open(r2_dest, "wb") as f:
                f.write(content_2)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to save paired file: {str(e)}")

    handler = UploadHandler(sandbox_root=str(upload_dir))
    val_res = handler.validate_uploaded_fastq(dest_path)

    logger.info("Saved standalone upload %s to %s with file_id %s", clean_name, dest_path, file_id)

    return {
        "file_id": file_id,
        "filename": clean_name,
        "stored_filename": stored_filename,
        "file_path": str(dest_path),
        "r1_file_path": str(dest_path),
        "r2_file_path": str(r2_dest) if r2_dest else None,
        "sample_id": sample_id,
        "validation": val_res
    }


upload_file = upload_fastq_standalone


@router.post("/{project_id}/upload")
def upload_fastq_endpoint(
    project_id: str,
    file: UploadFile = File(...),
    paired_file: Optional[UploadFile] = File(None),
    sample_id: Optional[str] = Form(None)
):
    """
    Uploads gzipped FASTQ file(s) into project-isolated sandbox directory
    and runs syntax and header validation.
    """
    pm = ProjectManager()
    project = pm.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    uploads_dir = pm.projects_dir / project_id / "data" / "uploads"
    handler = UploadHandler(sandbox_root=str(uploads_dir))

    # Save primary file R1
    try:
        content_1 = file.file.read()
        r1_dest = handler.save_uploaded_file(project_id=project_id, filename=file.filename, content_bytes=content_1)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save primary FASTQ file: {str(e)}")

    r2_dest = None
    if isinstance(paired_file, UploadFile) and paired_file.filename:
        try:
            content_2 = paired_file.file.read()
            r2_dest = handler.save_uploaded_file(project_id=project_id, filename=paired_file.filename, content_bytes=content_2)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to save paired FASTQ file: {str(e)}")

    # Validate file integrity
    val_tool = ValidateFASTQTool(sandbox_root=str(uploads_dir))
    val_res = val_tool.run({
        "fastq_file_path": str(r1_dest),
        "paired_file_path": str(r2_dest) if r2_dest else None
    })

    return {
        "project_id": project_id,
        "sample_id": sample_id,
        "r1_file_path": str(r1_dest),
        "r2_file_path": str(r2_dest) if r2_dest else None,
        "validation": val_res.result
    }


@router.post("/{project_id}/quantify")
def quantify_project_endpoint(project_id: str, req: Optional[QuantifyProjectRequest] = None):
    """
    Executes read quantification via Nextflow/Salmon or fallback engine,
    then aggregates transcript counts into gene-level counts_matrix.csv.
    """
    pm = ProjectManager()
    # Auto-derive sample manifest and layout from uploaded FASTQ files
    project = pm.auto_derive_manifest_from_uploads(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    sample_ids = [s.sample_id for s in project.manifest.samples]
    project_dir = pm.projects_dir / project_id
    reads_dir = req.reads_dir if (req and req.reads_dir) else str(project_dir / "data" / "uploads")
    output_dir = str(project_dir)

    # Run Nextflow or deterministic quantification bridge
    nf_runner = NextflowRunner()
    try:
        quant_map = nf_runner.run_pipeline(
            project_id=project_id,
            sample_ids=sample_ids,
            reads_dir=reads_dir,
            output_dir=output_dir,
            transcriptome_fasta=req.transcriptome_fasta if req else None
        )
    except DependencyNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Aggregate counts_matrix.csv
    quant_tool = QuantifyReadsTool(projects_dir=str(pm.projects_dir))
    res_quant = quant_tool.run({
        "project_id": project_id,
        "quant_directories": quant_map
    })

    if res_quant.status != "success":
        err_msg = str(res_quant.error.message) if (res_quant.error and hasattr(res_quant.error, "message")) else (str(res_quant.error) if res_quant.error else "Quantification aggregation failed.")
        raise HTTPException(status_code=500, detail=err_msg)

    return res_quant.result


@router.get("")
@router.get("/")
def list_projects_endpoint():
    """Returns list of registered user and benchmark datasets/projects."""
    pm = ProjectManager()
    projects = pm.list_projects()

    # Normalize projects list to dictionary format
    discovered = []
    for p in projects:
        if hasattr(p, "model_dump"):
            discovered.append(p.model_dump())
        elif hasattr(p, "dict"):
            discovered.append(p.dict())
        elif isinstance(p, dict):
            discovered.append(p)
        else:
            discovered.append(dict(p))

    # Discover static/benchmark configs as well
    configs_dir = pm.configs_dir
    if configs_dir.exists():
        for yf in configs_dir.glob("*.yaml"):
            ds_id = yf.stem.upper()
            if not any(p.get("project_id") == ds_id for p in discovered):
                discovered.append({
                    "project_id": ds_id,
                    "name": f"Config Dataset ({ds_id})",
                    "origin": "CONFIG",
                    "organism": "Arabidopsis thaliana",
                    "samples_count": 0
                })

    return {"projects": discovered}


@router.get("/{project_id}")
def get_project_endpoint(project_id: str):
    """Returns full canonical manifest for requested project."""
    pm = ProjectManager()
    project = pm.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return project.model_dump()


@router.get("/{project_id}/history")
def get_project_history_endpoint(project_id: str):
    """Returns persistent step-by-step tool execution history for a project workspace."""
    pm = ProjectManager()
    history = pm.get_execution_history(project_id)
    return {"project_id": project_id, "execution_history": history}


class MetadataAssignItem(BaseModel):
    sample_id: str
    condition: str
    replicate_id: Optional[str] = None


class MetadataAssignRequest(BaseModel):
    sample_metadata: List[MetadataAssignItem]


@router.post("/{project_id}/metadata")
def assign_metadata_endpoint(project_id: str, req: MetadataAssignRequest):
    """
    Assign experimental condition and replicate metadata to samples in project.
    Validates that every metadata sample ID corresponds to an uploaded sample.
    """
    pm = ProjectManager()
    project = pm.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    records = [item.model_dump() for item in req.sample_metadata]
    try:
        updated_proj = pm.assign_sample_metadata(project_id, records)
        return updated_proj.model_dump()
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign metadata: {str(e)}")


@router.post("/{project_id}/metadata/csv")
def assign_metadata_csv_endpoint(project_id: str, file: UploadFile = File(...)):
    """
    Upload CSV sample-sheet metadata to assign conditions/groups to project samples.
    CSV must contain 'sample_id' and 'condition' columns.
    """
    pm = ProjectManager()
    project = pm.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No CSV file provided.")

    try:
        import pandas as pd
        import io
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # Lowercase column names normalization
        col_map = {str(c).lower().strip(): c for c in df.columns}
        if "sample_id" not in col_map and "sample" in col_map:
            df.rename(columns={col_map["sample"]: "sample_id"}, inplace=True)
            col_map = {str(c).lower().strip(): c for c in df.columns}
        if "group" in col_map and "condition" not in col_map:
            df.rename(columns={col_map["group"]: "condition"}, inplace=True)
            col_map = {str(c).lower().strip(): c for c in df.columns}

        if "sample_id" not in col_map or "condition" not in col_map:
            raise HTTPException(status_code=400, detail=f"CSV must contain 'sample_id' and 'condition' columns (found: {list(df.columns)})")

        records = df.to_dict(orient="records")
        # Normalize keys to sample_id and condition
        clean_records = []
        for r in records:
            sid = str(r.get(col_map["sample_id"])).strip()
            cond = str(r.get(col_map["condition"])).strip()
            clean_records.append({"sample_id": sid, "condition": cond})

        updated_proj = pm.assign_sample_metadata(project_id, clean_records)
        return updated_proj.model_dump()
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV sample sheet: {str(e)}")
