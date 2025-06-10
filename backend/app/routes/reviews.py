"""
Reviews API: my reviews, movie reviews (own + others).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User, UserInteraction
from ..model_service import get_model_service

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("/my")
async def get_my_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    """Get current user's reviews (rating + text) with movie info."""
    rows = (
        db.query(UserInteraction)
        .filter(
            UserInteraction.user_id == current_user.user_id,
            UserInteraction.action == "review",
        )
        .order_by(UserInteraction.created_at.desc())
        .limit(limit)
        .all()
    )
    model = get_model_service()
    out = []
    for r in rows:
        md = model.movie_data.get(str(r.movie_id)) or model.movie_data.get(r.movie_id)
        out.append({
            "id": r.id,
            "movie_id": r.movie_id,
            "movie_title": (md or {}).get("title", f"Movie {r.movie_id}"),
            "poster_path": (md or {}).get("poster_path"),
            "rating": r.rating,
            "review_text": r.review_text,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return {"reviews": out, "total": len(out)}


@router.get("/movie/{movie_id}")
async def get_movie_reviews(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """Get all reviews for a movie (other users + own). Marks current user's review."""
    rows = (
        db.query(UserInteraction, User.username)
        .join(User, User.user_id == UserInteraction.user_id)
        .filter(
            UserInteraction.movie_id == movie_id,
            UserInteraction.action == "review",
        )
        .order_by(UserInteraction.created_at.desc())
        .limit(limit)
        .all()
    )
    model = get_model_service()
    md = model.movie_data.get(str(movie_id)) or model.movie_data.get(movie_id)
    movie_title = (md or {}).get("title", f"Movie {movie_id}")
    out = []
    for row in rows:
        r, username = row[0], (row[1] or "Anonymous")
        out.append({
            "id": r.id,
            "user_id": r.user_id,
            "username": username,
            "is_you": r.user_id == current_user.user_id,
            "rating": r.rating,
            "review_text": r.review_text,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return {
        "movie_id": movie_id,
        "movie_title": movie_title,
        "reviews": out,
        "total": len(out),
    }
