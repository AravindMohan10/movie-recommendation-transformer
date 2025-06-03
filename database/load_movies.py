import psycopg2
import json

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname='movie_recommendation',
    user='postgres',
    password='Believe@1007', 
    host='localhost',
    port='5432'
)
cur = conn.cursor()

# Load JSONL data
with open('data/raw/tmdb_complete_dataset.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        movie = json.loads(line)
        tmdb_id = int(movie['tmdb_id'])
        title = movie['title']
        overview = movie['overview']
        genres = ', '.join(movie['genres']) if movie['genres'] else None
        vote_average = float(movie['vote_average']) if movie['vote_average'] is not None else None
        vote_count = int(movie['vote_count']) if movie['vote_count'] is not None else None
        runtime = int(movie['runtime']) if movie['runtime'] is not None else None
        release_date = movie['release_date'] if movie['release_date'] else None
        revenue = int(movie['revenue']) if movie['revenue'] is not None else None
        original_language = movie['original_language']
        poster_path = movie['poster_path']

        # Insert into movies table
        cur.execute("""
            INSERT INTO movies (
                tmdb_id, title, overview, genres, vote_average,
                vote_count, runtime, release_date, revenue,
                original_language, poster_path
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tmdb_id) DO NOTHING
        """, (
            tmdb_id, title, overview, genres, vote_average,
            vote_count, runtime, release_date, revenue,
            original_language, poster_path
        ))

        # Insert reviews (if any)
        for review in movie.get('reviews', []):
            author = review['author']
            content = review['content']
            created_at = review['created_at']
            rating = float(review['rating']) if review['rating'] is not None else None

            cur.execute("""
                INSERT INTO reviews (
                    tmdb_id, author, content, created_at, rating
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                tmdb_id, author, content, created_at, rating
            ))

# Commit and close
conn.commit()
cur.close()
conn.close()

print(" Data inserted successfully!")