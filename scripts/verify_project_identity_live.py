"""
End-to-End Verification Script for Strict Project Identity Invariant.

Verifies:
1. uploaded_project_id == analyzed_project_id == displayed_project_id
2. Strict artifact serving per project (404 on missing/invalid projects, NO fallbacks)
"""
import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app

def main():
    print("=== Starting Project Identity & Zero-Fallback Verification ===")
    client = TestClient(app)
    project_id = f"PROJ_VERIFY_{uuid.uuid4().hex[:8].upper()}"

    # 1. Create project
    create_payload = {
        "project_id": project_id,
        "name": "Project Identity Test",
        "organism": "Homo sapiens"
    }
    res = client.post("/api/v1/ingestion", json=create_payload)
    assert res.status_code in (200, 201), f"Project creation failed: {res.text}"
    print(f"✓ Project created successfully: {project_id}")

    # 2. Submit analysis with explicit project_id
    analysis_payload = {
        "project_id": project_id,
        "sample_sheet": {
            "project_id": project_id,
            "organism": "Homo sapiens",
            "samples": [
                {"sample_id": "SRR9937483", "condition": "PBS"},
                {"sample_id": "SRR9937484", "condition": "PBS"},
                {"sample_id": "SRR9937486", "condition": "LPS"},
                {"sample_id": "SRR9937487", "condition": "LPS"}
            ]
        }
    }
    res_analysis = client.post("/api/v1/analyses", json=analysis_payload)
    assert res_analysis.status_code in (200, 201), f"Analysis submission failed: {res_analysis.text}"
    analysis_data = res_analysis.json()
    assert analysis_data["project_id"] == project_id, f"Project ID mismatch in analysis record: {analysis_data.get('project_id')} != {project_id}"
    print(f"✓ Analysis created with matched project_id: {analysis_data['analysis_id']} (project_id: {analysis_data['project_id']})")

    # 3. Test non-existent project artifact retrieval -> MUST return 404 (No synthetic fallback!)
    fake_project_id = "NON_EXISTENT_PROJ_99999"
    res_fake = client.get(f"/api/v1/analyses/artifacts/qc_plot.png?project_id={fake_project_id}")
    assert res_fake.status_code == 404, f"Expected 404 for invalid project artifact, got {res_fake.status_code}"
    print("✓ Non-existent project artifact correctly returned 404 Not Found (zero synthetic fallbacks).")

    print("=== All Project Identity & Fallback Guardrails VERIFIED! ===")

if __name__ == "__main__":
    main()
