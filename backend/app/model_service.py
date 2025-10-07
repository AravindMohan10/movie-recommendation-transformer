import torch
import torch.nn as nn
import numpy as np
import pickle
import json
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from pathlib import Path

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import redis, make it optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")

# Environment-based cache configuration
# Development: 5 minutes for faster testing
# Production: 24 hours (86400 seconds) for stable recommendations
ENV = os.getenv("ENV", "production").lower()
DEV_MODE = ENV in ["development", "dev", "test"]
CACHE_TTL_PRODUCTION = 86400  # 24 hours
CACHE_TTL_DEVELOPMENT = 300   # 5 minutes

CACHE_TTL = CACHE_TTL_DEVELOPMENT if DEV_MODE else CACHE_TTL_PRODUCTION
logger.info(f"🔧 Cache Configuration: {'DEVELOPMENT' if DEV_MODE else 'PRODUCTION'} mode - TTL: {CACHE_TTL}s ({CACHE_TTL // 60 if CACHE_TTL < 3600 else CACHE_TTL // 3600}{'min' if CACHE_TTL < 3600 else 'h'})")

# RAG + LLM: keep transformers in codebase but use CF + RAG rerank
USE_RAG_LLM_RERANK = os.getenv("USE_RAG_LLM_RERANK", "true").lower() in ("1", "true", "yes")

# Main recommendations: only movies from this year onward (older movies in "Classics" genre)
MAIN_REC_MIN_YEAR = int(os.getenv("MAIN_REC_MIN_YEAR", "1980"))

class MovieRecommendationModel:
    def __init__(self, model_path: Optional[str] = None, use_redis: bool = True):
        """
        Initialize the recommendation model service.
        
        Args:
            model_path: Path to ensemble model base directory (e.g., "Checkpoints/recommendation_engine")
            use_redis: Whether to use Redis for caching (falls back to in-memory if Redis unavailable)
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Determine model path
        if model_path is None:
            BASE_DIR = Path(__file__).parent.parent.parent
            model_path = BASE_DIR / "Checkpoints" / "recommendation_engine"
        self.model_path = Path(model_path)
        
        # Redis setup (optional)
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.redis_client = None
        if self.use_redis:
            try:
                self.redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    db=int(os.getenv('REDIS_DB', 0)),
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Connected to Redis")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory cache: {e}")
                self.use_redis = False
        
        # In-memory cache fallback
        if not self.use_redis:
            self._in_memory_cache = {}
            self._in_memory_interactions = defaultdict(dict)
            self._last_shown: Dict[int, List[int]] = {}
            logger.info("Using in-memory cache (Redis not available)")
        else:
            self._last_shown = None
        
        # Model components
        self.engine = None
        self.movie_data = {}
        
        # Load model and mappings
        self._load_model()
        
    def _load_model(self):
        """Load the trained ensemble recommendation engine"""
        try:
            # Check if model files exist
            ensemble_path = f"{self.model_path}_ensemble.json"
            if not Path(ensemble_path).exists():
                logger.warning(f"Model not found at {self.model_path}. Using fallback mode.")
                logger.warning("Please train models using train_recommendation_engine.py")
                return
            
            # Import ensemble model (lazy import to avoid circular deps)
            import sys
            BASE_DIR = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(BASE_DIR))
            
            from models.ensemble_recommender import MovieRecommendationEngine
            from models.content_transformer import ContentBasedRecommender, MovieContentTransformer
            from models.collaborative_filtering import CollaborativeFilteringRecommender, MatrixFactorization
            from models.context_transformer import ContextualRecommender, ReviewContextTransformer
            
            # Load movie data for initialization
            movie_data_path = BASE_DIR / "data" / "raw" / "tmdb_movies_50k_20250711_011112.jsonl"
            if not movie_data_path.exists():
                # Try alternative path
                movie_data_path = BASE_DIR / "data" / "raw" / "tmdb_complete_dataset.jsonl"
            
            movies = []
            if movie_data_path.exists():
                with open(movie_data_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            movies.append(json.loads(line.strip()))
                        except:
                            continue
                logger.info(f"Loaded {len(movies)} movies for model initialization")
            else:
                logger.warning("Movie data file not found. Model will be in limited mode.")
            
            # Initialize model components (minimal initialization for loading)
            content_model = MovieContentTransformer(
                model_name="distilbert-base-uncased",
                embedding_dim=768,
                max_length=512,
                dropout=0.1
            )
            content_recommender = ContentBasedRecommender(content_model)
            
            # Create minimal collaborative model (will load weights)
            collab_model = MatrixFactorization(
                num_users=10000,  # Will be overridden by loaded state
                num_movies=50000,  # Will be overridden by loaded state
                embedding_dim=128,
                dropout=0.1
            )
            collab_recommender = CollaborativeFilteringRecommender(collab_model)
            
            # Contextual model
            context_model = ReviewContextTransformer(
                model_name="distilbert-base-uncased",
                embedding_dim=768,
                max_length=512,
                dropout=0.1
            )
            contextual_recommender = ContextualRecommender(context_model)
            
            # Create engine and load
            self.engine = MovieRecommendationEngine(
                content_recommender=content_recommender,
                collaborative_recommender=collab_recommender,
                contextual_recommender=contextual_recommender
            )
            
            # Load engine state
            self.engine.load_engine(str(self.model_path), movies)
            
            # Store movie data for lookup
            for movie in movies:
                movie_id = movie.get('tmdb_id') or movie.get('id')
                if movie_id:
                    self.movie_data[str(movie_id)] = movie
            
            logger.info(f"✅ Model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)
            logger.warning("Model service will operate in fallback mode")
            self.engine = None
        
        # Always try to load movie data, even if model failed (needed for fallback)
        if len(self.movie_data) == 0:
            try:
                BASE_DIR = Path(__file__).parent.parent.parent
                movie_data_path = BASE_DIR / "data" / "raw" / "tmdb_movies_50k_20250711_011112.jsonl"
                if not movie_data_path.exists():
                    movie_data_path = BASE_DIR / "data" / "raw" / "tmdb_complete_dataset.jsonl"
                
                if movie_data_path.exists():
                    logger.info(f"Loading movie data from {movie_data_path}")
                    with open(movie_data_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                movie = json.loads(line.strip())
                                movie_id = movie.get('tmdb_id') or movie.get('id')
                                if movie_id:
                                    self.movie_data[str(movie_id)] = movie
                            except:
                                continue
                    logger.info(f"✅ Loaded {len(self.movie_data)} movies for recommendations")
                else:
                    logger.warning(f"Movie data file not found at {movie_data_path}")
            except Exception as fallback_error:
                logger.error(f"Failed to load movie data: {fallback_error}", exc_info=True)
    
    def _get_cached(self, key: str) -> Optional[str]:
        """Get value from cache (Redis or in-memory)"""
        if self.use_redis and self.redis_client:
            try:
                return self.redis_client.get(key)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
                return None
        else:
            return self._in_memory_cache.get(key)
    
    def _set_cached(self, key: str, value: str, ttl: int = 3600):
        """Set value in cache (Redis or in-memory)"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(key, ttl, value)
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        else:
            self._in_memory_cache[key] = value
    
    def _delete_cached(self, key: str):
        """Delete value from cache"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
        else:
            self._in_memory_cache.pop(key, None)

    def _invalidate_user_recommendations(self, user_id: int):
        """Invalidate all recommendation cache entries for this user (so next request gets fresh recs)."""
        prefix = f"recommendations:{user_id}:"
        if self.use_redis and self.redis_client:
            try:
                keys = self.redis_client.keys(f"{prefix}*")
                if keys:
                    self.redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} recommendation cache key(s) for user {user_id}")
            except Exception as e:
                logger.warning(f"Redis delete by pattern failed: {e}")
        else:
            to_remove = [k for k in self._in_memory_cache if k.startswith(prefix)]
            for k in to_remove:
                self._in_memory_cache.pop(k, None)
            if to_remove:
                logger.info(f"Invalidated {len(to_remove)} recommendation cache key(s) for user {user_id}")

    LAST_SHOWN_TTL = 172800  # 48h

    def _get_last_shown(self, user_id: int) -> List[int]:
        """Last batch of movie IDs we showed (exclude on next 24h refresh)."""
        key = f"last_shown:{user_id}"
        if self.use_redis and self.redis_client:
            try:
                raw = self.redis_client.get(key)
                if raw:
                    out = json.loads(raw)
                    return [int(x) for x in out if x is not None]
            except Exception as e:
                logger.warning(f"Redis get last_shown failed: {e}")
            return []
        out = getattr(self, "_last_shown", {}).get(user_id) or []
        return list(out)

    def _set_last_shown(self, user_id: int, movie_ids: List[int]) -> None:
        key = f"last_shown:{user_id}"
        ids = [int(x) for x in movie_ids if x is not None]
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(key, self.LAST_SHOWN_TTL, json.dumps(ids))
            except Exception as e:
                logger.warning(f"Redis set last_shown failed: {e}")
        else:
            if not hasattr(self, "_last_shown"):
                self._last_shown = {}
            self._last_shown[user_id] = ids

    def get_recommendations(self, user_id: int, n_recommendations: int = 10, interaction_count: int = 0, db_session=None, force_refresh: bool = False) -> List[Dict]:
        """
        Get top movie recommendations for a user.
        
        Args:
            user_id: User ID
            n_recommendations: Number of recommendations to return
            interaction_count: Number of user interactions (for progressive enhancement)
            db_session: Optional database session to load fresh interactions
            force_refresh: Force cache refresh (only works in development mode)
        """
        import time
        start_time = time.time()
        
        rag_suffix = "rag" if USE_RAG_LLM_RERANK else "cf"
        cache_key = f"recommendations:{user_id}:{n_recommendations}:{rag_suffix}"

        # Check cache first (unless force_refresh is requested)
        if force_refresh:
            logger.info(f"🔄 Force refresh requested - bypassing cache")
            # Delete cache to force fresh generation
            self._delete_cached(cache_key)
        else:
            # Normal cache check
            cached = self._get_cached(cache_key)
            if cached:
                try:
                    result = json.loads(cached)
                    ids = [r.get("movie_id") or r.get("id") for r in result if r.get("movie_id") or r.get("id")]
                    if ids:
                        self._set_last_shown(user_id, ids)
                    elapsed = (time.time() - start_time) * 1000
                    logger.info(f"✅ Recommendations from cache: {elapsed:.2f}ms (TTL: {CACHE_TTL}s)")
                    return result
                except Exception:
                    pass
        
        if self.engine is None:
            logger.warning("Model not loaded, using fallback recommendations")
            try:
                exclude_last = self._get_last_shown(user_id)
                fallback_recs = self._get_fallback_recommendations(
                    user_id, n_recommendations, exclude_ids=exclude_last
                )
                if fallback_recs:
                    self._set_last_shown(user_id, [r["movie_id"] for r in fallback_recs])
                return fallback_recs
            except Exception as fallback_error:
                logger.error(f"Fallback recommendations also failed: {fallback_error}", exc_info=True)
                return []
        
        # Before generating recommendations, reload all user interactions from database
        if db_session:
            try:
                self._reload_user_interactions_from_db(user_id, db_session)
            except Exception as e:
                logger.warning(f"Failed to reload interactions from DB: {e}, using existing model state")
        else:
            logger.warning("No db_session provided - recommendations may not include latest interactions")

        try:
            exclude_last_shown = self._get_last_shown(user_id)
            if exclude_last_shown:
                logger.info(f"Excluding {len(exclude_last_shown)} last-shown movies from this refresh")
            valid_movie_ids = self._get_valid_movie_ids(min_year=MAIN_REC_MIN_YEAR)
            logger.info(f"Constraining recommendations to {len(valid_movie_ids)} valid movies (release year >= {MAIN_REC_MIN_YEAR})")

            if hasattr(self.engine, "collaborative_recommender"):
                if USE_RAG_LLM_RERANK:
                    recs = self._get_cf_rag_recommendations(
                        user_id, n_recommendations, valid_movie_ids, db_session, exclude_last_shown
                    )
                else:
                    recs = self._get_cf_only_recommendations(
                        user_id, n_recommendations, valid_movie_ids, db_session, exclude_last_shown
                    )
            else:
                recs = self._get_ensemble_recommendations(
                    user_id, n_recommendations * 2, valid_movie_ids
                )

            formatted_recs = []
            for rec in recs:
                movie_id = rec.get('movie_id')
                tmdb_id = movie_id  # Assume movie_id is already tmdb_id
                
                # Try multiple lookup strategies
                movie_info = None
                
                # Strategy 1: Try as string key (most common)
                movie_info = self.movie_data.get(str(tmdb_id))
                
                # Strategy 2: Try as int key
                if not movie_info and isinstance(tmdb_id, (int, str)):
                    try:
                        int_id = int(tmdb_id) if isinstance(tmdb_id, str) else tmdb_id
                        movie_info = self.movie_data.get(int_id)
                        # Also try string version of int
                        if not movie_info:
                            movie_info = self.movie_data.get(str(int_id))
                    except (ValueError, TypeError):
                        pass
                
                # Strategy 3: Try direct key
                if not movie_info:
                    movie_info = self.movie_data.get(tmdb_id)
                
                # If still not found, try to get from content_recommender's movie_data
                if not movie_info and hasattr(self.engine, 'content_recommender'):
                    content_data = getattr(self.engine.content_recommender, 'movie_data', {})
                    # Try multiple key formats
                    movie_info = (content_data.get(tmdb_id) or 
                                 content_data.get(str(tmdb_id)) or 
                                 (content_data.get(int(tmdb_id)) if isinstance(tmdb_id, (int, str)) and str(tmdb_id).isdigit() else {}))
                
                # If still no info, skip this recommendation and log
                if not movie_info:
                    logger.warning(f"Movie {tmdb_id} not found in movie_data. Skipping recommendation.")
                    continue  # Skip movies we don't have data for
                
                formatted_rec = {
                    "movie_id": int(tmdb_id) if isinstance(tmdb_id, (int, str)) and str(tmdb_id).isdigit() else tmdb_id,
                    "title": movie_info.get('title', f"Movie {tmdb_id}"),
                    "predicted_rating": float(rec.get('ensemble_score', 0.0)),
                    "confidence": float(rec.get('confidence', 0.5)),
                    "poster_path": movie_info.get('poster_path'),
                    "overview": movie_info.get('overview', '')[:200] if movie_info.get('overview') else '',
                    "vote_average": movie_info.get('vote_average'),
                    "guarantee_level": rec.get('guarantee', {}).get('guarantee_level', 'medium'),
                    "explanation": rec.get('explanation', 'Personalized recommendation based on your preferences.')
                }
                formatted_recs.append(formatted_rec)
            
            if len(formatted_recs) < n_recommendations:
                logger.info(f"Only {len(formatted_recs)} valid recommendations found, supplementing with fallback")
                fallback_needed = n_recommendations - len(formatted_recs)
                existing_ids = {rec["movie_id"] for rec in formatted_recs}
                exclude_fallback = list(existing_ids) + exclude_last_shown
                fallback_recs = self._get_fallback_recommendations(user_id, fallback_needed, exclude_ids=exclude_fallback)
                for fallback in fallback_recs:
                    if fallback["movie_id"] not in existing_ids:
                        formatted_recs.append(fallback)
                        existing_ids.add(fallback["movie_id"])
                        if len(formatted_recs) >= n_recommendations:
                            break

            out = formatted_recs[:n_recommendations]
            ids = [r["movie_id"] for r in out]
            if ids:
                self._set_last_shown(user_id, ids)
            self._set_cached(cache_key, json.dumps(out), ttl=CACHE_TTL)
            elapsed = (time.time() - start_time) * 1000
            ttl_hours = CACHE_TTL / 3600 if CACHE_TTL >= 3600 else CACHE_TTL / 60
            ttl_unit = "h" if CACHE_TTL >= 3600 else "min"
            logger.info(f"⚡ Generated new recommendations: {elapsed:.2f}ms (cached for {ttl_hours:.1f}{ttl_unit})")
            return out
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}", exc_info=True)
            exclude_last = self._get_last_shown(user_id)
            return self._get_fallback_recommendations(
                user_id, n_recommendations, exclude_ids=exclude_last
            )
    
    def _reload_user_interactions_from_db(self, user_id: int, db_session) -> None:
        """
        Reload all user interactions from database and sync to model state.
        This ensures recommendations always use the latest interactions.
        
        Args:
            user_id: User ID
            db_session: Database session to query interactions
        """
        try:
            # Import UserInteraction - add project root to path for absolute import
            import sys
            if str(Path(__file__).parent.parent.parent) not in sys.path:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from .models import UserInteraction
            
            # Get all interactions from database
            interactions_query = db_session.query(UserInteraction).filter(
                UserInteraction.user_id == user_id
            ).order_by(UserInteraction.created_at.asc()).all()
            
            logger.info(f"🔄 Reloading {len(interactions_query)} interactions from database for user {user_id}")
            
            # Clear existing interactions for this user in model state
            if self.engine and hasattr(self.engine, 'ensemble'):
                if user_id in self.engine.ensemble.user_interactions:
                    self.engine.ensemble.user_interactions[user_id] = []
            
            # Reload all interactions into model state
            for interaction in interactions_query:
                try:
                    # Add interaction to ensemble model state
                    if self.engine:
                        # Use the existing method to add interactions
                        self.engine.ensemble.add_user_interaction(
                            user_id,
                            interaction.movie_id,
                            interaction.rating or 5.0,  # Default rating if None
                            interaction.review_text
                        )
                except Exception as e:
                    logger.warning(f"Failed to add interaction {interaction.id} to model: {e}")
                    continue
            
            logger.info(f"✅ Synced {len(interactions_query)} interactions to model state")
            
        except Exception as e:
            logger.error(f"Error reloading interactions from database: {e}", exc_info=True)
            raise

    def _get_exclude_watched(self, user_id: int, db_session) -> List[int]:
        """Movie IDs to exclude (already interacted with)."""
        if not db_session:
            return []
        try:
            from .models import UserInteraction
            rows = db_session.query(UserInteraction.movie_id).filter(
                UserInteraction.user_id == user_id
            ).distinct().all()
            return [int(r[0]) for r in rows]
        except Exception as e:
            logger.warning("Could not load exclude_watched: %s", e)
            return []

    def _get_interaction_counts(self, user_id: int, db_session) -> Tuple[int, int]:
        """(n_liked, n_reviewed) for confidence/explanation. liked = like + favorite."""
        if not db_session:
            return 0, 0
        try:
            from .models import UserInteraction
            rows = db_session.query(UserInteraction).filter(UserInteraction.user_id == user_id).all()
            n_liked = sum(1 for r in rows if r.action in ("like", "favorite"))
            n_reviewed = sum(1 for r in rows if r.action == "review")
            return n_liked, n_reviewed
        except Exception as e:
            logger.warning("Could not load interaction counts: %s", e)
            return 0, 0

    def _get_ensemble_recommendations(
        self, user_id: int, top_k: int, valid_movie_ids: List[int]
    ) -> List[Dict]:
        """Original ensemble path (content + collaborative + contextual)."""
        return self.engine.get_recommendations(
            user_id=user_id,
            top_k=top_k,
            include_guarantees=True,
            valid_movie_ids=valid_movie_ids,
        )

    def _get_cf_rag_recommendations(
        self,
        user_id: int,
        n_recommendations: int,
        valid_movie_ids: List[int],
        db_session,
        exclude_last_shown: Optional[List[int]] = None,
    ) -> List[Dict]:
        """CF + RAG rerank (Options A, B, C). Per-rec confidence + dynamic LLM explanation (or None)."""
        from .rag_reranker import rerank as rag_rerank, get_user_context_for_explanations
        from .llm_service import generate_why_recommendations_batch
        from .rag_service import get_rag_service

        cf = self.engine.collaborative_recommender
        exclude_watched = self._get_exclude_watched(user_id, db_session)
        exclude = list(set(exclude_watched) | set(exclude_last_shown or []))
        candidates = cf.recommend_for_user(
            user_id=user_id,
            top_k=min(n_recommendations * 5, 500),
            exclude_watched=exclude,
            candidate_movies=valid_movie_ids,
        )
        if not candidates:
            logger.info("CF returned no candidates; using fallback for CF+RAG path")
            return []
        reranked = rag_rerank(
            user_id=user_id,
            cf_candidates=candidates,
            movie_data=self.movie_data,
            db_session=db_session,
            valid_movie_ids=valid_movie_ids,
        )
        n_liked, n_reviewed = self._get_interaction_counts(user_id, db_session)
        has_signal = n_liked >= 2 or n_reviewed >= 1
        limit = n_recommendations * 2
        batch = reranked[:limit]
        n_batch = len(batch)
        rag_svc = get_rag_service()
        recs = []
        explanation_items: List[Tuple[Dict[str, Any], str]] = []
        for idx, item in enumerate(batch):
            movie_id = item["movie_id"]
            score = item["score"]
            inj = item["is_rag_injected"]
            cf_c = item["cf_contribution"]
            rag_c = item["rag_contribution"]
            had_emb = item["had_pref_emb"]
            rag_dominated = had_emb and rag_c > cf_c
            cf_dominated = not rag_dominated or cf_c >= rag_c
            is_top = idx < 3
            is_bottom = idx >= max(0, n_batch - 3)

            if inj and rag_dominated:
                reason_bucket = "rag_similar_reviews"
                confidence = 0.86 if has_signal else 0.64
            elif inj and cf_dominated:
                reason_bucket = "rag_injected"
                confidence = 0.80 if has_signal else 0.58
            elif rag_dominated and not inj:
                reason_bucket = "rag_similar_reviews"
                confidence = 0.84 if has_signal else 0.62
            elif cf_dominated and has_signal:
                reason_bucket = "cf_similar_users"
                if is_top:
                    confidence = 0.78
                elif is_bottom:
                    confidence = 0.52
                else:
                    confidence = 0.62
            else:
                reason_bucket = "limited_data"
                if is_bottom:
                    confidence = 0.38
                elif is_top:
                    confidence = 0.50
                else:
                    confidence = 0.44

            confidence = max(0.35, min(0.92, confidence))
            movie_info = self.movie_data.get(str(movie_id)) or self.movie_data.get(movie_id) or self.movie_data.get(int(movie_id)) or {}
            genres_list = movie_info.get("genres") or []
            if isinstance(genres_list, list) and genres_list and isinstance(genres_list[0], dict):
                genres = [g.get("name", "") for g in genres_list if isinstance(g, dict) and g.get("name")]
            else:
                genres = [str(g) for g in genres_list if g]
            directors = []
            for p in (movie_info.get("crew") or []):
                if isinstance(p, dict) and "director" in (p.get("job") or "").lower():
                    n = p.get("name") or p.get("Name")
                    if n:
                        directors.append(n)
            if not directors and movie_info.get("director"):
                directors = [movie_info["director"]] if isinstance(movie_info["director"], str) else list(movie_info.get("director") or [])
            rag_doc = rag_svc.get_document_for_movie(int(movie_id)) if rag_svc else None
            movie_context = {
                "title": (movie_info.get("title") or "").strip(),
                "overview": (movie_info.get("overview") or "")[:200],
                "genres": genres,
                "directors": directors,
                "rag_document": rag_doc or "",
            }
            explanation_items.append((movie_context, reason_bucket))
            recs.append({
                "movie_id": movie_id,
                "ensemble_score": float(score),
                "confidence": round(confidence, 2),
                "guarantee": {"guarantee_level": "medium"},
                "explanation": None,
            })

        if recs and (n_liked >= 1 or n_reviewed >= 1):
            try:
                user_context = get_user_context_for_explanations(user_id, db_session, self.movie_data)
                why_results = generate_why_recommendations_batch(user_context, explanation_items)
                for i, expl in enumerate(why_results):
                    if i < len(recs) and expl:
                        recs[i]["explanation"] = expl
            except Exception as e:
                logger.warning("Dynamic explanation batch failed: %s", e)
        return recs

    def _get_cf_only_recommendations(
        self,
        user_id: int,
        n_recommendations: int,
        valid_movie_ids: List[int],
        db_session,
        exclude_last_shown: Optional[List[int]] = None,
    ) -> List[Dict]:
        """CF-only, no RAG. Per-rec confidence + dynamic LLM explanation (or None)."""
        from .rag_reranker import get_user_context_for_explanations
        from .llm_service import generate_why_recommendations_batch
        from .rag_service import get_rag_service

        cf = self.engine.collaborative_recommender
        exclude_watched = self._get_exclude_watched(user_id, db_session)
        exclude = list(set(exclude_watched) | set(exclude_last_shown or []))
        candidates = cf.recommend_for_user(
            user_id=user_id,
            top_k=n_recommendations * 2,
            exclude_watched=exclude,
            candidate_movies=valid_movie_ids,
        )
        n_liked, n_reviewed = self._get_interaction_counts(user_id, db_session)
        has_signal = n_liked >= 2 or n_reviewed >= 1
        recs = []
        explanation_items: List[Tuple[Dict[str, Any], str]] = []
        if not candidates:
            return recs
        n = len(candidates)
        scores = [s for _, s in candidates]
        smin, smax = min(scores), max(scores)
        span = (smax - smin) or 1.0
        rag_svc = get_rag_service()
        for idx, (movie_id, score) in enumerate(candidates):
            score_norm = (score - smin) / span if span else 0.5
            is_top = idx < 3
            is_bottom = idx >= max(0, n - 3)
            if has_signal:
                reason_bucket = "cf_similar_users"
                if is_top:
                    confidence = 0.80 - (idx * 0.02)
                elif is_bottom:
                    confidence = 0.44 + (n - 1 - idx) * 0.02
                else:
                    confidence = 0.54 + 0.10 * score_norm
            else:
                reason_bucket = "limited_data"
                if is_top:
                    confidence = 0.54 - (idx * 0.04)
                elif is_bottom:
                    confidence = 0.34 + (n - 1 - idx) * 0.02
                else:
                    confidence = 0.40 + 0.06 * score_norm
            confidence = round(max(0.34, min(0.88, confidence)), 2)
            movie_info = self.movie_data.get(str(movie_id)) or self.movie_data.get(movie_id) or self.movie_data.get(int(movie_id)) or {}
            genres_list = movie_info.get("genres") or []
            if isinstance(genres_list, list) and genres_list and isinstance(genres_list[0], dict):
                genres = [g.get("name", "") for g in genres_list if isinstance(g, dict) and g.get("name")]
            else:
                genres = [str(g) for g in genres_list if g]
            directors = []
            for p in (movie_info.get("crew") or []):
                if isinstance(p, dict) and "director" in (p.get("job") or "").lower():
                    n_ = p.get("name") or p.get("Name")
                    if n_:
                        directors.append(n_)
            if not directors and movie_info.get("director"):
                directors = [movie_info["director"]] if isinstance(movie_info["director"], str) else list(movie_info.get("director") or [])
            rag_doc = rag_svc.get_document_for_movie(int(movie_id)) if rag_svc else None
            movie_context = {
                "title": (movie_info.get("title") or "").strip(),
                "overview": (movie_info.get("overview") or "")[:200],
                "genres": genres,
                "directors": directors,
                "rag_document": rag_doc or "",
            }
            explanation_items.append((movie_context, reason_bucket))
            recs.append({
                "movie_id": movie_id,
                "ensemble_score": float(score),
                "confidence": confidence,
                "guarantee": {"guarantee_level": "medium"},
                "explanation": None,
            })
        if recs and (n_liked >= 1 or n_reviewed >= 1):
            try:
                user_context = get_user_context_for_explanations(user_id, db_session, self.movie_data)
                why_results = generate_why_recommendations_batch(user_context, explanation_items)
                for i, expl in enumerate(why_results):
                    if i < len(recs) and expl:
                        recs[i]["explanation"] = expl
            except Exception as e:
                logger.warning("Dynamic explanation batch (CF-only) failed: %s", e)
        return recs

    def _release_year(self, movie: Dict) -> Optional[int]:
        """Extract release year from movie dict. Returns None if missing or invalid."""
        rd = movie.get("release_date") or movie.get("release_year")
        if not rd:
            return None
        s = str(rd)[:4]
        if len(s) == 4 and s.isdigit():
            return int(s)
        return None

    def _get_valid_movie_ids(self, min_year: Optional[int] = None) -> List[int]:
        """
        Extract valid movie IDs from movie_data.
        If min_year is set (e.g. 1980), only include movies with release year >= min_year.
        Handles both string and int keys.
        """
        valid_ids = set()
        for key in self.movie_data.keys():
            try:
                movie = self.movie_data.get(key)
                if movie and min_year is not None:
                    year = self._release_year(movie)
                    if year is None or year < min_year:
                        continue
                kid = key
                if isinstance(key, str) and key.isdigit():
                    kid = int(key)
                elif isinstance(key, str):
                    try:
                        kid = int(key)
                    except ValueError:
                        continue
                valid_ids.add(int(kid))
            except (ValueError, TypeError):
                continue
        return sorted(list(valid_ids))
    
    def _extract_director(self, movie: Dict) -> Optional[str]:
        """Extract director name from movie data"""
        crew_list = movie.get("crew", [])
        if isinstance(crew_list, list) and len(crew_list) > 0:
            for person in crew_list:
                if isinstance(person, dict):
                    job = person.get("job", "").lower()
                    if "director" in job:
                        name = person.get("name") or person.get("Name")
                        if name:
                            return name
        return movie.get("director")
    
    def _get_fallback_recommendations(
        self, user_id: int, n_recommendations: int, exclude_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """Fallback recommendations when model is not available. exclude_ids: skip these (e.g. last-shown)."""
        exclude_set = set()
        for x in exclude_ids or []:
            exclude_set.add(x)
            if isinstance(x, int):
                exclude_set.add(str(x))
            elif isinstance(x, str) and x.isdigit():
                exclude_set.add(int(x))
        if len(self.movie_data) == 0:
            logger.warning("Movie data is empty, attempting to load...")
            try:
                BASE_DIR = Path(__file__).parent.parent.parent
                movie_data_path = BASE_DIR / "data" / "raw" / "tmdb_movies_50k_20250711_011112.jsonl"
                if not movie_data_path.exists():
                    movie_data_path = BASE_DIR / "data" / "raw" / "tmdb_complete_dataset.jsonl"
                
                if movie_data_path.exists():
                    with open(movie_data_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                movie = json.loads(line.strip())
                                movie_id = movie.get('tmdb_id') or movie.get('id')
                                if movie_id:
                                    self.movie_data[str(movie_id)] = movie
                            except:
                                continue
                    logger.info(f"✅ Loaded {len(self.movie_data)} movies for fallback")
                else:
                    logger.error(f"Movie data file not found at {movie_data_path}")
            except Exception as e:
                logger.error(f"Failed to load movie data: {e}", exc_info=True)
        
        # If still no movies, return empty
        if len(self.movie_data) == 0:
            logger.error("No movie data available for fallback recommendations - check data files!")
            return []
        
        candidates = sorted(
            self.movie_data.items(),
            key=lambda x: (x[1].get("vote_average", 0) or 0) * ((x[1].get("vote_count", 0) or 1)),
            reverse=True,
        )
        out = []
        for movie_id, movie in candidates:
            if len(out) >= n_recommendations:
                break
            year = self._release_year(movie)
            if year is None or year < MAIN_REC_MIN_YEAR:
                continue
            mid = int(movie_id) if isinstance(movie_id, str) and movie_id.isdigit() else movie_id
            if mid in exclude_set:
                continue
            out.append({
                "movie_id": mid,
                "title": movie.get("title", f"Movie {movie_id}"),
                "predicted_rating": float(movie.get("vote_average", 7.0)),
                "confidence": 0.3,
                "poster_path": movie.get("poster_path"),
                "overview": (movie.get("overview") or "")[:200],
                "vote_average": movie.get("vote_average"),
                "director": self._extract_director(movie),
                "guarantee_level": "low",
                "explanation": "Popular movie (fallback recommendation)",
            })
        return out
    
    def update_user_preferences(self, user_id: int, movie_id: int, rating: float, action: str, review_text: Optional[str] = None):
        """Update user preferences and invalidate cache"""
        try:
            # Store user interaction
            interaction_key = f"user_interaction:{user_id}:{movie_id}"
            interaction_data = {
                "rating": rating,
                "action": action,  # like, dislike, favorite, review
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in cache
            self._set_cached(interaction_key, json.dumps(interaction_data), ttl=86400)  # 24 hours
            
            # Also store in in-memory dict for fast lookup
            if not self.use_redis:
                if user_id not in self._in_memory_interactions:
                    self._in_memory_interactions[user_id] = {}
                self._in_memory_interactions[user_id][movie_id] = interaction_data
            
            # Update model if available
            if self.engine:
                try:
                    self.engine.add_user_feedback(user_id, movie_id, rating)
                except Exception as e:
                    logger.warning(f"Failed to update model feedback: {e}")
            
            # Invalidate this user's recommendation cache so next request gets fresh recs
            self._invalidate_user_recommendations(user_id)
            logger.info(f"✅ Saved interaction for user {user_id}, movie {movie_id} (cache invalidated – fresh recs on next load)")
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}", exc_info=True)
    
    def get_user_interactions(self, user_id: int) -> List[Dict]:
        """Get recent user interactions"""
        try:
            interactions = []
            
            if self.use_redis and self.redis_client:
                # Get from Redis
                pattern = f"user_interaction:{user_id}:*"
                try:
                    keys = self.redis_client.keys(pattern)
                    for key in keys:
                        data = self.redis_client.get(key)
                        if data:
                            interaction = json.loads(data)
                            movie_id = key.split(":")[-1]
                            movie_info = self.movie_data.get(str(movie_id), {})
                            interaction["movie_id"] = int(movie_id)
                            interaction["movie_title"] = movie_info.get('title', f"Movie {movie_id}")
                            interactions.append(interaction)
                except Exception as e:
                    logger.warning(f"Redis keys failed: {e}")
            else:
                # Get from in-memory
                user_interactions = self._in_memory_interactions.get(user_id, {})
                for movie_id, interaction_data in user_interactions.items():
                    try:
                        movie_info = self.movie_data.get(str(movie_id), {})
                        interaction = interaction_data.copy()
                        # Safely convert movie_id to int
                        try:
                            interaction["movie_id"] = int(movie_id) if isinstance(movie_id, str) and movie_id.isdigit() else movie_id
                        except (ValueError, TypeError):
                            interaction["movie_id"] = movie_id
                        interaction["movie_title"] = movie_info.get('title', f"Movie {movie_id}")
                        interactions.append(interaction)
                    except Exception as e:
                        logger.warning(f"Error processing interaction for movie {movie_id}: {e}")
                        continue
            
            # Sort by timestamp
            interactions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return interactions
            
        except Exception as e:
            logger.error(f"Error getting user interactions: {e}", exc_info=True)
            return []

# Global model instance
model_service = None

def get_model_service() -> MovieRecommendationModel:
    """Get or create the global model service instance"""
    global model_service
    if model_service is None:
        try:
            # Check if Redis should be used (default: True, but falls back if unavailable)
            use_redis = os.getenv('USE_REDIS', 'true').lower() == 'true'
            logger.info("Initializing model service...")
            model_service = MovieRecommendationModel(use_redis=use_redis)
            logger.info(f"Model service initialized. Engine: {model_service.engine is not None}, Movies: {len(model_service.movie_data)}")
        except Exception as e:
            logger.error(f"Failed to initialize model service: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            raise
    return model_service 