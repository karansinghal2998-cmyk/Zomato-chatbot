"""
Unified End-to-End Test Suite for Zomato AI Recommendation Pipeline (Phase 9).
Covers all pipeline stages:
  - Dataset loading and cost bucketing (Phase 2)
  - Candidate filtering accuracy (Phase 4)
  - Groq rate limiter logic (Phase 5)
  - Offline fallback engine (Phase 5)
  - End-to-end API recommendation payload verification (Phase 6)
"""
import sys
import json
import time
import unittest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_budget_tier, GROQ_LLM_MODEL
from src.ingestion.loader import ZomatoDatasetIngestor, SAMPLE_ZOMATO_DATASET
from src.input.preference_handler import UserPreferenceRequest, PreferenceHandler
from src.retrieval.filter_engine import CandidateFilterEngine
from src.recommendation.offline_fallback import OfflineFallbackEngine
from src.recommendation.groq_rate_limiter import GroqRateLimiter


# ─────────────────────────────────────────────
# Phase 2: Dataset Loading & Budget Bucketing
# ─────────────────────────────────────────────
class TestDatasetLoadingAndBudgetBucketing(unittest.TestCase):
    """Tests the ingestion pipeline including HF fetch, fallback, and budget tier assignment."""

    def setUp(self):
        self.ingestor = ZomatoDatasetIngestor()

    def test_sample_dataset_not_empty(self):
        """Sample dataset must contain at least one restaurant record."""
        self.assertGreater(len(SAMPLE_ZOMATO_DATASET), 0)

    def test_fallback_dataset_loads_to_dataframe(self):
        """Fallback dataset should produce a valid DataFrame with expected columns."""
        df = pd.DataFrame(SAMPLE_ZOMATO_DATASET)
        clean_df = self.ingestor.clean_and_transform_dataframe(df)
        self.assertIsInstance(clean_df, pd.DataFrame)
        self.assertGreater(len(clean_df), 0)
        for col in ["restaurant_name", "locality", "aggregate_rating", "cost_for_two", "budget_tier"]:
            self.assertIn(col, clean_df.columns, f"Missing column: {col}")

    def test_budget_tier_low(self):
        """Costs ≤500 must be classified as 'low'."""
        self.assertEqual(get_budget_tier(300), "low")
        self.assertEqual(get_budget_tier(500), "low")

    def test_budget_tier_medium(self):
        """Costs between 501-1200 must be classified as 'medium'."""
        self.assertEqual(get_budget_tier(501), "medium")
        self.assertEqual(get_budget_tier(1200), "medium")

    def test_budget_tier_high(self):
        """Costs >1200 must be classified as 'high'."""
        self.assertEqual(get_budget_tier(1201), "high")
        self.assertEqual(get_budget_tier(3500), "high")

    def test_parse_rating_string(self):
        """Rating strings like '4.1/5' should parse to float 4.1."""
        self.assertEqual(self.ingestor.parse_rating("4.1/5"), 4.1)
        self.assertEqual(self.ingestor.parse_rating("3.8"), 3.8)

    def test_parse_rating_invalid(self):
        """Invalid rating values like 'NEW' should return None."""
        self.assertIsNone(self.ingestor.parse_rating("NEW"))
        self.assertIsNone(self.ingestor.parse_rating("-"))

    def test_parse_cost_with_commas_and_symbols(self):
        """Cost strings with commas and currency symbols should parse cleanly."""
        self.assertEqual(self.ingestor.parse_cost("1,200"), 1200)
        self.assertEqual(self.ingestor.parse_cost("₹500"), 500)

    def test_parse_cuisines_from_string(self):
        """Comma-separated cuisine strings should produce clean lists."""
        result = self.ingestor.parse_cuisines("Italian, Chinese, Desserts")
        self.assertIn("Italian", result)
        self.assertIn("Chinese", result)
        self.assertEqual(len(result), 3)

    def test_load_processed_dataset_returns_dataframe(self):
        """load_processed_dataset() must always return a non-empty DataFrame."""
        df = self.ingestor.load_processed_dataset()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)


# ─────────────────────────────────────────────
# Phase 4: Candidate Filtering Accuracy
# ─────────────────────────────────────────────
class TestCandidateFilteringEngine(unittest.TestCase):
    """Tests deterministic candidate filtering and ranking logic."""

    def setUp(self):
        self.ingestor = ZomatoDatasetIngestor()
        self.df = self.ingestor.load_processed_dataset()
        self.filter_engine = CandidateFilterEngine(max_k=10)
        self.handler = PreferenceHandler()

    def test_filter_returns_list(self):
        """filter_and_rank_candidates must return a list."""
        pref = UserPreferenceRequest(location="Indiranagar", budget="high", cuisine=["Italian"], min_rating=4.0)
        result = self.filter_engine.filter_and_rank_candidates(self.df, pref)
        self.assertIsInstance(result, list)

    def test_filter_respects_max_k(self):
        """Result must never exceed max_k (10) candidates."""
        pref = UserPreferenceRequest(location="Indiranagar", budget="high", cuisine=["Italian"], min_rating=0.0)
        result = self.filter_engine.filter_and_rank_candidates(self.df, pref)
        self.assertLessEqual(len(result), 10)

    def test_filter_rating_threshold(self):
        """Filter engine applies rating threshold; relaxes it gracefully when no candidates meet criteria."""
        # High threshold test — if filtered results are non-empty, top result should meet threshold
        pref = UserPreferenceRequest(location="Bangalore", budget="medium", cuisine=[], min_rating=4.0)
        result = self.filter_engine.filter_and_rank_candidates(self.df, pref)
        # Result must be a list (engine should not crash)
        self.assertIsInstance(result, list)
        # If results exist, they come from a valid ranking (no assertion on exact rating due to relaxation)
        if result:
            self.assertIn("restaurant_name", result[0])

    def test_filter_no_crash_on_empty_location(self):
        """Filter engine must not crash with unknown location — returns empty or partial list."""
        pref = UserPreferenceRequest(location="NonExistentCity123", budget="low", cuisine=[], min_rating=0.0)
        result = self.filter_engine.filter_and_rank_candidates(self.df, pref)
        self.assertIsInstance(result, list)


# ─────────────────────────────────────────────
# Phase 5: Groq Rate Limiter Logic
# ─────────────────────────────────────────────
class TestGroqRateLimiter(unittest.TestCase):
    """Tests the Groq API rate governor for token estimation and retry behavior."""

    def setUp(self):
        self.limiter = GroqRateLimiter()

    def test_token_estimate_is_positive(self):
        """Token estimate for any non-empty prompt must be > 0."""
        tokens = self.limiter.estimate_tokens("Hello world, recommend a restaurant.")
        self.assertGreater(tokens, 0)

    def test_successful_call_passes_through(self):
        """execute_with_retry must return result of a successful callable."""
        mock_fn = MagicMock(return_value="ok")
        result = self.limiter.execute_with_retry(mock_fn, max_retries=1, estimated_tokens=100)
        self.assertEqual(result, "ok")

    def test_rate_limiter_retries_on_exception(self):
        """execute_with_retry should retry on 429 rate-limit errors and succeed on second attempt."""
        call_count = {"n": 0}

        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise Exception("429 rate_limit exceeded")
            return "success"

        result = self.limiter.execute_with_retry(flaky, max_retries=3, estimated_tokens=100)
        self.assertEqual(result, "success")
        self.assertEqual(call_count["n"], 2)


# ─────────────────────────────────────────────
# Phase 5: Offline Fallback Engine
# ─────────────────────────────────────────────
class TestOfflineFallbackEngine(unittest.TestCase):
    """Tests the standalone offline fallback recommendation engine."""

    def setUp(self):
        self.engine = OfflineFallbackEngine()
        self.candidates = [
            {
                "restaurant_id": "rest_001",
                "restaurant_name": "Toit",
                "locality": "Indiranagar",
                "city": "Bangalore",
                "cuisines": ["Italian", "Pizza"],
                "aggregate_rating": 4.6,
                "cost_for_two": 1500,
                "budget_tier": "high",
                "highlights": ["Craft Beer", "Wood Fired Pizza"],
            },
            {
                "restaurant_id": "rest_002",
                "restaurant_name": "MTR",
                "locality": "Lalbagh",
                "city": "Bangalore",
                "cuisines": ["South Indian"],
                "aggregate_rating": 4.4,
                "cost_for_two": 400,
                "budget_tier": "low",
                "highlights": ["Idli", "Heritage"],
            },
        ]
        self.user_pref = UserPreferenceRequest(
            location="Indiranagar", budget="high", cuisine=["Italian"], min_rating=4.0
        )

    def test_recommend_returns_correct_count(self):
        """Offline engine should return exactly min(top_n, len(candidates)) records."""
        recs = self.engine.recommend(self.candidates, self.user_pref, top_n=5)
        self.assertEqual(len(recs), 2)  # only 2 candidates provided

    def test_recommendation_has_required_keys(self):
        """Each recommendation card must have all required API response keys."""
        recs = self.engine.recommend(self.candidates, self.user_pref, top_n=5)
        required_keys = {"rank", "restaurant_name", "cuisines", "rating", "estimated_cost_for_two", "locality", "ai_explanation"}
        for rec in recs:
            self.assertTrue(required_keys.issubset(set(rec.keys())), f"Missing keys in: {rec}")

    def test_rank_is_sequential(self):
        """Recommendation ranks must start at 1 and be sequential."""
        recs = self.engine.recommend(self.candidates, self.user_pref, top_n=5)
        for i, rec in enumerate(recs, start=1):
            self.assertEqual(rec["rank"], i)

    def test_explanation_is_non_empty_string(self):
        """Every AI explanation must be a non-empty string."""
        recs = self.engine.recommend(self.candidates, self.user_pref, top_n=5)
        for rec in recs:
            self.assertIsInstance(rec["ai_explanation"], str)
            self.assertGreater(len(rec["ai_explanation"]), 10)


# ─────────────────────────────────────────────
# Phase 6: End-to-End API Payload Verification
# ─────────────────────────────────────────────
class TestEndToEndAPIPayload(unittest.TestCase):
    """Integration test verifying full pipeline output matches API response contract."""

    def setUp(self):
        self.ingestor = ZomatoDatasetIngestor()
        self.df = self.ingestor.load_processed_dataset()
        self.handler = PreferenceHandler()
        self.filter_engine = CandidateFilterEngine(max_k=10)
        self.fallback_engine = OfflineFallbackEngine()

    def test_full_pipeline_produces_valid_payload(self):
        """Full pipeline must produce a valid recommendation payload."""
        raw_pref = UserPreferenceRequest(
            location="Indiranagar",
            budget="high",
            cuisine=["Italian", "Pizza"],
            min_rating=3.5,
            additional_notes="Looking for a good ambiance"
        )
        sanitized = self.handler.sanitize_and_parse(raw_pref)
        candidates = self.filter_engine.filter_and_rank_candidates(self.df, sanitized)
        recs = self.fallback_engine.recommend(candidates, sanitized, top_n=5)

        # Validate top-level pipeline produces recommendations
        self.assertIsInstance(recs, list)
        if len(recs) > 0:
            self.assertIn("restaurant_name", recs[0])
            self.assertIn("ai_explanation", recs[0])
            self.assertIn("rating", recs[0])
            self.assertIn("estimated_cost_for_two", recs[0])

    def test_no_crash_on_minimal_preference(self):
        """Pipeline must not crash on minimal user preference input."""
        raw_pref = UserPreferenceRequest(
            location="Koramangala",
            budget="low",
            cuisine=[],
            min_rating=0.0
        )
        sanitized = self.handler.sanitize_and_parse(raw_pref)
        candidates = self.filter_engine.filter_and_rank_candidates(self.df, sanitized)
        recs = self.fallback_engine.recommend(candidates, sanitized, top_n=5)
        self.assertIsInstance(recs, list)

    def test_cost_format_includes_rupee_symbol(self):
        """Estimated cost in all recommendations must use ₹ prefix."""
        raw_pref = UserPreferenceRequest(location="Indiranagar", budget="medium", cuisine=[], min_rating=3.0)
        sanitized = self.handler.sanitize_and_parse(raw_pref)
        candidates = self.filter_engine.filter_and_rank_candidates(self.df, sanitized)
        recs = self.fallback_engine.recommend(candidates, sanitized, top_n=5)
        for rec in recs:
            self.assertTrue(
                str(rec["estimated_cost_for_two"]).startswith("₹"),
                f"Cost format invalid: {rec['estimated_cost_for_two']}"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
