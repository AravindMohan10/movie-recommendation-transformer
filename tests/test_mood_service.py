"""
Unit tests for mood→criteria: schema validation and fallback (no LLM).
Fixed prompts/fallback so changes don't regress.
"""

import os
import sys
from pathlib import Path

# Project root and backend/app
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend" / "app"))

# Ensure we don't call LLM in tests
os.environ.pop("GROQ_API_KEY", None)


def test_mood_criteria_schema():
    """MoodCriteria accepts valid payload and normalizes."""
    from mood_service import MoodCriteria
    c = MoodCriteria(genres=["Drama", "Comedy"], keywords=["cozy"], min_year=1990, max_year=2020)
    assert c.genres == ["drama", "comedy"]
    assert c.keywords == ["cozy"]
    assert c.min_year == 1990
    assert c.max_year == 2020
    c2 = MoodCriteria(genres=[], keywords=[])
    assert c2.genres == [] and c2.keywords == []


def test_fallback_mood_to_criteria():
    """Fallback returns valid MoodCriteria for common phrases (no LLM)."""
    from mood_service import _fallback_mood_to_criteria
    c = _fallback_mood_to_criteria("something cozy for a rainy day")
    assert c is not None
    assert "cozy" in c.keywords or "comfort" in c.keywords
    assert "drama" in c.genres or "comedy" in c.genres
    c2 = _fallback_mood_to_criteria("action thriller")
    assert c2 is not None
    assert "action" in [g.lower() for g in c2.genres]
    c3 = _fallback_mood_to_criteria("random gibberish xyz")
    assert c3 is not None
    assert len(c3.keywords) >= 1  # uses input as keyword


def test_mood_to_criteria_no_llm_uses_fallback():
    """When GROQ_API_KEY not set, mood_to_criteria uses fallback."""
    from mood_service import mood_to_criteria
    # With no key, should get fallback
    c = mood_to_criteria("cozy comedy")
    assert c is not None
    assert isinstance(c.genres, list) and isinstance(c.keywords, list)
