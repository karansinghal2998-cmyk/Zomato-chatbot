"""
Daily Dataset Refresh Cron Script (Phase 8).
Downloads the latest Zomato restaurant dataset from Hugging Face Hub
and updates the local processed parquet and JSON files.

Triggered by:
  - GitHub Actions scheduled cron (daily at 05:00 UTC / 10:30 IST)
  - Manual: python -m src.scheduler.daily_refresh_cron
"""
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in PYTHONPATH when run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.loader import ZomatoDatasetIngestor
from src.config import PROCESSED_PARQUET_PATH, PROCESSED_JSON_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


def run_daily_refresh() -> bool:
    """
    Executes the full dataset refresh pipeline:
    1. Downloads fresh data from Hugging Face Hub
    2. Cleans and normalizes fields
    3. Overwrites the processed parquet & JSON files

    Returns:
        True if refresh completed successfully, False otherwise.
    """
    start_time = time.time()
    utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    logger.info("=" * 60)
    logger.info(f"🔄 Zomato Daily Dataset Refresh — {utc_now}")
    logger.info("=" * 60)

    try:
        ingestor = ZomatoDatasetIngestor()

        # Force a fresh fetch from Hugging Face (bypass cached parquet)
        logger.info("📥 Fetching fresh dataset from Hugging Face Hub...")
        raw_df = ingestor.fetch_raw_dataset()
        logger.info(f"   ↳ Raw dataset: {len(raw_df)} rows fetched.")

        logger.info("🧹 Cleaning and normalizing dataset...")
        clean_df = ingestor.clean_and_transform_dataframe(raw_df)
        logger.info(f"   ↳ Clean dataset: {len(clean_df)} validated restaurant records.")

        logger.info("💾 Saving updated dataset to disk...")
        ingestor.save_processed_dataset(clean_df)
        logger.info(f"   ↳ Parquet: {PROCESSED_PARQUET_PATH}")
        logger.info(f"   ↳ JSON:    {PROCESSED_JSON_PATH}")

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"✅ Daily refresh completed successfully in {elapsed}s.")
        logger.info(f"   ↳ Total restaurants indexed: {len(clean_df)}")
        return True

    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        logger.error(f"❌ Daily refresh FAILED after {elapsed}s: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_daily_refresh()
    sys.exit(0 if success else 1)
