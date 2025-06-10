#!/usr/bin/env python3
"""
Count reviews in the movie dataset
"""

import json

def count_reviews():
    total_reviews = 0
    movies_with_reviews = 0
    total_movies = 0
    
    with open('../data/raw/tmdb_movies_50k_20250711_011112.jsonl', 'r') as f:
        for line in f:
            movie = json.loads(line.strip())
            total_movies += 1
            
            reviews = movie.get('reviews', [])
            review_count = len(reviews)
            
            total_reviews += review_count
            if review_count > 0:
                movies_with_reviews += 1
    
    print(f"📊 Review Statistics:")
    print(f"Total movies: {total_movies}")
    print(f"Movies with reviews: {movies_with_reviews}")
    print(f"Total reviews: {total_reviews}")
    print(f"Average reviews per movie: {total_reviews / total_movies:.2f}")
    print(f"Percentage of movies with reviews: {(movies_with_reviews / total_movies) * 100:.1f}%")

if __name__ == "__main__":
    count_reviews()

