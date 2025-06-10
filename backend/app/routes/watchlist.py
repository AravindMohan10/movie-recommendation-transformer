from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict
from ..database import get_db
from ..models import User, Watchlist
from ..auth import get_current_user
from ..model_service import get_model_service
from ..limiter import limiter

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

@router.post("/add")
@limiter.limit("60/minute")
async def add_to_watchlist(
    request: Request,
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a movie to user's watchlist"""
    try:
        # Check if already in watchlist
        existing = db.query(Watchlist).filter(
            Watchlist.user_id == current_user.user_id,
            Watchlist.movie_id == movie_id
        ).first()
        
        if existing:
            return {
                "success": True,
                "message": "Movie already in watchlist",
                "watchlist_id": existing.id
            }
        
        # Add to watchlist
        watchlist_item = Watchlist(
            user_id=current_user.user_id,
            movie_id=movie_id
        )
        
        db.add(watchlist_item)
        db.commit()
        db.refresh(watchlist_item)
        
        return {
            "success": True,
            "message": "Added to watchlist",
            "watchlist_id": watchlist_item.id
        }
        
    except IntegrityError:
        db.rollback()
        return {
            "success": True,
            "message": "Movie already in watchlist"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to watchlist: {str(e)}"
        )

@router.delete("/remove/{movie_id}")
@limiter.limit("60/minute")
async def remove_from_watchlist(
    request: Request,
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a movie from user's watchlist"""
    try:
        watchlist_item = db.query(Watchlist).filter(
            Watchlist.user_id == current_user.user_id,
            Watchlist.movie_id == movie_id
        ).first()
        
        if not watchlist_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not in watchlist"
            )
        
        db.delete(watchlist_item)
        db.commit()
        
        return {
            "success": True,
            "message": "Removed from watchlist"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove from watchlist: {str(e)}"
        )

@router.get("/")
@limiter.limit("60/minute")
async def get_watchlist(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100
):
    """Get user's watchlist with movie title and poster."""
    try:
        watchlist_items = db.query(Watchlist).filter(
            Watchlist.user_id == current_user.user_id
        ).order_by(Watchlist.added_at.desc()).limit(limit).all()
        
        model = get_model_service()
        out = []
        for item in watchlist_items:
            md = model.movie_data.get(str(item.movie_id)) or model.movie_data.get(item.movie_id)
            out.append({
                "id": item.id,
                "movie_id": item.movie_id,
                "movie_title": (md or {}).get("title", f"Movie {item.movie_id}"),
                "poster_path": (md or {}).get("poster_path"),
                "added_at": item.added_at.isoformat() if item.added_at else None,
            })
        return {"watchlist": out, "total": len(out)}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get watchlist: {str(e)}"
        )

