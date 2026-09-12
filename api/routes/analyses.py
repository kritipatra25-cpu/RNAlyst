"""API Router for creating and inspecting RNA-seq analyses."""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status, Query, Body
from fastapi.responses import FileResponse
from pipeline.schemas.input_schemas import SampleSheetInput
from provenance.schemas import ProvenanceManifest
from scientific_guardrails.validators import run_pre_analysis_guardrails, ScientificGuardrailError

router = APIRouter()

ANALYSES_DB_PATH = Path("data/analyses_db.json")


class CreateAnalysisRequest(BaseModel):
    project_id: Optional[str] = Field(None, description="Associated dataset or project identifier")
    sample_sheet: SampleSheetInput


def _load_analyses_db() -> Dict[str, Dict[str, Any]]:
    if not ANALYSES_DB_PATH.exists():
        return {}
    try:
        with open(ANALYSES_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning("Failed to load analyses DB from %s: %s", ANALYSES_DB_PATH, e)
        return {}


def _save_analyses_db(db: Dict[str, Dict[str, Any]]) -> None:
    try:
        ANALYSES_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ANALYSES_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        logging.error("Failed to save analyses DB to %s: %s", ANALYSES_DB_PATH, e)


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
def list_analyses():
    """Lists all created analyses from the canonical analysis store."""
    db = _load_analyses_db()
    analyses_list = list(db.values())
    return {"analyses": analyses_list, "total": len(analyses_list)}


from pipeline.schemas.input_schemas import SampleSheetInput, SampleMetadata, LayoutType

def _parse_sample_sheet(data: Dict[str, Any]) -> SampleSheetInput:
    ss_dict = dict(data)
    if "samples" in ss_dict and isinstance(ss_dict["samples"], list):
        clean_samples = []
        for s in ss_dict["samples"]:
            if isinstance(s, dict):
                s_copy = dict(s)
                if "biological_unit_id" not in s_copy:
                    s_copy["biological_unit_id"] = s_copy.get("sample_id", "sample_1")
                clean_samples.append(SampleMetadata(**s_copy))
            else:
                clean_samples.append(s)
        ss_dict["samples"] = clean_samples

    valid_fields = {
        "organism": ss_dict.get("organism", "Homo sapiens"),
        "layout": LayoutType(ss_dict.get("layout", LayoutType.SINGLE)),
        "samples": ss_dict.get("samples", []),
        "fastq_files": ss_dict.get("fastq_files", {}),
        "reference_group": ss_dict.get("reference_group", ss_dict.get("reference_level", "PBS")),
        "comparison_group": ss_dict.get("comparison_group", ss_dict.get("numerator_level", "LPS")),
        "design_formula": ss_dict.get("design_formula", "~ condition")
    }
    return SampleSheetInput(**valid_fields)

@router.post("", status_code=status.HTTP_201_CREATED)
def create_analysis(payload: Dict[str, Any] = Body(...)):
    """Creates and submits a new RNA-seq analysis job with explicit project_id identity tracking."""
    if isinstance(payload, dict) and "file_id" in payload:
        file_id = payload["file_id"]
        from api.routes.qc import find_all_uploaded_files
        all_files = find_all_uploaded_files(file_id)
        if not all_files:
            raise HTTPException(status_code=404, detail=f"Uploaded file '{file_id}' not found.")
        from pipeline.orchestrator import AnalysisOrchestrator
        orchestrator = AnalysisOrchestrator()
        job = orchestrator.create_job(
            file_id=file_id,
            user_question=payload.get("user_question"),
            organism=payload.get("organism"),
            plan=payload.get("plan")
        )
        return job.model_dump() if hasattr(job, "model_dump") else job.dict()

    project_id = None
    sample_sheet = None

    if isinstance(payload, dict):
        project_id = payload.get("project_id")
        if "sample_sheet" in payload and isinstance(payload["sample_sheet"], dict):
            sample_sheet = _parse_sample_sheet(payload["sample_sheet"])
        elif "organism" in payload:
            sample_sheet = _parse_sample_sheet(payload)
    elif hasattr(payload, "sample_sheet"):
        project_id = getattr(payload, "project_id", None)
        sample_sheet = payload.sample_sheet
    elif isinstance(payload, SampleSheetInput):
        sample_sheet = payload

    if not sample_sheet:
        raise HTTPException(status_code=400, detail="Invalid sample sheet input.")

    if not project_id and hasattr(sample_sheet, "project_id"):
        project_id = getattr(sample_sheet, "project_id")

    try:
        status, warnings = run_pre_analysis_guardrails(sample_sheet)
    except ScientificGuardrailError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db = _load_analyses_db()
    analysis_id = f"analysis_{len(db) + 1:04d}"
    analysis_record = {
        "analysis_id": analysis_id,
        "project_id": project_id,
        "sample_sheet": sample_sheet.model_dump() if hasattr(sample_sheet, "model_dump") else str(sample_sheet),
        "status": "QUEUED",
        "validity_status": status,
        "warnings": warnings,
    }
    db[analysis_id] = analysis_record
    _save_analyses_db(db)

    return {
        "analysis_id": analysis_id,
        "project_id": project_id,
        "status": "QUEUED",
        "validity_status": status,
        "warnings": warnings,
        "message": "Analysis successfully created and queued."
    }


@router.get("/artifacts/{filename}")
def get_analysis_artifact_by_name(
    filename: str,
    analysis_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    """
    Serves project-specific analysis artifacts (plots, figures, tables).
    Strictly resolves project_id and validates file existence. Returns 404 on missing artifact (NO fallback!).
    """
    clean_name = Path(filename).name
    target_project_id = project_id

    if not target_project_id and analysis_id:
        db = _load_analyses_db()
        rec = db.get(analysis_id)
        if rec:
            target_project_id = rec.get("project_id")

    search_paths = []
    if target_project_id:
        search_paths.append(Path("projects") / target_project_id / "results" / clean_name)
        search_paths.append(Path("projects") / target_project_id / "data" / clean_name)
    else:
        # If no project_id specified, check general results directory
        search_paths.append(Path("results") / clean_name)

    found_path = None
    for p in search_paths:
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            found_path = p
            break

    if not found_path:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact '{clean_name}' not found for project '{target_project_id or 'UNKNOWN'}'. No synthetic fallback permitted."
        )

    media_type = "image/png" if clean_name.lower().endswith(".png") else "application/octet-stream"
    return FileResponse(path=str(found_path), media_type=media_type)


@router.get("/{analysis_id}")
def get_analysis_status(analysis_id: str):
    db = _load_analyses_db()
    if analysis_id in db:
        return db[analysis_id]

    from pipeline.orchestrator import AnalysisOrchestrator
    orchestrator = AnalysisOrchestrator()
    job = orchestrator.get_job(analysis_id)
    if job:
        return job.model_dump() if hasattr(job, "model_dump") else job.dict()

    raise HTTPException(status_code=404, detail="Analysis ID not found.")


@router.get("/{analysis_id}/artifacts/{filename}")
def get_analysis_artifact(analysis_id: str, filename: str):
    """Serves analysis artifacts tied explicitly to analysis_id."""
    return get_analysis_artifact_by_name(filename=filename, analysis_id=analysis_id)
