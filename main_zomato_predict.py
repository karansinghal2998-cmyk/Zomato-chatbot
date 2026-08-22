"""
Main Prediction & Demonstration Script for Zomato AI Restaurant Recommendation Engine.
Executes candidate retrieval and Groq LLM reasoning for the user's input:
- Location: Bellandur
- Rating: >= 4.2
- Budget: ₹1500 (High / Medium)
"""
import json
import logging
from src.ingestion.loader import ZomatoDatasetIngestor
from src.input.preference_handler import UserPreferenceRequest, PreferenceHandler
from src.retrieval.filter_engine import CandidateFilterEngine
from src.recommendation.llm_engine import ZomatoRecommendationEngine

logging.basicConfig(level=logging.INFO)

def run_prediction():
    print("=================================================================")
    print("🍽️ ZOMATO AI RESTAURANT RECOMMENDATION ENGINE (GROQ LLM)")
    print("   Target Model: llama-3.3-70b-versatile")
    print("=================================================================\n")

    # 1. Load Preprocessed Dataset
    ingestor = ZomatoDatasetIngestor()
    dataset_df = ingestor.load_processed_dataset()

    # 2. Parse User Preferences
    handler = PreferenceHandler()
    user_input = {
        "location": "Bellandur",
        "budget": "high",  # ₹1500 cost for two
        "min_rating": 4.2,
        "additional_notes": "Great food, vibrant ambiance, suitable for group dinner"
    }

    user_pref = handler.sanitize_and_parse(user_input)

    print(f"📋 USER INPUT PREFERENCES:")
    print(f"   - Location   : {user_pref.location}")
    print(f"   - Min Rating : {user_pref.min_rating}")
    print(f"   - Budget     : {user_pref.budget} (Approx ₹1500 for two)")
    print(f"   - Notes      : \"{user_pref.additional_notes}\"\n")

    # 3. Filter Candidates
    filter_engine = CandidateFilterEngine(max_k=10)
    candidate_pool = filter_engine.filter_and_rank_candidates(dataset_df, user_pref)

    print(f"🔍 CANDIDATE FILTERING RESULT:")
    print(f"   - Retrieved {len(candidate_pool)} relevant candidate restaurants in Bellandur.\n")

    # 4. Generate AI LLM Recommendations
    engine = ZomatoRecommendationEngine()
    response = engine.recommend(user_pref, candidate_pool, top_n=5)

    print("=================================================================")
    print("🤖 TOP 5 AI-GENERATED RESTAURANT RECOMMENDATIONS")
    print(f"   (Latency: {response['latency_ms']} ms)")
    print("=================================================================\n")

    for rec in response["recommendations"]:
        print(f"-----------------------------------------------------------------")
        print(f"Rank #{rec['rank']}: 🏆 {rec['restaurant_name']}")
        print(f"📍 Locality    : {rec['locality']}")
        print(f"⭐ Rating      : {rec['rating']} / 5.0")
        print(f"💵 Est. Cost   : {rec['estimated_cost_for_two']} for two")
        print(f"🍱 Cuisines    : {', '.join(rec['cuisines'])}")
        print(f"💡 AI Reason   : {rec['ai_explanation']}")
        print(f"-----------------------------------------------------------------\n")

    print("=================================================================")
    print("🎉 ZOMATO AI RECOMMENDATION PREDICTION COMPLETED!")
    print("=================================================================")

    # Save output report
    output_file = "data/outputs/bellandur_top5_recommendations.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(response, f, indent=2)
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    run_prediction()
