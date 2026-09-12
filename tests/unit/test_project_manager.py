"""
Unit tests for Canonical Data Model & ProjectManager (Step 1).
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.schemas.project_schemas import (
    Project,
    SampleManifest,
    ExperimentalDesign,
    Reference,
    DataOrigin,
    LayoutType,
    Sample,
    ContrastSpec,
    Artifact,
    Provenance
)
from pipeline.project_manager import ProjectManager
from pipeline.backend_api import RNASeqBackendAPI


class TestProjectManager(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.projects_dir = Path(self.tmp_dir) / "projects"
        self.configs_dir = Path(self.tmp_dir) / "configs"

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_project_schemas_valid(self):
        """Verify Pydantic models instantiate and validate correctly."""
        sample1 = Sample(sample_id="S1", condition="Flight", fastq_r1_path="/tmp/s1_1.fq.gz")
        sample2 = Sample(sample_id="S2", condition="Ground", fastq_r1_path="/tmp/s2_1.fq.gz")

        manifest = SampleManifest(
            samples=[sample1, sample2],
            layout=LayoutType.SINGLE,
            organism="Arabidopsis thaliana",
            condition_column="condition",
            total_samples=2,
            min_replicates_per_group=1,
            replicate_status="EXPLORATORY"
        )

        contrast = ContrastSpec(
            id="Flight_vs_Ground",
            factor="condition",
            numerator="Flight",
            denominator="Ground",
            description="Flight vs Ground"
        )

        design = ExperimentalDesign(
            design_formula="~ condition",
            factors={"condition": ["Flight", "Ground"]},
            reference_levels={"condition": "Ground"},
            contrasts=[contrast]
        )

        proj = Project(
            project_id="PROJ_TEST_1",
            name="Test Project 1",
            origin=DataOrigin.LOCAL_FASTQ,
            organism="Arabidopsis thaliana",
            manifest=manifest,
            design=design
        )

        self.assertEqual(proj.project_id, "PROJ_TEST_1")
        self.assertEqual(len(proj.manifest.samples), 2)
        self.assertEqual(proj.manifest.samples[0].sample_id, "S1")

    def test_project_manager_creation_and_yaml(self):
        """Test ProjectManager project creation, JSON state persistence, and YAML generation."""
        pm = ProjectManager(projects_dir=str(self.projects_dir), configs_dir=str(self.configs_dir))

        sample1 = Sample(sample_id="S1", condition="Flight")
        sample2 = Sample(sample_id="S2", condition="Flight")
        sample3 = Sample(sample_id="S3", condition="Flight")
        sample4 = Sample(sample_id="S4", condition="Ground")
        sample5 = Sample(sample_id="S5", condition="Ground")
        sample6 = Sample(sample_id="S6", condition="Ground")

        manifest = SampleManifest(
            samples=[sample1, sample2, sample3, sample4, sample5, sample6],
            layout=LayoutType.PAIRED,
            organism="Mus musculus",
            condition_column="condition",
            total_samples=6,
            min_replicates_per_group=3,
            replicate_status="INFERENTIAL"
        )

        contrast = ContrastSpec(
            id="Flight_vs_Ground",
            factor="condition",
            numerator="Flight",
            denominator="Ground",
            description="Flight vs Ground Control"
        )

        design = ExperimentalDesign(
            design_formula="~ condition",
            factors={"condition": ["Flight", "Ground"]},
            reference_levels={"condition": "Ground"},
            contrasts=[contrast]
        )

        project = pm.create_project(
            project_id="MY_USER_PROJECT",
            name="Arbitrary Researcher Project",
            origin=DataOrigin.LOCAL_FASTQ,
            organism="Mus musculus",
            manifest=manifest,
            design=design
        )

        self.assertEqual(project.project_id, "MY_USER_PROJECT")
        json_file = self.projects_dir / "MY_USER_PROJECT" / "project.json"
        self.assertTrue(json_file.exists())

        # Load back project
        loaded_proj = pm.get_project("MY_USER_PROJECT")
        self.assertEqual(loaded_proj.name, "Arbitrary Researcher Project")
        self.assertEqual(len(loaded_proj.manifest.samples), 6)

        # Verify YAML generated
        yaml_file = self.configs_dir / "my_user_project.yaml"
        self.assertTrue(yaml_file.exists())

        # Verify RNASeqBackendAPI can discover generated YAML
        api = RNASeqBackendAPI(configs_dir=str(self.configs_dir))
        datasets = api.list_available_datasets()
        dataset_ids = [d.dataset_id for d in datasets]
        self.assertIn("MY_USER_PROJECT", dataset_ids)


if __name__ == "__main__":
    unittest.main()

