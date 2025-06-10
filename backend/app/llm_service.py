"""
LLM service for preference extraction from RAG chunks and dynamic "Why this recommendation?".
Uses Groq (free tier) — set GROQ_API_KEY in .env or environment.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Dynamic explanation: timeout and retry for production
_WHY_TIMEOUT_SEC = float(os.getenv("LLM_WHY_TIMEOUT", "8"))
_WHY_MAX_WORDS = 100
_WHY_NONE_MARKER = "NONE"

_llm_available: bool | None = None


def is_llm_available() -> bool:
    global _llm_available
    if _llm_available is not None:
        return _llm_available
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        logger.info("LLM: GROQ_API_KEY not set — preference extraction disabled")
        _llm_available = False
        return False
    try:
        import groq
        groq.Groq(api_key=key)
        _llm_available = True
        return True
    except Exception as e:
        logger.warning("LLM: Groq check failed: %s", e)
        _llm_available = False
        return False


def extract_preferences(
    retrieved_chunks: List[str],
    liked_titles: List[str],
) -> str:
    """
    Summarize user preferences from RAG chunks and liked movie titles.
    Returns a short string suitable for embedding (Option B).
    """
    if not is_llm_available():
        return _fallback_preferences(retrieved_chunks, liked_titles)

    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return _fallback_preferences(retrieved_chunks, liked_titles)

    try:
        from groq import Groq

        client = Groq(api_key=key)
        chunks_text = "\n\n---\n\n".join((c[:800] for c in retrieved_chunks[:8]))
        titles_text = ", ".join(liked_titles[:15]) if liked_titles else "none"
        prompt = f"""Based on these movie review excerpts and the movies the user liked, list 3–5 brief preference themes (genres, tones, themes) — one short phrase each, comma-separated. No preamble.

Liked movies: {titles_text}

Review excerpts:
{chunks_text}

Preferences (comma-separated phrases):"""

        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.3,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text[:500] if text else _fallback_preferences(retrieved_chunks, liked_titles)
    except Exception as e:
        logger.warning("LLM: extract_preferences failed: %s", e)
        return _fallback_preferences(retrieved_chunks, liked_titles)


def _fallback_preferences(chunks: List[str], titles: List[str]) -> str:
    """When LLM unavailable: simple concatenation of first bits of chunks."""
    if not chunks and not titles:
        return "general entertainment"
    parts = []
    for c in chunks[:3]:
        s = (c or "").strip()[:200]
        if s:
            parts.append(s)
    if titles:
        parts.append("Liked: " + ", ".join(titles[:5]))
    return " ".join(parts)[:400] if parts else "general entertainment"


# --- Dynamic "Why this recommendation?" (no generic fallback: dynamic or None) ---

def generate_why_recommendation(
    user_context: Dict[str, Any],
    movie_context: Dict[str, Any],
    reason_bucket: str,
) -> Optional[str]:
    """
    Generate one short, factual sentence explaining why we recommended this movie.
    Uses ONLY the provided facts; returns None if LLM unavailable or cannot explain.
    """
    if not is_llm_available():
        return None
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return None
    liked = (user_context.get("liked_titles") or [])[:15]
    pref = (user_context.get("pref_summary") or "").strip()[:500]
    user_reviews = (user_context.get("user_review_snippets") or [])[:2]
    title = (movie_context.get("title") or "").strip()[:200]
    overview = (movie_context.get("overview") or "").strip()[:300]
    genres = movie_context.get("genres") or []
    directors = movie_context.get("directors") or []
    rag_doc = (movie_context.get("rag_document") or "").strip()[:800]
    bucket_instruction = {
        "rag_similar_reviews": "The main reason is similarity to reviews of movies they liked.",
        "rag_injected": "The movie was surfaced from similar reviews and similar users.",
        "cf_similar_users": "Similar users rated this highly.",
        "limited_data": "We have limited data on this user; explain from movie and any likes only.",
    }.get(reason_bucket, "Explain briefly why this movie fits.")
    user_blob = []
    if liked:
        user_blob.append("Liked movies: " + ", ".join(liked))
    if pref:
        user_blob.append("Inferred preferences: " + pref)
    for s in user_reviews:
        if (s or "").strip():
            user_blob.append("User review excerpt: " + (s[:300].strip()))
    movie_blob = [f"Movie: {title}"]
    if overview:
        movie_blob.append("Overview: " + overview)
    if genres:
        movie_blob.append("Genres: " + ", ".join(str(g) for g in genres[:5]))
    if directors:
        movie_blob.append("Directors: " + ", ".join(str(d) for d in directors[:3]))
    if rag_doc:
        movie_blob.append("Review/overview excerpt for this movie: " + rag_doc)
    prompt = f"""Using ONLY the facts below, write one short sentence (under 25 words) explaining why we recommended this movie to this user. Do not invent any movie titles, names, or facts. {bucket_instruction}
If you cannot explain from the facts, respond with exactly: {_WHY_NONE_MARKER}

User context:
{chr(10).join(user_blob) if user_blob else "No likes or preferences yet."}

Movie context:
{chr(10).join(movie_blob)}

One sentence (or NONE):"""
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text or _WHY_NONE_MARKER.upper() in text.upper():
            return None
        if len(text.split()) > _WHY_MAX_WORDS:
            return None
        return text[:500]
    except Exception as e:
        logger.warning("LLM: generate_why_recommendation failed: %s", e)
        return None


def generate_why_recommendations_batch(
    user_context: Dict[str, Any],
    items: List[Tuple[Dict[str, Any], str]],
) -> List[Optional[str]]:
    """
    Generate one "why" sentence per (movie_context, reason_bucket). Single LLM call.
    Returns list of same length; None where explanation could not be produced.
    """
    if not is_llm_available() or not items:
        return [None] * len(items)
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return [None] * len(items)
    liked = (user_context.get("liked_titles") or [])[:15]
    pref = (user_context.get("pref_summary") or "").strip()[:500]
    user_reviews = (user_context.get("user_review_snippets") or [])[:2]
    user_blob = []
    if liked:
        user_blob.append("Liked movies: " + ", ".join(liked))
    if pref:
        user_blob.append("Inferred preferences: " + pref)
    for s in user_reviews:
        if (s or "").strip():
            user_blob.append("User review excerpt: " + (s[:300].strip()))
    user_section = "\n".join(user_blob) if user_blob else "No likes or preferences yet."
    bucket_instructions = {
        "rag_similar_reviews": "similarity to reviews of movies they liked",
        "rag_injected": "similar reviews and similar users",
        "cf_similar_users": "similar users rated it highly",
        "limited_data": "limited data; use movie and any likes only",
    }
    blocks = []
    for i, (movie_ctx, reason_bucket) in enumerate(items):
        title = (movie_ctx.get("title") or "").strip()[:200]
        overview = (movie_ctx.get("overview") or "").strip()[:200]
        genres = movie_ctx.get("genres") or []
        directors = movie_ctx.get("directors") or []
        rag_doc = (movie_ctx.get("rag_document") or "").strip()[:400]
        bucket_hint = bucket_instructions.get(reason_bucket, "fits the user")
        parts = [f"Movie {i+1}: {title}"]
        if overview:
            parts.append("Overview: " + overview)
        if genres:
            parts.append("Genres: " + ", ".join(str(g) for g in genres[:5]))
        if directors:
            parts.append("Directors: " + ", ".join(str(d) for d in directors[:2]))
        if rag_doc:
            parts.append("Excerpt: " + rag_doc)
        parts.append(f"Reason bucket: {bucket_hint}.")
        blocks.append("\n".join(parts))
    prompt = f"""You will see user context and then several movies. For each movie, write ONE short sentence (under 25 words) explaining why we recommended it. Use ONLY the facts given. Do not invent titles or names. If you cannot explain for a movie, write exactly NONE for that line.

User context:
{user_section}

Movies:
{chr(10).join(blocks)}

Output format: one line per movie, numbered 1., 2., 3., ... Each line is either one sentence or the word NONE."""
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=min(800, 80 * len(items)),
            temperature=0.2,
        )
        raw = (resp.choices[0].message.content or "").strip()
        results = _parse_numbered_why_lines(raw, len(items))
        out = []
        for j, s in enumerate(results):
            if not s or _WHY_NONE_MARKER.upper() in (s or "").upper():
                out.append(None)
            elif len((s or "").split()) > _WHY_MAX_WORDS:
                out.append(None)
            else:
                out.append((s or "").strip()[:500])
        while len(out) < len(items):
            out.append(None)
        return out[: len(items)]
    except Exception as e:
        logger.warning("LLM: generate_why_recommendations_batch failed: %s", e)
        return [None] * len(items)


def _parse_numbered_why_lines(raw: str, expected: int) -> List[Optional[str]]:
    """Parse '1. sentence\\n2. sentence' or '1) sentence' into list of strings."""
    out: List[Optional[str]] = [None] * expected
    lines = re.split(r"\n+", raw)
    for line in lines:
        line = (line or "").strip()
        if not line:
            continue
        m = re.match(r"^\s*(\d+)[.)]\s*(.+)$", line)
        if m:
            num = int(m.group(1))
            rest = m.group(2).strip()
            if 1 <= num <= expected and rest and rest.upper() != _WHY_NONE_MARKER:
                out[num - 1] = rest
    return out
