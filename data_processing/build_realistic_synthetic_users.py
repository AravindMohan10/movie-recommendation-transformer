#!/usr/bin/env python3
"""
Generate Realistic Synthetic Users for Movie Recommendation Training
Creates users with realistic preferences, genre clusters, and rating patterns.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import List, Dict, Tuple

def create_user_profiles(num_users: int = 10000) -> List[Dict]:
    """
    Create realistic user profiles with genre preferences and personality traits.
    """
    # Define user archetypes with realistic preferences
    user_archetypes = {
        'action_fan': {
            'preferred_genres': ['Action', 'Adventure', 'Thriller', 'Sci-Fi'],
            'avoided_genres': ['Romance', 'Musical', 'Documentary'],
            'rating_bias': 0.3,  # Slightly higher ratings for preferred genres
            'rating_volatility': 0.8,  # More consistent ratings
            'num_movies': (80, 150)  # Watches more movies
        },
        'romance_lover': {
            'preferred_genres': ['Romance', 'Comedy', 'Drama'],
            'avoided_genres': ['Horror', 'Action', 'Thriller'],
            'rating_bias': 0.2,
            'rating_volatility': 0.6,
            'num_movies': (60, 120)
        },
        'horror_buff': {
            'preferred_genres': ['Horror', 'Thriller', 'Mystery'],
            'avoided_genres': ['Romance', 'Comedy', 'Musical'],
            'rating_bias': 0.4,  # Very high ratings for horror
            'rating_volatility': 1.2,  # More extreme ratings
            'num_movies': (40, 100)
        },
        'cinephile': {
            'preferred_genres': ['Drama', 'Documentary', 'Biography', 'History'],
            'avoided_genres': ['Action', 'Horror'],
            'rating_bias': 0.1,  # More critical
            'rating_volatility': 0.5,  # Very consistent
            'num_movies': (100, 200)  # Watches many movies
        },
        'casual_viewer': {
            'preferred_genres': ['Comedy', 'Action', 'Adventure'],
            'avoided_genres': ['Documentary', 'Horror', 'Mystery'],
            'rating_bias': 0.0,  # Neutral
            'rating_volatility': 1.0,  # Average volatility
            'num_movies': (30, 80)
        },
        'family_viewer': {
            'preferred_genres': ['Animation', 'Comedy', 'Adventure', 'Family'],
            'avoided_genres': ['Horror', 'Thriller', 'Romance'],
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
        profile['rating_volatility'] += np.random.normal(0, 0.2)
        
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
        
        for i, genres in enumerate(movies_df['genres']):
            if pd.isna(genres):
                continue
                
            # Convert genres string to list
            movie_genres = [g.strip() for g in str(genres).split(',')]
            
            # Boost weight for preferred genres
            for genre in preferred_genres:
                if genre in movie_genres:
                    genre_weights[i] *= 3.0
            
            # Reduce weight for avoided genres
            for genre in avoided_genres:
                if genre in movie_genres:
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
            base_rating = movie['vote_average']
            
            # Add user's genre bias
            movie_genres = [g.strip() for g in str(movie['genres']).split(',')]
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
                'movie_id': movie['movie_id'],
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
    
    # Evening hours (6 PM - 11 PM) are more common
    hour_weights = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1,  # 12 AM - 5 PM
                   0.2, 0.3, 0.4, 0.5, 0.4, 0.3]   # 6 PM - 11 PM
    
    hour = np.random.choice(range(24), p=hour_weights)
    minute = np.random.randint(0, 60)
    
    watch_date = watch_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    return watch_date.strftime('%Y-%m-%d %H:%M:%S')

def main():
    print("🎬 Generating Realistic Synthetic Users...")
    
    # Load movie data
    print("Loading movie data...")
    movies_df = pd.read_csv('../data/combined_training_data.csv', low_memory=False)
    
    # Convert vote_average to numeric, handling errors
    movies_df['vote_average'] = pd.to_numeric(movies_df['vote_average'], errors='coerce')
    movies_df['vote_count'] = pd.to_numeric(movies_df['vote_count'], errors='coerce')
    movies_df = movies_df.dropna(subset=['vote_average', 'vote_count'])
    print(f"Loaded {len(movies_df)} movies")
    
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
    output_file = '../data/realistic_synthetic_ratings.csv'
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

if __name__ == "__main__":
    main()
