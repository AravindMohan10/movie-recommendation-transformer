"""
News digest: user-provided articles, personalized by user preferences.
POST /api/news — ingest article (you provide content).
GET /api/news/digest — personalized feed for current user.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..rag_reranker import get_user_context_for_explanations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["news"])


class NewsArticleCreate(BaseModel):
    """Payload for ingesting an article."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    url: Optional[str] = Field(None, max_length=1000)
    tags: Optional[str] = Field(None, max_length=500, description="Comma-separated e.g. Sci-Fi, Drama")
    published_at: Optional[datetime] = None


class NewsArticleOut(BaseModel):
    id: int
    title: str
    content: str
    url: Optional[str]
    tags: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


def _get_model_service_movie_data() -> Dict[Any, Any]:
    """Load movie_data for user context (liked titles, etc.)."""
    try:
        from ..model_service import get_model_service
        svc = get_model_service()
        return getattr(svc, "movie_data", {}) or {}
    except Exception:
        return {}


def _score_article_for_user(article: Any, liked_titles: List[str], pref_summary: str) -> float:
    """Simple relevance: keyword overlap between article title/content/tags and user prefs."""
    text = " ".join([
        (article.title or ""),
        (article.content or "")[:2000],
        (article.tags or "").replace(",", " "),
    ]).lower()
    user_text = (pref_summary or "").lower() + " " + " ".join((t or "").lower() for t in liked_titles[:20])
    if not user_text.strip():
        return 0.5
    user_words = set(w for w in user_text.split() if len(w) > 2)
    text_words = set(w for w in text.split() if len(w) > 2)
    overlap = len(user_words & text_words)
    return min(1.0, 0.3 + 0.7 * (overlap / max(len(user_words), 1)))


@router.post("", response_model=NewsArticleOut)
async def create_article(
    body: NewsArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ingest one article. You provide title, content, and optionally url, tags, published_at."""
    from ..models import NewsArticle
    published = body.published_at or datetime.now(timezone.utc)
    article = NewsArticle(
        title=body.title.strip(),
        content=body.content.strip(),
        url=body.url.strip() if body.url else None,
        tags=body.tags.strip() if body.tags else None,
        published_at=published,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    logger.info("News article created id=%s title=%s", article.id, article.title[:50])
    return article


@router.get("/digest", response_model=Dict[str, Any])
async def get_digest(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    """Personalized news digest: articles ranked by relevance to user preferences (liked titles, pref summary)."""
    from ..models import NewsArticle
    rows = db.query(NewsArticle).order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.created_at.desc()).limit(limit * 3).all()
    if not rows:
        return {"articles": [], "total": 0}
    movie_data = _get_model_service_movie_data()
    user_ctx = get_user_context_for_explanations(current_user.user_id, db, movie_data)
    liked_titles = user_ctx.get("liked_titles") or []
    pref_summary = user_ctx.get("pref_summary") or ""
    scored = [(_score_article_for_user(a, liked_titles, pref_summary), a) for a in rows]
    scored.sort(key=lambda x: -x[0])
    top = [a for _, a in scored[:limit]]
    out = []
    for a in top:
        out.append({
            "id": a.id,
            "title": a.title,
            "content": (a.content or "")[:1500],
            "url": a.url,
            "tags": a.tags,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return {"articles": out, "total": len(out)}
