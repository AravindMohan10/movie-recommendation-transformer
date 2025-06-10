"""
Ensemble Recommendation System
Combines content-based, collaborative filtering, and contextual models with confidence-based weighting.
"""

import torch
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import json
import logging

from .content_transformer import ContentBasedRecommender
from .collaborative_filtering import CollaborativeFilteringRecommender
from .context_transformer import ContextualRecommender

logger = logging.getLogger(__name__)


class ConfidenceEnsembleRecommender:
    """
    Ensemble recommendation system with confidence-based weighting.
    Combines three models: content-based, collaborative filtering, and contextual.
    """
    
    def __init__(
        self,
        content_recommender: ContentBasedRecommender,
        collaborative_recommender: CollaborativeFilteringRecommender,
        contextual_recommender: ContextualRecommender,
        confidence_thresholds: Dict[str, float] = None
    ):
        self.content_recommender = content_recommender
        self.collaborative_recommender = collaborative_recommender
        self.contextual_recommender = contextual_recommender
        
        # Default confidence thresholds
        self.confidence_thresholds = confidence_thresholds or {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
        
        # Model weights (can be learned)
        self.model_weights = {
            'content': 0.4,
            'collaborative': 0.4,
            'contextual': 0.2
        }
        
        # User interaction history
        self.user_interactions = defaultdict(list)
        
    def compute_confidence_score(
        self,
        user_id: int,
        movie_id: int,
        model_type: str
    ) -> float:
        """
        Compute confidence score for a model's recommendation.
        
        Args:
            user_id: User ID
            movie_id: Movie ID
            model_type: Type of model ('content', 'collaborative', 'contextual')
        
        Returns:
            Confidence score between 0 and 1
        """
        if model_type == 'content':
            return self._compute_content_confidence(user_id, movie_id)
        elif model_type == 'collaborative':
            return self._compute_collaborative_confidence(user_id, movie_id)
        elif model_type == 'contextual':
            return self._compute_contextual_confidence(user_id, movie_id)
        else:
            return 0.5  # Default confidence
    
    def _compute_content_confidence(self, user_id: int, movie_id: int) -> float:
        """Compute confidence for content-based recommendations."""
        try:
            # Get user's watched movies
            user_watched = [interaction['movie_id'] for interaction in self.user_interactions[user_id]]
            
            if not user_watched:
                return 0.3  # Low confidence if no history
            
            # Find most similar watched movie
            similarities = []
            for watched_id in user_watched[:10]:  # Check last 10 watched
                try:
                    similarity = self.content_recommender.model.compute_similarity(
                        self.content_recommender.movie_data[watched_id],
                        self.content_recommender.movie_data[movie_id]
                    )
                    similarities.append(similarity)
                except:
                    continue
            
            if not similarities:
                return 0.3
            
            # Confidence based on average similarity
            avg_similarity = np.mean(similarities)
            return min(1.0, max(0.1, avg_similarity))
            
        except Exception:
            return 0.3
    
    def _compute_collaborative_confidence(self, user_id: int, movie_id: int) -> float:
        """Compute confidence for collaborative filtering recommendations."""
        try:
            # Check if user has enough interactions
            user_interactions = len(self.user_interactions[user_id])
            
            if user_interactions < 5:
                return 0.2  # Very low confidence for new users
            elif user_interactions < 20:
                return 0.5  # Medium confidence for moderate users
            else:
                return 0.8  # High confidence for active users
                
        except Exception:
            return 0.3
    
    def _compute_contextual_confidence(self, user_id: int, movie_id: int) -> float:
        """Compute confidence for contextual recommendations."""
        try:
            # Check if user has reviews
            if user_id not in self.contextual_recommender.user_reviews:
                return 0.1  # No reviews, very low confidence
            
            user_reviews = self.contextual_recommender.user_reviews[user_id]
            
            if len(user_reviews) < 3:
                return 0.3  # Few reviews, low confidence
            elif len(user_reviews) < 10:
                return 0.6  # Moderate reviews, medium confidence
            else:
                return 0.8  # Many reviews, high confidence
                
        except Exception:
            return 0.2
    
    def recommend(
        self,
        user_id: int,
        top_k: int = 10,
        exclude_watched: Optional[List[int]] = None,
        include_explanations: bool = True,
        valid_movie_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate ensemble recommendations with confidence scores.
        
        Args:
            user_id: User ID
            top_k: Number of recommendations
            exclude_watched: List of movie IDs to exclude
            include_explanations: Whether to include explanations
            valid_movie_ids: Optional list of valid movie IDs to constrain recommendations
        
        Returns:
            List of recommendation dicts with scores and explanations
        """
        # Get recommendations from each model, passing valid_movie_ids
        content_recs = self._get_content_recommendations(user_id, top_k * 2, exclude_watched, valid_movie_ids)
        collaborative_recs = self._get_collaborative_recommendations(user_id, top_k * 2, exclude_watched, valid_movie_ids)
        contextual_recs = self._get_contextual_recommendations(user_id, top_k * 2, exclude_watched, valid_movie_ids)
        
        # Diagnostic logging: Track model contributions
        logger.info(f"📊 Model Recommendations Breakdown (user_id={user_id}):")
        logger.info(f"   Content Model: {len(content_recs)} recommendations")
        logger.info(f"   Collaborative Model: {len(collaborative_recs)} recommendations")
        logger.info(f"   Contextual Model: {len(contextual_recs)} recommendations")
        
        if len(content_recs) == 0:
            logger.warning("⚠️  Content model returned 0 recommendations - may need user watch history")
        if len(collaborative_recs) == 0:
            logger.warning("⚠️  Collaborative model returned 0 recommendations - may need user in training data")
        if len(contextual_recs) == 0:
            logger.warning("⚠️  Contextual model returned 0 recommendations - may need user reviews/preferences")
        
        # Combine and score recommendations
        all_recommendations = self._combine_recommendations(
            content_recs, collaborative_recs, contextual_recs
        )
        
        # Filter to only valid movies if valid_movie_ids provided
        if valid_movie_ids is not None:
            valid_set = set(valid_movie_ids)
            before_filter = len(all_recommendations)
            all_recommendations = [r for r in all_recommendations if r['movie_id'] in valid_set]
            if before_filter != len(all_recommendations):
                logger.info(f"   Filtered {before_filter - len(all_recommendations)} invalid recommendations")
        
        # Sort by ensemble score
        all_recommendations.sort(key=lambda x: x['ensemble_score'], reverse=True)
        
        # Diagnostic logging: Analyze final recommendations
        if all_recommendations:
            top_recs = all_recommendations[:top_k]
            content_only = sum(1 for r in top_recs if r['content_score'] > 0 and r['collaborative_score'] == 0 and r['contextual_score'] == 0)
            collaborative_only = sum(1 for r in top_recs if r['collaborative_score'] > 0 and r['content_score'] == 0 and r['contextual_score'] == 0)
            contextual_only = sum(1 for r in top_recs if r['contextual_score'] > 0 and r['content_score'] == 0 and r['collaborative_score'] == 0)
            content_collab = sum(1 for r in top_recs if r['content_score'] > 0 and r['collaborative_score'] > 0)
            all_three = sum(1 for r in top_recs if r['content_score'] > 0 and r['collaborative_score'] > 0 and r['contextual_score'] > 0)
            
            logger.info(f"🎯 Final Top-{len(top_recs)} Recommendations Source:")
            logger.info(f"   Content-only: {content_only}")
            logger.info(f"   Collaborative-only: {collaborative_only}")
            logger.info(f"   Contextual-only: {contextual_only}")
            logger.info(f"   Content + Collaborative: {content_collab}")
            logger.info(f"   All three models: {all_three}")
            
            # Show contribution percentages
            total_content_contrib = sum(r['content_score'] * 0.4 * r.get('content_confidence', 0.7) for r in top_recs)
            total_collab_contrib = sum(r['collaborative_score'] * 0.4 * r.get('collaborative_confidence', 0.8) for r in top_recs)
            total_contextual_contrib = sum(r['contextual_score'] * 0.2 * r.get('contextual_confidence', 0.6) for r in top_recs)
            total_ensemble = sum(r['ensemble_score'] for r in top_recs)
            
            if total_ensemble > 0:
                content_pct = (total_content_contrib / total_ensemble) * 100
                collab_pct = (total_collab_contrib / total_ensemble) * 100
                contextual_pct = (total_contextual_contrib / total_ensemble) * 100
                
                logger.info(f"📈 Weighted Contribution in Final Scores:")
                logger.info(f"   Content: {content_pct:.1f}% (target: 40%)")
                logger.info(f"   Collaborative: {collab_pct:.1f}% (target: 40%)")
                logger.info(f"   Contextual: {contextual_pct:.1f}% (target: 20%)")
        
        # Add explanations if requested
        if include_explanations:
            for rec in all_recommendations[:top_k]:
                rec['explanation'] = self._generate_explanation(user_id, rec)
        
        return all_recommendations[:top_k]
    
    def _get_content_recommendations(
        self,
        user_id: int,
        top_k: int,
        exclude_watched: Optional[List[int]],
        valid_movie_ids: Optional[List[int]] = None
    ) -> List[Tuple[int, float]]:
        """Get content-based recommendations."""
        logger.info(f"🎯 _get_content_recommendations called for user {user_id}")
        try:
            # Use user's most recent watched movie as reference
            user_interactions_list = self.user_interactions.get(user_id, [])
            logger.info(f"   Found {len(user_interactions_list)} interactions for user {user_id}")
            user_watched = [interaction['movie_id'] for interaction in user_interactions_list]
            logger.info(f"   Extracted {len(user_watched)} movie IDs")
            
            if not user_watched:
                logger.warning(f"⚠️ Content model: User {user_id} has no watch history in model state (found {len(user_interactions_list)} interactions), returning empty")
                logger.debug(f"   User interactions keys: {list(self.user_interactions.keys())}")
                if user_interactions_list:
                    logger.debug(f"   Sample interaction format: {user_interactions_list[0]}")
                return []
            
            # Filter to only movies that exist in content model's embeddings
            # This prevents errors when user interacted with movies not in content model
            available_movies = set(self.content_recommender.movie_embeddings.keys())
            
            # Try both int and string conversions for robust matching
            available_movies_int = {int(mid) if isinstance(mid, (int, str)) and str(mid).isdigit() else mid for mid in available_movies}
            available_movies_str = {str(mid) for mid in available_movies}
            
            valid_watched = []
            for mid in user_watched:
                # Try multiple matching strategies
                if mid in available_movies or mid in available_movies_int or str(mid) in available_movies_str:
                    valid_watched.append(mid)
            
            logger.info(f"🔍 Content model: Found {len(valid_watched)}/{len(user_watched)} valid movies in content embeddings")
            
            if not valid_watched:
                logger.warning(f"⚠️ Content model: User {user_id} has {len(user_watched)} interactions, but none exist in content model embeddings")
                logger.warning(f"   Sample watched IDs (first 5): {user_watched[:5]}")
                logger.warning(f"   Sample watched IDs (types): {[type(mid).__name__ for mid in user_watched[:5]]}")
                logger.warning(f"   Content model has {len(available_movies)} movies")
                logger.warning(f"   Sample available IDs (first 5): {list(available_movies)[:5]}")
                logger.warning(f"   Sample available IDs (types): {[type(mid).__name__ for mid in list(available_movies)[:5]]}")
                
                # Try to see if there's overlap with different type conversion
                watched_as_ints = [int(mid) if isinstance(mid, (int, str)) and str(mid).isdigit() else mid for mid in user_watched[:5]]
                logger.warning(f"   Watched IDs as ints (first 5): {watched_as_ints}")
                return []
            
            # Use most recent watched movie that exists in content model
            reference_movie_original = valid_watched[-1]
            if len(valid_watched) < len(user_watched):
                skipped = len(user_watched) - len(valid_watched)
                logger.debug(f"Content model: Using movie {reference_movie_original} as reference (skipped {skipped} movies not in content model)")
            
            # Normalize reference_movie to match exact key format in movie_embeddings
            # Find the actual key that matches this movie ID
            reference_movie = None
            for key in self.content_recommender.movie_embeddings.keys():
                # Try all matching strategies
                if (key == reference_movie_original or 
                    str(key) == str(reference_movie_original) or
                    (isinstance(key, int) and isinstance(reference_movie_original, (int, str)) and key == int(reference_movie_original)) or
                    (isinstance(key, str) and isinstance(reference_movie_original, int) and key == str(reference_movie_original))):
                    reference_movie = key
                    break
            
            if reference_movie is None:
                logger.error(f"Content model: Could not find matching key for movie {reference_movie_original} in embeddings")
                return []
            
            logger.info(f"🎬 Content model: Using reference movie {reference_movie} (original: {reference_movie_original})")
            recs = self.content_recommender.recommend_similar(
                reference_movie, top_k * 2, exclude_watched  # Request more to filter later
            )
            logger.info(f"📊 Content model: Got {len(recs)} raw recommendations from recommend_similar")
            
            # Capture sample IDs BEFORE filtering for debugging
            sample_rec_ids_before = [mid for mid, _ in recs[:5]] if recs else []
            
            # Filter to valid movies if provided
            # valid_movie_ids are always ints from _get_valid_movie_ids
            # Content model returns IDs from movie_embeddings.keys() which could be int or str
            if valid_movie_ids is not None:
                # CRITICAL DEBUG: Log what we're working with
                print(f"🔴 CONTENT FILTER DEBUG: Got {len(recs)} recs, {len(valid_movie_ids)} valid IDs")
                if recs:
                    print(f"🔴 First rec ID: {recs[0][0]}, type: {type(recs[0][0])}, in valid_set: {recs[0][0] in set(valid_movie_ids)}")
                    print(f"🔴 First rec ID as int: {int(recs[0][0]) if isinstance(recs[0][0], (int, str)) and str(recs[0][0]).isdigit() else 'N/A'}")
                    print(f"🔴 Sample valid IDs: {valid_movie_ids[:5]}")
                # Build comprehensive valid set - convert everything to int for comparison
                valid_set_int = set(valid_movie_ids)  # Already ints
                valid_set_str = {str(mid) for mid in valid_movie_ids}
                
                before_valid = len(recs)
                
                # Use flexible matching that handles type mismatches
                filtered_recs = []
                for mid, score in recs:
                    # Convert recommendation ID to int for comparison
                    mid_int = None
                    try:
                        # Handle int, str, float, numpy types
                        if isinstance(mid, (int, float)):
                            mid_int = int(mid)
                        elif isinstance(mid, str):
                            if mid.isdigit():
                                mid_int = int(mid)
                            else:
                                try:
                                    mid_int = int(float(mid))
                                except:
                                    pass
                        else:
                            # numpy types, etc.
                            mid_int = int(mid)
                    except (ValueError, TypeError, OverflowError):
                        pass
                    
                    # Check if ID matches (try int first, then string)
                    if mid_int and mid_int in valid_set_int:
                        filtered_recs.append((mid, score))
                    elif str(mid) in valid_set_str:
                        filtered_recs.append((mid, score))
                    elif mid in valid_set_int:  # Direct match
                        filtered_recs.append((mid, score))
                
                recs = filtered_recs
                if before_valid != len(recs):
                    logger.info(f"🔍 Content model: Filtered {before_valid - len(recs)} invalid movie IDs (kept {len(recs)})")
                    if len(recs) == 0 and before_valid > 0:
                        logger.warning(f"⚠️ Content model: ALL {before_valid} recommendations filtered!")
                        logger.warning(f"   Sample rec IDs (before filter): {sample_rec_ids_before[:5]}")
                        logger.warning(f"   Sample rec ID types: {[type(mid).__name__ for mid in sample_rec_ids_before[:5]]}")
                        logger.warning(f"   Valid set size: {len(valid_set_int)}, Sample valid IDs: {list(valid_set_int)[:5]}")
            
            result = recs[:top_k]
            logger.info(f"✅ Content model: Returning {len(result)} recommendations (ref movie: {reference_movie}, valid_watched: {len(valid_watched)}/{len(user_watched)})")
            return result
        except Exception as e:
            logger.warning(f"Content model failed: {e}", exc_info=True)
            return []
    
    def _get_collaborative_recommendations(
        self,
        user_id: int,
        top_k: int,
        exclude_watched: Optional[List[int]],
        valid_movie_ids: Optional[List[int]] = None
    ) -> List[Tuple[int, float]]:
        """Get collaborative filtering recommendations."""
        try:
            result = self.collaborative_recommender.recommend_for_user(
                user_id, top_k, exclude_watched, candidate_movies=valid_movie_ids
            )
            logger.debug(f"Collaborative model: Returning {len(result)} recommendations for user {user_id}")
            return result
        except Exception as e:
            logger.warning(f"Collaborative model failed: {e}", exc_info=True)
            return []
    
    def _get_contextual_recommendations(
        self,
        user_id: int,
        top_k: int,
        exclude_watched: Optional[List[int]],
        valid_movie_ids: Optional[List[int]] = None
    ) -> List[Tuple[int, float]]:
        """Get contextual recommendations."""
        try:
            # Check if user has preferences
            if user_id not in self.contextual_recommender.user_preferences:
                logger.debug(f"Contextual model: User {user_id} has no preferences, returning empty")
                return []
            
            # Get all available movie IDs
            all_movies = list(self.content_recommender.movie_embeddings.keys())
            
            # Filter to valid movies if provided
            if valid_movie_ids is not None:
                valid_set = set(valid_movie_ids)
                all_movies = [m for m in all_movies if m in valid_set]
            
            candidate_movies = [m for m in all_movies if m not in (exclude_watched or [])]
            
            result = self.contextual_recommender.recommend_based_on_context(
                user_id, candidate_movies, top_k
            )
            logger.debug(f"Contextual model: Returning {len(result)} recommendations for user {user_id} (from {len(candidate_movies)} candidates)")
            return result
        except Exception as e:
            logger.warning(f"Contextual model failed: {e}", exc_info=True)
            return []
    
    def _combine_recommendations(
        self,
        content_recs: List[Tuple[int, float]],
        collaborative_recs: List[Tuple[int, float]],
        contextual_recs: List[Tuple[int, float]]
    ) -> List[Dict[str, Any]]:
        """Combine recommendations from all models."""
        movie_scores = defaultdict(lambda: {
            'content_score': 0.0,
            'collaborative_score': 0.0,
            'contextual_score': 0.0,
            'content_confidence': 0.0,
            'collaborative_confidence': 0.0,
            'contextual_confidence': 0.0
        })
        
        # Process content recommendations
        for movie_id, score in content_recs:
            movie_scores[movie_id]['content_score'] = score
            movie_scores[movie_id]['content_confidence'] = 0.7  # Default confidence
        
        # Process collaborative recommendations
        for movie_id, score in collaborative_recs:
            movie_scores[movie_id]['collaborative_score'] = score
            movie_scores[movie_id]['collaborative_confidence'] = 0.8  # Default confidence
        
        # Process contextual recommendations
        for movie_id, score in contextual_recs:
            movie_scores[movie_id]['contextual_score'] = score
            movie_scores[movie_id]['contextual_confidence'] = 0.6  # Default confidence
        
        # Compute ensemble scores
        recommendations = []
        for movie_id, scores in movie_scores.items():
            # Weighted ensemble score
            ensemble_score = (
                scores['content_score'] * self.model_weights['content'] * scores['content_confidence'] +
                scores['collaborative_score'] * self.model_weights['collaborative'] * scores['collaborative_confidence'] +
                scores['contextual_score'] * self.model_weights['contextual'] * scores['contextual_confidence']
            )
            
            # Overall confidence
            overall_confidence = (
                scores['content_confidence'] * self.model_weights['content'] +
                scores['collaborative_confidence'] * self.model_weights['collaborative'] +
                scores['contextual_confidence'] * self.model_weights['contextual']
            )
            
            recommendations.append({
                'movie_id': movie_id,
                'ensemble_score': ensemble_score,
                'confidence': overall_confidence,
                'content_score': scores['content_score'],
                'collaborative_score': scores['collaborative_score'],
                'contextual_score': scores['contextual_score'],
                'content_confidence': scores['content_confidence'],
                'collaborative_confidence': scores['collaborative_confidence'],
                'contextual_confidence': scores['contextual_confidence']
            })
        
        return recommendations
    
    def _generate_explanation(self, user_id: int, recommendation: Dict) -> str:
        """Generate explanation for a recommendation."""
        movie_id = recommendation['movie_id']
        confidence = recommendation['confidence']
        
        explanations = []
        
        # Content-based explanation
        if recommendation['content_confidence'] > 0.5:
            explanations.append("This movie is similar to films you've enjoyed")
        
        # Collaborative explanation
        if recommendation['collaborative_confidence'] > 0.5:
            explanations.append("Users with similar tastes loved this movie")
        
        # Contextual explanation
        if recommendation['contextual_confidence'] > 0.5:
            contextual_explanation = self.contextual_recommender.get_contextual_explanation(
                user_id, movie_id
            )
            explanations.append(contextual_explanation)
        
        # Confidence level explanation
        if confidence > self.confidence_thresholds['high']:
            confidence_text = "We're very confident you'll love this"
        elif confidence > self.confidence_thresholds['medium']:
            confidence_text = "We think you'll enjoy this movie"
        else:
            confidence_text = "This might be worth checking out"
        
        if explanations:
            return f"{confidence_text}. {' '.join(explanations)}."
        else:
            return confidence_text
    
    def add_user_interaction(
        self,
        user_id: int,
        movie_id: int,
        rating: float,
        review: Optional[str] = None
    ):
        """
        Add a user interaction (rating, review) to update the models.
        
        Args:
            user_id: User ID
            movie_id: Movie ID
            rating: User rating (1-10)
            review: Optional review text
        """
        # Add to interaction history
        interaction = {
            'movie_id': movie_id,
            'rating': rating,
            'review': review,
            'timestamp': np.datetime64('now')
        }
        self.user_interactions[user_id].append(interaction)
        
        # Update collaborative filtering model
        try:
            # This would require retraining or online updates
            pass
        except Exception:
            pass
        
        # Update contextual model if review provided
        if review:
            try:
                review_data = {
                    'content': review,
                    'rating': rating,
                    'movie_id': movie_id
                }
                self.contextual_recommender.add_user_reviews(user_id, [review_data])
            except Exception:
                pass
        
        print(f"Added interaction: User {user_id} rated movie {movie_id} with {rating}/10")
    
    def get_recommendation_guarantee(
        self,
        user_id: int,
        movie_id: int
    ) -> Dict[str, Any]:
        """
        Get guarantee information for a specific recommendation.
        
        Args:
            user_id: User ID
            movie_id: Movie ID
        
        Returns:
            Dictionary with guarantee information
        """
        confidence = self.compute_confidence_score(user_id, movie_id, 'ensemble')
        
        guarantee_info = {
            'confidence': confidence,
            'guarantee_level': 'none',
            'refund_policy': 'none',
            'explanation': ''
        }
        
        if confidence > self.confidence_thresholds['high']:
            guarantee_info.update({
                'guarantee_level': 'high',
                'refund_policy': 'full_refund_if_not_satisfied',
                'explanation': 'We guarantee you will love this movie based on your preferences'
            })
        elif confidence > self.confidence_thresholds['medium']:
            guarantee_info.update({
                'guarantee_level': 'medium',
                'refund_policy': 'partial_refund',
                'explanation': 'We are confident you will enjoy this movie'
            })
        elif confidence > self.confidence_thresholds['low']:
            guarantee_info.update({
                'guarantee_level': 'low',
                'refund_policy': 'no_refund',
                'explanation': 'This movie might interest you based on similar users'
            })
        
        return guarantee_info
    
    def save_ensemble(self, filepath: str):
        """Save ensemble model state."""
        state = {
            'model_weights': self.model_weights,
            'confidence_thresholds': self.confidence_thresholds,
            'user_interactions': dict(self.user_interactions)
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        print(f"Saved ensemble state to {filepath}")
    
    def load_ensemble(self, filepath: str):
        """Load ensemble model state."""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.model_weights = state['model_weights']
        self.confidence_thresholds = state['confidence_thresholds']
        self.user_interactions = defaultdict(list, state['user_interactions'])
        
        print(f"Loaded ensemble state from {filepath}")


class MovieRecommendationEngine:
    """
    Main recommendation engine that orchestrates all components.
    """
    
    def __init__(
        self,
        content_recommender: ContentBasedRecommender,
        collaborative_recommender: CollaborativeFilteringRecommender,
        contextual_recommender: ContextualRecommender
    ):
        self.ensemble = ConfidenceEnsembleRecommender(
            content_recommender,
            collaborative_recommender,
            contextual_recommender
        )
        
        self.content_recommender = content_recommender
        self.collaborative_recommender = collaborative_recommender
        self.contextual_recommender = contextual_recommender
    
    def initialize_from_data(self, movies: List[Dict], interactions: List[Dict]):
        """
        Initialize the recommendation engine with movie data and interactions.
        
        Args:
            movies: List of movie dictionaries
            interactions: List of interaction dictionaries
        """
        print("Initializing recommendation engine...")
        
        # Initialize content-based model
        self.content_recommender.add_movies(movies)
        
        # Initialize collaborative filtering model
        user_ids = list(set(interaction['user_id'] for interaction in interactions))
        movie_ids = list(set(interaction['movie_id'] for interaction in interactions))
        
        self.collaborative_recommender.build_interaction_matrix(
            interactions, user_ids, movie_ids
        )
        
        # Initialize contextual model with movie reviews
        for movie in movies:
            if movie.get('reviews'):
                self.contextual_recommender.add_movie_context(
                    movie['tmdb_id'], movie['reviews']
                )
        
        print("Recommendation engine initialized successfully!")
    
    def get_recommendations(
        self,
        user_id: int,
        top_k: int = 10,
        include_guarantees: bool = True,
        valid_movie_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations for a user.
        
        Args:
            user_id: User ID
            top_k: Number of recommendations
            include_guarantees: Whether to include guarantee information
            valid_movie_ids: Optional list of valid movie IDs to constrain recommendations
        
        Returns:
            List of recommendation dictionaries
        """
        recommendations = self.ensemble.recommend(
            user_id=user_id,
            top_k=top_k,
            include_explanations=True,
            valid_movie_ids=valid_movie_ids
        )
        
        if include_guarantees:
            for rec in recommendations:
                guarantee_info = self.ensemble.get_recommendation_guarantee(
                    user_id, rec['movie_id']
                )
                rec['guarantee'] = guarantee_info
        
        return recommendations
    
    def add_user_feedback(
        self,
        user_id: int,
        movie_id: int,
        rating: float,
        review: Optional[str] = None
    ):
        """
        Add user feedback to improve recommendations.
        
        Args:
            user_id: User ID
            movie_id: Movie ID
            rating: User rating (1-10)
            review: Optional review text
        """
        self.ensemble.add_user_interaction(user_id, movie_id, rating, review)
    
    def save_engine(self, base_path: str):
        """Save the entire recommendation engine."""
        # Save ensemble
        self.ensemble.save_ensemble(f"{base_path}_ensemble.json")
        
        # Save individual models
        self.content_recommender.save_embeddings(f"{base_path}_content_embeddings.npz")
        self.collaborative_recommender.save_model(f"{base_path}_collaborative.pt")
        self.contextual_recommender.save_contexts(f"{base_path}_contexts.npz")
        
        print(f"Saved recommendation engine to {base_path}")
    
    def load_engine(self, base_path: str, movies: List[Dict]):
        """Load the entire recommendation engine."""
        # Load ensemble
        self.ensemble.load_ensemble(f"{base_path}_ensemble.json")
        
        # Load individual models
        self.content_recommender.load_embeddings(f"{base_path}_content_embeddings.npz", movies)
        self.collaborative_recommender.load_model(f"{base_path}_collaborative.pt")
        self.contextual_recommender.load_contexts(f"{base_path}_contexts.npz")
        
        print(f"Loaded recommendation engine from {base_path}") 