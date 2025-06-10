#!/usr/bin/env python3
"""
Data Preparation for Movie Recommendation System
This is where we transform raw data into training-ready format.

Learning Goals:
1. Understanding data structures for recommendation systems
2. Data preprocessing techniques
3. Feature engineering for ML models
"""

import pandas as pd
import numpy as np
import json
import torch
from typing import Dict, List, Tuple
from pathlib import Path

class MovieDataPreparator:
    """
    Prepares movie and user data for training recommendation models.
    
    Key Concepts:
    - Feature engineering: Creating useful features from raw data
    - Data normalization: Scaling features to similar ranges
    - Sparse matrices: Efficient representation of user-movie interactions
    """
    
    def __init__(self, movie_file: str, ratings_file: str):
        self.movie_file = movie_file
        self.ratings_file = ratings_file
        self.movies_df = None
        self.ratings_df = None
        self.user_movie_matrix = None
        
    def load_movie_data(self) -> pd.DataFrame:
        """
        Load and preprocess movie data from JSONL format.
        
        Learning: JSONL (JSON Lines) is a text format where each line is a JSON object.
        It's memory-efficient for large datasets compared to loading everything at once.
        """
        print("📚 Loading movie data...")
        movies = []
        
        with open(self.movie_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    movie = json.loads(line.strip())
                    movies.append(movie)
                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON at line {line_num}")
                    continue
        
        # Convert to DataFrame for easy manipulation
        df = pd.DataFrame(movies)
        print(f"✅ Loaded {len(df)} movies")
        
        # Feature Engineering: Extract useful information
        df = self._extract_movie_features(df)
        
        self.movies_df = df
        return df
    
    def _extract_movie_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract and engineer features from raw movie data.
        
        Learning: Feature engineering is crucial for ML success.
        We transform raw data into features that models can learn from.
        """
        print("🔧 Engineering movie features...")
        
        # 1. Extract genre names from complex structure
        df['genre_names'] = df['genres'].apply(
            lambda x: [g['name'] for g in x] if x else []
        )
        df['genres_string'] = df['genre_names'].apply(lambda x: ', '.join(x))
        
        # 2. Extract cast names (top 5 actors)
        df['cast_names'] = df['cast'].apply(
            lambda x: [actor['name'] for actor in x[:5]] if x else []
        )
        df['cast_string'] = df['cast_names'].apply(lambda x: ', '.join(x))
        
        # 3. Extract director name
        df['director'] = df['crew'].apply(self._extract_director)
        
        # 4. Clean and normalize numerical features
        df['vote_average'] = pd.to_numeric(df['vote_average'], errors='coerce').fillna(0.0)
        df['vote_count'] = pd.to_numeric(df['vote_count'], errors='coerce').fillna(0)
        df['popularity'] = pd.to_numeric(df['popularity'], errors='coerce').fillna(0.0)
        
        # 5. Create popularity score (combines rating and count)
        # Learning: Simple features often work best
        df['popularity_score'] = df['vote_average'] * np.log1p(df['vote_count'])
        
        # 6. Create content text for embedding
        df['content_text'] = df.apply(self._create_content_text, axis=1)
        
        # 7. Extract review count and sentiment
        df['review_count'] = df['reviews'].apply(lambda x: len(x) if x else 0)
        df['has_reviews'] = df['review_count'] > 0
        
        print(f"✅ Engineered features for {len(df)} movies")
        return df
    
    def _extract_director(self, crew_list: List[Dict]) -> str:
        """Extract director name from crew list."""
        if not crew_list:
            return "Unknown"
        
        for person in crew_list:
            if person.get('job') == 'Director':
                return person.get('name', 'Unknown')
        return "Unknown"
    
    def _create_content_text(self, movie: pd.Series) -> str:
        """
        Create a text representation of movie content for embedding.
        
        Learning: Text embeddings need comprehensive text that captures movie essence.
        We combine title, overview, genres, and cast into one text.
        """
        parts = []
        
        # Title (most important)
        if pd.notna(movie['title']):
            parts.append(movie['title'])
        
        # Overview (description)
        if pd.notna(movie['overview']) and movie['overview'].strip():
            parts.append(movie['overview'])
        
        # Genres
        if movie['genres_string']:
            parts.append(f"Genres: {movie['genres_string']}")
        
        # Cast
        if movie['cast_string']:
            parts.append(f"Starring: {movie['cast_string']}")
        
        # Director
        if movie['director'] != "Unknown":
            parts.append(f"Directed by: {movie['director']}")
        
        return " ".join(parts)
    
    def load_ratings_data(self) -> pd.DataFrame:
        """
        Load user ratings data.
        
        Learning: User-item interaction data is the core of collaborative filtering.
        Each row represents a user's rating of a movie.
        """
        print("📊 Loading user ratings...")
        
        self.ratings_df = pd.read_csv(self.ratings_file)
        
        # Clean the data
        self.ratings_df = self.ratings_df.dropna()
        self.ratings_df['rating'] = pd.to_numeric(self.ratings_df['rating'], errors='coerce')
        self.ratings_df = self.ratings_df.dropna()
        
        print(f"✅ Loaded {len(self.ratings_df)} ratings")
        print(f"   Users: {self.ratings_df['user_id'].nunique()}")
        print(f"   Movies: {self.ratings_df['movie_id'].nunique()}")
        print(f"   Rating range: {self.ratings_df['rating'].min():.1f} - {self.ratings_df['rating'].max():.1f}")
        
        return self.ratings_df
    
    def create_user_movie_matrix(self) -> torch.Tensor:
        """
        Create user-movie interaction matrix.
        
        Learning: This is the fundamental data structure for collaborative filtering.
        Rows = users, Columns = movies, Values = ratings
        Most entries are 0 (sparse matrix) because users rate few movies.
        """
        print("🏗️ Creating user-movie interaction matrix...")
        
        # Get unique users and movies
        unique_users = sorted(self.ratings_df['user_id'].unique())
        unique_movies = sorted(self.ratings_df['movie_id'].unique())
        
        # Create mapping dictionaries
        self.user_to_idx = {user_id: idx for idx, user_id in enumerate(unique_users)}
        self.movie_to_idx = {movie_id: idx for idx, movie_id in enumerate(unique_movies)}
        self.idx_to_user = {idx: user_id for user_id, idx in self.user_to_idx.items()}
        self.idx_to_movie = {idx: movie_id for movie_id, idx in self.movie_to_idx.items()}
        
        # Create the matrix
        matrix = torch.zeros(len(unique_users), len(unique_movies))
        
        for _, row in self.ratings_df.iterrows():
            user_idx = self.user_to_idx[row['user_id']]
            movie_idx = self.movie_to_idx[row['movie_id']]
            matrix[user_idx, movie_idx] = row['rating']
        
        # Calculate sparsity
        total_entries = matrix.numel()
        non_zero_entries = torch.count_nonzero(matrix).item()
        sparsity = (total_entries - non_zero_entries) / total_entries * 100
        
        print(f"✅ Created {matrix.shape[0]} x {matrix.shape[1]} matrix")
        print(f"   Sparsity: {sparsity:.1f}% (most entries are 0)")
        
        self.user_movie_matrix = matrix
        return matrix
    
    def get_training_data(self) -> Dict:
        """
        Prepare all data for training.
        
        Returns organized data dictionary for model training.
        """
        if self.movies_df is None:
            self.load_movie_data()
        
        if self.ratings_df is None:
            self.load_ratings_data()
        
        if self.user_movie_matrix is None:
            self.create_user_movie_matrix()
        
        print("📦 Preparing training data package...")
        
        training_data = {
            'movies': self.movies_df,
            'ratings': self.ratings_df,
            'user_movie_matrix': self.user_movie_matrix,
            'user_to_idx': self.user_to_idx,
            'movie_to_idx': self.movie_to_idx,
            'idx_to_user': self.idx_to_user,
            'idx_to_movie': self.idx_to_movie,
            'num_users': len(self.user_to_idx),
            'num_movies': len(self.movie_to_idx)
        }
        
        print("✅ Training data ready!")
        return training_data

def main():
    """Demonstrate data preparation."""
    print("🎬 Movie Recommendation System - Data Preparation")
    print("=" * 50)
    
    # Initialize data preparator
    preparator = MovieDataPreparator(
        movie_file='../data/raw/tmdb_movies_50k_20250711_011112.jsonl',
        ratings_file='../data/realistic_synthetic_ratings_new_data.csv'
    )
    
    # Prepare training data
    training_data = preparator.get_training_data()
    
    # Show some statistics
    print("\n📈 Data Summary:")
    print(f"Movies: {training_data['num_movies']}")
    print(f"Users: {training_data['num_users']}")
    print(f"Ratings: {len(training_data['ratings'])}")
    print(f"Matrix sparsity: {(1 - len(training_data['ratings']) / (training_data['num_users'] * training_data['num_movies'])) * 100:.1f}%")
    
    # Save processed data
    print("\n💾 Saving processed data...")
    torch.save(training_data, '../data/processed_training_data_new.pt')
    print("✅ Saved to ../data/processed_training_data_new.pt")

if __name__ == "__main__":
    main()
