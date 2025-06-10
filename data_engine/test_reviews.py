#!/usr/bin/env python3
"""
Test script to debug review extraction issue.
"""

import asyncio
import json
import traceback
from tmdb_client import TMDBClient
from config import TMDB_CONFIG

async def test_review_extraction():
    """Test review extraction with a few specific movies."""
    
    # Test with some popular movies that should have reviews
    test_movie_ids = [550, 13, 680, 155, 238]  # Fight Club, Forrest Gump, Pulp Fiction, Dark Knight, Godfather
    
    async with TMDBClient(api_key=TMDB_CONFIG["api_key"]) as client:
        print("🔍 Testing review extraction...")
        
        for movie_id in test_movie_ids:
            try:
                print(f"\n📽️  Testing movie ID: {movie_id}")
                
                # Get movie with reviews
                movie = await client.get_movie(movie_id, include_reviews=True)
                
                print(f"   Title: {movie.title}")
                print(f"   Reviews count: {len(movie.reviews)}")
                
                if movie.reviews:
                    print(f"   First review author: {movie.reviews[0].author}")
                    print(f"   First review content preview: {movie.reviews[0].content[:100]}...")
                else:
                    print("   ❌ No reviews found")
                    
                    # Test the reviews endpoint directly
                    print("   🔍 Testing reviews endpoint directly...")
                    try:
                        reviews_data = await client._make_request(f"movie/{movie_id}/reviews")
                        print(f"   Raw reviews response: {reviews_data}")
                        print(f"   Results count: {len(reviews_data.get('results', []))}")
                    except Exception as e:
                        print(f"   ❌ Reviews endpoint failed: {e}")
                
            except Exception as e:
                print(f"   ❌ Failed to fetch movie {movie_id}: {e}")
                print(f"   Full traceback:")
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_review_extraction()) 