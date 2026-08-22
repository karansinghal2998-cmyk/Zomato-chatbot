"""
Unit Test Suite for Phase 6 (Backend API Layer) and Phase 7 (Web Frontend UI).
"""
import unittest
from fastapi.testclient import TestClient
from src.api.server import app

class TestPhase6Phase7APIFrontend(unittest.TestCase):
    """Test FastAPI endpoints, JSON response contracts, location lists, and frontend HTML serving."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("dataset", data)

    def test_locations_endpoint(self):
        response = self.client.get("/api/v1/locations")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data["locations"]) > 0)
        self.assertIn("Bellandur", data["locations"])

    def test_recommend_endpoint(self):
        payload = {
            "location": "Bellandur",
            "budget": "high",
            "min_rating": 4.2,
            "additional_notes": "Group dinner"
        }
        response = self.client.post("/api/v1/recommend", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["location"], "Bellandur")
        self.assertTrue(len(data["recommendations"]) > 0)
        first_rec = data["recommendations"][0]
        self.assertIn("restaurant_name", first_rec)
        self.assertIn("ai_explanation", first_rec)

    def test_frontend_html_serving(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Zomato AI", response.text)

if __name__ == "__main__":
    unittest.main()
