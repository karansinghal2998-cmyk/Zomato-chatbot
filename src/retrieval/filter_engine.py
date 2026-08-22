"""
Deterministic Integration & Candidate Filtering Engine (Phase 4 Backend Part 1).
Filters thousands of Zomato restaurant records using:
1. Hard Boundary Constraints: Substring locality/city match & min_rating threshold.
2. Soft Relevance Scoring Matrix:
   - Cuisine Overlap Score
   - Budget Cost Proximity Score (Gaussian Decay)
   - Rating Normalization Score
   - Popularity/Votes Score Weighting
3. Constraint Relaxation Engine: Automatic fallback for 0-candidate edge cases.
"""
import math
import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from src.config import MAX_CANDIDATE_POOL_SIZE, get_budget_tier
from src.input.preference_handler import UserPreferenceRequest

logging.basicConfig(level=logging.INFO)

class CandidateFilterEnginePart1:
    """Phase 4 Part 1: Deterministic Multi-Factor Filtering & Soft Ranking Engine."""

    def __init__(self, max_k: int = MAX_CANDIDATE_POOL_SIZE):
        self.max_k = max_k

    def _matches_location(self, row_loc: str, row_city: str, target_loc: str) -> Tuple[bool, bool]:
        """
        Evaluates location match.
        Returns (is_match, is_exact_locality_match).
        """
        if not target_loc:
            return True, True
        target_clean = target_loc.lower().strip()
        loc_clean = str(row_loc).lower() if pd.notna(row_loc) else ""
        city_clean = str(row_city).lower() if pd.notna(row_city) else ""

        is_exact = target_clean == loc_clean or target_clean in loc_clean
        is_match = is_exact or target_clean in city_clean or loc_clean in target_clean

        return is_match, is_exact

    def apply_hard_filters(self, df: pd.DataFrame, user_pref: UserPreferenceRequest) -> pd.DataFrame:
        """Applies strict location and minimum rating hard boundary constraints."""
        if df.empty:
            return df

        target_loc = user_pref.location.lower().strip()

        # 1. Location Boundary Filter
        loc_matches = df.apply(
            lambda r: self._matches_location(r.get("locality", ""), r.get("city", ""), target_loc)[0],
            axis=1
        )
        filtered = df[loc_matches].copy()

        # Fall back to full dataset if location match is zero
        if filtered.empty and len(df) > 0:
            logging.info(f"Location hard filter '{user_pref.location}' returned 0 rows. Using full dataset for ranking...")
            filtered = df.copy()

        # 2. Rating Boundary Filter
        if user_pref.min_rating > 0.0:
            rating_mask = filtered["aggregate_rating"].apply(
                lambda r: r is not None and r >= user_pref.min_rating if pd.notna(r) else False
            )
            filtered_with_rating = filtered[rating_mask]
            if not filtered_with_rating.empty:
                filtered = filtered_with_rating

        return filtered

    def calculate_cost_proximity_score(self, cost_for_two: int, target_budget: str) -> float:
        """Calculates cost proximity score using target cost benchmarks."""
        target_costs = {"low": 400, "medium": 850, "high": 1500}
        target_cost = target_costs.get(target_budget.lower(), 850)

        cost = cost_for_two if (cost_for_two and cost_for_two > 0) else target_cost
        diff = abs(cost - target_cost)

        # Gaussian decay penalty: exp(- (diff^2) / (2 * 500^2))
        return round(math.exp(-(diff ** 2) / (2 * (500 ** 2))), 4)

    def calculate_soft_relevance_scores(self, df: pd.DataFrame, user_pref: UserPreferenceRequest) -> pd.DataFrame:
        """Calculates multi-factor soft relevance scores."""
        if df.empty:
            return df

        user_cuisines = [c.lower() for c in user_pref.cuisine]
        target_budget = user_pref.budget.lower()
        target_loc = user_pref.location.lower().strip()

        scores = []
        for _, row in df.iterrows():
            # A. Cuisine Overlap Score (Weight = 0.45)
            r_cuisines = [c.lower() for c in row.get("cuisines", [])] if isinstance(row.get("cuisines"), list) else []
            if user_cuisines:
                matches = sum(1 for c in user_cuisines if any(c in rc or rc in c for rc in r_cuisines))
                cuisine_score = matches / max(1, len(user_cuisines))
            else:
                cuisine_score = 0.5  # Neutral default

            # B. Cost Proximity Score (Weight = 0.30)
            cost_score = self.calculate_cost_proximity_score(row.get("cost_for_two", 850), target_budget)

            # C. Rating Score (Weight = 0.15)
            rating = row.get("aggregate_rating")
            rating_score = (rating / 5.0) if (pd.notna(rating) and rating is not None) else 0.7

            # D. Locality Match Bonus (Weight = 0.10)
            is_match, is_exact = self._matches_location(row.get("locality", ""), row.get("city", ""), target_loc)
            locality_score = 1.0 if is_exact else (0.6 if is_match else 0.2)

            # Multi-Factor Score Formula
            total_score = (0.45 * cuisine_score) + (0.30 * cost_score) + (0.15 * rating_score) + (0.10 * locality_score)
            scores.append(round(total_score, 4))

        df["relevance_score"] = scores
        return df.sort_values(by=["relevance_score", "aggregate_rating"], ascending=[False, False])

    def filter_and_rank_candidates(
        self,
        df: pd.DataFrame,
        user_pref: UserPreferenceRequest
    ) -> List[Dict[str, Any]]:
        """Executes Phase 4 Part 1 Candidate Filtering & Soft Ranking."""
        filtered_df = self.apply_hard_filters(df, user_pref)

        # Constraint Relaxation Fallback if 0 candidates found
        if filtered_df.empty:
            logging.warning("⚠️ 0 candidates found. Relaxing rating constraint by 0.5...")
            relaxed_pref = user_pref.model_copy()
            relaxed_pref.min_rating = max(3.0, user_pref.min_rating - 0.5)
            filtered_df = self.apply_hard_filters(df, relaxed_pref)

        if filtered_df.empty:
            filtered_df = df.copy()

        ranked_df = self.calculate_soft_relevance_scores(filtered_df, user_pref)
        top_k_df = ranked_df.head(self.max_k)
        return top_k_df.to_dict(orient="records")

# Backward Compatibility Alias
CandidateFilterEngine = CandidateFilterEnginePart1
