"""
LLM service for preference extraction from RAG chunks and dynamic "Why this recommendation?".
Uses Groq (free tier) — set GROQ_API_KEY in .env or environment.
"""

from __future__ import annotations

import logging
import os
import json
import re
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Dynamic explanation: timeout and retry for production
_WHY_TIMEOUT_SEC = float(os.getenv("LLM_WHY_TIMEOUT", "8"))
_WHY_MAX_WORDS = 100
_WHY_NONE_MARKER = "NONE"
_WHY_CACHE_TTL_SEC = int(os.getenv("LLM_WHY_CACHE_TTL_SEC", "86400"))
_WHY_CACHE_VERSION = os.getenv("LLM_WHY_CACHE_VERSION", "v2")
# Approximation for rough cost and latency budgeting without provider usage API
_CHARS_PER_TOKEN_EST = 4
_WHY_INPUT_COST_PER_1M = float(os.getenv("LLM_WHY_INPUT_COST_PER_1M", "0.05"))
_WHY_OUTPUT_COST_PER_1M = float(os.getenv("LLM_WHY_OUTPUT_COST_PER_1M", "0.08"))

_llm_available: bool | None = None
_BASE = Path(__file__).resolve().parent.parent.parent
_WHY_CACHE_DIR = _BASE / "data" / "rag" / "why_cache"


def _stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _cache_path(cache_key: str) -> Path:
    _WHY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _WHY_CACHE_DIR / f"{cache_key}.json"


def _load_cached_why(cache_key: str) -> Optional[List[Optional[str]]]:
    p = _cache_path(cache_key)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            payload = json.load(f)
        created_at = float(payload.get("created_at", 0))
        if (time.time() - created_at) > _WHY_CACHE_TTL_SEC:
            return None
        results = payload.get("results")
        if not isinstance(results, list):
            return None
        return [x if isinstance(x, str) else None for x in results]
    except Exception as e:
        logger.debug("LLM why cache load failed: %s", e)
        return None


def _save_cached_why(cache_key: str, results: List[Optional[str]]) -> None:
    p = _cache_path(cache_key)
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": _WHY_CACHE_VERSION,
                    "created_at": time.time(),
                    "results": results,
                },
                f,
            )
    except Exception as e:
        logger.debug("LLM why cache save failed: %s", e)


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / _CHARS_PER_TOKEN_EST))


def _build_why_cache_key(
    user_context: Dict[str, Any],
    items: List[Tuple[Dict[str, Any], str]],
    model_name: str,
) -> str:
    user_sig = {
        "liked_titles": (user_context.get("liked_titles") or [])[:15],
        "pref_summary": (user_context.get("pref_summary") or "")[:500],
        "user_review_snippets": [(s or "")[:300] for s in (user_context.get("user_review_snippets") or [])[:2]],
    }
    item_sig = []
    for movie_ctx, reason_bucket in items:
        item_sig.append(
            {
                "title": (movie_ctx.get("title") or "")[:200],
                "overview": (movie_ctx.get("overview") or "")[:200],
                "genres": [str(g) for g in (movie_ctx.get("genres") or [])[:5]],
                "directors": [str(d) for d in (movie_ctx.get("directors") or [])[:2]],
                "rag_document": (movie_ctx.get("rag_document") or "")[:400],
                "reason_bucket": reason_bucket,
            }
        )
    payload = {"v": _WHY_CACHE_VERSION, "model": model_name, "user": user_sig, "items": item_sig}
    return _stable_hash(payload)


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
        prompt = f"""Based on the movies the user liked and these review excerpts, identify 3-5 preference themes.
Weight the liked movies list heavily — capture ALL genres present (action, thriller, sci-fi, drama, superhero, etc.), not just emotional themes.
Output comma-separated short phrases. No preamble.

Liked movies (with genres):
{titles_text}

Review excerpts (secondary signal):
{chunks_text}

Preferences (comma-separated, must include genre preferences):"""

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
    max_items: Optional[int] = None,
    skip_buckets: Optional[List[str]] = None,
) -> List[Optional[str]]:
    """
    Generate one "why" sentence per (movie_context, reason_bucket). Single LLM call.
    Returns list of same length; None where explanation could not be produced.
    """
    if not items:
        return []
    if max_items is not None and max_items <= 0:
        logger.info("LLM why disabled by max_items=%s", max_items)
        return [None] * len(items)
    if max_items is not None and max_items > 0:
        items = items[:max_items]
    original_len = len(items)
    skip_set = set(skip_buckets or [])
    active_items: List[Tuple[Dict[str, Any], str]] = []
    active_index_map: List[int] = []
    for idx, (movie_ctx, reason_bucket) in enumerate(items):
        if reason_bucket in skip_set:
            continue
        active_items.append((movie_ctx, reason_bucket))
        active_index_map.append(idx)
    if not active_items:
        logger.info("LLM why skipped all items by bucket policy: %s", sorted(skip_set))
        return [None] * original_len
    if not is_llm_available():
        return [None] * len(items)
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return [None] * len(items)
    model_name = os.getenv("LLM_WHY_MODEL", "llama-3.1-8b-instant")
    cache_key = _build_why_cache_key(user_context, active_items, model_name)
    cached = _load_cached_why(cache_key)
    if cached is not None and len(cached) == len(active_items):
        logger.info("LLM why cache hit: n_items=%d", len(active_items))
        out_full: List[Optional[str]] = [None] * original_len
        for out_idx, src_idx in enumerate(active_index_map):
            out_full[src_idx] = cached[out_idx]
        return out_full
    start = time.perf_counter()
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
    user_profile = "\n".join(user_blob) if user_blob else "No likes or preferences yet."
    bucket_instructions = {
        "rag_similar_reviews": "similarity to reviews of movies they liked",
        "rag_injected": "similar reviews and similar users",
        "cf_similar_users": "similar users rated it highly",
        "limited_data": "limited data; use movie and any likes only",
    }
    blocks = []
    for i, (movie_ctx, reason_bucket) in enumerate(active_items):
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
    # NOTE: Keep output strictly JSON to simplify parsing/caching.
    prompt = f"""Based on this user's taste profile:
{user_profile}

Recommend movies and explain specifically why each one matches their taste.
Reference specific aspects of the user's taste profile in each explanation.

You will receive several movies (in order). Use ONLY the facts provided for each movie.
Do not invent any movie titles or external facts.

Respond as JSON (and ONLY JSON) in this schema:
[
  {{
    "movie": "<movie title>",
    "explanation": "<specific explanation>"
  }}
]

Rules for "explanation":
- Write 1-3 sentences.
- Must connect 1-2 preference aspects from the user's taste profile to 1-2 concrete movie facts (genres/directors/overview excerpt/rag excerpt).
- If you cannot explain from the facts, set "explanation" to exactly "{_WHY_NONE_MARKER}" (uppercase), not any other text.
- Keep it under 60 words.

Movies (in order):
{chr(10).join(blocks)}"""
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=min(1200, 120 * len(active_items)),
            temperature=0.2,
        )
        raw = (resp.choices[0].message.content or "").strip()
        out = _parse_json_why_array(raw, expected_len=len(active_items))
        _save_cached_why(cache_key, out)
        out_full: List[Optional[str]] = [None] * original_len
        for out_idx, src_idx in enumerate(active_index_map):
            out_full[src_idx] = out[out_idx]
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        prompt_tokens = _estimate_tokens(prompt)
        output_tokens = _estimate_tokens(raw)
        cost_usd = ((prompt_tokens / 1_000_000) * _WHY_INPUT_COST_PER_1M) + (
            (output_tokens / 1_000_000) * _WHY_OUTPUT_COST_PER_1M
        )
        logger.info(
            "LLM why generated: n_items=%d latency_ms=%d prompt_tokens~=%d output_tokens~=%d est_cost_usd=%.6f",
            len(active_items),
            elapsed_ms,
            prompt_tokens,
            output_tokens,
            cost_usd,
        )
        return out_full
    except Exception as e:
        logger.warning("LLM: generate_why_recommendations_batch failed: %s", e)
        return [None] * original_len


def _parse_json_why_array(raw: str, expected_len: int) -> List[Optional[str]]:
    """
    Parse strict JSON array output from the LLM.
    If parsing fails, return [None] * expected_len.
    """
    try:
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return [None] * expected_len
        candidate = raw[start : end + 1]
        parsed = json.loads(candidate)
        if not isinstance(parsed, list):
            return [None] * expected_len
        out: List[Optional[str]] = [None] * expected_len
        for i in range(min(expected_len, len(parsed))):
            obj = parsed[i]
            if not isinstance(obj, dict):
                continue
            expl = obj.get("explanation")
            if not isinstance(expl, str):
                continue
            expl_norm = expl.strip()
            if not expl_norm:
                continue
            if expl_norm.upper() == _WHY_NONE_MARKER.upper():
                out[i] = None
                continue
            # Keep output bounded.
            if len(expl_norm.split()) > _WHY_MAX_WORDS:
                out[i] = None
                continue
            out[i] = expl_norm[:500]
        return out
    except Exception:
        return [None] * expected_len


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