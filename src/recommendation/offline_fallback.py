"""
Offline Fallback Recommendation Engine (Phase 5).
Standalone rule-based recommendation module activated when Groq LLM API
is unavailable (rate limits exceeded, missing API key, or network errors).
Generates structured recommendation cards from candidate pool without any LLM call.
"""
import logging
from typing import List, Dict, Any

from src.input.preference_handler import UserPreferenceRequest

logging.basicConfig(level=logging.INFO)


class OfflineFallbackEngine:
    """
    Rule-based restaurant recommendation engine.
    Activated as a fallback when Groq LLM API is unreachable or rate-limited.
    Produces deterministic, structured recommendation cards directly from
    the ranked candidate pool using heuristic explanation templates.
    """

    HIGHLIGHT_TEMPLATES = [
        "Known for {highlights}, it is a popular dining destination in {locality}.",
        "Guests love {highlights} — making it a standout in {locality}.",
        "It stands out with {highlights}, ideal for a memorable dining experience.",
    ]

    def generate_explanation(
        self,
        restaurant: Dict[str, Any],
        user_pref: UserPreferenceRequest,
        rank: int
    ) -> str:
        """Generates a deterministic, human-readable recommendation explanation."""
        name = str(restaurant.get("restaurant_name", "This restaurant"))
        loc = str(restaurant.get("locality", user_pref.location))
        cost = int(restaurant.get("cost_for_two", 1000))
        rating = float(restaurant.get("aggregate_rating", 4.0))
        budget_tier = str(restaurant.get("budget_tier", user_pref.budget))

        cuisines = restaurant.get("cuisines", [])
        if hasattr(cuisines, "tolist"):
            cuisines = cuisines.tolist()
        elif not isinstance(cuisines, list):
            cuisines = list(cuisines) if cuisines else []
        cuisines_list = [str(c) for c in cuisines]
        cuisines_str = ", ".join(cuisines_list) if cuisines_list else "Multi-Cuisine"

        highlights = restaurant.get("highlights", [])
        if hasattr(highlights, "tolist"):
            highlights = highlights.tolist()
        elif not isinstance(highlights, list):
            highlights = list(highlights) if highlights else []
        highlights_list = [str(h) for h in highlights]
        highlights_str = ", ".join(highlights_list[:3]) if highlights_list else "excellent food quality"

        # Cuisine match note
        user_cuisines = [c.lower() for c in (user_pref.cuisine or [])]
        matched = [c for c in cuisines_list if c.lower() in user_cuisines]
        cuisine_match_note = (
            f"It matches your preference for {', '.join(matched)} cuisine. "
            if matched else ""
        )

        # Budget commentary
        budget_note = {
            "low": f"At ₹{cost} for two, it is very budget-friendly.",
            "medium": f"At ₹{cost} for two, it offers great value for money.",
            "high": f"At ₹{cost} for two, it delivers a premium dining experience.",
        }.get(budget_tier, f"Estimated cost ₹{cost} for two.")

        explanation = (
            f"{name} in {loc} is an excellent choice with a strong rating of {rating}/5, "
            f"comfortably meeting your minimum rating threshold of {user_pref.min_rating}. "
            f"{cuisine_match_note}"
            f"{budget_note} "
            f"{highlights_str.capitalize()} make it a highly recommended spot."
        )
        return explanation

    def recommend(
        self,
        candidate_pool: List[Dict[str, Any]],
        user_pref: UserPreferenceRequest,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generates structured top-N recommendation cards from candidate pool.

        Args:
            candidate_pool: Pre-filtered, ranked list of restaurant dicts.
            user_pref: Sanitized user preference request.
            top_n: Maximum number of recommendations to return.

        Returns:
            List of recommendation card dicts matching API response schema.
        """
        logging.info(
            f"🔄 OfflineFallbackEngine generating {top_n} recommendations "
            f"from {len(candidate_pool)} candidates (no LLM)."
        )

        recs = []
        for rank, restaurant in enumerate(candidate_pool[:top_n], start=1):
            cuisines = restaurant.get("cuisines", [])
            if hasattr(cuisines, "tolist"):
                cuisines = cuisines.tolist()
            elif not isinstance(cuisines, list):
                cuisines = list(cuisines) if cuisines else []
            cuisines_list = [str(c) for c in cuisines]

            cost = int(restaurant.get("cost_for_two", 1000))
            rating = float(restaurant.get("aggregate_rating", 4.0))
            loc = str(restaurant.get("locality", user_pref.location))

            recs.append({
                "rank": rank,
                "restaurant_name": str(restaurant.get("restaurant_name", f"Restaurant {rank}")),
                "cuisines": cuisines_list,
                "rating": rating,
                "estimated_cost_for_two": f"₹{cost}",
                "locality": loc,
                "ai_explanation": self.generate_explanation(restaurant, user_pref, rank),
            })

        logging.info(f"✅ OfflineFallbackEngine produced {len(recs)} recommendation cards.")
        return recs
