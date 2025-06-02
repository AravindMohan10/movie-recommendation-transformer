import pandas as pd
import numpy as np

# Load movie metadata
df = pd.read_csv('data/combined_training_data.csv', low_memory=False)
print(f"Loaded {len(df)} rows")

df['vote_average'] = pd.to_numeric(df['vote_average'], errors='coerce')
df['vote_count'] = pd.to_numeric(df['vote_count'], errors='coerce')
df = df.dropna(subset=['vote_average', 'vote_count'])

print(f"After cleaning: {len(df)} rows")

# Get movie popularity as a weighting factor (vote_average × log(vote_count))
df['popularity_weight'] = df['vote_average'] * np.log1p(df['vote_count'])

# Normalize popularity to [0, 1]
df['popularity_norm'] = (df['popularity_weight'] - df['popularity_weight'].min()) / (df['popularity_weight'].max() - df['popularity_weight'].min())

# Simulate synthetic user ratings
num_users = 10000  # or match your user count
synthetic_ratings = []

for user_id in range(num_users):
    # Sample ~50-200 movies per user, biased by popularity
    num_rated = np.random.randint(50, 200)
    sampled_movies = df.sample(n=num_rated, weights='popularity_norm', replace=False)

    for _, row in sampled_movies.iterrows():
        # Generate rating around the movie's vote_average ± noise
        rating = np.clip(np.random.normal(loc=row['vote_average'], scale=1.0), 1.0, 10.0)
        synthetic_ratings.append({
            'user_id': user_id,
            'movie_id': row['movie_id'],
            'rating': rating
        })

synthetic_df = pd.DataFrame(synthetic_ratings)
print(f"Generated {len(synthetic_df)} synthetic ratings")

# Save to CSV
synthetic_df.to_csv('data/synthetic_ratings.csv', index=False)
print("Saved synthetic ratings to data/synthetic_ratings.csv")