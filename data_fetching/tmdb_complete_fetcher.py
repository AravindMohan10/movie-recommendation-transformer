import csv
import requests
import json
import time
import os

TMDB_API_KEY = os.getenv('TMDB_API_KEY') or 'b9e581106ed9db74350afe96fe1f1688'
BASE_MOVIE_URL = 'https://api.themoviedb.org/3/movie/{}'
REVIEWS_URL = 'https://api.themoviedb.org/3/movie/{}/reviews'
OUTPUT_FILE = 'data/raw/tmdb_complete_dataset.jsonl'  # JSONL format

os.makedirs('data/raw', exist_ok=True)

# Load already processed IDs
def load_existing_ids(output_file):
    existing_ids = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    existing_ids.add(str(obj['tmdb_id']))
                except:
                    continue
    print(f"Resuming — found {len(existing_ids)} already saved movies")
    return existing_ids

def load_tmdb_ids(csv_file):
    tmdb_ids = []
    with open(csv_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            tmdb_ids.append(str(row['id']))
    return tmdb_ids

def fetch_movie_metadata(movie_id):
    url = BASE_MOVIE_URL.format(movie_id)
    params = {'api_key': TMDB_API_KEY, 'language': 'en-US'}
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'tmdb_id': movie_id,
                    'title': data.get('title'),
                    'overview': data.get('overview'),
                    'genres': [g['name'] for g in data.get('genres', [])],
                    'vote_average': data.get('vote_average'),
                    'vote_count': data.get('vote_count'),
                    'runtime': data.get('runtime'),
                    'release_date': data.get('release_date'),
                    'revenue': data.get('revenue'),
                    'original_language': data.get('original_language'),
                    'poster_path': data.get('poster_path')  # store just the relative path
                }
            else:
                print(f"Failed metadata fetch for {movie_id}, status {response.status_code}")
                return None
        except requests.RequestException:
            print(f"⚠️ Retry {attempt + 1} for metadata {movie_id}")
            time.sleep(2)
    return None

def fetch_movie_reviews(movie_id):
    reviews = []
    page = 1
    while True:
        url = REVIEWS_URL.format(movie_id)
        params = {'api_key': TMDB_API_KEY, 'language': 'en-US', 'page': page}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                break
            data = response.json()
            page_reviews = data.get('results', [])
            if not page_reviews:
                break
            for review in page_reviews:
                reviews.append({
                    'author': review.get('author'),
                    'content': review.get('content'),
                    'created_at': review.get('created_at'),
                    'rating': review.get('author_details', {}).get('rating')
                })
            if page >= data.get('total_pages', 1):
                break
            page += 1
            time.sleep(0.5)
        except requests.RequestException:
            print(f"⚠️ Error fetching reviews for {movie_id}, page {page}")
            break
    return reviews

def main():
    csv_file = 'balanced_50k_unique_tmdb_ids.csv'
    tmdb_ids = load_tmdb_ids(csv_file)
    existing_ids = load_existing_ids(OUTPUT_FILE)
    total = len(tmdb_ids)

    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        for idx, tmdb_id in enumerate(tmdb_ids, start=1):
            if tmdb_id in existing_ids:
                continue
            print(f"Processing {idx}/{total} → TMDB ID {tmdb_id}")
            movie_data = fetch_movie_metadata(tmdb_id)
            if movie_data is None:
                continue
            movie_data['reviews'] = fetch_movie_reviews(tmdb_id)
            f.write(json.dumps(movie_data) + '\n')
            f.flush()
            time.sleep(0.5)

    print(f"All data saved to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()