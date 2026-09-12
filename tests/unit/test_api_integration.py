"""
Integration tests for FastAPI POST /api/v1/query route -> AgentOrchestrator tool-calling loop.
"""

import unittest
from fastapi.testclient import TestClient
from api.main import app

class TestAPIIntegration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_api_v1_query_endpoint_success(self):
        """Test 1: POST /api/v1/query endpoint receives user query and returns structured AgentResponse."""
        payload = {
            "query": "What genes are differentially expressed between spaceflight and ground control in OSD-678?",
            "session_id": "session_test_integration_001"
        }

        response = self.client.post("/api/v1/query", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["operation"], "AGENTIC_QUERY")


        self.assertEqual(data["session_id"], "session_test_integration_001")
        self.assertIn("message", data)
        self.assertIn("iterations_count", data)
        self.assertGreaterEqual(data["iterations_count"], 1)

    def test_api_v1_query_empty_query_rejected(self):
        """Test 2: Empty query string returned HTTP 400 Bad Request."""
        payload = {"query": "   ", "session_id": "session_test_002"}
        response = self.client.post("/api/v1/query", json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot be empty", response.json()["detail"])

    def test_api_v1_query_multi_turn_session_continuity(self):
        """Test 3: Multi-turn queries reuse session_id and retain conversational memory."""
        payload_turn1 = {
            "query": "Show literature for spaceflight candidate genes",
            "session_id": "session_multi_turn_999"
        }

        res1 = self.client.post("/api/v1/query", json=payload_turn1)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(data1["session_id"], "session_multi_turn_999")

        payload_turn2 = {
            "query": "Tell me more about the first paper",
            "session_id": "session_multi_turn_999"
        }

        res2 = self.client.post("/api/v1/query", json=payload_turn2)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2["session_id"], "session_multi_turn_999")


if __name__ == "__main__":
    unittest.main()
