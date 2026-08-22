"""
User Preference Input & Validation Module (Phase 3).
Defines Pydantic schemas for user dining preferences (Location, Budget, Cuisine, Min Rating, Notes),
performs input sanitization, and protects against prompt injection attacks.
"""
import re
import logging
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator

logging.basicConfig(level=logging.INFO)

# Pre-LLM Security Regex Guardrail for Prompt Injection Attacks
PROMPT_INJECTION_REGEX = re.compile(
    r'\b(?:ignore|override|bypass|disregard)\s+(?:all\s+)?(?:previous\s+)?(?:instructions|directives|prompts|rules)\b',
    re.IGNORECASE
)

class UserPreferenceRequest(BaseModel):
    """Pydantic model representing structured user dining preferences."""
    location: str = Field(..., description="Target city or locality (e.g., 'Indiranagar', 'Delhi', 'Bangalore')")
    budget: str = Field(default="medium", description="Budget tier: 'low', 'medium', or 'high'")
    cuisine: List[str] = Field(default_factory=list, description="List of preferred cuisines (e.g., ['Italian', 'Chinese'])")
    min_rating: float = Field(default=3.5, ge=0.0, le=5.0, description="Minimum rating threshold (0.0 to 5.0)")
    additional_notes: Optional[str] = Field(default="", description="Qualitative preferences (e.g., 'family friendly', 'rooftop seating')")

    @field_validator("location")
    @classmethod
    def sanitize_location(cls, v: str) -> str:
        if not v or not v.strip():
            return "Bangalore"  # Default fallback location
        return v.strip()

    @field_validator("budget")
    @classmethod
    def sanitize_budget(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            return "medium"
        clean = v.strip().lower()
        if clean in ["low", "cheap", "pocket friendly", "budget", "1", "$"]:
            return "low"
        elif clean in ["high", "expensive", "fine dining", "luxury", "3", "$$$"]:
            return "high"
        else:
            return "medium"

    @field_validator("cuisine")
    @classmethod
    def sanitize_cuisine(cls, v: Union[List[str], str]) -> List[str]:
        if not v:
            return []
        if isinstance(v, str):
            return [c.strip().title() for c in v.split(",") if c.strip()]
        return [str(c).strip().title() for c in v if str(c).strip()]

    @field_validator("additional_notes")
    @classmethod
    def sanitize_notes(cls, v: Optional[str]) -> str:
        if not v:
            return ""
        notes_str = str(v).strip()
        # Security Guardrail Check
        if PROMPT_INJECTION_REGEX.search(notes_str):
            logging.warning(f"🛡️ Security Alert: Prompt injection attempt scrubbed in user notes: '{notes_str}'")
            return "[Sanitized: User note removed due to safety policy]"
        return notes_str[:250]  # Limit length

class PreferenceHandler:
    """Handles preference aggregation, sanitization, and keyword extraction."""

    def sanitize_and_parse(self, input_data: Union[Dict[str, Any], UserPreferenceRequest]) -> UserPreferenceRequest:
        """Parses and sanitizes input data into a validated UserPreferenceRequest object."""
        if isinstance(input_data, UserPreferenceRequest):
            return input_data
        return UserPreferenceRequest(**input_data)

    def extract_search_keywords(self, user_pref: UserPreferenceRequest) -> List[str]:
        """Extracts normalized search tokens from location, cuisine, and notes."""
        tokens = set()
        tokens.add(user_pref.location.lower())

        for c in user_pref.cuisine:
            tokens.add(c.lower())

        if user_pref.additional_notes:
            for word in re.findall(r'\w+', user_pref.additional_notes.lower()):
                if len(word) > 3 and word not in ["want", "looking", "with", "good", "place"]:
                    tokens.add(word)

        return list(tokens)
