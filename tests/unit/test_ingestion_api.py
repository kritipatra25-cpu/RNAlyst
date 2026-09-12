"""
End-to-End API Integration Test: Arbitrary Dataset Ingestion to Agentic Analysis.

Proves complete execution path:
FastAPI REST Upload -> Sandbox -> FASTQ Validation -> Nextflow/Salmon Quantification ->
tximport / Count Matrix Generation -> PyDESeq2 DE Engine -> Agentic Query Synthesis (/api/v1/query).
"""

import os
import gzip
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from pipeline.project_manager import ProjectManager


class TestIngestionAPIWorkflow(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.tmp_dir = tempfile.mkdtemp()
        self.projects_dir = Path(self.tmp_dir) / "projects"
        self.configs_dir = Path(self.tmp_dir) / "configs"

        # Patch ProjectManager directories for isolated testing
        def mock_init(self_pm, projects_dir=None, configs_dir=None):
            self_pm.projects_dir = Path(self.projects_dir)
            self_pm.configs_dir = Path(self.configs_dir)
            self_pm.projects_dir.mkdir(parents=True, exist_ok=True)
            self_pm.configs_dir.mkdir(parents=True, exist_ok=True)

        self.pm_patcher = patch("pipeline.project_manager.ProjectManager.__init__", mock_init)
        self.pm_patcher.start()

    def tearDown(self):
        self.pm_patcher.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def create_mock_fastq_pair(self, sample_id: str) -> tuple:
        """Create valid gzipped FASTQ file pair for sample."""
        r1_path = Path(self.tmp_dir) / f"{sample_id}_R1.fastq.gz"
        r2_path = Path(self.tmp_dir) / f"{sample_id}_R2.fastq.gz"

        r1_content = f"@{sample_id}_READ1/1\nATGCATGCATGC\n+\nIIIIIIIIIIII\n".encode("utf-8")
        r2_content = f"@{sample_id}_READ1/2\nTACGTACGTACG\n+\nIIIIIIIIIIII\n".encode("utf-8")

        with gzip.open(r1_path, "wb") as f1, gzip.open(r2_path, "wb") as f2:
            f1.write(r1_content)
            f2.write(r2_content)

        return r1_path, r2_path

    def test_e2e_arbitrary_dataset_ingestion_to_query(self):
        """Execute end-to-end workflow starting from REST API endpoints down to agent query synthesis."""
        project_id = "E2E_RESEARCH_STUDY_2026"
        sample_ids = ["S1", "S2", "S3", "S4", "S5", "S6"]
        conditions = ["Spaceflight", "Spaceflight", "Spaceflight", "Ground", "Ground", "Ground"]

        # STEP 1: POST /api/v1/projects (Create Project)
        create_payload = {
            "project_id": project_id,
            "name": "Arbitrary E2E Spaceflight Study 2026",
            "origin": "LOCAL_FASTQ",
            "organism": "Arabidopsis thaliana",
            "condition_column": "treatment",
            "sample_ids": sample_ids,
            "conditions": conditions,
            "numerator_level": "Spaceflight",
            "reference_level": "Ground"
        }
        res_create = self.client.post("/api/v1/projects", json=create_payload)
        self.assertEqual(res_create.status_code, 201)
        res_create_json = res_create.json()
        self.assertEqual(res_create_json["project_id"], project_id)

        # STEP 2: POST /api/v1/projects/{project_id}/upload (Upload & Validate FASTQ Files)
        r1_file, r2_file = self.create_mock_fastq_pair("S1")
        with open(r1_file, "rb") as f1, open(r2_file, "rb") as f2:
            files = {
                "file": ("S1_R1.fastq.gz", f1, "application/gzip"),
                "paired_file": ("S1_R2.fastq.gz", f2, "application/gzip")
            }
            data = {"sample_id": "S1"}
            res_upload = self.client.post(f"/api/v1/projects/{project_id}/upload", files=files, data=data)

        self.assertEqual(res_upload.status_code, 200)
        res_upload_json = res_upload.json()
        self.assertTrue(res_upload_json["validation"]["is_valid"])

        # STEP 3: POST /api/v1/projects/{project_id}/quantify (Quantify Reads & Build Count Matrix)
        res_quant = self.client.post(f"/api/v1/projects/{project_id}/quantify", json={})
        self.assertEqual(res_quant.status_code, 200)
        res_quant_json = res_quant.json()
        self.assertTrue(Path(res_quant_json["counts_matrix_path"]).exists())
        self.assertEqual(res_quant_json["sample_count"], 6)

        # STEP 4: POST /api/v1/query (Agentic Analysis & Report Synthesis)
        query_payload = {
            "query": f"Execute differential expression analysis for dataset {project_id}.",
            "dataset_id": project_id
        }
        res_query = self.client.post("/api/v1/query", json=query_payload)
        self.assertEqual(res_query.status_code, 200)
        res_query_json = res_query.json()

        self.assertTrue(res_query_json["success"])


        self.assertIsNotNone(res_query_json["message"])


if __name__ == "__main__":
    unittest.main()
