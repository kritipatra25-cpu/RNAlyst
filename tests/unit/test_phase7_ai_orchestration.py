"""
Unit and Integration Test Suite for Phase 7 AI Orchestration & Scientific Reasoning Layer.
"""

import unittest
from typing import Dict, Any

from agent.orchestrator.intent_parser import NaturalLanguageIntentParser, AnalysisIntent
from agent.orchestrator.analysis_plan import PlanValidator, AnalysisPlan
from agent.orchestrator.conversational_manager import ConversationalManager, ConversationalSession
from agent.rag.literature_engine import LiteratureRAGEngine, LiteratureSnippet
from agent.reasoning.evidence_classifier import EvidenceClassifier, EvidenceBadge, EvidenceStatement
from agent.reasoning.scientific_synthesizer import ScientificSynthesizer, ScientificReport
from agent.orchestrator.agent_runner import AgentOrchestrator, AgentResponse
from pipeline.backend_api import RNASeqBackendAPI


class TestPhase7AIOrchestration(unittest.TestCase):
    """Test suite for Phase 7 AI Orchestration, RAG, and Scientific Reasoning boundary."""

    def setUp(self):
        self.parser = NaturalLanguageIntentParser()
        self.api = RNASeqBackendAPI()
        self.plan_validator = PlanValidator(backend_api=self.api)
        self.conversational_manager = ConversationalManager(backend_api=self.api)
        self.rag_engine = LiteratureRAGEngine()
        self.evidence_classifier = EvidenceClassifier()
        self.synthesizer = ScientificSynthesizer(
            classifier=self.evidence_classifier,
            rag_engine=self.rag_engine
        )
        self.orchestrator = AgentOrchestrator(backend_api=self.api)

    def test_natural_language_intent_parsing(self):
        # 1. Dataset & Action resolution
        intent1 = self.parser.parse("What genes are significantly different between spaceflight and ground under light in OSD-678?")
        self.assertEqual(intent1.dataset_id, "OSD-678")
        self.assertEqual(intent1.action, "run_analysis")
        self.assertEqual(intent1.contrast_id, "A1_Col0_Light_Flight_vs_Ground")

        # 2. Validation query
        intent2 = self.parser.parse("Check metadata and validate biological replicates for OSD-120")
        self.assertEqual(intent2.dataset_id, "OSD-120")
        self.assertEqual(intent2.action, "validate")

        # 3. Gene symbol extraction
        intent3 = self.parser.parse("Find literature and biological functions for CRY1 and ANAC001 in OSD-678")
        self.assertEqual(intent3.dataset_id, "OSD-678")
        self.assertIn("CRY1", intent3.candidate_genes)
        self.assertIn("ANAC001", intent3.candidate_genes)

    def test_analysis_plan_generation_and_validation(self):
        # 1. Valid Plan
        intent_valid = self.parser.parse("Run differential expression on dataset OSD-678 under light")
        plan_valid = self.plan_validator.build_plan(intent_valid)
        self.assertTrue(plan_valid.is_validated)
        self.assertEqual(len(plan_valid.steps), 4)
        self.assertEqual(plan_valid.validation_errors, [])

        # 2. Invalid Dataset Plan Rejection
        intent_bad_ds = AnalysisIntent(dataset_id="NONEXISTENT-999", action="run_analysis")
        plan_bad_ds = self.plan_validator.build_plan(intent_bad_ds)
        self.assertFalse(plan_bad_ds.is_validated)
        self.assertGreaterEqual(len(plan_bad_ds.validation_errors), 1)

        # 3. Invalid Contrast Plan Rejection
        intent_bad_contrast = AnalysisIntent(dataset_id="OSD-678", contrast_id="FAKE_CONTRAST")
        plan_bad_contrast = self.plan_validator.build_plan(intent_bad_contrast)
        self.assertFalse(plan_bad_contrast.is_validated)
        self.assertIn("Invalid contrast_id 'FAKE_CONTRAST'", plan_bad_contrast.validation_errors[0])

    def test_conversational_session_context(self):
        session = self.conversational_manager.create_session()

        # Turn 1: Analyze OSD-678
        t1 = self.conversational_manager.process_turn("Analyze OSD-678", session_id=session.session_id)
        self.assertEqual(session.active_dataset_id, "OSD-678")
        self.assertTrue(t1.is_validated)

        # Turn 2: Focus on light contrast (retains active dataset OSD-678)
        t2 = self.conversational_manager.process_turn("Spaceflight vs ground under light", session_id=session.session_id)
        self.assertEqual(t2.intent.dataset_id, "OSD-678")
        self.assertEqual(t2.intent.contrast_id, "A1_Col0_Light_Flight_vs_Ground")
        self.assertTrue(t2.is_validated)

    def test_literature_rag_engine(self):
        # 1. Gene lookup
        snips_cry1 = self.rag_engine.search_gene_literature("AT1G04400", symbol="CRY1")
        self.assertGreaterEqual(len(snips_cry1), 1)
        self.assertEqual(snips_cry1[0].symbol, "CRY1")
        self.assertIsNotNone(snips_cry1[0].doi)
        self.assertIsNotNone(snips_cry1[0].provenance_id)

        # 2. Topic lookup
        snips_ros = self.rag_engine.search_topic_literature("reactive oxygen species")
        self.assertGreaterEqual(len(snips_ros), 1)

    def test_evidence_hierarchy_classification(self):
        # 1. Observed Statement
        s_obs = self.evidence_classifier.create_statement("1", EvidenceBadge.OBSERVED, "Processed 36 samples for OSD-678.")
        self.assertEqual(s_obs.badge, EvidenceBadge.OBSERVED)
        self.assertTrue(s_obs.formatted_text().startswith("[OBSERVED]"))

        # 2. Over-assertive Hypothesis Rejection
        s_hyp = self.evidence_classifier.create_statement(
            "2",
            EvidenceBadge.HYPOTHESIS,
            "Spaceflight microgravity is proven that it causes circadian disruption."
        )
        self.assertFalse(s_hyp.guardrail_passed)
        self.assertIn("over-assertive term", s_hyp.rejection_reason)

    def test_agent_orchestrator_query_execution(self):
        # 1. Natural Language Query for List Datasets
        resp1 = self.orchestrator.query("List all available datasets")
        self.assertTrue(resp1.success)
        self.assertEqual(resp1.operation, "LIST_DATASETS")
        self.assertIsNotNone(resp1.datasets)

        # 2. Natural Language Query for Literature Search
        resp2 = self.orchestrator.query("Find literature for CRY1 and HYH")
        self.assertTrue(resp2.success)
        self.assertEqual(resp2.operation, "LITERATURE_SEARCH")
        self.assertGreaterEqual(len(resp2.literature_snippets), 1)

        # 3. Natural Language Query for Analysis Execution
        resp3 = self.orchestrator.query("Run analysis for OSD-678 spaceflight vs ground under light")
        self.assertTrue(resp3.success)
        self.assertEqual(resp3.operation, "EXECUTE_PLAN")
        self.assertIsNotNone(resp3.analysis_result)
        self.assertIsNotNone(resp3.scientific_report)
        self.assertIn("1. What was tested?", resp3.scientific_report.full_markdown_report())


if __name__ == "__main__":
    unittest.main()
