"""
Unit Test Suite for Phase 4 Deterministic Candidate Filtering Engine.
"""
import unittest
import pandas as pd
from src.ingestion.loader import SAMPLE_ZOMATO_DATASET
from src.input.preference_handler import UserPreferenceRequest
from src.retrieval.filter_engine import CandidateFilterEngine

class TestPhase4Filter(unittest.TestCase):
    """Test hard constraint filters, soft relevance scoring, and constraint relaxation fallback."""

    def setUp(self):
        self.df = pd.DataFrame(SAMPLE_ZOMATO_DATASET)
        self.filter_engine = CandidateFilterEngine(max_k=5)

    def test_location_and_rating_hard_filter(self):
        user_pref = UserPreferenceRequest(
            location="Indiranagar",
            budget="medium",
            cuisine=["Italian"],
            min_rating=4.5
        )

        candidates = self.filter_engine.filter_and_rank_candidates(self.df, user_pref)
        self.assertTrue(len(candidates) > 0)
        top_cand = candidates[0]
        self.assertEqual(top_cand["restaurant_name"], "Toit")
        self.assertEqual(top_cand["locality"], "Indiranagar")

    def test_budget_scoring(self):
        user_pref = UserPreferenceRequest(
            location="Bangalore",
            budget="low",
            cuisine=["Desserts"]
        )

        candidates = self.filter_engine.filter_and_rank_candidates(self.df, user_pref)
        self.assertTrue(len(candidates) > 0)
        top_cand = candidates[0]
        self.assertEqual(top_cand["restaurant_name"], "Corner House Ice Cream")
        self.assertEqual(top_cand["budget_tier"], "low")

    def test_constraint_relaxation_on_zero_candidates(self):
        user_pref = UserPreferenceRequest(
            location="NonExistentPlace",
            min_rating=4.9
        )

        candidates = self.filter_engine.filter_and_rank_candidates(self.df, user_pref)
        self.assertTrue(len(candidates) > 0)

if __name__ == "__main__":
    unittest.main()
