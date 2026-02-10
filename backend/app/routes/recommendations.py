import threading
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
import json
import sys
import random
from pathlib import Path

# Add project root to path for monitoring import
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..database import get_db
from ..models import User, OnboardingStatus
from ..auth import get_current_user
from ..onboarding_service import onboarding_service
from ..limiter import limiter

# Initialize logger first (always needed)
import logging
logger = logging.getLogger(__name__)

# Import monitoring
try:
    from monitor_recommendations import RecommendationMonitor
    import os
    # Use same database path as backend
    BASE_DIR = Path(__file__).parent.parent.parent
    db_path = os.path.join(BASE_DIR, "cineai.db")
    monitor = RecommendationMonitor(db_path=db_path)
    MONITORING_AVAILABLE = True
except Exception as e:
    logger.warning(f"Monitoring not available: {e}")
    monitor = None
    MONITORING_AVAILABLE = False

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _get_model():
    """Lazy load model_service (defers torch import until first recommendation request)."""
    from ..model_service import get_model_service
    return get_model_service()


def _get_onboarding_status_db(db: Session, user_id: int) -> Dict[str, Optional[object]]:
    """Get onboarding status from the database (persistent across logins)."""
    row = db.query(OnboardingStatus).filter(OnboardingStatus.user_id == user_id).first()
    if not row:
        return {
            "completed": False,
            "onboarding_completed": False,
            "stage": None,
            "skipped": False,
            "data": {},
        }
    data = {}
    if row.data:
        try:
            data = json.loads(row.data)
        except Exception:
            data = {}
    return {
        "completed": bool(row.completed),
        "onboarding_completed": bool(row.completed),
        "stage": row.stage,
        "skipped": bool(row.skipped),
        "data": data,
    }


def _sanitize_rec_poster(rec: dict) -> dict:
    """Return a copy of rec with poster set to a title-based placeholder only (never use rec poster_path to avoid mismatches)."""
    out = dict(rec)
    movie_id = rec.get("movie_id") or rec.get("id")
    title = (rec.get("title") or f"Movie {movie_id}")[:20].replace(" ", "+")
    placeholder = f"https://via.placeholder.com/342x513/1a1a1a/666666?text={title}"
    out["poster_path"] = placeholder
    out["poster_url"] = placeholder
    out["image"] = placeholder
    return out


def _upsert_onboarding_status(
    db: Session,
    user_id: int,
    *,
    completed: Optional[bool] = None,
    skipped: Optional[bool] = None,
    stage: Optional[int] = None,
    data: Optional[Dict] = None,
) -> OnboardingStatus:
    """Create or update onboarding status row."""
    row = db.query(OnboardingStatus).filter(OnboardingStatus.user_id == user_id).first()
    if not row:
        row = OnboardingStatus(user_id=user_id)
        db.add(row)
    if completed is not None:
        row.completed = bool(completed)
    if skipped is not None:
        row.skipped = bool(skipped)
    if stage is not None:
        row.stage = stage
    if data is not None:
        row.data = json.dumps(data)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row

@router.get("", response_model=None)
@router.get("/", response_model=None)
@limiter.limit("60/minute")
async def get_recommendations(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    force_refresh: bool = False
):
    """Get personalized movie recommendations. Cached 24h unless force_refresh=True. Registered for '' and '/' so GET /api/recommendations works."""
    try:
        from ..models import UserInteraction
        
        # Get recommendations from model (works with or without onboarding)
        try:
            model_service = _get_model()
        except Exception as service_error:
            logger.error(f"Failed to get model service: {service_error}", exc_info=True)
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Model service initialization failed: {str(service_error)}"
            )
        
        # Check onboarding status from DB (persistent across logins)
        onboarding_status = _get_onboarding_status_db(db, current_user.user_id)
        onboarding_completed = onboarding_status.get("onboarding_completed", False)
        
        # Check user interaction count for progressive enhancement
        interaction_count = db.query(UserInteraction).filter(
            UserInteraction.user_id == current_user.user_id
        ).count()
        
        last_refresh = None
        # Progressive enhancement: Adjust recommendation strategy based on user data
        # 0 interactions: Pure content-based (popular movies by genre preferences)
        # 1-5 interactions: Content-based + light collaborative signals
        # 6-15 interactions: Balanced hybrid
        # 16+ interactions: Full ensemble with all models
        
        # Get recommendations - model service handles progressive enhancement internally
        # Pass db session so it can reload fresh interactions from database
        try:
            recommendations, last_refresh = model_service.get_recommendations(
                current_user.user_id, 
                limit, 
                interaction_count,
                db_session=db,  # Pass db session to reload interactions from database
                force_refresh=force_refresh
            )
            if recommendations and last_refresh:
                # Persist last_refresh for display (merge with existing onboarding data)
                status = _get_onboarding_status_db(db, current_user.user_id)
                data = status.get("data", {}) or {}
                if not isinstance(data, dict):
                    data = {}
                data = dict(data)
                data["last_recommendation_refresh"] = last_refresh
                _upsert_onboarding_status(db, current_user.user_id, data=data)
        except (ValueError, TypeError) as unpack_error:
            # Handle old model return format (list only)
            logger.warning("Model returned unexpected format: %s", unpack_error)
            recommendations = []
            last_refresh = None
        except Exception as rec_error:
            logger.warning("Failed to get recommendations: %s", rec_error)
            recommendations = []
            last_refresh = None
        
        # If no recommendations, try fallback
        if not recommendations or len(recommendations) == 0:
            logger.warning(f"No recommendations returned for user {current_user.user_id}, trying fallback...")
            try:
                # Force fallback recommendations
                recommendations = model_service._get_fallback_recommendations(
                    current_user.user_id, limit, db_session=db
                )
                logger.info(f"Fallback returned {len(recommendations)} recommendations")
                if recommendations and last_refresh is None:
                    last_refresh = datetime.now(timezone.utc).isoformat()
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}", exc_info=True)
                recommendations = []
        
        # If still no recommendations, return helpful message
        if not recommendations or len(recommendations) == 0:
            return {
                "recommendations": [],
                "onboarding_required": not onboarding_completed,
                "last_refresh": None,
                "message": "No recommendations available. Please ensure movie data files are present in data/raw/",
                "error": "movie_data_empty"
            }
        
        # Record recommendations shown (monitoring)
        if MONITORING_AVAILABLE and monitor:
            for i, rec in enumerate(recommendations, 1):
                try:
                    movie_id = rec.get("id") or rec.get("movie_id")
                    if movie_id:
                        monitor.record_recommendation_shown(
                            user_id=current_user.user_id,
                            movie_id=movie_id,
                            recommendation_id=f"rec_{current_user.user_id}_{i}_{limit}",
                            position=i
                        )
                except Exception as e:
                    logger.warning("Failed to record recommendation event: %s", e)
        
        # Enrich with additional movie data from model_service
        # Note: recommendations from model_service already have titles and basic info
        enriched_recommendations = []
        for rec in recommendations:
            try:
                movie_id = rec.get("movie_id") or rec.get("id")
                if not movie_id:
                    continue  # Skip if no movie ID
                
                # Get full movie data from model service (for additional fields)
                movie_data = model_service.movie_data.get(str(movie_id)) or model_service.movie_data.get(int(movie_id)) if isinstance(movie_id, (int, str)) and str(movie_id).isdigit() else {}
                if not movie_data:
                    # If not found, use what's already in the recommendation
                    movie_data = {}
                # Skip adult content so main feed stays family-friendly
                if _is_adult(movie_data):
                    continue

                # Extract genres
                genres_list = movie_data.get("genres", [])
                if isinstance(genres_list, list) and len(genres_list) > 0:
                    if isinstance(genres_list[0], dict):
                        genres = [g.get("name", "") for g in genres_list if isinstance(g, dict)]
                    else:
                        genres = [str(g) for g in genres_list]
                else:
                    genres = []
                
                # Extract release year
                release_date = movie_data.get("release_date", "")
                release_year = None
                if release_date and len(str(release_date)) >= 4:
                    try:
                        release_year = int(str(release_date)[:4])
                    except (ValueError, TypeError):
                        pass
                
                # Extract directors from crew - try multiple formats
                directors = []
                crew_list = movie_data.get("crew", [])
                if isinstance(crew_list, list) and len(crew_list) > 0:
                    for person in crew_list:
                        if isinstance(person, dict):
                            # Check for director role
                            job = person.get("job", "").lower()
                            if "director" in job:
                                name = person.get("name") or person.get("Name")
                                if name:
                                    directors.append(name)
                
                # If no directors found, try alternative fields
                if not directors:
                    # Try director field directly
                    director_field = movie_data.get("director") or movie_data.get("directors")
                    if director_field:
                        if isinstance(director_field, list):
                            directors = [d for d in director_field if d]
                        elif isinstance(director_field, str):
                            directors = [director_field]
                
                # Build poster URL - only use poster from movie_data when lookup succeeded.
                # When movie_data is empty, do NOT use rec.get("poster_path") (could be wrong from stale cache).
                poster_url = None
                if movie_data:
                    poster_path = movie_data.get("poster_path")
                    if poster_path and str(poster_path).strip() and str(poster_path) != "None":
                        poster_path = str(poster_path).strip()
                        if poster_path.startswith("http"):
                            poster_url = poster_path
                        elif poster_path.startswith("/"):
                            poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}"
                        else:
                            poster_url = f"https://image.tmdb.org/t/p/w342/{poster_path}"
                # Placeholder when no poster (missing movie_data or no poster_path) - use title for this rec
                if not poster_url:
                    title_for_placeholder = (movie_data.get("title") or rec.get("title") or f"Movie {movie_id}")[:20].replace(" ", "+")
                    poster_url = f"https://via.placeholder.com/342x513/1a1a1a/666666?text={title_for_placeholder}"
                
                conf = rec.get("confidence", 0.5)
                if conf >= 0.7:
                    confidence_level = "high"
                elif conf >= 0.5:
                    confidence_level = "medium"
                else:
                    confidence_level = "low"
                # Use data from recommendation first, then enrich from movie_data
                enriched_rec = {
                    "id": movie_id,
                    "movie_id": movie_id,  # Include both for compatibility
                    "title": rec.get("title") or movie_data.get("title", f"Movie {movie_id}"),
                    "predicted_rating": rec.get("predicted_rating", 0.0),
                    "confidence": conf,
                    "confidence_level": confidence_level,
                    "poster_path": poster_url,
                    "image": poster_url,
                    "poster_url": poster_url,  # Add this for HolographicGallery
                    "genres": genres if genres else (rec.get("genres", []) if isinstance(rec.get("genres"), list) else []),
                    "genre": genres[0] if genres else (rec.get("genres", [None])[0] if isinstance(rec.get("genres"), list) and rec.get("genres") else "Unknown"),
                    "year": release_year or movie_data.get("release_year") or rec.get("year", 2020),
                    "release_year": release_year or rec.get("release_year"),
                    "director": directors[0] if directors else (rec.get("director") or movie_data.get("director") or "Unknown"),
                    "directors": directors if directors else (rec.get("directors") or []),
                    "genres_list": genres if genres else (rec.get("genres", []) if isinstance(rec.get("genres"), list) else []),
                    "overview": rec.get("overview") or movie_data.get("overview", "")[:200],
                    "vote_average": rec.get("vote_average") or movie_data.get("vote_average", 0.0),
                    "rating": rec.get("vote_average") or rec.get("rating") or movie_data.get("vote_average", 0.0),
                    "ai_reason": rec.get("explanation") or rec.get("ai_reason") or None
                }
                enriched_recommendations.append(enriched_rec)
            except Exception as enrich_error:
                logger.warning(f"Failed to enrich recommendation {rec.get('movie_id', 'unknown')}: {enrich_error}")
                # Append sanitized rec (placeholder poster only) so we never surface wrong posters
                enriched_recommendations.append(_sanitize_rec_poster(rec))
        
        if not enriched_recommendations and recommendations:
            # Sanitize posters so we never return wrong poster_path from cache
            enriched_recommendations = [_sanitize_rec_poster(r) for r in recommendations]
        
        # Determine if using model or fallback
        is_model_recommendations = (
            model_service.engine is not None and 
            len(enriched_recommendations) > 0 and
            any(rec.get("confidence", 0) > 0.3 for rec in enriched_recommendations)
        )
        
        # Get user interactions count safely
        try:
            total_interactions = len(model_service.get_user_interactions(current_user.user_id))
        except Exception as interactions_error:
            logger.warning(f"Failed to get user interactions: {interactions_error}")
            total_interactions = 0
        
        # Fallback: get last_refresh from DB if not from cache (existing users)
        if last_refresh is None:
            status = _get_onboarding_status_db(db, current_user.user_id)
            data = status.get("data") or {}
            if isinstance(data, dict):
                last_refresh = data.get("last_recommendation_refresh")
        
        return {
            "recommendations": enriched_recommendations,
            "onboarding_required": not onboarding_completed,
            "onboarding_completed": onboarding_completed,
            "total_interactions": total_interactions,
            "model_source": "ensemble" if is_model_recommendations else "fallback",
            "last_refresh": last_refresh,
            "message": "Personalized recommendations based on your preferences" if onboarding_completed else "Popular recommendations - complete onboarding for personalized suggestions"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (these are intentional)
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        error_traceback = traceback.format_exc()
        logger.error("get_recommendations: %s\n%s", error_detail, error_traceback)
        
        # Try to return empty recommendations instead of crashing
        try:
            return {
                "recommendations": [],
                "onboarding_required": False,
                "onboarding_completed": False,
                "total_interactions": 0,
                "model_source": "error",
                "message": f"Error getting recommendations: {error_detail}. Please check server logs.",
                "error": error_detail
            }
        except:
            # If even that fails, raise HTTPException
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get recommendations: {error_detail}. Check server logs for details."
            )

@router.post("/interact")
@limiter.limit("120/minute")
async def record_interaction(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record user interaction - accepts JSON body with movie_id, action, etc."""
    try:
        # Parse JSON body
        try:
            body = await request.json()
        except Exception as json_error:
            logger.warning("Failed to parse JSON body: %s", json_error)
            raise HTTPException(status_code=400, detail=f"Invalid JSON body: {str(json_error)}")
        
        movie_id = body.get("movie_id")
        action = body.get("action")
        rating = body.get("rating")
        review_text = body.get("review_text")
        
        # Validate required fields
        if not movie_id:
            raise HTTPException(status_code=400, detail="movie_id is required")
        if not action:
            raise HTTPException(status_code=400, detail="action is required")
        
        movie_id = int(movie_id)
        action = str(action)
        
        logger.debug("POST /interact: user_id=%s movie_id=%s action=%s", current_user.user_id, movie_id, action)
        from ..models import UserInteraction
        
        # Validate action
        valid_actions = ["like", "dislike", "favorite", "review"]
        if action not in valid_actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action. Must be one of: {valid_actions}"
            )
        
        # Check if interaction already exists
        existing = db.query(UserInteraction).filter(
            UserInteraction.user_id == current_user.user_id,
            UserInteraction.movie_id == movie_id,
            UserInteraction.action == action
        ).first()
        
        # Handle mutual exclusivity: like and dislike cannot coexist
        opposite_action = None
        opposite_interaction = None
        if action == "like":
            opposite_action = "dislike"
        elif action == "dislike":
            opposite_action = "like"
        
        # Delete opposite interaction if it exists
        if opposite_action:
            opposite_interaction = db.query(UserInteraction).filter(
                UserInteraction.user_id == current_user.user_id,
                UserInteraction.movie_id == movie_id,
                UserInteraction.action == opposite_action
            ).first()
            if opposite_interaction:
                logger.debug("Removing opposite interaction: %s for movie %s", opposite_action, movie_id)
                db.delete(opposite_interaction)
                db.flush()  # Flush before commit to ensure order
        
        if existing:
            # For favorite action: toggle off (delete) if already exists
            if action == "favorite":
                logger.debug("Removing favorite for movie %s", movie_id)
                db.delete(existing)
                db.commit()
                return {
                    "success": True,
                    "message": f"Removed favorite for movie {movie_id}",
                    "interaction_id": None,
                    "removed": True,
                    "is_duplicate": False
                }
            # For other actions: Update existing interaction
            existing.rating = rating if rating else existing.rating
            existing.review_text = review_text if review_text else existing.review_text
            existing.created_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "success": True,
                "message": f"Updated {action} for movie {movie_id}",
                "interaction_id": existing.id,
                "removed_opposite": opposite_action if opposite_interaction else None,
                "is_duplicate": False  # It's an update, not duplicate
            }
        
        # Map action to rating (improved weights for better recommendations)
        action_ratings = {
            "like": 6.0,        # Moderate positive (increased from 4.0)
            "dislike": 1.0,     # Strong negative (decreased from 2.0)
            "favorite": 9.0,    # Very strong positive (increased from 5.0)
            "review": rating or 5.0  # User-provided or neutral default
        }
        
        # Create new interaction in database
        interaction = UserInteraction(
            user_id=current_user.user_id,
            movie_id=movie_id,
            action=action,
            rating=rating if rating else action_ratings[action],
            review_text=review_text
        )
        
        logger.debug("Saving interaction: user_id=%s movie_id=%s action=%s", current_user.user_id, movie_id, action)
        removed_opposite = None
        try:
            db.add(interaction)
            db.commit()
            db.refresh(interaction)
            logger.info("Saved interaction id=%s", interaction.id)
            if opposite_interaction:
                removed_opposite = opposite_action
        except IntegrityError as ie:
            logger.warning("IntegrityError: %s", ie)
            # Race condition: another request created it
            db.rollback()
            existing = db.query(UserInteraction).filter(
                UserInteraction.user_id == current_user.user_id,
                UserInteraction.movie_id == movie_id,
                UserInteraction.action == action
            ).first()
            if existing:
                return {
                    "success": True,
                    "message": f"Already recorded {action} for movie {movie_id}",
                    "interaction_id": existing.id,
                    "removed_opposite": removed_opposite,
                    "is_duplicate": True
                }
            raise
        
        # Update model in background so we return fast (model load can take 15-30s when cold)
        def _update_model_background():
            try:
                svc = _get_model()
                svc.update_user_preferences(
                    current_user.user_id,
                    movie_id,
                    action_ratings[action],
                    action,
                    review_text=review_text if action == "review" else None,
                )
            except Exception as e:
                logger.warning("Background model update failed: %s", e)

        t = threading.Thread(target=_update_model_background, daemon=True)
        t.start()

        # Record interaction (monitoring)
        if MONITORING_AVAILABLE and monitor:
            try:
                interaction_type_map = {
                    "like": "click",
                    "dislike": "click",
                    "favorite": "click",
                    "review": "rating" if rating else "click"
                }
                monitor.record_interaction(
                    user_id=current_user.user_id,
                    movie_id=movie_id,
                    interaction_type=interaction_type_map.get(action, "click"),
                    rating=rating if action == "review" and rating else action_ratings[action]
                )
            except Exception as e:
                logger.warning("Failed to record interaction: %s", e)
        
        return {
            "success": True,
            "message": f"Recorded {action} for movie {movie_id}",
            "interaction_id": interaction.id,
            "removed_opposite": removed_opposite,
            "next_recommendations_ready": True,
            "is_duplicate": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("record_interaction error")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record interaction: {str(e)}"
        )

@router.get("/interactions")
async def get_user_interactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get recent user interactions from database"""
    logger.debug("GET /interactions user_id=%s", current_user.user_id)
    try:
        from ..models import UserInteraction
        
        # Get interactions from database
        interactions_query = db.query(UserInteraction).filter(
            UserInteraction.user_id == current_user.user_id
        ).order_by(UserInteraction.created_at.desc()).limit(limit).all()
        
        logger.debug("Found %d interactions for user %s", len(interactions_query), current_user.user_id)
        
        # Get movie data for enrichment
        model_service = _get_model()
        
        interactions = []
        for interaction in interactions_query:
            movie_id = interaction.movie_id
            movie_data = model_service.movie_data.get(str(movie_id)) or model_service.movie_data.get(int(movie_id)) if isinstance(movie_id, (int, str)) and str(movie_id).isdigit() else {}
            movie_title = movie_data.get('title', f"Movie {movie_id}")
            
            interactions.append({
                "id": interaction.id,
                "movie_id": movie_id,
                "movie_title": movie_title,
                "action": interaction.action,
                "rating": interaction.rating,
                "review_text": interaction.review_text,
                "timestamp": interaction.created_at.isoformat() if interaction.created_at else None,
                "created_at": interaction.created_at.isoformat() if interaction.created_at else None
            })
        
        return {
            "interactions": interactions,
            "total": len(interactions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interactions: {str(e)}"
        )

@router.get("/onboarding/status")
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get onboarding status for the current user"""
    try:
        return _get_onboarding_status_db(db, current_user.user_id)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get onboarding status: {str(e)}"
        )

@router.post("/onboarding/start")
async def start_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start the onboarding process"""
    try:
        result = onboarding_service.start_onboarding(current_user.user_id)
        _upsert_onboarding_status(
            db,
            current_user.user_id,
            completed=False,
            skipped=False,
            stage=1,
            data={"started_at": datetime.now(timezone.utc).isoformat()},
        )
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start onboarding: {str(e)}"
        )

@router.post("/onboarding/update")
async def update_onboarding(
    stage: int,
    selections: List,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update onboarding progress"""
    try:
        result = onboarding_service.update_onboarding(current_user.user_id, stage, selections)

        # Persist progress so onboarding isn't re-prompted after completion
        key_map = {1: "genres", 2: "favorite_movies", 3: "mood_preferences"}
        status = _get_onboarding_status_db(db, current_user.user_id)
        data = status.get("data", {}) if isinstance(status.get("data", {}), dict) else {}
        pref_key = key_map.get(stage)
        if pref_key:
            data.setdefault("preferences", {})
            data["preferences"][pref_key] = selections

        completed = bool(result.get("completed", False))
        _upsert_onboarding_status(
            db,
            current_user.user_id,
            completed=completed,
            skipped=False,
            stage=result.get("stage", stage),
            data=data,
        )
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update onboarding: {str(e)}"
        )

@router.post("/onboarding/complete")
async def complete_onboarding(
    onboarding_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark onboarding as completed"""
    try:
        skipped = bool(onboarding_data.get("skipped")) if onboarding_data else False
        preferences = {}
        if onboarding_data and not skipped:
            if onboarding_data.get("preferences") and isinstance(onboarding_data.get("preferences"), dict):
                preferences = onboarding_data.get("preferences", {})
            else:
                preferences = onboarding_data

        data = {
            "preferences": preferences,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        _upsert_onboarding_status(
            db,
            current_user.user_id,
            completed=True,
            skipped=skipped,
            stage=4,
            data=data,
        )

        # Keep in-memory onboarding service in sync (best-effort)
        try:
            key = f"onboarding:{current_user.user_id}"
            onboarding_service._set_data(
                key,
                {
                    "user_id": current_user.user_id,
                    "completed": True,
                    "skipped": skipped,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "preferences": preferences,
                },
                86400,
            )
        except Exception:
            pass

        return {"message": "Onboarding completed successfully", "onboarding_completed": True}
        
    except Exception as e:
        logger.error(f"Error completing onboarding: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete onboarding: {str(e)}"
        )


@router.post("/onboarding/reset")
async def reset_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset onboarding so user can update preferences."""
    try:
        # Reset persistent status
        _upsert_onboarding_status(
            db,
            current_user.user_id,
            completed=False,
            skipped=False,
            stage=1,
            data={"preferences": {}},
        )
        # Reset in-memory onboarding service (best-effort)
        try:
            key = f"onboarding:{current_user.user_id}"
            onboarding_service._set_data(
                key,
                {
                    "user_id": current_user.user_id,
                    "completed": False,
                    "skipped": False,
                    "stage": 1,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "preferences": {
                        "genres": [],
                        "favorite_movies": [],
                        "mood_preferences": [],
                        "time_preferences": [],
                    },
                },
                86400,
            )
        except Exception:
            pass
        return {"message": "Onboarding reset", "onboarding_completed": False}
    except Exception as e:
        logger.error(f"Error resetting onboarding: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset onboarding: {str(e)}"
        )

def _is_documentary(movie_data: dict) -> bool:
    """True if movie is a documentary (excluded from Surprise Me / random)."""
    genres = movie_data.get("genres") or []
    for g in genres:
        if isinstance(g, dict):
            gid, gname = g.get("id"), (g.get("name") or "")
            if gid == 99 or str(gname).upper() == "DOCUMENTARY":
                return True
        elif isinstance(g, str) and "documentary" in g.lower():
            return True
    return False


def _is_adult(movie_data: dict) -> bool:
    """True if movie is marked adult (excluded from Surprise Me and main feed when possible)."""
    if not movie_data:
        return False
    return movie_data.get("adult") is True


@router.get("/surprise-me")
@limiter.limit("30/minute")
async def get_surprise_me(
    request: Request,
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Good movies only, no documentaries, any genre mixed. Random sample."""
    try:
        model_service = _get_model()
        if len(model_service.movie_data) == 0:
            try:
                model_service._get_fallback_recommendations(current_user.user_id, 1)
            except Exception:
                pass
            if len(model_service.movie_data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Movie data not available. Please ensure data files are present."
                )

        pool = []
        for movie_id, md in model_service.movie_data.items():
            if _is_documentary(md) or _is_adult(md):
                continue
            vote_avg = (md.get("vote_average") or 0) or 0
            vote_count = (md.get("vote_count") or 0) or 0
            if vote_avg < 7.0 or vote_count < 100:
                continue
            mid = int(movie_id) if isinstance(movie_id, str) and str(movie_id).isdigit() else movie_id
            pool.append({"movie_id": mid, "movie_data": md, "vote_average": vote_avg, "vote_count": vote_count})

        random.shuffle(pool)
        selected = pool[:limit]
        recommendations = []
        for m in selected:
            md = m["movie_data"]
            recommendations.append({
                "movie_id": m["movie_id"],
                "title": md.get("title", f"Movie {m['movie_id']}"),
                "predicted_rating": float(m["vote_average"]),
                "confidence": 0.85,
                "poster_path": md.get("poster_path"),
                "overview": (md.get("overview") or "")[:200],
                "vote_average": m["vote_average"],
                "vote_count": m["vote_count"],
                "director": model_service._extract_director(md),
                "guarantee_level": "high",
                "explanation": f"Quality pick: {m['vote_average']}/10 from {m['vote_count']} votes. No documentaries or adult content, any genre.",
                "is_surprise": True,
            })

        return {
            "recommendations": recommendations,
            "message": f"🎬 {len(recommendations)} good movies — no documentaries or adult content, mixed genres.",
            "type": "surprise_me",
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get surprise recommendations: {str(e)}",
        )

@router.get("/mood")
@limiter.limit("30/minute")
async def get_mood_recommendations(
    request: Request,
    current_user: User = Depends(get_current_user),
    q: str = Query(..., min_length=1, description="Mood/vibe e.g. cozy rainy Sunday"),
    limit: int = Query(20, ge=1, le=50),
):
    """Mood/Vibe recommendations: natural-language mood → structured criteria → movies. One canonical mood→criteria path."""
    from ..mood_service import mood_to_criteria
    criteria = mood_to_criteria(q.strip())
    if not criteria:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Could not interpret mood. Try different words.")
    try:
        model_service = _get_model()
        movie_data = model_service.movie_data or {}
        if not movie_data:
            return {"recommendations": [], "criteria": criteria.model_dump(), "total": 0}
        from ..routes.movies import _is_adult, _is_documentary, _movie_has_genre
        candidates = []
        for mid, m in movie_data.items():
            if _is_adult(m) or _is_documentary(m):
                continue
            mid_int = int(mid) if isinstance(mid, str) and str(mid).isdigit() else mid
            vote_avg = (m.get("vote_average") or 0) or 0
            vote_count = (m.get("vote_count") or 0) or 0
            if vote_count < 50 or vote_avg < 5.0:
                continue
            score = 0
            for g in criteria.genres:
                if _movie_has_genre(m, g):
                    score += 2
                    break
            overview = (m.get("overview") or "").lower()
            title = (m.get("title") or "").lower()
            for kw in criteria.keywords:
                if kw.lower() in overview or kw.lower() in title:
                    score += 1
            if criteria.min_year or criteria.max_year:
                rd = m.get("release_date") or m.get("release_year")
                y = int(str(rd)[:4]) if rd and len(str(rd)) >= 4 else None
                if y is not None:
                    if criteria.min_year and y < criteria.min_year:
                        continue
                    if criteria.max_year and y > criteria.max_year:
                        continue
            if score > 0 or not criteria.genres:
                candidates.append((mid_int, m, score + vote_avg * 0.1))
        candidates.sort(key=lambda x: -x[2])
        recs = []
        for mid_int, m, _ in candidates[:limit]:
            recs.append({
                "movie_id": mid_int,
                "title": m.get("title", "Unknown"),
                "overview": (m.get("overview") or "")[:200],
                "vote_average": m.get("vote_average", 0),
                "poster_path": m.get("poster_path"),
                "explanation": None,
                "confidence": None,
            })
        return {"recommendations": recs, "criteria": criteria.model_dump(), "total": len(recs)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Mood recommendations failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/hidden-gems")
@limiter.limit("30/minute")
async def get_hidden_gems(
    request: Request,
    current_user: User = Depends(get_current_user),
    limit: int = Query(15, ge=1, le=50),
):
    """Hidden gems: high quality, low popularity, configurable filters. Serendipity score = relevance * vote_quality * (1 - norm_popularity)."""
    from ..hidden_gems_config import (
        passes_hidden_gems_filters,
        serendipity_score,
        get_hidden_gems_config,
    )
    try:
        model_service = _get_model()
        movie_data = model_service.movie_data or {}
        if not movie_data:
            return {"recommendations": [], "config": get_hidden_gems_config(), "total": 0}
        from ..routes.recommendations import _is_adult, _is_documentary
        pool = []
        for mid, m in movie_data.items():
            if _is_adult(m) or _is_documentary(m):
                continue
            pop = float(m.get("popularity") or 0)
            vc = int(m.get("vote_count") or 0)
            va = float(m.get("vote_average") or 0)
            if not passes_hidden_gems_filters(pop, vc, va):
                continue
            mid_int = int(mid) if isinstance(mid, str) and str(mid).isdigit() else mid
            rel = 1.0
            score = serendipity_score(pop, vc, va, rel)
            pool.append((mid_int, m, score))
        pool.sort(key=lambda x: -x[2])
        recs = []
        for mid_int, m, score in pool[:limit]:
            pp = m.get("poster_path")
            if pp and str(pp).strip() and str(pp) != "None":
                pp = str(pp).strip()
                poster_url = pp if pp.startswith("http") else f"https://image.tmdb.org/t/p/w342{pp}" if pp.startswith("/") else f"https://image.tmdb.org/t/p/w342/{pp}"
            else:
                title_safe = (m.get("title") or "Movie")[:20].replace(" ", "+")
                poster_url = f"https://via.placeholder.com/342x513/1a1a1a/666666?text={title_safe}"
            recs.append({
                "movie_id": mid_int,
                "title": m.get("title", "Unknown"),
                "overview": (m.get("overview") or "")[:200],
                "vote_average": m.get("vote_average", 0),
                "vote_count": m.get("vote_count", 0),
                "popularity": m.get("popularity", 0),
                "serendipity_score": round(score, 4),
                "poster_path": m.get("poster_path"),
                "poster_url": poster_url,
                "explanation": None,
                "confidence": None,
            })
        return {"recommendations": recs, "config": get_hidden_gems_config(), "total": len(recs)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Hidden gems failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/onboarding/data")
async def get_onboarding_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get onboarding data (genres, popular movies, etc.)"""
    try:
        return {
            "genres": onboarding_service.genres,
            "popular_movies": onboarding_service.popular_movies
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get onboarding data: {str(e)}"
        ) 