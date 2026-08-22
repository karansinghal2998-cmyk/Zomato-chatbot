"""
Zomato Data Ingestion & Preprocessing Module.
Loads the Zomato restaurant recommendation dataset from Hugging Face
(ManikaSaini/zomato-restaurant-recommendation), performs schema mapping,
cleans rating floats, scrubs cost strings, categorizes budget tiers,
and exports clean records to parquet and json stores.
"""
import re
import logging
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.config import (
    HUGGINGFACE_DATASET_ID,
    PROCESSED_PARQUET_PATH,
    PROCESSED_JSON_PATH,
    RAW_DATA_DIR,
    get_budget_tier
)

logging.basicConfig(level=logging.INFO)

# Sample synthetic backup dataset for offline execution or network fallback
SAMPLE_ZOMATO_DATASET = [
    {
        "restaurant_id": "rest_101",
        "restaurant_name": "Toit",
        "locality": "Indiranagar",
        "city": "Bangalore",
        "cuisines": ["Italian", "American", "Pizza", "Brewery"],
        "aggregate_rating": 4.6,
        "votes": 14200,
        "cost_for_two": 1500,
        "budget_tier": "high",
        "highlights": ["Outdoor Seating", "Craft Beer", "Wood Fired Pizza", "Trendy Ambiance"]
    },
    {
        "restaurant_id": "rest_102",
        "restaurant_name": "Corner House Ice Cream",
        "locality": "Indiranagar",
        "city": "Bangalore",
        "cuisines": ["Desserts", "Ice Cream", "Beverages"],
        "aggregate_rating": 4.7,
        "votes": 8900,
        "cost_for_two": 400,
        "budget_tier": "low",
        "highlights": ["DBC Special", "Quick Service", "Family Friendly", "Pocket Friendly"]
    },
    {
        "restaurant_id": "rest_103",
        "restaurant_name": "Truffles",
        "locality": "Koramangala",
        "city": "Bangalore",
        "cuisines": ["American", "Burgers", "Continental", "Italian"],
        "aggregate_rating": 4.5,
        "votes": 16500,
        "cost_for_two": 800,
        "budget_tier": "medium",
        "highlights": ["Juicy Burgers", "Casual Dining", "Youth Popular", "Quick Service"]
    },
    {
        "restaurant_id": "rest_201",
        "restaurant_name": "The Fisherman's Wharf",
        "locality": "Bellandur",
        "city": "Bangalore",
        "cuisines": ["Seafood", "Goan", "North Indian", "Continental"],
        "aggregate_rating": 4.4,
        "votes": 9800,
        "cost_for_two": 1500,
        "budget_tier": "high",
        "highlights": ["Seafood Platter", "Live Music", "Lakeside Dining", "Goan Vibe"]
    },
    {
        "restaurant_id": "rest_202",
        "restaurant_name": "Social Bellandur",
        "locality": "Bellandur",
        "city": "Bangalore",
        "cuisines": ["Continental", "Finger Food", "Asian", "American"],
        "aggregate_rating": 4.4,
        "votes": 7500,
        "cost_for_two": 1500,
        "budget_tier": "high",
        "highlights": ["Co-working Space", "Craft Cocktails", "Vibrant Ambience", "DJ Nights"]
    },
    {
        "restaurant_id": "rest_203",
        "restaurant_name": "Ironhill India",
        "locality": "Bellandur",
        "city": "Bangalore",
        "cuisines": ["Microbrewery", "Italian", "Continental", "North Indian"],
        "aggregate_rating": 4.5,
        "votes": 11200,
        "cost_for_two": 1600,
        "budget_tier": "high",
        "highlights": ["World's Largest Brewery", "Lakeside Seating", "Wood Fired Pizza", "Live Sports Screen"]
    },
    {
        "restaurant_id": "rest_204",
        "restaurant_name": "Punjabi By Nature 2.0",
        "locality": "Bellandur",
        "city": "Bangalore",
        "cuisines": ["North Indian", "Mughlai", "Kebabs"],
        "aggregate_rating": 4.3,
        "votes": 4300,
        "cost_for_two": 1400,
        "budget_tier": "high",
        "highlights": ["Rich Dal Makhani", "Family Dining", "Butter Chicken", "Buffet Available"]
    },
    {
        "restaurant_id": "rest_205",
        "restaurant_name": "Central Jail Restaurant",
        "locality": "Bellandur",
        "city": "Bangalore",
        "cuisines": ["North Indian", "Chinese", "Biryani"],
        "aggregate_rating": 4.2,
        "votes": 3100,
        "cost_for_two": 800,
        "budget_tier": "medium",
        "highlights": ["Jail Theme Ambiance", "Unique Photo Spots", "Spicy Biryani", "Casual Dining"]
    },
    {
        "restaurant_id": "rest_206",
        "restaurant_name": "Byg Brewski Brewing Company",
        "locality": "Bellandur",
        "city": "Bangalore",
        "cuisines": ["Asian", "Italian", "Continental", "North Indian"],
        "aggregate_rating": 4.6,
        "votes": 18900,
        "cost_for_two": 1600,
        "budget_tier": "high",
        "highlights": ["Open-Air Ambiance", "Craft Beers", "Sunset Dining", "Dim Sums"]
    },
    {
        "restaurant_id": "rest_104",
        "restaurant_name": "Bakehouse Naman",
        "locality": "Connaught Place",
        "city": "Delhi",
        "cuisines": ["North Indian", "Mughlai", "Street Food"],
        "aggregate_rating": 4.3,
        "votes": 5400,
        "cost_for_two": 600,
        "budget_tier": "medium",
        "highlights": ["Butter Chicken", "Family Dining", "Authentic Spices"]
    },
    {
        "restaurant_id": "rest_105",
        "restaurant_name": "San Gimignano - The Imperial",
        "locality": "Janpath",
        "city": "Delhi",
        "cuisines": ["Italian", "Fine Dining", "Pasta", "Wine Bar"],
        "aggregate_rating": 4.8,
        "votes": 2100,
        "cost_for_two": 3500,
        "budget_tier": "high",
        "highlights": ["Luxury Fine Dining", "Romantic Ambiance", "Outdoor Courtyard"]
    },
    {
        "restaurant_id": "rest_106",
        "restaurant_name": "Saravana Bhavan",
        "locality": "Connaught Place",
        "city": "Delhi",
        "cuisines": ["South Indian", "Vegetarian", "Dosa"],
        "aggregate_rating": 4.4,
        "votes": 11200,
        "cost_for_two": 450,
        "budget_tier": "low",
        "highlights": ["Pure Veg", "Crispy Dosa", "Quick Service", "Family Friendly"]
    }
]

class ZomatoDatasetIngestor:
    """Ingests, cleans, normalizes, and stores the Zomato restaurant recommendation dataset."""

    def __init__(self, dataset_id: str = HUGGINGFACE_DATASET_ID):
        self.dataset_id = dataset_id

    def parse_rating(self, val: Any) -> Optional[float]:
        """Extracts float rating from string representations like '4.1/5', '4.2', 'NEW'."""
        if pd.isna(val) or val is None:
            return None
        val_str = str(val).strip().upper()
        if val_str in ["NEW", "-", "OPENING SOON", ""]:
            return None
        match = re.search(r"(\d+\.\d+|\d+)", val_str)
        if match:
            try:
                score = float(match.group(1))
                return score if 0.0 <= score <= 5.0 else None
            except ValueError:
                return None
        return None

    def parse_cost(self, val: Any) -> int:
        """Scrubs cost strings like '1,200', '₹500' to integer values."""
        if pd.isna(val) or val is None:
            return 600  # Default median fallback
        val_str = str(val).strip()
        digits = re.sub(r"[^\d]", "", val_str)
        if digits:
            try:
                return int(digits)
            except ValueError:
                return 600
        return 600

    def parse_cuisines(self, val: Any) -> List[str]:
        """Converts comma-separated cuisine string to clean list of normalized strings."""
        if val is None:
            return ["Multi-Cuisine"]
        if isinstance(val, list):
            return [str(c).strip() for c in val if str(c).strip()]
        if pd.isna(val):
            return ["Multi-Cuisine"]
        val_str = str(val).strip()
        if not val_str:
            return ["Multi-Cuisine"]
        return [c.strip() for c in val_str.split(",") if c.strip()]

    def parse_highlights(self, val: Any) -> List[str]:
        """Converts highlights string/list into clean list of tags."""
        if val is None:
            return []
        if isinstance(val, list):
            return [str(h).strip() for h in val if str(h).strip()]
        if pd.isna(val):
            return []
        val_str = str(val).strip()
        return [h.strip() for h in val_str.split(",") if h.strip()]

    def fetch_raw_dataset_via_api(self, max_rows: int = 5000) -> pd.DataFrame:
        """
        Fetches dataset from HuggingFace Datasets Server REST API (paginated).
        This approach avoids downloading raw parquet shards (~1 GB) and instead
        fetches rows directly via the dataset viewer endpoint in pages of 100.

        Args:
            max_rows: Maximum number of rows to fetch (default 5000).

        Returns:
            DataFrame of raw restaurant records, or empty DataFrame on failure.
        """
        import requests

        base_url = "https://datasets-server.huggingface.co/rows"
        params_base = {
            "dataset": self.dataset_id,
            "config": "default",
            "split": "train",
        }

        all_rows = []
        offset = 0
        page_size = 100

        logging.info(f"📡 Fetching up to {max_rows} rows from HuggingFace REST API: {self.dataset_id}")

        try:
            while offset < max_rows:
                params = {**params_base, "offset": offset, "length": page_size}
                response = requests.get(base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                rows = data.get("rows", [])
                if not rows:
                    break

                for item in rows:
                    all_rows.append(item.get("row", {}))

                total_available = data.get("num_rows_total", 0)
                offset += page_size

                if offset % 500 == 0:
                    logging.info(f"   ↳ Fetched {len(all_rows)} / {min(max_rows, total_available)} rows...")

                if offset >= total_available:
                    break

            if all_rows:
                df = pd.DataFrame(all_rows)
                logging.info(f"✅ HuggingFace REST API: fetched {len(df)} rows successfully.")
                return df
            else:
                logging.warning("⚠️ HuggingFace REST API returned no rows.")
                return pd.DataFrame()

        except Exception as e:
            logging.warning(f"⚠️ HuggingFace REST API fetch failed ({e}).")
            return pd.DataFrame()

    def fetch_raw_dataset(self) -> pd.DataFrame:
        """
        Fetches dataset from HuggingFace, trying:
        1. Lightweight REST API (no disk download required) — primary method.
        2. datasets library full download — secondary fallback.
        3. Built-in sample dataset — final fallback.
        """
        logging.info(f"📥 Attempting HuggingFace REST API fetch: {self.dataset_id}...")

        # Primary: lightweight REST API fetch (no large disk requirement)
        df = self.fetch_raw_dataset_via_api(max_rows=5000)
        if not df.empty:
            return df

        # Secondary: try datasets library (requires ~1 GB disk)
        logging.info("📥 Falling back to datasets library download...")
        try:
            from datasets import load_dataset
            dataset = load_dataset(self.dataset_id)
            if "train" in dataset:
                df = dataset["train"].to_pandas()
            else:
                first_split = list(dataset.keys())[0]
                df = dataset[first_split].to_pandas()
            logging.info(f"✅ datasets library: loaded {len(df)} rows.")
            return df
        except Exception as e:
            logging.warning(f"⚠️ datasets library failed ({e}). Using built-in sample dataset.")
            return pd.DataFrame(SAMPLE_ZOMATO_DATASET)


    def clean_and_transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalizes schema, cleans ratings, costs, cuisine lists, and assigns budget tiers."""
        logging.info("Preprocessing and cleaning raw Zomato dataset...")

        if df.empty:
            df = pd.DataFrame(SAMPLE_ZOMATO_DATASET)

        # Standardize Column Names
        col_mapping = {
            "name": "restaurant_name",
            "Restaurant Name": "restaurant_name",
            "location": "locality",
            "Location": "locality",
            "locality": "locality",
            "city": "city",
            "City": "city",
            "rate": "aggregate_rating",
            "rating": "aggregate_rating",
            "Aggregate rating": "aggregate_rating",
            "approx_cost(for two people)": "cost_for_two",
            "cost_for_two": "cost_for_two",
            "Average Cost for two": "cost_for_two",
            "cuisines": "cuisines",
            "Cuisines": "cuisines",
            "votes": "votes",
            "Votes": "votes",
            "highlights": "highlights",
            "facilities": "highlights"
        }

        df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})

        # Ensure essential columns exist
        if "restaurant_name" not in df.columns:
            df["restaurant_name"] = "Zomato Restaurant"
        if "locality" not in df.columns:
            df["locality"] = "Bangalore"
        if "city" not in df.columns:
            df["city"] = "Bangalore"

        # Apply Field Transformations — use .apply() when column exists, else fill entire column
        df["aggregate_rating"] = df["aggregate_rating"].apply(self.parse_rating) if "aggregate_rating" in df.columns else 4.0
        df["cost_for_two"] = df["cost_for_two"].apply(self.parse_cost) if "cost_for_two" in df.columns else 600
        if "cuisines" in df.columns:
            df["cuisines"] = df["cuisines"].apply(self.parse_cuisines)
        else:
            df["cuisines"] = pd.Series([["Multi-Cuisine"]] * len(df), index=df.index)
        # HuggingFace dataset uses 'dish_liked' as highlights proxy when 'highlights' not present
        if "highlights" in df.columns:
            df["highlights"] = df["highlights"].apply(self.parse_highlights)
        elif "dish_liked" in df.columns:
            df["highlights"] = df["dish_liked"].apply(
                lambda v: [d.strip() for d in str(v).split(",")[:5] if str(v) not in ("nan", "")] if pd.notna(v) else []
            )
        else:
            df["highlights"] = pd.Series([[]] * len(df), index=df.index)

        # Calculate Budget Tiers
        df["budget_tier"] = df["cost_for_two"].apply(get_budget_tier)

        # Fill missing votes
        if "votes" not in df.columns:
            df["votes"] = 100
        else:
            df["votes"] = df["votes"].fillna(100).astype(int)

        # Assign unique IDs if missing
        if "restaurant_id" not in df.columns:
            df["restaurant_id"] = [f"rest_{idx+1:04d}" for idx in range(len(df))]

        # Select Final Clean Columns
        clean_cols = [
            "restaurant_id", "restaurant_name", "locality", "city",
            "cuisines", "aggregate_rating", "votes", "cost_for_two",
            "budget_tier", "highlights"
        ]

        clean_df = df[clean_cols].copy()
        logging.info(f"✅ Clean dataset ready with {len(clean_df)} validated restaurant records.")
        return clean_df

    def save_processed_dataset(self, df: pd.DataFrame):
        """Exports preprocessed dataset to Parquet and JSON files."""
        try:
            df.to_parquet(PROCESSED_PARQUET_PATH, index=False)
            logging.info(f"💾 Exported processed dataset to Parquet: {PROCESSED_PARQUET_PATH}")
        except Exception as e:
            logging.warning(f"Parquet export failed ({e}). Defaulting to JSON export...")

        df.to_json(PROCESSED_JSON_PATH, orient="records", indent=2)
        logging.info(f"💾 Exported processed dataset to JSON: {PROCESSED_JSON_PATH}")

    def load_processed_dataset(self) -> pd.DataFrame:
        """Loads preprocessed dataset if present, else executes full ingestion pipeline."""
        if PROCESSED_PARQUET_PATH.exists():
            try:
                logging.info(f"Loading preprocessed dataset from Parquet: {PROCESSED_PARQUET_PATH}")
                return pd.read_parquet(PROCESSED_PARQUET_PATH)
            except Exception:
                pass

        if PROCESSED_JSON_PATH.exists():
            logging.info(f"Loading preprocessed dataset from JSON: {PROCESSED_JSON_PATH}")
            return pd.read_json(PROCESSED_JSON_PATH)

        raw_df = self.fetch_raw_dataset()
        clean_df = self.clean_and_transform_dataframe(raw_df)
        self.save_processed_dataset(clean_df)
        return clean_df

if __name__ == "__main__":
    ingestor = ZomatoDatasetIngestor()
    df = ingestor.load_processed_dataset()
    print(f"Loaded {len(df)} restaurant records.")
    print(df.head(2))
