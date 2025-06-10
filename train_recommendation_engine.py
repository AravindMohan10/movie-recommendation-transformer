#!/usr/bin/env python3
"""
Training Script for Movie Recommendation Engine
Designed for Google Colab with A100 GPU support.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import logging

# Add project root to path (for Colab compatibility)
# This allows imports to work whether running locally or in Colab
import os
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import torch
import numpy as np

# Import our models
from models.content_transformer import MovieContentTransformer, ContentBasedRecommender
from models.collaborative_filtering import MatrixFactorization, CollaborativeFilteringRecommender
from models.context_transformer import ReviewContextTransformer, ContextualRecommender
from models.ensemble_recommender import MovieRecommendationEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_movie_data(jsonl_path: str) -> List[Dict]:
    """
    Load movie data from JSONL file.
    
    Args:
        jsonl_path: Path to JSONL file
    
    Returns:
        List of movie dictionaries
    """
    movies = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            movies.append(json.loads(line))
    
    logger.info(f"Loaded {len(movies)} movies from {jsonl_path}")
    return movies


def load_realistic_synthetic_interactions(csv_path: str) -> List[Dict]:
    """
    Load realistic synthetic user-movie interactions from CSV.
    
    Args:
        csv_path: Path to CSV file with columns: user_id, movie_id, rating, timestamp
    
    Returns:
        List of interaction dictionaries
    """
    import pandas as pd
    
    logger.info(f"Loading realistic synthetic interactions from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    interactions = []
    for _, row in df.iterrows():
        interaction = {
            'user_id': int(row['user_id']),
            'movie_id': int(row['movie_id']),
            'rating': float(row['rating']),
            'timestamp': str(row.get('timestamp', '2024-01-01T00:00:00Z'))
        }
        interactions.append(interaction)
    
    logger.info(f"Loaded {len(interactions)} realistic interactions")
    logger.info(f"  Users: {df['user_id'].nunique()}")
    logger.info(f"  Movies: {df['movie_id'].nunique()}")
    logger.info(f"  Average rating: {df['rating'].mean():.2f}")
    
    return interactions


def train_content_model(movies: List[Dict], device: str = 'cuda') -> ContentBasedRecommender:
    """
    Train the content-based transformer model.
    
    Args:
        movies: List of movie dictionaries
        device: Device to train on
    
    Returns:
        Trained content-based recommender
    """
    logger.info("Training content-based transformer model...")
    
    # Initialize model
    model = MovieContentTransformer(
        model_name="bert-base-uncased",
        embedding_dim=768,
        max_length=512,
        dropout=0.1
    )
    
    model.to(device)
    model.eval()  # Set to evaluation mode for inference
    
    # Create recommender
    recommender = ContentBasedRecommender(model)
    
    # Add movies and compute embeddings
    recommender.add_movies(movies)
    
    logger.info("Content-based model training completed!")
    return recommender


def train_collaborative_model(interactions: List[Dict], device: str = 'cuda') -> CollaborativeFilteringRecommender:
    """
    Train the collaborative filtering model.
    
    Args:
        interactions: List of interaction dictionaries
        device: Device to train on
    
    Returns:
        Trained collaborative filtering recommender
    """
    logger.info("Training collaborative filtering model...")
    
    # Get unique users and movies
    user_ids = list(set(interaction['user_id'] for interaction in interactions))
    movie_ids = list(set(interaction['movie_id'] for interaction in interactions))
    
    # Create internal ID mappings
    user_id_map = {user_id: i for i, user_id in enumerate(user_ids)}
    movie_id_map = {movie_id: i for i, movie_id in enumerate(movie_ids)}
    
    # Initialize model
    model = MatrixFactorization(
        num_users=len(user_ids),
        num_movies=len(movie_ids),
        embedding_dim=128,
        dropout=0.1
    )
    
    # Create recommender
    recommender = CollaborativeFilteringRecommender(model)
    
    # Build interaction matrix and train
    recommender.build_interaction_matrix(interactions, user_ids, movie_ids)
    recommender.train(interactions, epochs=50, learning_rate=0.01, device=device)
    
    logger.info("Collaborative filtering model training completed!")
    return recommender


def train_contextual_model(movies: List[Dict], device: str = 'cuda') -> ContextualRecommender:
    """
    Train the contextual transformer model.
    
    Args:
        movies: List of movie dictionaries
        device: Device to train on
    
    Returns:
        Trained contextual recommender
    """
    logger.info("Training contextual transformer model...")
    
    # Initialize model
    model = ReviewContextTransformer(
        model_name="bert-base-uncased",
        embedding_dim=768,
        max_length=512,
        dropout=0.1
    )
    
    model.to(device)
    model.eval()  # Set to evaluation mode for inference
    
    # Create recommender
    recommender = ContextualRecommender(model)
    
    # Add movie contexts from reviews
    movies_with_reviews = [movie for movie in movies if movie.get('reviews')]
    logger.info(f"Processing {len(movies_with_reviews)} movies with reviews")
    
    for movie in movies_with_reviews:
        recommender.add_movie_context(movie['tmdb_id'], movie['reviews'])
    
    logger.info("Contextual model training completed!")
    return recommender


def create_recommendation_engine(
    movies: List[Dict],
    interactions: List[Dict],
    device: str = 'cuda'
) -> MovieRecommendationEngine:
    """
    Create and initialize the complete recommendation engine.
    
    Args:
        movies: List of movie dictionaries
        interactions: List of interaction dictionaries
        device: Device to use
    
    Returns:
        Initialized recommendation engine
    """
    logger.info("Creating recommendation engine...")
    
    # Train individual models
    content_recommender = train_content_model(movies, device)
    collaborative_recommender = train_collaborative_model(interactions, device)
    contextual_recommender = train_contextual_model(movies, device)
    
    # Create ensemble engine
    engine = MovieRecommendationEngine(
        content_recommender=content_recommender,
        collaborative_recommender=collaborative_recommender,
        contextual_recommender=contextual_recommender
    )
    
    # Initialize from data
    engine.initialize_from_data(movies, interactions)
    
    logger.info("Recommendation engine created successfully!")
    return engine


def test_recommendations(engine: MovieRecommendationEngine, test_user_id: int = 1):
    """
    Test the recommendation engine with a sample user.
    
    Args:
        engine: Recommendation engine
        test_user_id: Test user ID
    """
    logger.info(f"Testing recommendations for user {test_user_id}...")
    
    # Get recommendations
    recommendations = engine.get_recommendations(
        user_id=test_user_id,
        top_k=5,
        include_guarantees=True
    )
    
    # Display results
    print(f"\n🎬 Recommendations for User {test_user_id}:")
    print("=" * 60)
    
    for i, rec in enumerate(recommendations, 1):
        movie_id = rec['movie_id']
        confidence = rec['confidence']
        ensemble_score = rec['ensemble_score']
        guarantee = rec.get('guarantee', {})
        
        print(f"\n{i}. Movie ID: {movie_id}")
        print(f"   Ensemble Score: {ensemble_score:.4f}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Guarantee Level: {guarantee.get('guarantee_level', 'none')}")
        print(f"   Explanation: {rec.get('explanation', 'No explanation available')}")
    
    print("\n" + "=" * 60)


def main():
    """
    Main training function for Google Colab.
    """
    # Check for GPU
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"Using device: {device}")
    
    if device == 'cuda':
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # AUTO-DETECT FILE PATHS (works in both local and Colab)
    import os
    base_paths = [
        Path.cwd(),  # Current directory
        Path('/content/drive/MyDrive/movie-recommendation-transformer'),  # Colab Drive
        Path('/content/movie-recommendation-transformer'),  # Colab clone
        Path(__file__).parent,  # Script directory
    ]
    
    jsonl_path = None
    csv_path = None
    
    for base in base_paths:
        jsonl_candidate = base / "data" / "raw" / "tmdb_movies_50k_20250711_011112.jsonl"
        csv_candidate = base / "data" / "realistic_synthetic_ratings_new_data.csv"
        
        if jsonl_candidate.exists() and not jsonl_path:
            jsonl_path = str(jsonl_candidate)
            logger.info(f"✅ Found movie data: {jsonl_path}")
        
        if csv_candidate.exists() and not csv_path:
            csv_path = str(csv_candidate)
            logger.info(f"✅ Found ratings data: {csv_path}")
        
        if jsonl_path and csv_path:
            break
    
    if not jsonl_path:
        logger.error("❌ Movie data file not found!")
        logger.error(f"Current directory: {os.getcwd()}")
        logger.error("Searched in:")
        for base in base_paths:
            logger.error(f"   - {base}")
        raise FileNotFoundError("Movie data file not found. Please check file paths.")
    
    if not csv_path:
        logger.error("❌ Ratings CSV file not found!")
        logger.error(f"Current directory: {os.getcwd()}")
        raise FileNotFoundError("Ratings CSV file not found. Please check file paths.")
    
    # Load movie data (14K movies with 18K reviews)
    movies = load_movie_data(jsonl_path)
    logger.info(f"Loaded {len(movies)} movies")
    
    # Count movies with reviews
    movies_with_reviews = sum(1 for m in movies if m.get('reviews'))
    logger.info(f"Movies with reviews: {movies_with_reviews}")
    
    # Load realistic synthetic interactions (905K ratings from 10K users)
    interactions = load_realistic_synthetic_interactions(csv_path)
    
    # Create recommendation engine
    engine = create_recommendation_engine(movies, interactions, device)
    
    # Test recommendations
    test_recommendations(engine, test_user_id=1)
    
    # Save the engine
    save_path = "Checkpoints/recommendation_engine"
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    engine.save_engine(save_path)
    
    logger.info("✅ Training completed successfully!")
    logger.info(f"📁 Models saved to: {save_path}")
    logger.info(f"   - Ensemble: {save_path}_ensemble.json")
    logger.info(f"   - Content embeddings: {save_path}_content_embeddings.npz")
    logger.info(f"   - Collaborative model: {save_path}_collaborative.pt")
    logger.info(f"   - Context embeddings: {save_path}_contexts.npz")
    
    return engine


if __name__ == "__main__":
    # This will be run in Google Colab
    engine = main() 