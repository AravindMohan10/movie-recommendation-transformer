import json
import random
import csv
import os
from datetime import datetime, timedelta

data_file = 'data/raw/tmdb_complete_dataset.jsonl'
output_file = 'data/synthetic_watch_history.csv'

os.makedirs('data', exist_ok=True)

movies = []
print(f"Loading movies from {data_file}")
with open(data_file, 'r', encoding='utf-8') as f:
    for line in f:
        movie = json.loads(line)
        movies.append({
            'tmdb_id': int(movie['tmdb_id']),
            'vote_average': float(movie['vote_average']) if movie['vote_average'] else 5.0,
            'vote_count': int(movie['vote_count']) if movie['vote_count'] else 0
        })

print(f"Loaded {len(movies)} movies")

num_users = 10000
min_interactions = 50
max_interactions = 200

print(f"Generating synthetic watch history for {num_users} users...")

with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['user_id', 'movie_id', 'rating', 'timestamp'])

    for user_id in range(1, num_users + 1):
        num_interactions = random.randint(min_interactions, max_interactions)
        sampled_movies = random.choices(
            movies,
            weights=[m['vote_count'] + 1 for m in movies],
            k=num_interactions
        )

        for m in sampled_movies:
            rating = min(10.0, max(1.0, random.gauss(m['vote_average'], 1.0)))
            
            days_ago = random.randint(0, 730)
            watch_time = datetime.now() - timedelta(days=days_ago)
            timestamp = watch_time.strftime('%Y-%m-%d %H:%M:%S')

            writer.writerow([user_id, m['tmdb_id'], round(rating, 1), timestamp])

print(f"Synthetic watch history saved to {output_file}")