"""API Router for creating and inspecting RNA-seq analyses."""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from pipeline.schemas.input_schemas import SampleSheetInput
from provenance.schemas import ProvenanceManifest
from scientific_guardrails.validators import run_pre_analysis_guardrails, ScientificGuardrailError

router = APIRouter()

ANALYSES_DB_PATH = Path("data/analyses_db.json")


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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_analysis(sample_sheet: SampleSheetInput):
    """Creates and submits a new RNA-seq analysis job after guardrail validation."""
    try:
        status, warnings = run_pre_analysis_guardrails(sample_sheet)
    except ScientificGuardrailError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db = _load_analyses_db()
    analysis_id = f"analysis_{len(db) + 1:04d}"
    analysis_record = {
        "analysis_id": analysis_id,
        "sample_sheet": sample_sheet.model_dump(),
        "status": "QUEUED",
        "validity_status": status,
        "warnings": warnings,
    }
    db[analysis_id] = analysis_record
    _save_analyses_db(db)

    return {
        "analysis_id": analysis_id,
        "status": "QUEUED",
        "validity_status": status,
        "warnings": warnings,
        "message": "Analysis successfully created and queued."
    }


@router.get("/{analysis_id}")
def get_analysis_status(analysis_id: str):
    db = _load_analyses_db()
    if analysis_id not in db:
        raise HTTPException(status_code=404, detail="Analysis ID not found.")
    return db[analysis_id]
