"""
Movie journeys: ordered list of (movie_id, reason) with fixed taxonomy.
Reasons: director, theme, era. 3–5 films, each validated in catalog.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Fixed reason taxonomy for testability and localization
JOURNEY_REASONS = ("director", "theme", "era")
JOURNEY_MIN_LENGTH = 3
JOURNEY_MAX_LENGTH = 5


def get_journey(
    seed_movie_id: int,
    movie_data: Dict[Any, Any],
    valid_movie_ids: Optional[Set[int]] = None,
    max_steps: int = JOURNEY_MAX_LENGTH,
) -> List[Dict[str, Any]]:
    """
    Build a journey starting from seed_movie_id.
    Returns list of {movie_id, reason, reason_detail}, 3–5 steps.
    Each film must exist in movie_data and (if provided) valid_movie_ids.
    """
    max_steps = max(JOURNEY_MIN_LENGTH, min(JOURNEY_MAX_LENGTH, max_steps))
    journey: List[Dict[str, Any]] = []
    seen: Set[int] = set()
    valid = valid_movie_ids or set()

    def get_movie(mid: int) -> Optional[Dict]:
        m = movie_data.get(mid) or movie_data.get(str(mid)) or movie_data.get(int(mid))
        return m

    def in_catalog(mid: int) -> bool:
        if not get_movie(mid):
            return False
        if valid and mid not in valid:
            return False
        return True

    seed = get_movie(seed_movie_id)
    if not seed:
        return []
    journey.append({
        "movie_id": seed_movie_id,
        "reason": "seed",
        "reason_detail": "Starting point",
    })
    seen.add(seed_movie_id)

    # Collect directors and genres from seed for "director" and "theme" steps
    directors = _directors_from_movie(seed)
    genres = _genres_from_movie(seed)
    release_year = _year_from_movie(seed)

    # Next: same director (1 film)
    if directors and len(journey) < max_steps:
        for m in _movies_by_director(movie_data, directors[0], exclude=seen, valid=valid):
            if in_catalog(m.get("id") or m.get("tmdb_id")):
                mid = int(m.get("tmdb_id") or m.get("id"))
                if mid not in seen:
                    journey.append({
                        "movie_id": mid,
                        "reason": "director",
                        "reason_detail": f"Same director: {directors[0]}",
                    })
                    seen.add(mid)
                    break

    # Next: same theme/genre (1 film)
    if genres and len(journey) < max_steps:
        for m in _movies_by_genre(movie_data, genres[0], exclude=seen, valid=valid):
            if in_catalog(m.get("tmdb_id") or m.get("id")):
                mid = int(m.get("tmdb_id") or m.get("id"))
                if mid not in seen:
                    journey.append({
                        "movie_id": mid,
                        "reason": "theme",
                        "reason_detail": f"Same theme: {genres[0]}",
                    })
                    seen.add(mid)
                    break

    # Next: same era (1 film) if we have year
    if release_year and len(journey) < max_steps:
        for m in _movies_by_era(movie_data, release_year, exclude=seen, valid=valid):
            if in_catalog(m.get("tmdb_id") or m.get("id")):
                mid = int(m.get("tmdb_id") or m.get("id"))
                if mid not in seen:
                    journey.append({
                        "movie_id": mid,
                        "reason": "era",
                        "reason_detail": f"Same era: {release_year}s",
                    })
                    seen.add(mid)
                    break

    # Pad to at least JOURNEY_MIN_LENGTH with same-genre if needed
    while len(journey) < JOURNEY_MIN_LENGTH and genres:
        for m in _movies_by_genre(movie_data, genres[0], exclude=seen, valid=valid):
            mid = int(m.get("tmdb_id") or m.get("id"))
            if mid not in seen and in_catalog(mid):
                journey.append({
                    "movie_id": mid,
                    "reason": "theme",
                    "reason_detail": f"Theme: {genres[0]}",
                })
                seen.add(mid)
                break
        else:
            break

    return journey[:max_steps]


def _directors_from_movie(m: Dict) -> List[str]:
    out = []
    for p in (m.get("crew") or []):
        if isinstance(p, dict) and "director" in (p.get("job") or "").lower():
            n = p.get("name") or p.get("Name")
            if n:
                out.append(n)
    if not out and m.get("director"):
        out = [m["director"]] if isinstance(m["director"], str) else list(m.get("director") or [])
    return out[:3]


def _genres_from_movie(m: Dict) -> List[str]:
    gs = m.get("genres") or []
    out = []
    for g in gs:
        if isinstance(g, dict) and g.get("name"):
            out.append(g["name"])
        elif isinstance(g, str) and g:
            out.append(g)
    return out[:5]


def _year_from_movie(m: Dict) -> Optional[int]:
    rd = m.get("release_date") or m.get("release_year")
    if not rd:
        return None
    s = str(rd)[:4]
    if len(s) == 4 and s.isdigit():
        return int(s)
    return None


def _movies_by_director(
    movie_data: Dict[Any, Any],
    director: str,
    exclude: Set[int],
    valid: Set[int],
) -> List[Dict]:
    seen_mid: Set[int] = set()
    out = []
    for _k, m in movie_data.items():
        mid = m.get("tmdb_id") or m.get("id")
        if mid is None or int(mid) in seen_mid:
            continue
        if director in _directors_from_movie(m) and int(mid) not in exclude and (not valid or int(mid) in valid):
            seen_mid.add(int(mid))
            out.append(m)
    return out[:20]


def _movie_has_genre(m: Dict, genre: str) -> bool:
    q = str(genre).strip().upper().replace(" ", "_")
    for g in (m.get("genres") or []):
        name = (g.get("name") if isinstance(g, dict) else str(g)) or ""
        if name.strip().upper().replace(" ", "_") == q:
            return True
    return False


def _movies_by_genre(
    movie_data: Dict[Any, Any],
    genre: str,
    exclude: Set[int],
    valid: Set[int],
) -> List[Dict]:
    seen_mid: Set[int] = set()
    out = []
    for _k, m in movie_data.items():
        mid = m.get("tmdb_id") or m.get("id")
        if mid is None or int(mid) in seen_mid:
            continue
        if _movie_has_genre(m, genre) and int(mid) not in exclude and (not valid or int(mid) in valid):
            seen_mid.add(int(mid))
            out.append(m)
    out.sort(key=lambda x: -(x.get("vote_average") or 0))
    return out[:20]


def _movies_by_era(
    movie_data: Dict[Any, Any],
    year: int,
    exclude: Set[int],
    valid: Set[int],
) -> List[Dict]:
    decade = (year // 10) * 10
    lo, hi = decade, decade + 9
    seen_mid: Set[int] = set()
    out = []
    for _k, m in movie_data.items():
        mid = m.get("tmdb_id") or m.get("id")
        if mid is None or int(mid) in seen_mid:
            continue
        y = _year_from_movie(m)
        if y is not None and lo <= y <= hi and int(mid) not in exclude and (not valid or int(mid) in valid):
            seen_mid.add(int(mid))
            out.append(m)
    out.sort(key=lambda x: -(x.get("vote_average") or 0))
    return out[:20]
