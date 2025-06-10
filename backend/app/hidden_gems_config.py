"""
Hidden gems: configurable filters and serendipity score.
True hidden gems = high quality, LOW popularity / moderate vote count (not blockbusters).
Same formula in backend and (if shown) frontend. Env-based tuning.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Configurable via env (tune without code changes)
# TMDB popularity: blockbusters can be 50–800+; keep max low so we get under-exposed titles
HIDDEN_GEMS_MAX_POPULARITY = float(os.getenv("HIDDEN_GEMS_MAX_POPULARITY", "25.0"))
# Exclude blockbusters: max vote_count so we don't show Inception/Star Wars–level titles
HIDDEN_GEMS_MAX_VOTE_COUNT = int(os.getenv("HIDDEN_GEMS_MAX_VOTE_COUNT", "4000"))
HIDDEN_GEMS_MIN_VOTE_COUNT = int(os.getenv("HIDDEN_GEMS_MIN_VOTE_COUNT", "100"))
HIDDEN_GEMS_MIN_RATING = float(os.getenv("HIDDEN_GEMS_MIN_RATING", "7.0"))
# Cap popularity for normalization (TMDB can be 0–800+)
HIDDEN_GEMS_POP_CAP = float(os.getenv("HIDDEN_GEMS_POP_CAP", "100.0"))
# Vote count cap for "under-exposed" factor (lower votes = more hidden when rating is good)
HIDDEN_GEMS_VC_CAP = float(os.getenv("HIDDEN_GEMS_VC_CAP", "5000.0"))


def serendipity_score(
    popularity: float,
    vote_count: int,
    vote_average: float,
    relevance_to_user: float = 1.0,
) -> float:
    """
    Serendipity = high quality, low popularity, moderate vote count (not blockbusters).
    Formula: relevance * vote_quality * (1 - norm_pop) * (1 - norm_vc).
    Rewards lower popularity AND lower vote_count so we don't surface mega-hit blockbusters.
    """
    pop = max(0.0, float(popularity or 0))
    vc = max(0, int(vote_count or 0))
    va = max(0.0, min(10.0, float(vote_average or 0)))
    rel = max(0.0, min(1.0, float(relevance_to_user or 1.0)))
    cap_pop = max(0.1, HIDDEN_GEMS_POP_CAP)
    cap_vc = max(1.0, HIDDEN_GEMS_VC_CAP)
    norm_pop = min(1.0, pop / cap_pop)
    norm_vc = min(1.0, vc / cap_vc)  # lower votes = more "hidden"
    vote_quality = (va / 10.0) * min(1.0, (vc + 1) / 300)  # enough votes to be reliable, not blockbuster
    return rel * vote_quality * (1.0 - norm_pop) * (1.0 - norm_vc * 0.5)  # 0.5 so vote_count doesn't dominate


def passes_hidden_gems_filters(
    popularity: float,
    vote_count: int,
    vote_average: float,
) -> bool:
    """True if movie passes: good rating, not too popular, not a blockbuster (vote_count cap)."""
    pop = float(popularity or 0)
    vc = int(vote_count or 0)
    va = float(vote_average or 0)
    if pop > HIDDEN_GEMS_MAX_POPULARITY:
        return False
    if vc < HIDDEN_GEMS_MIN_VOTE_COUNT:
        return False
    if vc > HIDDEN_GEMS_MAX_VOTE_COUNT:
        return False
    if va < HIDDEN_GEMS_MIN_RATING:
        return False
    return True


def get_hidden_gems_config() -> Dict[str, Any]:
    """Expose config for frontend (same formula description, no secrets)."""
    return {
        "max_popularity": HIDDEN_GEMS_MAX_POPULARITY,
        "max_vote_count": HIDDEN_GEMS_MAX_VOTE_COUNT,
        "min_vote_count": HIDDEN_GEMS_MIN_VOTE_COUNT,
        "min_rating": HIDDEN_GEMS_MIN_RATING,
        "formula": "relevance * vote_quality * (1 - norm_pop) * (1 - 0.5*norm_vc)",
    }
