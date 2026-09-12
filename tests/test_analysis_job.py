import os
import sys
import io
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from pipeline.job_models import AnalysisJob, JobStatus, StepStatus, ArtifactType
from pipeline.orchestrator import AnalysisOrchestrator
from api.routes.ingestion import upload_file
from fastapi import UploadFile, HTTPException


class TestAnalysisJobOrchestration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.orchestrator = AnalysisOrchestrator()
        
        fastq_text = "@READ_1\nGATCGATCGATC\n+\nIIIIIIIIIIII\n@READ_2\nATCGATCGATCG\n+\nIIIIIIIIIIII\n"
        mock_file = UploadFile(
            filename="test_job_fixture.fastq",
            file=io.BytesIO(fastq_text.encode("utf-8"))
        )
        
        import asyncio
        up_res = asyncio.run(upload_file(mock_file))
        self.file_id = up_res["file_id"]
        self.filename = up_res["filename"]

    def test_1_create_analysis_job(self):
        """Test creating an AnalysisJob via API."""
        payload = {
            "file_id": self.file_id,
            "user_question": "What is the GC content of this FASTQ file?",
            "organism": "Arabidopsis thaliana",
            "plan": ["validating_dataset", "qc"]
        }
        res = self.client.post("/analyses", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("analysis_id", data)
        self.assertEqual(data["file_id"], self.file_id)
        self.assertEqual(data["status"], "queued")
        self.assertEqual(len(data["steps"]), 2)
        self.assertEqual(data["steps"][0]["status"], "pending")

    def test_2_retrieve_analysis_job(self):
        """Test retrieving an AnalysisJob via API."""
        job = self.orchestrator.create_job(file_id=self.file_id, plan=["qc"])
        res = self.client.get(f"/analyses/{job.analysis_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["analysis_id"], job.analysis_id)
        self.assertEqual(data["file_id"], self.file_id)

    def test_3_initial_status(self):
        """Test correct initial status of newly created job."""
        job = self.orchestrator.create_job(file_id=self.file_id)
        self.assertEqual(job.status, JobStatus.QUEUED)
        self.assertIsNone(job.current_step)
        self.assertEqual(len(job.artifacts), 0)

    def test_4_run_qc_step_orchestration(self):
        """Test running QC step through the orchestration layer."""
        job = self.orchestrator.create_job(file_id=self.file_id, plan=["validating_dataset", "qc"])
        updated_job = self.orchestrator.execute_job(job.analysis_id)
        
        self.assertEqual(updated_job.status, JobStatus.COMPLETED)
        self.assertIsNone(updated_job.current_step)
        self.assertEqual(len(updated_job.steps), 2)
        self.assertEqual(updated_job.steps[0].status, StepStatus.COMPLETED)
        self.assertEqual(updated_job.steps[1].status, StepStatus.COMPLETED)

    def test_5_successful_step_state_transition(self):
        """Test step state transitions during orchestration."""
        job = self.orchestrator.create_job(file_id=self.file_id, plan=["qc"])
        self.assertEqual(job.steps[0].status, StepStatus.PENDING)
        
        updated_job = self.orchestrator.execute_job(job.analysis_id)
        self.assertEqual(updated_job.steps[0].status, StepStatus.COMPLETED)
        self.assertIsNotNone(updated_job.steps[0].started_at)
        self.assertIsNotNone(updated_job.steps[0].completed_at)

    def test_6_failed_step_state_transition_for_unsupported_step(self):
        """Test that requesting an unimplemented step yields explicit failed state."""
        job = self.orchestrator.create_job(file_id=self.file_id, plan=["qc", "unimplemented_step"])
        updated_job = self.orchestrator.execute_job(job.analysis_id)
        
        self.assertEqual(updated_job.status, JobStatus.FAILED)
        self.assertEqual(updated_job.steps[0].status, StepStatus.COMPLETED)
        self.assertEqual(updated_job.steps[1].status, StepStatus.FAILED)
        self.assertIn("is currently not implemented", updated_job.steps[1].message)

    def test_7_artifact_registration(self):
        """Test artifact registration when running job."""
        job = self.orchestrator.create_job(file_id=self.file_id, plan=["qc"])
        updated_job = self.orchestrator.execute_job(job.analysis_id)
        
        self.assertGreaterEqual(len(updated_job.artifacts), 1)
        art = updated_job.artifacts[0]
        self.assertEqual(art.type, ArtifactType.QC_SUMMARY)
        self.assertTrue(os.path.exists(art.path))

    def test_8_invalid_file_id_handling(self):
        """Test error handling when creating job with non-existent file_id."""
        invalid_id = "00000000-0000-0000-0000-000000000000"
        res = self.client.post("/analyses", json={"file_id": invalid_id})
        self.assertEqual(res.status_code, 404)
        self.assertIn("Uploaded file '00000000-0000-0000-0000-000000000000' not found", res.json()["detail"])

    def test_9_existing_qc_endpoint_working(self):
        """Test existing GET /qc/{file_id} endpoint remains fully functional."""
        res = self.client.get(f"/qc/{self.file_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["qc"]["total_reads"], 2)

    def test_10_existing_ingestion_upload_working(self):
        """Test existing POST /ingestion/upload endpoint remains fully functional."""
        fastq_text = "@READ_1\nACGT\n+\nIIII\n"
        res = self.client.post(
            "/ingestion/upload",
            files={"file": ("test_ingest.fastq", io.BytesIO(fastq_text.encode("utf-8")), "application/octet-stream")}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("file_id", data)
        self.assertEqual(data["filename"], "test_ingest.fastq")


if __name__ == "__main__":
    unittest.main()
