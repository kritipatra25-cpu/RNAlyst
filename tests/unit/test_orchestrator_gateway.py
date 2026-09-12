"""
Unit and Boundary Integration Tests for Phase 6B RNASeqBackendAPI <-> AgentOrchestrator Gateway.
"""

import unittest
from typing import Dict, Any

from pipeline.backend_api import (
    RNASeqBackendAPI,
    AnalysisRequest,
    AnalysisResult,
    PreflightValidationResult,
    AnalysisErrorResult,
)
from agent.orchestrator.agent_runner import AgentOrchestrator, AgentResponse


class TestOrchestratorGateway(unittest.TestCase):
    """Test suite for RNASeqBackendAPI and AgentOrchestrator gateway boundary."""

    def setUp(self):
        self.api = RNASeqBackendAPI()
        self.orchestrator = AgentOrchestrator(backend_api=self.api)

    def test_api_instantiation_and_dataset_discovery(self):
        datasets = self.api.list_available_datasets()
        self.assertGreaterEqual(len(datasets), 2)
        dataset_ids = [d.dataset_id for d in datasets]
        self.assertIn("OSD-678", dataset_ids)
        self.assertIn("OSD-120", dataset_ids)

    def test_contrast_listing(self):
        contrasts = self.api.list_available_contrasts("OSD-678")
        self.assertGreaterEqual(len(contrasts), 6)
        c_ids = [c.id for c in contrasts]
        self.assertIn("A1_Col0_Light_Flight_vs_Ground", c_ids)

        # Invalid dataset rejection
        with self.assertRaises(ValueError):
            self.api.list_available_contrasts("NONEXISTENT-999")

    def test_preflight_validation(self):
        pf_res = self.api.validate_preflight("OSD-678")
        self.assertIsInstance(pf_res, PreflightValidationResult)
        self.assertTrue(pf_res.is_valid)
        self.assertEqual(pf_res.dataset_id, "OSD-678")
        self.assertEqual(pf_res.sample_count, 36)
        self.assertGreaterEqual(pf_res.min_replicates, 3)

        # Invalid dataset preflight
        pf_bad = self.api.validate_preflight("INVALID-000")
        self.assertFalse(pf_bad.is_valid)
        self.assertEqual(pf_bad.replicate_status, "INVALID")
        self.assertGreaterEqual(len(pf_bad.errors), 1)

    def test_backend_validation_rejection(self):
        # 1. Invalid fdr_cutoff (< 0)
        with self.assertRaises(ValueError):
            AnalysisRequest(dataset_id="OSD-678", fdr_cutoff=-0.01)

        # 2. Invalid fdr_cutoff (> 1)
        with self.assertRaises(ValueError):
            AnalysisRequest(dataset_id="OSD-678", fdr_cutoff=1.5)

        # 3. Invalid analysis_type
        with self.assertRaises(ValueError):
            AnalysisRequest(dataset_id="OSD-678", analysis_type="ARBITRARY_CODE_EXECUTION")

        # 4. Unknown dataset_id in validate_request
        req_unknown = AnalysisRequest(dataset_id="UNKNOWN-999")
        with self.assertRaises(ValueError):
            self.api.validate_request(req_unknown)

        # 5. Invalid contrast_id for valid dataset
        req_bad_contrast = AnalysisRequest(dataset_id="OSD-678", contrast_id="NONEXISTENT_CONTRAST")
        with self.assertRaises(ValueError):
            self.api.validate_request(req_bad_contrast)

    def test_safe_analysis_wrapper_rejection(self):
        req_unknown = AnalysisRequest(dataset_id="UNKNOWN-999")
        success, result, error = self.api.run_analysis_safe(req_unknown)
        self.assertFalse(success)
        self.assertIsNone(result)
        self.assertIsInstance(error, AnalysisErrorResult)
        self.assertTrue(error.rejected_by_backend)
        self.assertIn("UNKNOWN-999", error.message)

    def test_orchestrator_natural_language_intent_routing(self):
        # 1. List Datasets Intent
        resp1 = self.orchestrator.process_natural_language_intent({"action": "list_datasets"})
        self.assertTrue(resp1.success)
        self.assertEqual(resp1.operation, "LIST_DATASETS")
        self.assertIsNotNone(resp1.datasets)

        # 2. List Contrasts Intent
        resp2 = self.orchestrator.process_natural_language_intent({"action": "list_contrasts", "dataset_id": "OSD-678"})
        self.assertTrue(resp2.success)
        self.assertEqual(resp2.operation, "LIST_CONTRASTS")
        self.assertIsNotNone(resp2.contrasts)

        # 3. Validate Intent
        resp3 = self.orchestrator.process_natural_language_intent({"action": "validate", "dataset_id": "OSD-678"})
        self.assertTrue(resp3.success)
        self.assertEqual(resp3.operation, "VALIDATE_DATASET")
        self.assertTrue(resp3.preflight_result.is_valid)

        # 4. Unsupported Action Intent
        resp4 = self.orchestrator.process_natural_language_intent({"action": "execute_arbitrary_python", "dataset_id": "OSD-678"})
        self.assertFalse(resp4.success)
        self.assertEqual(resp4.operation, "UNKNOWN_ACTION")
        self.assertTrue(resp4.error_result.rejected_by_backend)

        # 5. Rejection on Invalid Contrast via Orchestrator
        resp5 = self.orchestrator.process_natural_language_intent({
            "action": "run_analysis",
            "dataset_id": "OSD-678",
            "contrast_id": "FAKE_CONTRAST_ID"
        })
        self.assertFalse(resp5.success)
        self.assertIsNotNone(resp5.error_result)
        self.assertTrue(resp5.error_result.rejected_by_backend)


if __name__ == "__main__":
    unittest.main()
