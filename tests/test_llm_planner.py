import sys
import unittest
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.llm_provider import MockLLMProvider, LLMIntentProposal
from pipeline.planner import AnalysisPlanner
from pipeline.orchestrator import AnalysisOrchestrator
from pipeline.job_models import JobStatus, StepStatus


class TestLLMPlannerIntegration(unittest.TestCase):

    def setUp(self):
        self.uploads_dir = PROJECT_ROOT / "data" / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

        # Setup valid dataset fixture
        self.valid_id = "test_llm_valid_fixture"
        self.counts_path = self.uploads_dir / f"{self.valid_id}_counts.csv"
        self.meta_path = self.uploads_dir / f"{self.valid_id}_metadata.csv"

        pd.DataFrame({
            "gene_id": ["G1", "G2"],
            "C1": [10, 20], "C2": [12, 22],
            "T1": [100, 200], "T2": [110, 210]
        }).to_csv(self.counts_path, index=False)

        pd.DataFrame({
            "sample": ["C1", "C2", "T1", "T2"],
            "condition": ["Control", "Control", "Treated", "Treated"]
        }).to_csv(self.meta_path, index=False)

        # Setup FASTQ only fixture
        self.fq_id = "test_llm_fq_only_fixture"
        self.fq_path = self.uploads_dir / f"{self.fq_id}.fastq"
        self.fq_path.write_text("@READ1\nACGT\n+\nIIII\n", encoding="utf-8")

    def test_1_valid_llm_proposal(self):
        """Test valid LLM proposal creates authoritative plan and validates inputs."""
        llm = MockLLMProvider(mode="standard")
        planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=llm)

        plan = planner.create_analysis_plan(
            file_id=self.valid_id,
            user_question="Compare treated vs control and identify significant genes"
        )

        self.assertTrue(plan.is_valid)
        self.assertEqual(len(plan.validation_errors), 0)
        self.assertIn("differential_expression", plan.selected_steps)
        self.assertIn("pca", plan.selected_steps)
        self.assertEqual(plan.interpreted_intent, "PCA_AND_DIFFERENTIAL_EXPRESSION")

    def test_2_malformed_llm_output_fallback(self):
        """Test malformed LLM output falls back to deterministic keyword parsing seamlessly."""
        llm = MockLLMProvider(mode="malformed")
        planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=llm)

        plan = planner.create_analysis_plan(
            file_id=self.valid_id,
            user_question="Perform PCA on expression counts"
        )

        self.assertTrue(plan.is_valid)
        self.assertIn("pca", plan.selected_steps)

    def test_3_adversarial_missing_input_defense(self):
        """Test LLM proposing DE for dataset lacking count matrix/metadata is deterministically rejected."""
        custom_proposal = LLMIntentProposal(
            proposed_goal="Perform differential expression",
            proposed_steps=["differential_expression"],
            suggested_intent="DIFFERENTIAL_EXPRESSION",
            reasoning="The user wants DE"
        )
        llm = MockLLMProvider(mode="custom", custom_proposal=custom_proposal)
        orchestrator = AnalysisOrchestrator(uploads_dir=self.uploads_dir, llm_provider=llm)

        job = orchestrator.create_job(
            file_id=self.fq_id,
            user_question="Perform differential expression on my FASTQ reads"
        )

        self.assertIsNotNone(job.structured_plan)
        self.assertFalse(job.structured_plan.is_valid)
        self.assertGreaterEqual(len(job.structured_plan.validation_errors), 1)

        # Attempt execution to verify step 0 fails without running DE
        executed_job = orchestrator.execute_job(job.analysis_id)
        self.assertEqual(executed_job.status, JobStatus.FAILED)
        self.assertEqual(executed_job.steps[0].status, StepStatus.FAILED)
        self.assertIn("expression/count matrix", executed_job.steps[0].message)

    def test_4_adversarial_path_injection_defense(self):
        """Test LLM injecting fake paths (/etc/passwd, synthetic matrix) is completely ignored."""
        llm = MockLLMProvider(mode="adversarial_path")
        planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=llm)

        plan = planner.create_analysis_plan(
            file_id=self.fq_id,
            user_question="Perform DE on custom synthetic counts"
        )

        # Planner must ignore injected paths and evaluate only workspace files for self.fq_id
        self.assertFalse(plan.is_valid)
        for inp in plan.required_inputs:
            if inp.resolved_path:
                self.assertNotIn("/etc/passwd", inp.resolved_path)
                self.assertNotIn("fake_matrix.csv", inp.resolved_path)

    def test_5_adversarial_unsupported_question_defense(self):
        """Test LLM claiming an unrelated question ('Analyze the weather') is supported is rejected."""
        llm = MockLLMProvider(mode="adversarial_unsupported")
        planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=llm)

        plan = planner.create_analysis_plan(
            file_id=self.valid_id,
            user_question="Analyze the weather."
        )

        self.assertFalse(plan.is_valid)
        self.assertEqual(plan.interpreted_intent, "UNSUPPORTED_QUESTION")
        self.assertIn("not a recognized RNA-seq analysis request", plan.validation_errors[0])

    def test_6_backward_compatibility_no_llm_provider(self):
        """Test AnalysisPlanner without LLM provider preserves standard deterministic behavior."""
        planner = AnalysisPlanner(uploads_dir=self.uploads_dir, llm_provider=None)

        plan = planner.create_analysis_plan(
            file_id=self.valid_id,
            user_question="Do PCA to see sample clustering"
        )

        self.assertTrue(plan.is_valid)
        self.assertEqual(plan.selected_steps, ["pca"])
        self.assertEqual(plan.interpreted_intent, "PCA")

    def test_7_e2e_llm_pipeline(self):
        """Test full E2E pipeline: Question -> Mock LLM proposal -> Planner -> Plan -> Orchestrator -> Completed Job."""
        llm = MockLLMProvider(mode="standard")
        orchestrator = AnalysisOrchestrator(uploads_dir=self.uploads_dir, llm_provider=llm)

        job = orchestrator.create_job(
            file_id=self.valid_id,
            user_question="Compare treated vs control and find significant genes"
        )

        self.assertTrue(job.structured_plan.is_valid)
        self.assertEqual(job.status, JobStatus.QUEUED)

        executed_job = orchestrator.execute_job(job.analysis_id)
        self.assertEqual(executed_job.status, JobStatus.COMPLETED)
        self.assertGreaterEqual(len(executed_job.artifacts), 4)


if __name__ == "__main__":
    unittest.main()
