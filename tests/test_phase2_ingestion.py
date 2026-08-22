"""
Unit Test Suite for Phase 2 Data Ingestion & Preprocessing.
"""
import unittest
import pandas as pd
from src.ingestion.loader import ZomatoDatasetIngestor

class TestPhase2Ingestion(unittest.TestCase):
    """Test data cleaning, rating parsing, cost scrubbing, and cuisine tokenization."""

    def setUp(self):
        self.ingestor = ZomatoDatasetIngestor()

    def test_rating_parsing(self):
        self.assertEqual(self.ingestor.parse_rating("4.1/5"), 4.1)
        self.assertEqual(self.ingestor.parse_rating("3.8"), 3.8)
        self.assertIsNone(self.ingestor.parse_rating("NEW"))
        self.assertIsNone(self.ingestor.parse_rating("-"))
        self.assertIsNone(self.ingestor.parse_rating(None))

    def test_cost_parsing(self):
        self.assertEqual(self.ingestor.parse_cost("1,500"), 1500)
        self.assertEqual(self.ingestor.parse_cost("₹450"), 450)
        self.assertEqual(self.ingestor.parse_cost(None), 600)

    def test_cuisine_parsing(self):
        self.assertEqual(self.ingestor.parse_cuisines("Italian, North Indian"), ["Italian", "North Indian"])
        self.assertEqual(self.ingestor.parse_cuisines(["Chinese", "Thai"]), ["Chinese", "Thai"])
        self.assertEqual(self.ingestor.parse_cuisines(None), ["Multi-Cuisine"])

    def test_clean_and_transform_dataframe(self):
        raw_data = pd.DataFrame([
            {
                "name": "Test Resto",
                "location": "Indiranagar",
                "city": "Bangalore",
                "rate": "4.5/5",
                "approx_cost(for two people)": "1,200",
                "cuisines": "Italian, Pizza"
            }
        ])

        clean_df = self.ingestor.clean_and_transform_dataframe(raw_data)
        self.assertEqual(len(clean_df), 1)
        self.assertEqual(clean_df.iloc[0]["restaurant_name"], "Test Resto")
        self.assertEqual(clean_df.iloc[0]["aggregate_rating"], 4.5)
        self.assertEqual(clean_df.iloc[0]["cost_for_two"], 1200)
        self.assertEqual(clean_df.iloc[0]["budget_tier"], "medium")
        self.assertEqual(clean_df.iloc[0]["cuisines"], ["Italian", "Pizza"])

if __name__ == "__main__":
    unittest.main()
