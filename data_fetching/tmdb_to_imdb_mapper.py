import requests
import time
import os
import json

TMDB_API_KEY = os.getenv('TMDB_API_KEY') 

if not TMDB_API_KEY:
    TMDB_API_KEY = 'b9e581106ed9db74350afe96fe1f1688'

# TMDB movie IDs to map (sample)
tmdb_ids = ['27205', '157336', '19995']

def get_imdb_id(tmdb_id):
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        imdb_id = data.get('imdb_id')
        title = data.get('title')
        print(f"TMDB ID {tmdb_id} → IMDb ID {imdb_id} → {title}")
        return {'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'title': title}
    else:
        print(f"Failed to fetch TMDB ID {tmdb_id}: {response.status_code}")
        return None

def main():
    results = []
    for tmdb_id in tmdb_ids:
        mapped = get_imdb_id(tmdb_id)
        if mapped:
            results.append(mapped)
        time.sleep(1)  # Respect TMDB API rate limits

    # Save to JSON for backup
    with open('data/raw/tmdb_to_imdb_mapping.json', 'w') as f:
        json.dump(results, f, indent=4)
    print("Mapping saved to data/raw/tmdb_to_imdb_mapping.json")

if __name__ == "__main__":
    main()