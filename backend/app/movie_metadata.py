"""
Lightweight movie metadata loader for reviews/watchlist.
Avoids loading the full ML model (torch, ensemble) — just reads JSONL and caches.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

_cache: Dict[str, Dict[str, Any]] = {}
_loaded = False


def _ensure_loaded() -> None:
    global _loaded, _cache
    if _loaded:
        return
    BASE_DIR = Path(__file__).parent.parent.parent
    for name in ("tmdb_movies_50k_20250711_011112.jsonl", "tmdb_complete_dataset.jsonl"):
        path = BASE_DIR / "data" / "raw" / name
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            m = json.loads(line.strip())
                            mid = m.get("tmdb_id") or m.get("id")
                            if mid is not None:
                                _cache[str(mid)] = m
                        except Exception:
                            continue
                logger.info("Movie metadata: loaded %d movies from %s", len(_cache), name)
                break
            except Exception as e:
                logger.warning("Movie metadata load failed: %s", e)
        else:
            continue
    _loaded = True


def get_movie_info(movie_id: int) -> Dict[str, Any]:
    """Return {title, poster_path} for a movie. No model load."""
    _ensure_loaded()
    mid = int(movie_id)
    m = _cache.get(str(mid)) or _cache.get(mid)
    if m:
        return {
            "title": m.get("title", f"Movie {mid}"),
            "poster_path": m.get("poster_path"),
        }
    return {"title": f"Movie {mid}", "poster_path": None}
