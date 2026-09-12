"""
Unit & Integration Test Suite for Workspace-Centric Agentic Architecture (Biomni Reference Model).

Verifies:
1. First-class ReferenceSpec provenance and workspace state models.
2. Production dependency guard (DependencyNotFoundError when Nextflow/Salmon missing in production).
3. ToolRegistry tool categorization and dynamic intent-based tool retrieval.
4. ProjectManager execution trace recording and workspace state updates.
5. AgentOrchestrator execution history trace recording.
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
    ReferenceSpec,
    ToolExecutionStep,
    WorkspaceState,
    DataOrigin,
    LayoutType,
    Sample,
    ContrastSpec
)
from pipeline.project_manager import ProjectManager
from pipeline.nextflow_runner import NextflowRunner, DependencyNotFoundError
from agent.tools.registry import ToolRegistry, TOOL_CATEGORIES
from agent.tools.deseq2_tool import DESeq2Tool
from agent.tools.literature_tool import LiteratureTool
from agent.tools.gene_annotation_tool import GeneAnnotationTool
from agent.tools.visualization_tools import VolcanoPlotTool
from agent.orchestrator.agent_runner import AgentOrchestrator
from agent.llm.providers import MockLLMProvider
from agent.llm.client import ToolCallRequest


class TestWorkspaceAgenticArchitecture(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.projects_dir = Path(self.tmp_dir) / "projects"
        self.configs_dir = Path(self.tmp_dir) / "configs"
        self.pm = ProjectManager(
            projects_dir=str(self.projects_dir),
            configs_dir=str(self.configs_dir)
        )

        # Create sample project
        samples = [
            Sample(sample_id="S1", condition="Treatment", fastq_r1_path="/tmp/s1_1.fq.gz"),
            Sample(sample_id="S2", condition="Treatment", fastq_r1_path="/tmp/s2_1.fq.gz"),
            Sample(sample_id="S3", condition="Control", fastq_r1_path="/tmp/s3_1.fq.gz"),
            Sample(sample_id="S4", condition="Control", fastq_r1_path="/tmp/s4_1.fq.gz"),
        ]
        manifest = SampleManifest(
            samples=samples,
            layout=LayoutType.PAIRED,
            organism="Arabidopsis thaliana",
            condition_column="condition"
        )
        design = ExperimentalDesign(
            design_formula="~ condition",
            factors={"condition": ["Treatment", "Control"]},
            reference_levels={"condition": "Control"},
            contrasts=[ContrastSpec(id="Tx_vs_Ctrl", factor="condition", numerator="Treatment", denominator="Control")]
        )

        ref_spec = ReferenceSpec(
            organism="Arabidopsis thaliana",
            source="TAIR10",
            version_build="TAIR10.55",
            transcriptome_fasta=str(self.projects_dir / "trans.fasta"),
            sha256_hashes={"transcriptome": "abc123sha256hash"}
        )

        self.project = self.pm.create_project(
            project_id="PROJ-WORK-01",
            name="Workspace Test Project",
            origin=DataOrigin.LOCAL_FASTQ,
            organism="Arabidopsis thaliana",
            manifest=manifest,
            design=design
        )
        self.project.reference_spec = ref_spec
        self.pm.save_project(self.project)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_reference_spec_provenance(self):
        """Verify first-class ReferenceSpec models organism, source, version, and hashes."""
        proj = self.pm.get_project("PROJ-WORK-01")
        self.assertIsNotNone(proj.reference_spec)
        self.assertEqual(proj.reference_spec.organism, "Arabidopsis thaliana")
        self.assertEqual(proj.reference_spec.source, "TAIR10")
        self.assertEqual(proj.reference_spec.version_build, "TAIR10.55")
        self.assertIn("transcriptome", proj.reference_spec.sha256_hashes)

    def test_production_dependency_guard(self):
        """Verify NextflowRunner raises DependencyNotFoundError when Nextflow/Salmon absent and allow_mock=False."""
        runner = NextflowRunner(workspace_root=self.tmp_dir)
        # Ensure PATH check returns False or test explicit allow_mock=False
        if not runner.has_nextflow():
            with self.assertRaises(DependencyNotFoundError):
                runner.run_pipeline(
                    project_id="PROJ-WORK-01",
                    sample_ids=["S1", "S2"],
                    reads_dir=self.tmp_dir,
                    output_dir=self.tmp_dir,
                    allow_mock=False
                )

    def test_tool_registry_categorization_and_intent_search(self):
        """Verify ToolRegistry categorizes tools and returns intent-matched tools."""
        registry = ToolRegistry()
        registry.register(DESeq2Tool())
        registry.register(LiteratureTool())
        registry.register(GeneAnnotationTool())
        registry.register(VolcanoPlotTool())

        # Test categories
        cat_stats = registry.list_tools_by_category("STATISTICS")
        self.assertEqual(len(cat_stats), 1)
        self.assertEqual(cat_stats[0].name, "run_differential_expression")

        # Test intent retrieval
        matched = registry.find_tools_for_intent("differential expression volcano plot")
        matched_names = [t.name for t in matched]
        self.assertIn("run_differential_expression", matched_names)
        self.assertIn("generate_volcano_plot", matched_names)

    def test_execution_history_recording(self):
        """Verify ProjectManager records ToolExecutionStep and updates workspace state."""
        step = ToolExecutionStep(
            step_id="step_001",
            tool_name="quantify_reads",
            timestamp="2026-08-24T22:00:00Z",
            arguments={"project_id": "PROJ-WORK-01"},
            status="SUCCESS",
            output_summary="Quantification completed across 4 samples.",
            artifact_paths=["/path/to/counts_matrix.csv"],
            provenance_hash="sha256_test_hash_123"
        )
        self.pm.record_execution_step("PROJ-WORK-01", step)

        history = self.pm.get_execution_history("PROJ-WORK-01")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["step_id"], "step_001")
        self.assertEqual(history[0]["tool_name"], "quantify_reads")
        self.assertEqual(history[0]["provenance_hash"], "sha256_test_hash_123")

        # Verify project workspace state updated
        proj = self.pm.get_project("PROJ-WORK-01")
        self.assertEqual(len(proj.execution_history), 1)
        self.assertEqual(proj.workspace_state.total_samples, 4)

    def test_agent_orchestrator_records_execution_trace(self):
        """Verify AgentOrchestrator records execution step into project workspace history."""
        from agent.llm.client import LLMResponse
        mock_provider = MockLLMProvider()
        mock_provider.queue_response(LLMResponse(
            content="",
            tool_calls=[
                ToolCallRequest(
                    call_id="call_001",
                    tool_name="search_literature",
                    arguments={"topic": "spaceflight"}
                )
            ],
            finish_reason="tool_calls"
        ))
        mock_provider.queue_response(LLMResponse(
            content="Synthesized literature response grounded in evidence.",
            tool_calls=[],
            finish_reason="stop"
        ))

        orchestrator = AgentOrchestrator(llm_provider=mock_provider)
        orchestrator.project_manager = self.pm

        session = orchestrator.conversational_manager.get_or_create_session()
        session.active_dataset_id = "PROJ-WORK-01"

        resp = orchestrator.agentic_query(
            user_query="Find literature on Arabidopsis spaceflight",
            session_id=session.session_id
        )

        self.assertTrue(resp.success)
        history = self.pm.get_execution_history("PROJ-WORK-01")
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["tool_name"], "search_literature")


if __name__ == "__main__":
    unittest.main()
