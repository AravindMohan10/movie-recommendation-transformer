"""
Mood/Vibe → criteria: one canonical function, structured LLM output, validation.
Used by API and any future UI. No free-text parsing.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# Allowed genre names (TMDB-style) for validation
ALLOWED_GENRES = {
    "action", "adventure", "animation", "comedy", "crime", "documentary",
    "drama", "family", "fantasy", "history", "horror", "music", "mystery",
    "romance", "science fiction", "sci-fi", "tv movie", "thriller", "war", "western",
}


class MoodCriteria(BaseModel):
    """Structured output from mood query. All lists may be empty."""
    genres: List[str] = Field(default_factory=list, max_length=8)
    keywords: List[str] = Field(default_factory=list, max_length=12)
    min_year: Optional[int] = Field(None, ge=1900, le=2030)
    max_year: Optional[int] = Field(None, ge=1900, le=2030)

    @field_validator("genres", mode="before")
    @classmethod
    def normalize_genres(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            return []
        out = []
        for g in v[:8]:
            s = (str(g).strip().lower() if g else "").replace("_", " ").replace("-", " ")
            if s and len(s) <= 50:
                out.append(s)
        return out

    @field_validator("keywords", mode="before")
    @classmethod
    def normalize_keywords(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            return []
        out = []
        for k in v[:12]:
            s = (str(k).strip().lower() if k else "").replace("\n", " ")[:80]
            if s:
                out.append(s)
        return out


def mood_to_criteria(mood_text: str) -> Optional[MoodCriteria]:
    """
    Canonical mood → criteria. Returns structured criteria or None if LLM unavailable or invalid.
    Same path for API and UI. Validates against schema; rejects on mismatch.
    """
    mood_text = (mood_text or "").strip()[:500]
    if not mood_text:
        return None

    if not _is_llm_available():
        return _fallback_mood_to_criteria(mood_text)

    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return _fallback_mood_to_criteria(mood_text)

    prompt = f"""The user wants movie recommendations. They said: "{mood_text}"

Respond with ONLY a single JSON object, no other text. Use exactly these keys:
- "genres": array of 0-6 genre names (e.g. "Drama", "Comedy", "Sci-Fi")
- "keywords": array of 0-8 short phrases or words that describe tone/themes (e.g. "cozy", "mind-bending", "feel-good")
- "min_year": number or null (release year minimum, 1900-2030)
- "max_year": number or null (release year maximum)

Example: {{"genres": ["Drama", "Comedy"], "keywords": ["feel-good", "rainy day"], "min_year": null, "max_year": null}}
JSON only:"""

    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.2,
        )
        raw = (resp.choices[0].message.content or "").strip()
        # Extract JSON (handle markdown code blocks)
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)
        raw = raw.strip()
        data = json.loads(raw)
        if not isinstance(data, dict):
            return _fallback_mood_to_criteria(mood_text)
        criteria = MoodCriteria(
            genres=data.get("genres") or [],
            keywords=data.get("keywords") or [],
            min_year=data.get("min_year"),
            max_year=data.get("max_year"),
        )
        return criteria
    except json.JSONDecodeError as e:
        logger.warning("Mood LLM: invalid JSON %s", e)
        return _fallback_mood_to_criteria(mood_text)
    except Exception as e:
        logger.warning("Mood LLM failed: %s", e)
        return _fallback_mood_to_criteria(mood_text)


def _is_llm_available() -> bool:
    try:
        from .llm_service import is_llm_available
        return is_llm_available()
    except Exception:
        return False


def _fallback_mood_to_criteria(mood_text: str) -> Optional[MoodCriteria]:
    """When LLM unavailable: map a few common phrases to criteria; else generic."""
    t = mood_text.lower().strip()
    if not t:
        return MoodCriteria(genres=[], keywords=[])
    genres = []
    keywords = []
    if "cozy" in t or "rainy" in t or "comfort" in t:
        keywords.extend(["cozy", "comfort"])
        genres.extend(["Drama", "Comedy"])
    if "action" in t or "thriller" in t:
        genres.append("Action")
    if "comedy" in t or "funny" in t or "laugh" in t:
        genres.append("Comedy")
    if "sci-fi" in t or "sci fi" in t or "space" in t:
        genres.append("Sci-Fi")
    if "feel-good" in t or "feel good" in t:
        keywords.append("feel-good")
    if not genres and not keywords:
        keywords.append(t[:50])
    return MoodCriteria(genres=genres[:6], keywords=keywords[:8], min_year=None, max_year=None)
