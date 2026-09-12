import os
import sys
import unittest
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.planner import AnalysisPlanner
from pipeline.orchestrator import AnalysisOrchestrator
from pipeline.job_models import JobStatus, StepStatus


class TestAnalysisPlanner(unittest.TestCase):

    def setUp(self):
        self.uploads_dir = PROJECT_ROOT / "data" / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.planner = AnalysisPlanner(uploads_dir=self.uploads_dir)
        self.orchestrator = AnalysisOrchestrator(uploads_dir=self.uploads_dir)

    def test_1_intent_parsing_differential_expression(self):
        """Test question intent parser maps DE query to DE intent and steps."""
        q = "Compare treated vs control and find significantly different genes."
        intent, goal, steps = self.planner.parse_question_intent(q)

        self.assertIn("DIFFERENTIAL_EXPRESSION", intent)
        self.assertIn("differential_expression", steps)
        self.assertIn("pca", steps)

    def test_2_intent_parsing_qc(self):
        """Test question intent parser maps QC query to QC intent and steps."""
        q = "Run quality control and check Phred scores on raw FASTQ"
        intent, goal, steps = self.planner.parse_question_intent(q)

        self.assertIn("QC", intent)
        self.assertIn("validating_dataset", steps)

    def test_3_input_validation_missing_metadata_fails(self):
        """Test planner rejects DE request when sample metadata is missing."""
        file_id = "test_planner_missing_meta"
        counts_path = self.uploads_dir / f"{file_id}_counts.csv"
        pd.DataFrame({"gene_id": ["G1"], "S1": [10]}).to_csv(counts_path, index=False)

        plan = self.planner.create_analysis_plan(
            file_id=file_id,
            user_question="Perform differential expression analysis"
        )

        self.assertFalse(plan.is_valid)
        self.assertGreaterEqual(len(plan.validation_errors), 1)
        self.assertTrue(any("sample metadata" in err for err in plan.validation_errors))

    def test_4_input_validation_valid_dataset_succeeds(self):
        """Test planner approves DE request when count matrix and metadata exist."""
        file_id = "test_planner_valid_de"
        counts_path = self.uploads_dir / f"{file_id}_counts.csv"
        meta_path = self.uploads_dir / f"{file_id}_metadata.csv"

        pd.DataFrame({
            "gene_id": ["G1", "G2"],
            "C1": [10, 20], "C2": [12, 22],
            "T1": [100, 200], "T2": [110, 210]
        }).to_csv(counts_path, index=False)

        pd.DataFrame({
            "sample": ["C1", "C2", "T1", "T2"],
            "condition": ["Control", "Control", "Treated", "Treated"]
        }).to_csv(meta_path, index=False)

        plan = self.planner.create_analysis_plan(
            file_id=file_id,
            user_question="Compare treated vs control and find significant genes"
        )

        self.assertTrue(plan.is_valid)
        self.assertEqual(len(plan.validation_errors), 0)
        self.assertGreaterEqual(len(plan.step_rationales), 2)
        self.assertGreaterEqual(len(plan.expected_artifacts), 4)

    def test_5_orchestrator_integration_populates_structured_plan(self):
        """Test AnalysisOrchestrator create_job populates job.structured_plan."""
        file_id = "test_planner_valid_de"
        job = self.orchestrator.create_job(
            file_id=file_id,
            user_question="Perform PCA and Differential Expression"
        )

        self.assertIsNotNone(job.structured_plan)
        self.assertTrue(job.structured_plan.is_valid)
        self.assertEqual(job.status, JobStatus.QUEUED)
        self.assertIn("differential_expression", job.plan)


if __name__ == "__main__":
    unittest.main()
