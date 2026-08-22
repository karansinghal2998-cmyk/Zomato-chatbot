"""
Zomato AI Restaurant Recommendation System Configuration Module.
Defines environment settings, directory structures, Hugging Face dataset IDs,
Groq LLM model specs, and budget tier boundary constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Directory Layout Configuration
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = DATA_DIR / "outputs"

for d in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Hugging Face Dataset Configuration
HUGGINGFACE_DATASET_ID = os.getenv("HUGGINGFACE_DATASET_ID", "ManikaSaini/zomato-restaurant-recommendation")
PROCESSED_PARQUET_PATH = PROCESSED_DATA_DIR / "clean_zomato_restaurants.parquet"
PROCESSED_JSON_PATH = PROCESSED_DATA_DIR / "clean_zomato_restaurants.json"

# Groq LLM API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
GROQ_FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "qwen/qwen3.6-27b")

# Rate Limiting & Governor Thresholds for llama-3.3-70b-versatile
GROQ_MAX_RPM = 25       # Safe cap below 30 RPM limit
GROQ_MAX_TPM = 10000    # Safe cap below 12,000 TPM limit
GROQ_MAX_RPD = 1000     # Daily request limit
GROQ_MAX_TPD = 100000   # Daily token limit

# Candidate Filtering & Budget Boundaries
MAX_CANDIDATE_POOL_SIZE = int(os.getenv("MAX_CANDIDATES_POOL", "10"))

LOW_BUDGET_MAX_COST = 500       # <= ₹500 is Low Budget
MEDIUM_BUDGET_MAX_COST = 1200    # ₹501 - ₹1200 is Medium Budget, > ₹1200 is High Budget

def get_budget_tier(cost_for_two: int) -> str:
    """Categorizes cost for two into budget tiers: low, medium, or high."""
    if cost_for_two is None or cost_for_two <= 0:
        return "medium"  # Default fallback
    if cost_for_two <= LOW_BUDGET_MAX_COST:
        return "low"
    elif cost_for_two <= MEDIUM_BUDGET_MAX_COST:
        return "medium"
    else:
        return "high"
