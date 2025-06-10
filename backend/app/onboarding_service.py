import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

# Optional redis import
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)
if not REDIS_AVAILABLE:
    logger.debug("Redis not available; onboarding uses in-memory storage.")

class OnboardingService:
    def __init__(self):
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
        
        # Fallback to in-memory storage if Redis not available
        self._in_memory_storage = {}
    
    def _get_data(self, key: str) -> Optional[str]:
        """Get data from storage (Redis or in-memory)"""
        try:
            if self.redis_client:
                return self.redis_client.get(key)
            else:
                data = self._in_memory_storage.get(key)
                if data and isinstance(data, dict):
                    return json.dumps(data)
                return data
        except Exception as e:
            logger.error(f"Error getting data: {e}")
            return self._in_memory_storage.get(key)
    
    def _set_data(self, key: str, value: any, ttl: Optional[int] = None):
        """Set data in storage (Redis or in-memory)"""
        try:
            if self.redis_client:
                if isinstance(value, dict):
                    value = json.dumps(value)
                if ttl:
                    self.redis_client.setex(key, ttl, value)
                else:
                    self.redis_client.set(key, value)
            else:
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except:
                        pass
                self._in_memory_storage[key] = value
        except Exception as e:
            logger.error(f"Error setting data: {e}")
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except:
                    pass
            self._in_memory_storage[key] = value
    
    def _delete_data(self, key: str):
        """Delete data from storage"""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                self._in_memory_storage.pop(key, None)
        except Exception as e:
            logger.error(f"Error deleting data: {e}")
            self._in_memory_storage.pop(key, None)
        
        # Predefined genres and popular movies for onboarding
        self.genres = [
            "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
            "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
            "Romance", "Sci-Fi", "Thriller", "War", "Western"
        ]
        
        self.popular_movies = [
            {"id": 1, "title": "The Shawshank Redemption", "genre": "Drama"},
            {"id": 2, "title": "The Godfather", "genre": "Crime"},
            {"id": 3, "title": "The Dark Knight", "genre": "Action"},
            {"id": 4, "title": "Pulp Fiction", "genre": "Crime"},
            {"id": 5, "title": "Fight Club", "genre": "Drama"},
            {"id": 6, "title": "Inception", "genre": "Sci-Fi"},
            {"id": 7, "title": "The Matrix", "genre": "Sci-Fi"},
            {"id": 8, "title": "Goodfellas", "genre": "Crime"},
            {"id": 9, "title": "The Silence of the Lambs", "genre": "Thriller"},
            {"id": 10, "title": "Interstellar", "genre": "Sci-Fi"},
            {"id": 11, "title": "The Departed", "genre": "Crime"},
            {"id": 12, "title": "Gladiator", "genre": "Action"},
            {"id": 13, "title": "The Prestige", "genre": "Drama"},
            {"id": 14, "title": "The Lion King", "genre": "Animation"},
            {"id": 15, "title": "Titanic", "genre": "Romance"}
        ]
    
    def start_onboarding(self, user_id: int) -> Dict:
        """Start the onboarding process for a new user"""
        try:
            onboarding_data = {
                "user_id": user_id,
                "stage": 1,
                "started_at": datetime.now().isoformat(),
                "completed": False,
                "preferences": {
                    "genres": [],
                    "favorite_movies": [],
                    "mood_preferences": [],
                    "time_preferences": []
                }
            }
            
            # Store onboarding data
            key = f"onboarding:{user_id}"
            self._set_data(key, onboarding_data, 86400)  # 24 hours
            
            return {
                "stage": 1,
                "message": "Welcome to cine.ai! Let's personalize your experience.",
                "data": self._get_stage_data(1)
            }
            
        except Exception as e:
            logger.error(f"Error starting onboarding: {e}")
            return {"error": "Failed to start onboarding"}
    
    def _get_stage_data(self, stage: int) -> Dict:
        """Get data for specific onboarding stage"""
        if stage == 1:
            return {
                "type": "genre_selection",
                "title": "What genres do you enjoy?",
                "subtitle": "Select all that apply",
                "options": self.genres,
                "max_selections": 5
            }
        elif stage == 2:
            return {
                "type": "movie_selection",
                "title": "What are your favorite movies?",
                "subtitle": "Search and select movies you love",
                "movies": self.popular_movies,
                "max_selections": 3
            }
        elif stage == 3:
            return {
                "type": "mood_preferences",
                "title": "When do you watch movies?",
                "subtitle": "Help us understand your viewing patterns",
                "options": [
                    {"id": "weekend", "label": "Weekends", "icon": "🌅"},
                    {"id": "weekday", "label": "Weekdays", "icon": "💼"},
                    {"id": "evening", "label": "Evenings", "icon": "🌙"},
                    {"id": "afternoon", "label": "Afternoons", "icon": "☀️"},
                    {"id": "late_night", "label": "Late Night", "icon": "🌃"}
                ],
                "max_selections": 3
            }
        else:
            return {"type": "completion", "title": "You're all set!"}
    
    def update_onboarding(self, user_id: int, stage: int, selections: List) -> Dict:
        """Update onboarding progress for a user"""
        try:
            key = f"onboarding:{user_id}"
            data = self._get_data(key)
            
            if not data:
                return {"error": "Onboarding session not found"}
            
            onboarding_data = json.loads(data) if isinstance(data, str) else data
            
            # Update based on stage
            if stage == 1:
                onboarding_data["preferences"]["genres"] = selections
            elif stage == 2:
                onboarding_data["preferences"]["favorite_movies"] = selections
            elif stage == 3:
                onboarding_data["preferences"]["mood_preferences"] = selections
            
            # Move to next stage or complete
            if stage < 3:
                onboarding_data["stage"] = stage + 1
                next_stage_data = self._get_stage_data(stage + 1)
            else:
                onboarding_data["stage"] = 4
                onboarding_data["completed"] = True
                onboarding_data["completed_at"] = datetime.now().isoformat()
                next_stage_data = self._get_stage_data(4)
            
            # Update storage
            self._set_data(key, onboarding_data, 86400)
            
            # If completed, generate initial recommendations
            if onboarding_data["completed"]:
                self._generate_initial_recommendations(user_id, onboarding_data["preferences"])
            
            return {
                "stage": onboarding_data["stage"],
                "completed": onboarding_data["completed"],
                "data": next_stage_data
            }
            
        except Exception as e:
            logger.error(f"Error updating onboarding: {e}")
            return {"error": "Failed to update onboarding"}
    
    def _generate_initial_recommendations(self, user_id: int, preferences: Dict):
        """Generate initial recommendations based on onboarding preferences"""
        try:
            # This would integrate with your model service
            # For now, we'll create a simple recommendation based on genres
            genre_movies = {
                "Action": [2, 12],  # The Godfather, Gladiator
                "Sci-Fi": [6, 7, 10],  # Inception, The Matrix, Interstellar
                "Drama": [1, 5, 13],  # Shawshank, Fight Club, The Prestige
                "Crime": [2, 4, 8, 11],  # Godfather, Pulp Fiction, Goodfellas, The Departed
                "Thriller": [9],  # Silence of the Lambs
                "Animation": [14],  # The Lion King
                "Romance": [15]  # Titanic
            }
            
            recommended_movies = []
            for genre in preferences.get("genres", []):
                if genre in genre_movies:
                    recommended_movies.extend(genre_movies[genre])
            
            # Remove duplicates and limit to 10
            recommended_movies = list(set(recommended_movies))[:10]
            
            # Store initial recommendations
            initial_recs = {
                "user_id": user_id,
                "movies": recommended_movies,
                "generated_at": datetime.now().isoformat(),
                "source": "onboarding"
            }
            
            rec_key = f"initial_recommendations:{user_id}"
            self._set_data(rec_key, initial_recs, 3600)  # 1 hour
            
            logger.info(f"Generated initial recommendations for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error generating initial recommendations: {e}")
    
    def get_onboarding_status(self, user_id: int) -> Dict:
        """Get current onboarding status for a user"""
        try:
            key = f"onboarding:{user_id}"
            data = self._get_data(key)
            
            if not data:
                return {"completed": True, "stage": None}  # User has completed onboarding
            
            onboarding_data = json.loads(data) if isinstance(data, str) else data
            return {
                "completed": onboarding_data.get("completed", False),
                "stage": onboarding_data.get("stage", None),
                "started_at": onboarding_data.get("started_at", None)
            }
            
        except Exception as e:
            logger.error(f"Error getting onboarding status: {e}")
            return {"error": "Failed to get onboarding status"}
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """Get user preferences from onboarding"""
        try:
            key = f"onboarding:{user_id}"
            data = self._get_data(key)
            
            if not data:
                return {}
            
            onboarding_data = json.loads(data) if isinstance(data, str) else data
            return onboarding_data.get("preferences", {})
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}

# Global onboarding service instance
onboarding_service = OnboardingService() 