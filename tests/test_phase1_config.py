"""
Unit Test Suite for Phase 0 / Phase 1 Environment Setup & Configuration.
"""
import unittest
from pathlib import Path
from src.config import (
    BASE_DIR,
    DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    OUTPUTS_DIR,
    HUGGINGFACE_DATASET_ID,
    GROQ_LLM_MODEL,
    MAX_CANDIDATE_POOL_SIZE,
    get_budget_tier
)

class TestPhase1Config(unittest.TestCase):
    """Test configuration paths, budget thresholds, and directory structures."""

    def test_directory_creation(self):
        self.assertTrue(BASE_DIR.exists())
        self.assertTrue(DATA_DIR.exists())
        self.assertTrue(RAW_DATA_DIR.exists())
        self.assertTrue(PROCESSED_DATA_DIR.exists())
        self.assertTrue(OUTPUTS_DIR.exists())

    def test_dataset_and_model_constants(self):
        self.assertEqual(HUGGINGFACE_DATASET_ID, "ManikaSaini/zomato-restaurant-recommendation")
        self.assertEqual(GROQ_LLM_MODEL, "openai/gpt-oss-120b")
        self.assertEqual(MAX_CANDIDATE_POOL_SIZE, 10)

    def test_budget_tier_calculation(self):
        self.assertEqual(get_budget_tier(300), "low")
        self.assertEqual(get_budget_tier(500), "low")
        self.assertEqual(get_budget_tier(800), "medium")
        self.assertEqual(get_budget_tier(1200), "medium")
        self.assertEqual(get_budget_tier(2000), "high")
        self.assertEqual(get_budget_tier(None), "medium")

if __name__ == "__main__":
    unittest.main()
