#!/usr/bin/env python3
"""
CineAI Discover-Based Data Extraction Script
Fetches a large, unique set of movies using TMDB's discover endpoint, skipping already-extracted movies.
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Any

import pandas as pd
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent))
from config import TMDB_CONFIG, DATA_CONFIG
from tmdb_client import TMDBClient
from schema import Movie

RAW_DIR = Path(DATA_CONFIG["raw_data_dir"])
RAW_DIR.mkdir(parents=True, exist_ok=True)

# --- Parameters ---
TARGET_MOVIES = 50000
MAX_HOURS = 24
SAVE_EVERY = 1000
PREV_JSONL = RAW_DIR / "tmdb_movies_full_20250629_204640.jsonl"  # Change if needed

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("discover_extractor")

# --- Helper: Load already-extracted IDs ---
def load_existing_ids(jsonl_path: Path) -> Set[int]:
    ids = set()
    if jsonl_path.exists():
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if "tmdb_id" in obj:
                        ids.add(int(obj["tmdb_id"]))
                except Exception:
                    continue
    logger.info(f"Loaded {len(ids)} previously extracted TMDB IDs.")
    return ids

# --- Main Extraction ---
async def main():
    start_time = time.time()
    already_ids = load_existing_ids(PREV_JSONL)
    new_movies: Dict[int, Movie] = {}
    total_fetched = 0
    genres = [None]  # Will fill with genre IDs
    years = list(range(1950, datetime.now().year + 1))
    languages = ["en"]  # Can expand

    # Get genre list from TMDB
    async with TMDBClient() as client:
        genre_list = await client._make_request("genre/movie/list", {})
        if genre_list and "genres" in genre_list:
            genres = [g["id"] for g in genre_list["genres"]]
        logger.info(f"Using {len(genres)} genres for discover extraction.")

    # Extraction loop
    async with TMDBClient() as client:
        for year in tqdm(years, desc="Years"):
            for genre_id in genres:
                for lang in languages:
                    page = 1
                    while True:
                        if (time.time() - start_time) > MAX_HOURS * 3600:
                            logger.info("⏰ Time limit reached. Stopping extraction.")
                            break
                        if len(new_movies) >= TARGET_MOVIES:
                            logger.info("🎯 Target reached. Stopping extraction.")
                            break
                        params = {"year": year, "with_genres": genre_id, "language": lang, "page": page}
                        # Remove None genre
                        if genre_id is None:
                            params.pop("with_genres")
                        try:
                            data = await client._make_request("discover/movie", params)
                            results = data.get("results", [])
                            if not results:
                                break
                            for movie in results:
                                tmdb_id = movie.get("id")
                                if not tmdb_id or tmdb_id in already_ids or tmdb_id in new_movies:
                                    continue
                                # Fetch full details with reviews
                                try:
                                    full_movie = await client.get_movie(tmdb_id, include_credits=True, include_reviews=True)
                                    if full_movie:
                                        new_movies[tmdb_id] = full_movie
                                        total_fetched += 1
                                        if total_fetched % SAVE_EVERY == 0:
                                            save_progress(new_movies, year, genre_id, lang)
                                            logger.info(f"Progress: {total_fetched} unique movies fetched. ETA: {estimate_eta(start_time, total_fetched, TARGET_MOVIES)})")
                                        if len(new_movies) >= TARGET_MOVIES:
                                            break
                                except Exception as e:
                                    logger.warning(f"Failed to fetch details for {tmdb_id}: {e}")
                            if len(new_movies) >= TARGET_MOVIES:
                                break
                            page += 1
                        except Exception as e:
                            logger.warning(f"Failed to fetch discover page {page} for year {year}, genre {genre_id}, lang {lang}: {e}")
                            break
                if (time.time() - start_time) > MAX_HOURS * 3600 or len(new_movies) >= TARGET_MOVIES:
                    break
            if (time.time() - start_time) > MAX_HOURS * 3600 or len(new_movies) >= TARGET_MOVIES:
                break
    # Final save
    save_progress(new_movies, "final", "final", "final")
    logger.info(f"✅ Extraction complete! {len(new_movies)} new unique movies fetched.")

def save_progress(movies: Dict[int, Movie], year, genre, lang):
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"tmdb_movies_discover_{dt}_y{year}_g{genre}_l{lang}"
    jsonl_path = RAW_DIR / f"{base}.jsonl"
    csv_path = RAW_DIR / f"{base}.csv"
    # Save JSONL
    with open(jsonl_path, "w") as f:
        for m in movies.values():
            f.write(json.dumps(m.to_dict(), ensure_ascii=False) + "\n")
    # Save CSV
    df = pd.DataFrame([m.to_dict() for m in movies.values()])
    df.to_csv(csv_path, index=False)
    logger.info(f"Progress saved: {jsonl_path}, {csv_path}")

def estimate_eta(start_time, fetched, target):
    elapsed = time.time() - start_time
    if fetched == 0:
        return "Unknown"
    rate = elapsed / fetched
    remaining = target - fetched
    eta = remaining * rate
    return str(timedelta(seconds=int(eta)))

if __name__ == "__main__":
    asyncio.run(main()) 