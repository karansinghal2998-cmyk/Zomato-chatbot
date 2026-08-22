"""
FastAPI Production Server for Zomato AI Restaurant Recommendation Engine (Phase 6).
Exposes RESTful endpoints:
- POST /api/v1/recommend: Generates AI-ranked restaurant recommendations with Groq explanations.
- GET /api/v1/locations: Returns list of supported localities.
- GET /api/v1/health: Health check status endpoint.
- GET /: Serves the interactive Web Frontend UI.
"""
import logging
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

# Global Module Instances
ingestor = ZomatoDatasetIngestor()
dataset_df = ingestor.load_processed_dataset()
preference_handler = PreferenceHandler()
filter_engine = CandidateFilterEngine(max_k=10)
recommendation_engine = ZomatoRecommendationEngine()

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
        description="AI-powered restaurant recommendation engine combining Hugging Face telemetry and Groq LLM reasoning."
    )

    # Enable CORS for frontend web integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static frontend assets if directory exists
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    static_dir = frontend_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/api/v1/health")
    def health_check():
        return {
            "status": "healthy",
            "model": GROQ_LLM_MODEL,
            "dataset": HUGGINGFACE_DATASET_ID,
            "total_restaurants_indexed": len(dataset_df)
        }

    @app.get("/api/v1/locations", response_model=LocationResponse)
    def get_locations():
        if "locality" in dataset_df.columns:
            unique_locs = sorted(list(set(dataset_df["locality"].dropna().astype(str))))
        else:
            unique_locs = ["Bellandur", "Indiranagar", "Koramangala", "Connaught Place", "Janpath"]
        return {"locations": unique_locs, "total": len(unique_locs)}

    @app.post("/api/v1/recommend", response_model=APIRecommendationResponse)
    def generate_recommendations(user_pref: UserPreferenceRequest):
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
        uvicorn.run(app, host="0.0.0.0", port=8000)
