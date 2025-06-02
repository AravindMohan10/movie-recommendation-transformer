import requests
import json
import time
import os

# Load TMDB API key (from env or paste directly for testing)
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
if not TMDB_API_KEY:
    TMDB_API_KEY = 'b9e581106ed9db74350afe96fe1f1688'

# Sample TMDB movie IDs
tmdb_ids = ['27205', '157336', '19995']

BASE_URL = 'https://api.themoviedb.org/3/movie/{}/reviews'

all_reviews = []

def fetch_reviews_for_movie(movie_id):
    reviews = []
    page = 1
    while True:
        url = BASE_URL.format(movie_id)
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'en-US',
            'page': page
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch reviews for {movie_id} (status {response.status_code})")
            break

        data = response.json()
        page_results = data.get('results', [])
        if not page_results:
            break

        for review in page_results:
            reviews.append({
                'author': review.get('author'),
                'content': review.get('content'),
                'created_at': review.get('created_at'),
                'rating': review.get('author_details', {}).get('rating')
            })

        if page >= data.get('total_pages', 1):
            break
        page += 1
        time.sleep(0.5)  # Respectful delay

    return reviews

for tmdb_id in tmdb_ids:
    movie_reviews = fetch_reviews_for_movie(tmdb_id)
    print(f"TMDB ID {tmdb_id} → Collected {len(movie_reviews)} reviews")
    all_reviews.append({
        'tmdb_id': tmdb_id,
        'reviews': movie_reviews
    })

# Save to JSON
output_file = 'data/raw/tmdb_reviews_poc.json'
with open(output_file, 'w') as f:
    json.dump(all_reviews, f, indent=4)
print(f"\nAll reviews saved to {output_file}")