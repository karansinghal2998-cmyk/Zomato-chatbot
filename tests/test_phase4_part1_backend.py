"""
Unit Test Suite for Phase 4 Backend Part 1 (Deterministic Candidate Filtering Engine).
"""
import unittest
import pandas as pd
from src.ingestion.loader import SAMPLE_ZOMATO_DATASET
from src.input.preference_handler import UserPreferenceRequest
from src.retrieval.filter_engine import CandidateFilterEnginePart1

class TestPhase4BackendPart1(unittest.TestCase):
    """Test hard boundary filters, cost proximity Gaussian scoring, and constraint relaxation."""

    def setUp(self):
        self.df = pd.DataFrame(SAMPLE_ZOMATO_DATASET)
        self.engine = CandidateFilterEnginePart1(max_k=5)

    def test_cost_proximity_score(self):
        # Exact target cost (1500 vs 1500) -> score close to 1.0
        score_exact = self.engine.calculate_cost_proximity_score(1500, "high")
        self.assertEqual(score_exact, 1.0)

        # Cost diff 500 (1000 vs 1500) -> score ~ 0.6065
        score_diff = self.engine.calculate_cost_proximity_score(1000, "high")
        self.assertTrue(0.5 < score_diff < 0.7)

    def test_hard_boundary_filter(self):
        user_pref = UserPreferenceRequest(
            location="Bellandur",
            budget="high",
            min_rating=4.3
        )
        filtered = self.engine.apply_hard_filters(self.df, user_pref)
        self.assertTrue(len(filtered) > 0)
        for _, row in filtered.iterrows():
            self.assertTrue("bellandur" in str(row["locality"]).lower() or "bellandur" in str(row["city"]).lower())

    def test_end_to_end_filter_and_rank(self):
        user_pref = UserPreferenceRequest(
            location="Bellandur",
            budget="high",
            cuisine=["Microbrewery", "Italian"],
            min_rating=4.4
        )
        candidates = self.engine.filter_and_rank_candidates(self.df, user_pref)
        self.assertTrue(len(candidates) > 0)
        self.assertIn("restaurant_name", candidates[0])
        self.assertIn("relevance_score", candidates[0])

if __name__ == "__main__":
    unittest.main()
