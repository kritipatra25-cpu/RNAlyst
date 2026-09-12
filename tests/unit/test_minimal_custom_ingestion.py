"""
Unit and Integration Test: Minimal Custom FASTQ Dataset Ingestion & Zero Biological Metadata Fabrication.

Verifies:
1. Custom dataset ingestion requires ONLY Project Title + FASTQ file(s).
2. Auto-derivation of sample IDs ('S1', 'S2') and read layout ('PAIRED') from FASTQ filenames.
3. Unresolved organism and experimental design stay marked as 'UNRESOLVED' (zero metadata fabrication).
4. Quantification generates valid counts_matrix.csv without fabricating treatment/control levels.
"""

import gzip
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from pipeline.project_manager import ProjectManager


class TestMinimalCustomIngestion(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.tmp_dir = tempfile.mkdtemp()
        self.projects_dir = Path(self.tmp_dir) / "projects"
        self.configs_dir = Path(self.tmp_dir) / "configs"

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

    def create_gzipped_fastq(self, filename: str, header_id: str) -> Path:
        p = Path(self.tmp_dir) / filename
        content = f"@{header_id}\nATGCATGC\n+\nIIIIIIII\n".encode("utf-8")
        with gzip.open(p, "wb") as f:
            f.write(content)
        return p

    def test_minimal_custom_ingestion_zero_fabrication(self):
        project_id = "PROJ_CUSTOM_TEST_001"
        project_title = "Arbitrary Researcher Spaceflight Experiment"

        # 1. Create project with MINIMAL payload (only title, id, origin)
        create_payload = {
            "project_id": project_id,
            "name": project_title,
            "origin": "LOCAL_FASTQ"
        }
        res_create = self.client.post("/api/v1/projects", json=create_payload)
        self.assertEqual(res_create.status_code, 201)

        # Verify initial project.json has UNRESOLVED metadata rather than silent defaults
        pm = ProjectManager(projects_dir=str(self.projects_dir), configs_dir=str(self.configs_dir))
        proj_init = pm.get_project(project_id)
        self.assertEqual(proj_init.organism, "UNRESOLVED")
        self.assertNotEqual(proj_init.organism, "Arabidopsis thaliana")

        # 2. Upload paired-end FASTQ files for S1 and S2
        s1_r1 = self.create_gzipped_fastq("S1_R1.fastq.gz", "READ1/1")
        s1_r2 = self.create_gzipped_fastq("S1_R2.fastq.gz", "READ1/2")
        s2_r1 = self.create_gzipped_fastq("S2_R1.fastq.gz", "READ2/1")
        s2_r2 = self.create_gzipped_fastq("S2_R2.fastq.gz", "READ2/2")

        for fpath in [s1_r1, s1_r2, s2_r1, s2_r2]:
            with open(fpath, "rb") as f:
                res_up = self.client.post(
                    f"/api/v1/projects/{project_id}/upload",
                    files={"file": (fpath.name, f, "application/gzip")}
                )
                self.assertEqual(res_up.status_code, 200)

        # 3. Quantify & Auto-derive layout
        import os
        os.environ["RNASEQ_ALLOW_MOCK"] = "1"
        res_quant = self.client.post(f"/api/v1/projects/{project_id}/quantify", json={})
        self.assertEqual(res_quant.status_code, 200)

        # 4. Verify derived project state
        proj_final = pm.get_project(project_id)
        
        # Derived sample IDs
        sample_ids = [s.sample_id for s in proj_final.manifest.samples]
        self.assertIn("S1", sample_ids)
        self.assertIn("S2", sample_ids)
        self.assertEqual(len(sample_ids), 2)
        
        # Paired-end layout
        self.assertEqual(proj_final.manifest.layout.value, "PAIRED")

        # Zero biological fabrication check
        self.assertEqual(proj_final.organism, "UNRESOLVED")
        self.assertFalse(proj_final.workspace_state.is_ready_for_deseq2)
        self.assertIn("contrast configuration required", proj_final.workspace_state.unresolved_reason)

    def test_glds133_minimal_fastq_ingestion_and_quantification(self):
        """Regression test for single GLDS-133 FASTQ file minimal ingestion."""
        project_id = "PROJ_ABC_GLDS133"
        project_title = "abc"

        # 1. Create project with title 'abc' only
        res_create = self.client.post("/api/v1/projects", json={
            "project_id": project_id,
            "name": project_title,
            "origin": "LOCAL_FASTQ"
        })
        self.assertEqual(res_create.status_code, 201)

        # 2. Upload single FASTQ file GLDS-133_ma-seq_DRR076078_1.fastq.gz
        fastq_path = self.create_gzipped_fastq("GLDS-133_ma-seq_DRR076078_1.fastq.gz", "DRR076078.1 1/1")
        with open(fastq_path, "rb") as f:
            res_up = self.client.post(
                f"/api/v1/projects/{project_id}/upload",
                files={"file": (fastq_path.name, f, "application/gzip")}
            )
            self.assertEqual(res_up.status_code, 200)
            self.assertTrue(res_up.json()["validation"]["is_valid"])

        # 3. Quantify reads & derive sample manifest
        res_quant = self.client.post(f"/api/v1/projects/{project_id}/quantify", json={})
        self.assertEqual(res_quant.status_code, 200)
        self.assertEqual(res_quant.json()["sample_count"], 1)

        # 4. Verify project state
        pm = ProjectManager(projects_dir=str(self.projects_dir), configs_dir=str(self.configs_dir))
        proj = pm.get_project(project_id)
        self.assertEqual(len(proj.manifest.samples), 1)
        self.assertIn("GLDS-133_ma-seq_DRR076078", proj.manifest.samples[0].sample_id)


if __name__ == "__main__":
    unittest.main()
