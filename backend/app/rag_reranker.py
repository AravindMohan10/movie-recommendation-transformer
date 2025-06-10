"""
RAG + LLM reranker for CF recommendations (Options A, B, C).
- A: Inject/boost RAG-retrieved movies into candidate set.
- B: Rerank using review-aware similarity (user pref embedding vs movie review embedding).
- C: Both A and B.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Weights for combined score: cf_weight * cf_norm + (1 - cf_weight) * review_sim
CF_WEIGHT = 0.5
RAG_BOOST_SCORE = 0.6  # default score for RAG-injected movies (Option A)
TOP_RAG_INJECT = 20    # max extra movies to inject from RAG (Option A)
RAG_TOP_K = 50

# Eval hook: last rerank call sets this. key=user_id, value=rag_activated (had_pref_emb or n_injected>0)
_last_rag_activation: Dict[int, bool] = {}


def _get_liked_movies(db_session: Any, user_id: int) -> List[Tuple[int, str]]:
    """Returns [(movie_id, title), ...] for liked/favorite interactions."""
    if not db_session:
        return []
    try:
        from .models import UserInteraction

        rows = (
            db_session.query(UserInteraction.movie_id, UserInteraction.action)
            .filter(UserInteraction.user_id == user_id)
            .all()
        )
    except Exception as e:
        logger.warning("RAG reranker: could not load interactions: %s", e)
        return []

    liked_ids: List[int] = []
    for row in rows:
        movie_id, action = (row[0], row[1]) if len(row) >= 2 else (row.movie_id, row.action)
        if action in ("like", "favorite"):
            liked_ids.append(int(movie_id))
    return [(mid, "") for mid in liked_ids]


def _get_reviewed_movies(db_session: Any, user_id: int) -> List[Tuple[int, str]]:
    """Returns [(movie_id, review_text), ...] for user's reviews (used in RAG query)."""
    if not db_session:
        return []
    try:
        from .models import UserInteraction

        rows = (
            db_session.query(UserInteraction.movie_id, UserInteraction.review_text)
            .filter(
                UserInteraction.user_id == user_id,
                UserInteraction.action == "review",
                UserInteraction.review_text.isnot(None),
            )
            .all()
        )
        return [(int(r[0]), (r[1] or "").strip()) for r in rows if (r[1] or "").strip()]
    except Exception as e:
        logger.warning("RAG reranker: could not load reviews: %s", e)
        return []


def _query_from_liked(
    liked: List[Tuple[int, str]],
    movie_data: Dict[Any, Any],
) -> str:
    """Build RAG query from liked movies' overview + reviews."""
    parts = []
    for mid, _ in liked[:15]:
        m = movie_data.get(str(mid)) or movie_data.get(mid) or movie_data.get(int(mid))
        if not m:
            continue
        ov = (m.get("overview") or "").strip()
        if ov:
            parts.append(ov)
        for r in (m.get("reviews") or [])[:3]:
            c = (r.get("content") if isinstance(r, dict) else "") or ""
            if c:
                parts.append(c[:600])
    return "\n\n".join(parts)[:8000] if parts else ""


def _titles_from_liked(
    liked: List[Tuple[int, str]],
    movie_data: Dict[Any, Any],
    reviewed: Optional[List[Tuple[int, str]]] = None,
) -> List[str]:
    titles = []
    for mid, _ in liked[:15]:
        m = movie_data.get(str(mid)) or movie_data.get(mid) or movie_data.get(int(mid))
        if m:
            t = (m.get("title") or "").strip()
            if t:
                titles.append(t)
    if reviewed:
        for mid, _ in reviewed[:15]:
            m = movie_data.get(str(mid)) or movie_data.get(mid) or movie_data.get(int(mid))
            if m:
                t = (m.get("title") or "").strip()
                if t and t not in titles:
                    titles.append(t)
    return titles


def get_user_context_for_explanations(
    user_id: int,
    db_session: Any,
    movie_data: Dict[Any, Any],
) -> Dict[str, Any]:
    """
    Build user context for dynamic "Why this recommendation?" explanations.
    Returns pref_summary (from cache if available), liked_titles, user_review_snippets.
    """
    liked = _get_liked_movies(db_session, user_id)
    reviewed = _get_reviewed_movies(db_session, user_id)
    liked_ids = [mid for mid, _ in liked]
    reviewed_ids = [mid for mid, _ in reviewed]
    liked_titles = _titles_from_liked(liked, movie_data, reviewed)
    pref_summary = ""
    try:
        from .rag_prefs_store import load as prefs_load, _signature as prefs_signature
        sig = prefs_signature(liked_ids, reviewed_ids)
        cached = prefs_load(user_id, sig)
        if cached:
            pref_summary = (cached[0] or "").strip()
    except Exception as e:
        logger.debug("get_user_context_for_explanations: prefs load failed: %s", e)
    user_review_snippets = [text[:300].strip() for _, text in reviewed[:2] if (text or "").strip()]
    return {
        "pref_summary": pref_summary,
        "liked_titles": liked_titles,
        "user_review_snippets": user_review_snippets,
    }


def rerank(
    user_id: int,
    cf_candidates: List[Tuple[int, float]],
    movie_data: Dict[Any, Any],
    db_session: Any,
    valid_movie_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Apply Options A + B + C: RAG inject, LLM preferences, review-aware rerank.
    cf_candidates: [(movie_id, cf_score), ...]
    Returns list of dicts: movie_id, score, is_rag_injected, cf_contribution, rag_contribution, had_pref_emb.
    """
    if not cf_candidates:
        return []
    _last_rag_activation.pop(user_id, None)  # clear stale entry for this user
    valid_set = set(valid_movie_ids) if valid_movie_ids else None
    cf_by_mid: Dict[int, float] = {int(mid): s for mid, s in cf_candidates}
    rag_injected_ids: Set[int] = set()
    all_mids = list(cf_by_mid.keys())

    liked = _get_liked_movies(db_session, user_id)
    reviewed = _get_reviewed_movies(db_session, user_id)
    liked_ids = [mid for mid, _ in liked]
    reviewed_ids = [mid for mid, _ in reviewed]
    query = _query_from_liked(liked, movie_data)
    if reviewed:
        user_review_parts = [text[:1200] for _, text in reviewed[:10]]
        query = (query + "\n\n" + "\n\n".join(user_review_parts))[:12000] if query else "\n\n".join(user_review_parts)[:12000]
    liked_titles = _titles_from_liked(liked, movie_data, reviewed)

    from .rag_service import get_rag_service
    rag = get_rag_service()

    rag_movie_scores: Dict[int, float] = {}
    chunks_for_llm: List[str] = []
    if query:
        try:
            similar = rag.retrieve_similar(query, top_k=RAG_TOP_K)
            for mid, score, text in similar:
                if valid_set is not None and mid not in valid_set:
                    continue
                rag_movie_scores[mid] = max(rag_movie_scores.get(mid, 0), score)
                if text and len(chunks_for_llm) < 10:
                    chunks_for_llm.append(text)
        except Exception as e:
            logger.warning("RAG reranker: retrieve_similar failed: %s", e)

    inject: List[Tuple[int, float]] = []
    for mid, s in sorted(rag_movie_scores.items(), key=lambda x: -x[1])[:TOP_RAG_INJECT]:
        if mid in cf_by_mid:
            continue
        if valid_set is not None and mid not in valid_set:
            continue
        inject.append((mid, RAG_BOOST_SCORE))
        rag_injected_ids.add(mid)
    for mid, s in inject:
        cf_by_mid[mid] = s
        all_mids.append(mid)

    # Pref summary + embedding: reuse from past RAG runs when likes/reviews unchanged
    from .rag_prefs_store import load as prefs_load, save as prefs_save, _signature as prefs_signature

    sig = prefs_signature(liked_ids, reviewed_ids)
    cached = prefs_load(user_id, sig)
    user_pref_emb = None
    pref_summary = ""

    if cached is not None:
        pref_summary, emb_list = cached
        if emb_list:
            import numpy as np
            user_pref_emb = np.array(emb_list, dtype=np.float32)
        logger.info("RAG reranker: using stored prefs for user_id=%s (signature match)", user_id)

    if user_pref_emb is None:
        try:
            from .llm_service import extract_preferences
            pref_summary = extract_preferences(chunks_for_llm, liked_titles)
        except Exception as e:
            logger.warning("RAG reranker: extract_preferences failed: %s", e)
            pref_summary = ""

        if pref_summary and hasattr(rag, "_embedder") and rag._embedder is not None:
            try:
                emb = rag._embedder.encode([pref_summary])
                user_pref_emb = emb[0]
            except Exception as e:
                logger.debug("RAG reranker: could not embed preferences: %s", e)

        if pref_summary and user_pref_emb is not None:
            emb_list = user_pref_emb.tolist() if hasattr(user_pref_emb, "tolist") else list(user_pref_emb)
            prefs_save(user_id, sig, pref_summary, emb_list)

    had_pref_emb = user_pref_emb is not None
    logger.info(
        "EVAL_RAG user_id=%s n_liked=%s n_reviewed=%s had_pref_emb=%s n_injected=%s",
        user_id, len(liked), len(reviewed), had_pref_emb, len(rag_injected_ids),
    )
    cf_max = max(cf_by_mid.values()) if cf_by_mid else 1.0
    cf_min = min(cf_by_mid.values()) if cf_by_mid else 0.0
    span = (cf_max - cf_min) or 1.0

    scored: List[Dict[str, Any]] = []
    for mid in all_mids:
        cf_s = cf_by_mid[mid]
        cf_norm = (cf_s - cf_min) / span if span else 0.5
        review_sim = 0.0
        if user_pref_emb is not None:
            movie_emb = rag.get_movie_embedding(mid)
            if movie_emb is not None:
                import numpy as np

                a = np.asarray(user_pref_emb, dtype=np.float32)
                b = np.asarray(movie_emb, dtype=np.float32)
                review_sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
                review_sim = max(0.0, min(1.0, (review_sim + 1) / 2))
        cf_contrib = CF_WEIGHT * cf_norm
        rag_contrib = (1 - CF_WEIGHT) * (review_sim if had_pref_emb else cf_norm)
        combined = cf_contrib + rag_contrib
        scored.append({
            "movie_id": mid,
            "score": combined,
            "is_rag_injected": mid in rag_injected_ids,
            "cf_contribution": cf_contrib,
            "rag_contribution": rag_contrib,
            "had_pref_emb": had_pref_emb,
        })

    scored.sort(key=lambda x: -x["score"])
    rag_activated = had_pref_emb or len(rag_injected_ids) > 0
    _last_rag_activation[user_id] = rag_activated
    return scored
