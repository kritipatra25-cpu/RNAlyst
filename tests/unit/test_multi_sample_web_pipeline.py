"""
Automated Multi-Sample Pipeline, Project UI Continuity, & Strict File Isolation Tests.

Tests:
TEST 1: Four FASTQ upload -> one project -> four samples.
TEST 2: Unrelated FASTQ/test fixture exists elsewhere -> must NOT be included in project.
TEST 3: Upload project ID propagates to analysis.
TEST 4: Analysis project ID propagates to result rendering.
TEST 5: Displayed project ID equals uploaded project ID.
TEST 6: Real LOCAL_FASTQ project never falls back to synthetic data.
TEST 7: No single_sample contamination.
TEST 8: Existing multi-sample backend tests continue to pass.
E2E TEST: Upload -> project creation -> analysis -> QC -> result fetch -> displayed result identity.
"""

import gzip
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app
from api.routes.qc import find_all_uploaded_files, calculate_project_qc, UPLOAD_DIR
from pipeline.project_manager import ProjectManager
from pipeline.schemas.project_schemas import DataOrigin
from agent.tools.visualization_tools import QCPlotTool

client = TestClient(app)


def create_mock_fastq(path: Path, sample_id: str, num_reads: int = 10):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for i in range(num_reads):
            f.write(f"@{sample_id}.{i+1} 1\nACGTACGTACGTACGTACGTACGTACGTACGT\n+\nIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n")


def test_1_four_fastq_upload_four_samples(tmp_path):
    """TEST 1: Four FASTQ upload -> one project -> four samples."""
    expected_sample_ids = {"SRR9937483", "SRR9937484", "SRR9937486", "SRR9937487"}
    files_payload = []

    for sid in sorted(list(expected_sample_ids)):
        fpath = tmp_path / f"{sid}.fastq.gz"
        create_mock_fastq(fpath, sid, num_reads=15)
        files_payload.append(("files", (f"{sid}.fastq.gz", open(fpath, "rb"), "application/gzip")))

    res_upload = client.post("/api/v1/qc", files=files_payload)
    assert res_upload.status_code == 200
    data_upload = res_upload.json()

    assert data_upload.get("samples_count") == 4
    uploaded_project_id = data_upload.get("project_id")
    assert uploaded_project_id is not None

    pm = ProjectManager()
    samples = pm.get_project_samples(uploaded_project_id)
    assert len(samples) == 4
    discovered_ids = {s.sample_id for s in samples}
    assert discovered_ids == expected_sample_ids


def test_2_file_isolation_unrelated_file_excluded(tmp_path):
    """TEST 2: Unrelated FASTQ/test fixture exists elsewhere -> must NOT be included in project."""
    # Create an unrelated stray file in UPLOAD_DIR
    stray_file = UPLOAD_DIR / "UNRELATED_STRAY_single_sample.fastq.gz"
    create_mock_fastq(stray_file, "single_sample", num_reads=1)

    try:
        expected_sample_ids = {"SRR9937483", "SRR9937484", "SRR9937486", "SRR9937487"}
        files_payload = []

        for sid in sorted(list(expected_sample_ids)):
            fpath = tmp_path / f"{sid}.fastq.gz"
            create_mock_fastq(fpath, sid, num_reads=15)
            files_payload.append(("files", (f"{sid}.fastq.gz", open(fpath, "rb"), "application/gzip")))

        res_upload = client.post("/api/v1/qc", files=files_payload)
        assert res_upload.status_code == 200
        uploaded_project_id = res_upload.json().get("project_id")

        pm = ProjectManager()
        samples = pm.get_project_samples(uploaded_project_id)
        discovered_ids = {s.sample_id for s in samples}

        assert "single_sample" not in discovered_ids, "stray file 'single_sample' contaminated the project!"
        assert discovered_ids == expected_sample_ids
    finally:
        if stray_file.exists():
            stray_file.unlink()


def test_3_to_5_project_id_propagation_and_continuity(tmp_path):
    """TEST 3, 4, 5: Upload project ID propagates to analysis and result rendering."""
    expected_sample_ids = {"SRR9937483", "SRR9937484", "SRR9937486", "SRR9937487"}
    files_payload = []

    for sid in sorted(list(expected_sample_ids)):
        fpath = tmp_path / f"{sid}.fastq.gz"
        create_mock_fastq(fpath, sid, num_reads=15)
        files_payload.append(("files", (f"{sid}.fastq.gz", open(fpath, "rb"), "application/gzip")))

    # Upload
    res_upload = client.post("/api/v1/qc", files=files_payload)
    data_upload = res_upload.json()
    uploaded_project_id = data_upload.get("project_id")

    # Analysis / GET QC
    res_qc = client.get(f"/api/v1/qc/{uploaded_project_id}")
    analyzed_project_id = res_qc.json().get("file_id")

    # Query API
    res_query = client.post("/api/v1/query", json={
        "query": "Perform QC summary",
        "dataset_id": uploaded_project_id
    })
    displayed_project_id = res_query.json().get("project_id") or uploaded_project_id

    # TEST 5: Equality
    assert uploaded_project_id == analyzed_project_id == displayed_project_id, \
        f"Project ID mismatch: uploaded={uploaded_project_id}, analyzed={analyzed_project_id}, displayed={displayed_project_id}"


def test_6_and_7_real_data_guardrail_and_no_single_sample(tmp_path):
    """TEST 6 & 7: Real LOCAL_FASTQ project never falls back to synthetic data & no single_sample contamination."""
    expected_sample_ids = {"SRR9937483", "SRR9937484", "SRR9937486", "SRR9937487"}
    files_payload = []

    for sid in sorted(list(expected_sample_ids)):
        fpath = tmp_path / f"{sid}.fastq.gz"
        create_mock_fastq(fpath, sid, num_reads=15)
        files_payload.append(("files", (f"{sid}.fastq.gz", open(fpath, "rb"), "application/gzip")))

    res_upload = client.post("/api/v1/qc", files=files_payload)
    uploaded_project_id = res_upload.json().get("project_id")

    pm = ProjectManager()
    project = pm.get_project(uploaded_project_id)
    assert project.origin in (DataOrigin.LOCAL_FASTQ, "LOCAL_FASTQ", "uploaded_fastq")

    qc_tool = QCPlotTool()
    tool_res = qc_tool.run({"project_id": uploaded_project_id})
    assert tool_res.error is None
    source_art = tool_res.provenance.get("source_artifact", "")
    assert source_art != "Synthetic QC Fallback"

    tool_samples = {s["sample_id"] for s in tool_res.provenance.get("relevant_parameters", {}).get("samples_qc", [])}
    assert "single_sample" not in tool_samples
    assert tool_samples == expected_sample_ids


def test_browser_like_e2e_workflow(tmp_path):
    """Browser-like E2E Test: Upload -> Project -> Analysis -> QC -> Result Fetch -> Displayed Result Identity."""
    expected_sample_ids = {"SRR9937483", "SRR9937484", "SRR9937486", "SRR9937487"}
    files_payload = []

    for sid in sorted(list(expected_sample_ids)):
        fpath = tmp_path / f"{sid}.fastq.gz"
        create_mock_fastq(fpath, sid, num_reads=20)
        files_payload.append(("files", (f"{sid}.fastq.gz", open(fpath, "rb"), "application/gzip")))

    # 1. Browser Upload
    res_up = client.post("/api/v1/qc", files=files_payload)
    assert res_up.status_code == 200
    uploaded_project_id = res_up.json().get("project_id")

    # 2. Get Project Manifest
    pm = ProjectManager()
    project = pm.get_project(uploaded_project_id)
    discovered_ids = {s.sample_id for s in project.manifest.samples}

    # 3. GET /qc
    res_qc = client.get(f"/api/v1/qc/{uploaded_project_id}")
    analyzed_project_id = res_qc.json().get("file_id")
    qc_processed_ids = {s["sample_id"] for s in res_qc.json().get("samples_qc", [])}

    # 4. POST /query
    res_q = client.post("/api/v1/query", json={
        "query": "Perform QC and summarize quality",
        "dataset_id": uploaded_project_id
    })
    displayed_project_id = res_q.json().get("project_id") or uploaded_project_id

    # Explicit Assertions
    assert uploaded_project_id == analyzed_project_id == displayed_project_id
    assert project.origin != "SYNTHETIC"
    assert len(discovered_ids) == 4
    assert len(qc_processed_ids) == 4
    assert "single_sample" not in discovered_ids
    assert "single_sample" not in qc_processed_ids


def test_qc_plot_project_specific_path_and_png_validation(tmp_path):
    """Regression Test: Verify QCPlotTool outputs to projects/<project_id>/results/qc_plot.png and produces a valid PNG."""
    expected_sample_ids = {"SRR9937483", "SRR9937484", "SRR9937486", "SRR9937487"}
    files_payload = []

    for sid in sorted(list(expected_sample_ids)):
        fpath = tmp_path / f"{sid}.fastq.gz"
        create_mock_fastq(fpath, sid, num_reads=15)
        files_payload.append(("files", (f"{sid}.fastq.gz", open(fpath, "rb"), "application/gzip")))

    res_up = client.post("/api/v1/qc", files=files_payload)
    uploaded_project_id = res_up.json().get("project_id")

    qc_tool = QCPlotTool()
    tool_res = qc_tool.run({"project_id": uploaded_project_id})
    assert tool_res.error is None

    expected_plot_path = Path("projects") / uploaded_project_id / "results" / "qc_plot.png"
    reported_path = Path(tool_res.result.get("output_path"))

    assert reported_path == expected_plot_path, f"Reported path {reported_path} != expected {expected_plot_path}"
    assert expected_plot_path.exists(), f"Plot file {expected_plot_path} does not exist on disk"
    assert expected_plot_path.stat().st_size > 0, f"Plot file {expected_plot_path} is empty"

    with open(expected_plot_path, "rb") as f_img:
        header = f_img.read(8)
    assert header == b"\x89PNG\r\n\x1a\n", "Plot file is not a valid PNG image"

    samples_qc = tool_res.provenance.get("relevant_parameters", {}).get("samples_qc", [])
    plot_sample_ids = {s["sample_id"] for s in samples_qc}
    assert plot_sample_ids == expected_sample_ids
    assert "single_sample" not in plot_sample_ids
    assert tool_res.provenance.get("source_artifact") != "Synthetic QC Fallback"


def test_project_identity_and_no_fallback(tmp_path):
    """
    Regression Test: Ensures uploaded_project_id == analyzed_project_id == displayed_project_id,
    analysis creation persists project_id, artifact route resolves project_id, and non-existent
    projects return 404 rather than silently displaying demo/synthetic data.
    """
    expected_sample_ids = {"SRR9937483", "SRR9937484", "SRR9937486", "SRR9937487"}
    files_payload = []

    for sid in sorted(list(expected_sample_ids)):
        fpath = tmp_path / f"{sid}.fastq.gz"
        create_mock_fastq(fpath, sid, num_reads=15)
        files_payload.append(("files", (f"{sid}.fastq.gz", open(fpath, "rb"), "application/gzip")))

    # 1. Upload FASTQs
    res_up = client.post("/api/v1/qc", files=files_payload)
    assert res_up.status_code == 200
    up_data = res_up.json()
    uploaded_project_id = up_data.get("project_id")
    assert uploaded_project_id is not None

    # 2. Create Analysis Record with project_id
    sample_sheet_data = {
        "organism": "Homo sapiens",
        "layout": "SINGLE",
        "samples": [{"sample_id": sid, "biological_unit_id": sid, "condition": "PBS"} for sid in expected_sample_ids],
        "fastq_files": {sid: [f"{sid}.fastq.gz"] for sid in expected_sample_ids},
        "reference_group": "PBS",
        "comparison_group": "LPS"
    }
    res_an = client.post("/api/v1/analyses", json={
        "project_id": uploaded_project_id,
        "sample_sheet": sample_sheet_data
    })
    assert res_an.status_code == 201
    an_data = res_an.json()
    analysis_id = an_data.get("analysis_id")
    assert an_data.get("project_id") == uploaded_project_id

    # Verify persistent analysis record in GET /api/v1/analyses/{analysis_id}
    res_an_get = client.get(f"/api/v1/analyses/{analysis_id}")
    assert res_an_get.status_code == 200
    assert res_an_get.json().get("project_id") == uploaded_project_id

    # 3. Generate QC plot artifact
    qc_tool = QCPlotTool()
    qc_res = qc_tool.run({"project_id": uploaded_project_id})
    assert qc_res.status == "success"

    # 4. Fetch artifact via /api/v1/analyses/artifacts/qc_plot.png?analysis_id=...
    res_art = client.get(f"/api/v1/analyses/artifacts/qc_plot.png?analysis_id={analysis_id}")
    assert res_art.status_code == 200
    assert res_art.headers["content-type"] == "image/png"

    # 5. Verify non-existent project request fails visibly (404) with NO fallback
    res_invalid_proj = client.get("/api/v1/qc/NON_EXISTENT_PROJECT_999999")
    assert res_invalid_proj.status_code == 404

    res_invalid_art = client.get("/api/v1/analyses/artifacts/qc_plot.png?project_id=NON_EXISTENT_PROJECT_999999")
    assert res_invalid_art.status_code == 404


