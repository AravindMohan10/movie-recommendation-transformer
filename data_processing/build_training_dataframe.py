import psycopg2
import pandas as pd

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname='movie_recommendation',
    user='postgres',
    password='Believe@1007',
    host='localhost',
    port='5432'
)

# Query watch_history + movies
watch_history_query = """
SELECT wh.user_id, wh.movie_id, wh.rating, wh.watched_at, 
       m.tmdb_id, m.title, m.overview, m.genres, m.vote_average, 
       m.vote_count, m.runtime, m.release_date, m.revenue, 
       m.original_language, m.poster_path
FROM watch_history wh
JOIN movies m ON wh.movie_id = m.tmdb_id::INTEGER;
"""

watch_history_df = pd.read_sql_query(watch_history_query, conn)
print(f"Loaded {len(watch_history_df)} watch history rows")

# Query review aggregates
reviews_query = """
SELECT tmdb_id, AVG(rating) AS avg_review_rating
FROM reviews
WHERE rating IS NOT NULL
GROUP BY tmdb_id
"""

reviews_df = pd.read_sql_query(reviews_query, conn)
print(f"Loaded {len(reviews_df)} aggregated review scores")

# Ensure merge keys are strings
watch_history_df['movie_id'] = watch_history_df['movie_id'].astype(str)
reviews_df['tmdb_id'] = reviews_df['tmdb_id'].astype(str)

# Merge
combined_df = pd.merge(
    watch_history_df,
    reviews_df,
    how='left',
    left_on='movie_id',
    right_on='tmdb_id'
)

# Fill missing avg review ratings
combined_df['avg_review_rating'] = combined_df['avg_review_rating'].fillna(5.0)

# Process genres to list
combined_df['genres_list'] = combined_df['genres'].apply(
    lambda x: [g.strip() for g in x.split(',')] if pd.notnull(x) else []
)

# Extract release year
combined_df['release_year'] = pd.to_datetime(
    combined_df['release_date'], errors='coerce'
).dt.year

# Drop tmdb_id column only if it exists
if 'tmdb_id' in combined_df.columns:
    combined_df.drop(columns=['tmdb_id'], inplace=True)

# Save to CSV
output_path = 'data/combined_training_data.csv'
combined_df.to_csv(output_path, index=False)
print(f"Combined training data saved to {output_path}")

# Close DB connection
conn.close()
print("PostgreSQL connection closed")