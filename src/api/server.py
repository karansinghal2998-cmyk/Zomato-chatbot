"""
FastAPI Production Server for Zomato AI Restaurant Recommendation Engine (Phase 6).
Exposes RESTful endpoints:
- POST /api/v1/recommend: Generates AI-ranked restaurant recommendations with Groq explanations.
- GET /api/v1/locations: Returns list of supported localities.
- GET /api/v1/health: Health check status endpoint.
- GET /: Serves the interactive Web Frontend UI.

Deployment: Railway (backend) + Vercel (frontend)
"""
import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, FileResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from src.config import GROQ_LLM_MODEL, HUGGINGFACE_DATASET_ID
from src.ingestion.loader import ZomatoDatasetIngestor
from src.input.preference_handler import UserPreferenceRequest, PreferenceHandler
from src.retrieval.filter_engine import CandidateFilterEngine
from src.recommendation.llm_engine import ZomatoRecommendationEngine

logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Global state — populated during startup lifespan (Railway-safe cold start)
# ---------------------------------------------------------------------------
_state: Dict[str, Any] = {}

def _load_dataset_background():
    """Background loader function to populate dataset without blocking web server boot."""
    try:
        logging.info("📥 Background dataset load starting...")
        ingestor = ZomatoDatasetIngestor()
        df = ingestor.load_processed_dataset()
        _state["dataset_df"] = df
        logging.info(f"✅ Background dataset load complete: {len(df)} restaurants indexed.")
    except Exception as e:
        logging.error(f"⚠️ Error in background dataset load: {e}")
        _state["dataset_df"] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise components on startup. Dataset loaded asynchronously to allow instant port binding."""
    logging.info("🚀 Zomato AI server starting — initializing engines...")
    _state["preference_handler"] = PreferenceHandler()
    _state["filter_engine"] = CandidateFilterEngine(max_k=10)
    _state["recommendation_engine"] = ZomatoRecommendationEngine()
    
    # Launch dataset loading in background thread (non-blocking for fast healthcheck)
    import threading
    threading.Thread(target=_load_dataset_background, daemon=True).start()
    
    yield
    logging.info("🛑 Zomato AI server shutting down.")
    _state.clear()

# ---------------------------------------------------------------------------
# CORS allowed origins — read from env for flexible Railway + Vercel config
# Set ALLOWED_ORIGINS env var as comma-separated list, e.g.:
#   https://zomato-chatbot.vercel.app,http://localhost:3000
# ---------------------------------------------------------------------------
def _get_cors_origins() -> List[str]:
    env_origins = os.getenv("ALLOWED_ORIGINS", "")
    if env_origins:
        return [o.strip() for o in env_origins.split(",") if o.strip()]
    # Default: allow all during initial deployment (tighten after live URLs are known)
    return ["*"]

class LocationResponse(BaseModel):
    locations: List[str]
    total: int

class RecommendationItem(BaseModel):
    rank: int
    restaurant_name: str
    locality: str
    rating: float
    estimated_cost_for_two: str
    cuisines: List[str]
    ai_explanation: str

class APIRecommendationResponse(BaseModel):
    status: str
    location: str
    min_rating: float
    budget: str
    total_candidates_evaluated: int
    recommendations: List[RecommendationItem]
    latency_ms: float

if HAS_FASTAPI:
    app = FastAPI(
        title="Zomato AI Restaurant Recommendation API",
        version="1.0.0",
        description="AI-powered restaurant recommendation engine combining Hugging Face telemetry and Groq LLM reasoning.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — origins driven by ALLOWED_ORIGINS env var (set on Railway dashboard)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Mount static frontend assets if directory exists
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    static_dir = frontend_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/health")
    @app.get("/api/v1/health")
    def health_check():
        dataset_df = _state.get("dataset_df")
        return {
            "status": "healthy",
            "model": GROQ_LLM_MODEL,
            "dataset": HUGGINGFACE_DATASET_ID,
            "total_restaurants_indexed": len(dataset_df) if dataset_df is not None else 0,
        }


    @app.get("/api/v1/locations", response_model=LocationResponse)
    def get_locations():
        dataset_df = _state.get("dataset_df")
        if dataset_df is not None and "locality" in dataset_df.columns:
            unique_locs = sorted(list(set(dataset_df["locality"].dropna().astype(str))))
        else:
            unique_locs = ["Bellandur", "Indiranagar", "Koramangala", "Whitefield",
                           "Jayanagar", "HSR Layout", "BTM", "Electronic City",
                           "Marathahalli", "Banashankari"]
        return {"locations": unique_locs, "total": len(unique_locs)}

    @app.post("/api/v1/recommend", response_model=APIRecommendationResponse)
    def generate_recommendations(user_pref: UserPreferenceRequest):
        dataset_df = _state.get("dataset_df")
        preference_handler = _state.get("preference_handler")
        filter_engine = _state.get("filter_engine")
        recommendation_engine = _state.get("recommendation_engine")
        if any(v is None for v in [dataset_df, preference_handler, filter_engine, recommendation_engine]):
            raise HTTPException(status_code=503, detail="Service initialising, please retry in a moment.")
        try:
            # 1. Sanitize request
            sanitized_pref = preference_handler.sanitize_and_parse(user_pref)

            # 2. Filter Top Candidates
            candidates = filter_engine.filter_and_rank_candidates(dataset_df, sanitized_pref)

            # 3. LLM Recommendation & Reasoning
            res = recommendation_engine.recommend(sanitized_pref, candidates, top_n=5)
            return res
        except Exception as e:
            logging.error(f"Recommendation API error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/", response_class=HTMLResponse)
    def serve_frontend():
        index_file = frontend_dir / "templates" / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return "<h1>Zomato AI Restaurant Recommendation Engine API</h1><p>Visit /docs for API documentation.</p>"
else:
    app = None

if __name__ == "__main__":
    import uvicorn
    if app:
        port = int(os.getenv("PORT", 8000))  # Railway injects $PORT
        uvicorn.run(app, host="0.0.0.0", port=port)
