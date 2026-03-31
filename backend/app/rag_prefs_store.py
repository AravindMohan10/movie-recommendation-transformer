"""
Persist and reuse RAG outputs per user: pref summary + pref embedding.
When likes/reviews unchanged (signature match), skip LLM + embed and load from store.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

_BASE = Path(__file__).resolve().parent.parent.parent
_PREFS_DIR = _BASE / "data" / "rag" / "user_prefs"


def _signature(liked_ids: List[int], reviewed_ids: List[int]) -> str:
    """Stable hash of user's like/review state for cache invalidation."""
    blob = json.dumps([sorted(liked_ids), sorted(reviewed_ids)], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def _path(user_id: int) -> Path:
    _PREFS_DIR.mkdir(parents=True, exist_ok=True)
    return _PREFS_DIR / f"{user_id}.json"


def load(
    user_id: int,
    signature: str,
) -> Optional[Tuple[str, List[float]]]:
    """
    Load stored (pref_summary, pref_embedding) for user_id if signature matches.
    Returns None on miss or mismatch.
    """
    p = _path(user_id)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("signature") != signature:
            return None
        summary = data.get("pref_summary")
        emb = data.get("pref_embedding")
        if not summary or not isinstance(emb, list):
            return None
        return (summary, emb)
    except Exception as e:
        logger.debug("RAG prefs load failed for user %s: %s", user_id, e)
        return None


def save(
    user_id: int,
    signature: str,
    pref_summary: str,
    pref_embedding: List[float],
) -> None:
    """Store pref summary + embedding for user_id keyed by signature."""
    p = _path(user_id)
    try:
        _PREFS_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "signature": signature,
            "pref_summary": pref_summary,
            "pref_embedding": pref_embedding,
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("RAG prefs saved for user_id=%s (signature=%s)", user_id, signature[:8])
    except Exception as e:
        logger.warning("RAG prefs save failed for user %s: %s", user_id, e)

def clear(user_id: int) -> None:
    """Delete cached prefs for user_id so they regenerate on next request."""
    p = _path(user_id)
    try:
        if p.exists():
            p.unlink()
            logger.info("RAG prefs cleared for user_id=%s", user_id)
    except Exception as e:
        logger.warning("RAG prefs clear failed for user %s: %s", user_id, e)
