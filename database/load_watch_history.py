import os
import psycopg2
import csv

# Connect to PostgreSQL (use env vars; no hardcoded passwords)
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME", "movie_recommendation"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", ""),
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
)
cur = conn.cursor()

# Load CSV data
input_file = 'data/synthetic_watch_history.csv'

with open(input_file, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    count = 0
    for row in reader:
        user_id = int(row['user_id'])
        movie_id = int(row['movie_id'])
        rating = float(row['rating'])
        watched_at = row['timestamp']

        cur.execute("""
            INSERT INTO watch_history (user_id, movie_id, rating, watched_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, movie_id) DO NOTHING
        """, (user_id, movie_id, rating, watched_at))

        count += 1
        if count % 1000 == 0:
            conn.commit()
            print(f"Inserted {count} rows so far")

# Final commit
conn.commit()
cur.close()
conn.close()

print("Watch history data loaded successfully!")