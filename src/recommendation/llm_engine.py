"""
LLM Recommendation & Reasoning Engine (Phase 5).
Combines CandidateFilterEngine output with Groq LLM API (llama-3.3-70b-versatile)
to generate top-5 personalized restaurant recommendations with natural language AI explanations.
Falls back to OfflineFallbackEngine when LLM API is unavailable.
"""
import json
import time
import logging
from typing import List, Dict, Any, Optional

from src.config import GROQ_API_KEY, GROQ_LLM_MODEL
from src.input.preference_handler import UserPreferenceRequest
from src.recommendation.groq_rate_limiter import GroqRateLimiter
from src.recommendation.offline_fallback import OfflineFallbackEngine

logging.basicConfig(level=logging.INFO)

try:
    import groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

class ZomatoRecommendationEngine:
    """AI Restaurant Recommendation Engine powered by Groq LLM Reasoning."""

    def __init__(self):
        self.rate_limiter = GroqRateLimiter()
        self.fallback_engine = OfflineFallbackEngine()
        self.has_groq_sdk = HAS_GROQ and bool(GROQ_API_KEY and not GROQ_API_KEY.startswith("your_"))

        if self.has_groq_sdk:
            self.client = groq.Groq(api_key=GROQ_API_KEY)
            logging.info(f"✅ ZomatoRecommendationEngine initialized with Groq LLM API ({GROQ_LLM_MODEL}).")
        else:
            self.client = None
            logging.info("ℹ️ ZomatoRecommendationEngine initialized with OfflineFallbackEngine (no LLM key).")

    def build_prompt(
        self,
        user_pref: UserPreferenceRequest,
        candidate_pool: List[Dict[str, Any]],
        top_n: int = 5
    ) -> str:
        """Constructs RAG prompt with user criteria and top candidate JSON block."""

        simplified_candidates = []
        for c in candidate_pool:
            cuisines = c.get("cuisines", [])
            if hasattr(cuisines, "tolist"):
                cuisines = cuisines.tolist()
            elif not isinstance(cuisines, list):
                cuisines = list(cuisines) if cuisines else []

            highlights = c.get("highlights", [])
            if hasattr(highlights, "tolist"):
                highlights = highlights.tolist()
            elif not isinstance(highlights, list):
                highlights = list(highlights) if highlights else []

            simplified_candidates.append({
                "restaurant_id": str(c.get("restaurant_id", "")),
                "restaurant_name": str(c.get("restaurant_name", "")),
                "locality": str(c.get("locality", "")),
                "city": str(c.get("city", "")),
                "cuisines": [str(x) for x in cuisines],
                "rating": float(c.get("aggregate_rating")) if c.get("aggregate_rating") is not None else 4.0,
                "estimated_cost_for_two": f"₹{c.get('cost_for_two')}",
                "budget_tier": str(c.get("budget_tier", "medium")),
                "highlights": [str(x) for x in highlights]
            })

        candidate_json_str = json.dumps(simplified_candidates, indent=2)

        prompt = f"""You are Zomato AI, a premier culinary advisor.
Your job is to analyze the candidate restaurant list and select the top {top_n} recommendations that best fulfill the user's dining preferences.

USER PREFERENCES:
- Target Location: {user_pref.location}
- Target Budget: {user_pref.budget} (Estimated cost around ₹1500 for two)
- Minimum Rating Required: {user_pref.min_rating}
- Preferred Cuisines: {', '.join(user_pref.cuisine) if user_pref.cuisine else 'Any / Multi-Cuisine'}
- Additional Notes: {user_pref.additional_notes if user_pref.additional_notes else 'None'}

CANDIDATE RESTAURANTS DATA:
{candidate_json_str}

INSTRUCTIONS:
1. Select and rank the top {top_n} restaurants that best match the location, budget, rating, and cuisine criteria.
2. For each recommendation, provide a compelling 2-3 sentence AI explanation detailing WHY it matches the user's exact criteria.
3. Return ONLY a valid JSON object matching the exact format below, with NO markdown wrap outside the JSON.

REQUIRED JSON OUTPUT FORMAT:
{{
  "recommendations": [
    {{
      "rank": 1,
      "restaurant_name": "Exact Name From Data",
      "cuisines": ["Cuisine1", "Cuisine2"],
      "rating": 4.5,
      "estimated_cost_for_two": "₹1500",
      "locality": "Bellandur",
      "ai_explanation": "Detailed 2-3 sentence explanation why this restaurant is recommended."
    }}
  ]
}}
"""
        return prompt

    def generate_fallback_recommendations(
        self,
        candidate_pool: List[Dict[str, Any]],
        user_pref: UserPreferenceRequest,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """Generates structured recommendation cards if LLM API key is unavailable."""
        recs = []
        for rank, c in enumerate(candidate_pool[:top_n], 1):
            cuisines = c.get("cuisines", [])
            if hasattr(cuisines, "tolist"):
                cuisines = cuisines.tolist()
            elif not isinstance(cuisines, list):
                cuisines = list(cuisines) if cuisines else []
            cuisines_list = [str(x) for x in cuisines]

            highlights = c.get("highlights", [])
            if hasattr(highlights, "tolist"):
                highlights = highlights.tolist()
            elif not isinstance(highlights, list):
                highlights = list(highlights) if highlights else []
            highlights_list = [str(x) for x in highlights]

            cuisines_str = ", ".join(cuisines_list) if cuisines_list else "Multi-Cuisine"
            loc = str(c.get("locality", user_pref.location))
            cost = int(c.get("cost_for_two", 1500))
            rating = float(c.get("aggregate_rating", 4.2))
            highlights_str = ", ".join(highlights_list[:2]) if highlights_list else "Great food"

            explanation = (
                f"{c.get('restaurant_name')} in {loc} is an outstanding choice matching your rating threshold of {user_pref.min_rating}! "
                f"With a {rating} rating and estimated cost of ₹{cost} for two, it offers delicious {cuisines_str} "
                f"highlighted by {highlights_str}."
            )

            recs.append({
                "rank": rank,
                "restaurant_name": str(c.get("restaurant_name")),
                "cuisines": cuisines_list,
                "rating": rating,
                "estimated_cost_for_two": f"₹{cost}",
                "locality": loc,
                "ai_explanation": explanation
            })
        return recs

    def recommend(
        self,
        user_pref: UserPreferenceRequest,
        candidate_pool: List[Dict[str, Any]],
        top_n: int = 5
    ) -> Dict[str, Any]:
        """Generates top-N AI recommendations given user preferences and candidate pool."""
        start_time = time.time()

        if not candidate_pool:
            return {
                "status": "success",
                "location": user_pref.location,
                "recommendations": [],
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }

        prompt = self.build_prompt(user_pref, candidate_pool, top_n=top_n)

        if self.has_groq_sdk and self.client:
            models_to_try = [GROQ_LLM_MODEL, "qwen/qwen3.6-27b", "groq/compound", "openai/gpt-oss-20b"]

            def make_api_call():
                last_err = None
                for model_name in models_to_try:
                    try:
                        completion = self.client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": "You are Zomato AI, a premier culinary advisor. Respond exclusively in valid JSON format matching the schema."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.3,
                            response_format={"type": "json_object"}
                        )
                        logging.info(f"✅ Groq API successfully called with model: {model_name}")
                        return completion.choices[0].message.content
                    except Exception as e:
                        last_err = e
                        if "404" in str(e) or "400" in str(e) or "model" in str(e).lower():
                            logging.warning(f"Model {model_name} failed ({e}). Trying next model...")
                            continue
                        raise e
                raise last_err

            try:
                raw_json = self.rate_limiter.execute_with_retry(
                    make_api_call,
                    max_retries=3,
                    estimated_tokens=self.rate_limiter.estimate_tokens(prompt)
                )
                parsed = json.loads(raw_json)
                recs = parsed.get("recommendations", [])
                logging.info(f"✅ Successfully generated {len(recs)} AI recommendations using Groq ({GROQ_LLM_MODEL}).")
            except Exception as e:
                logging.warning(f"⚠️ Groq LLM API call error ({e}). Delegating to OfflineFallbackEngine...")
                recs = self.fallback_engine.recommend(candidate_pool, user_pref, top_n=top_n)
        else:
            recs = self.fallback_engine.recommend(candidate_pool, user_pref, top_n=top_n)

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "status": "success",
            "location": user_pref.location,
            "min_rating": user_pref.min_rating,
            "budget": user_pref.budget,
            "total_candidates_evaluated": len(candidate_pool),
            "recommendations": recs[:top_n],
            "latency_ms": elapsed_ms
        }
