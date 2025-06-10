#!/usr/bin/env python3
"""
Generate Realistic Synthetic Users for Movie Recommendation Training
Uses the new 14,778 movie dataset from JSONL format.
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import random
from typing import List, Dict, Tuple

def load_new_movie_data(jsonl_path: str) -> pd.DataFrame:
    """
    Load the new movie data from JSONL format.
    """
    print(f"Loading movie data from {jsonl_path}...")
    movies = []
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            movie = json.loads(line.strip())
            movies.append(movie)
    
    print(f"Loaded {len(movies)} movies")
    
    # Convert to DataFrame
    df = pd.DataFrame(movies)
    
    # Extract genre names from the complex genre structure
    df['genre_names'] = df['genres'].apply(lambda x: [g['name'] for g in x] if x else [])
    df['genres_string'] = df['genre_names'].apply(lambda x: ', '.join(x))
    
    # Clean up vote data
    df['vote_average'] = pd.to_numeric(df['vote_average'], errors='coerce')
    df['vote_count'] = pd.to_numeric(df['vote_count'], errors='coerce')
    
    # Filter out movies with missing vote data
    df = df.dropna(subset=['vote_average', 'vote_count'])
    
    print(f"After cleaning: {len(df)} movies with valid vote data")
    return df

def create_user_profiles(num_users: int = 10000) -> List[Dict]:
    """
    Create realistic user profiles with genre preferences and personality traits.
    """
    # Define user archetypes with realistic preferences
    user_archetypes = {
        'action_fan': {
            'preferred_genres': ['ACTION', 'ADVENTURE', 'THRILLER', 'SCIENCE FICTION'],
            'avoided_genres': ['ROMANCE', 'MUSICAL', 'DOCUMENTARY'],
            'rating_bias': 0.3,  # Slightly higher ratings for preferred genres
            'rating_volatility': 0.8,  # More consistent ratings
            'num_movies': (80, 150)  # Watches more movies
        },
        'romance_lover': {
            'preferred_genres': ['ROMANCE', 'COMEDY', 'DRAMA'],
            'avoided_genres': ['HORROR', 'ACTION', 'THRILLER'],
            'rating_bias': 0.2,
            'rating_volatility': 0.6,
            'num_movies': (60, 120)
        },
        'horror_buff': {
            'preferred_genres': ['HORROR', 'THRILLER', 'MYSTERY'],
            'avoided_genres': ['ROMANCE', 'COMEDY', 'MUSICAL'],
            'rating_bias': 0.4,  # Very high ratings for horror
            'rating_volatility': 1.2,  # More extreme ratings
            'num_movies': (40, 100)
        },
        'cinephile': {
            'preferred_genres': ['DRAMA', 'DOCUMENTARY', 'BIOGRAPHY', 'HISTORY'],
            'avoided_genres': ['ACTION', 'HORROR'],
            'rating_bias': 0.1,  # More critical
            'rating_volatility': 0.5,  # Very consistent
            'num_movies': (100, 200)  # Watches many movies
        },
        'casual_viewer': {
            'preferred_genres': ['COMEDY', 'ACTION', 'ADVENTURE'],
            'avoided_genres': ['DOCUMENTARY', 'HORROR', 'MYSTERY'],
            'rating_bias': 0.0,  # Neutral
            'rating_volatility': 1.0,  # Average volatility
            'num_movies': (30, 80)
        },
        'family_viewer': {
            'preferred_genres': ['ANIMATION', 'COMEDY', 'ADVENTURE', 'FAMILY'],
            'avoided_genres': ['HORROR', 'THRILLER', 'ROMANCE'],
            'rating_bias': 0.1,
            'rating_volatility': 0.7,
            'num_movies': (50, 100)
        }
    }
    
    # Distribution of user types (realistic proportions)
    archetype_distribution = {
        'action_fan': 0.25,
        'romance_lover': 0.20,
        'horror_buff': 0.15,
        'cinephile': 0.10,
        'casual_viewer': 0.20,
        'family_viewer': 0.10
    }
    
    users = []
    for user_id in range(num_users):
        # Assign archetype based on distribution
        archetype = np.random.choice(
            list(archetype_distribution.keys()),
            p=list(archetype_distribution.values())
        )
        
        profile = user_archetypes[archetype].copy()
        profile['user_id'] = user_id
        profile['archetype'] = archetype
        
        # Add some personality variation
        profile['rating_bias'] += np.random.normal(0, 0.1)
        profile['rating_volatility'] = max(0.1, profile['rating_volatility'] + np.random.normal(0, 0.2))
        
        users.append(profile)
    
    return users

def generate_realistic_ratings(movies_df: pd.DataFrame, user_profiles: List[Dict]) -> List[Dict]:
    """
    Generate realistic ratings based on user profiles and movie characteristics.
    """
    ratings = []
    
    for user_profile in user_profiles:
        user_id = user_profile['user_id']
        preferred_genres = user_profile['preferred_genres']
        avoided_genres = user_profile['avoided_genres']
        rating_bias = user_profile['rating_bias']
        rating_volatility = user_profile['rating_volatility']
        num_movies_range = user_profile['num_movies']
        
        # Determine how many movies this user will rate
        num_movies = np.random.randint(num_movies_range[0], num_movies_range[1])
        
        # Create genre preference weights
        genre_weights = np.ones(len(movies_df))
        
        for i, genre_names in enumerate(movies_df['genre_names']):
            if not genre_names:
                continue
                
            # Boost weight for preferred genres
            for genre in preferred_genres:
                if genre in genre_names:
                    genre_weights[i] *= 3.0
            
            # Reduce weight for avoided genres
            for genre in avoided_genres:
                if genre in genre_names:
                    genre_weights[i] *= 0.3
        
        # Sample movies based on genre preferences
        sampled_indices = np.random.choice(
            len(movies_df),
            size=min(num_movies, len(movies_df)),
            replace=False,
            p=genre_weights / genre_weights.sum()
        )
        
        for idx in sampled_indices:
            movie = movies_df.iloc[idx]
            
            # Base rating from movie's average rating
            base_rating = float(movie['vote_average'])
            
            # Add user's genre bias
            movie_genres = movie['genre_names']
            genre_bonus = 0
            
            for genre in preferred_genres:
                if genre in movie_genres:
                    genre_bonus += rating_bias
            
            for genre in avoided_genres:
                if genre in movie_genres:
                    genre_bonus -= rating_bias
            
            # Add some randomness based on user's volatility
            noise = np.random.normal(0, rating_volatility)
            
            # Calculate final rating
            final_rating = np.clip(base_rating + genre_bonus + noise, 1.0, 10.0)
            
            # Add timestamp (realistic viewing patterns)
            timestamp = generate_realistic_timestamp()
            
            ratings.append({
                'user_id': user_id,
                'movie_id': int(movie['tmdb_id']),
                'rating': round(final_rating, 1),
                'timestamp': timestamp
            })
    
    return ratings

def generate_realistic_timestamp() -> str:
    """
    Generate realistic timestamps for movie watching.
    """
    # Most people watch movies in the evening/weekends
    current_time = datetime.now()
    
    # Random date within last 2 years
    days_back = np.random.randint(0, 730)
    watch_date = current_time - timedelta(days=days_back)
    
    # Simple uniform distribution for hours
    hour = np.random.randint(0, 24)
    minute = np.random.randint(0, 60)
    
    watch_date = watch_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    return watch_date.strftime('%Y-%m-%d %H:%M:%S')

def main():
    print("🎬 Generating Realistic Synthetic Users with New 14K Movie Dataset...")
    
    # Load the new movie data
    jsonl_path = '../data/raw/tmdb_movies_50k_20250711_011112.jsonl'
    movies_df = load_new_movie_data(jsonl_path)
    
    # Create user profiles
    print("Creating user profiles...")
    num_users = 10000
    user_profiles = create_user_profiles(num_users)
    
    # Generate realistic ratings
    print("Generating realistic ratings...")
    ratings = generate_realistic_ratings(movies_df, user_profiles)
    
    # Convert to DataFrame
    ratings_df = pd.DataFrame(ratings)
    
    # Save to CSV
    output_file = '../data/realistic_synthetic_ratings_new_data.csv'
    ratings_df.to_csv(output_file, index=False)
    
    print(f"✅ Generated {len(ratings_df)} realistic ratings for {num_users} users")
    print(f"📊 Average ratings per user: {len(ratings_df) / num_users:.1f}")
    print(f"📁 Saved to: {output_file}")
    
    # Show some statistics
    print("\n📈 Rating Statistics:")
    print(f"Average rating: {ratings_df['rating'].mean():.2f}")
    print(f"Rating std: {ratings_df['rating'].std():.2f}")
    print(f"Rating range: {ratings_df['rating'].min():.1f} - {ratings_df['rating'].max():.1f}")
    
    # Show user archetype distribution
    archetype_counts = {}
    for profile in user_profiles:
        archetype = profile['archetype']
        archetype_counts[archetype] = archetype_counts.get(archetype, 0) + 1
    
    print("\n👥 User Archetype Distribution:")
    for archetype, count in archetype_counts.items():
        percentage = (count / num_users) * 100
        print(f"  {archetype}: {count} users ({percentage:.1f}%)")
    
    # Show genre distribution in the dataset
    print("\n🎭 Movie Genre Distribution:")
    all_genres = []
    for genres in movies_df['genre_names']:
        all_genres.extend(genres)
    
    genre_counts = pd.Series(all_genres).value_counts()
    print("Top 10 genres:")
    for genre, count in genre_counts.head(10).items():
        print(f"  {genre}: {count} movies")

if __name__ == "__main__":
    main()
