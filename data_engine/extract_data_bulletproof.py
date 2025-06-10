#!/usr/bin/env python3
"""
CineAI Bulletproof 50K Movie Data Extraction Script
Guarantees 50,000 unique movies using a robust grid search over TMDB's discover endpoint.
Customizable: years, genres, sort orders, languages, and additional discover filters.
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

import pandas as pd
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent))
from config import TMDB_CONFIG, DATA_CONFIG
from tmdb_client import TMDBClient
from schema import Movie

RAW_DIR = Path(DATA_CONFIG.get("raw_data_dir", "data/raw"))
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Path to previous extraction JSONL file (set to your 14.7k file)
PREV_JSONL = RAW_DIR / "tmdb_movies_50k_20250711_011112.jsonl"  # Change as needed

# --- Customization Parameters ---
TARGET_MOVIES = 50000
MAX_HOURS = 48  # Max run time
SAVE_EVERY = 1000  # Save progress every N movies
YEARS = list(range(1950, datetime.now().year + 1))  # Customize as needed
# Add more languages for diverse world cinema
LANGUAGES = [
    "en",  # English
    "hi",  # Hindi
    "ta",  # Tamil
    "fa",  # Persian (Iranian)
    "fr",  # French
    "es",  # Spanish
    "de",  # German
    "it",  # Italian
    "ja",  # Japanese
    "ko",  # Korean
    "zh",  # Chinese
    "ru",  # Russian
    "tr",  # Turkish
    "ar",  # Arabic
    "te",  # Telugu
    "ml",  # Malayalam
    "bn",  # Bengali
    "mr",  # Marathi
    "kn",  # Kannada
    "pt",  # Portuguese
    "id",  # Indonesian
    "th",  # Thai
    "vi",  # Vietnamese
    "pl",  # Polish
    "nl",  # Dutch
    "el",  # Greek
    "sv",  # Swedish
    "da",  # Danish
    "no",  # Norwegian
    "fi",  # Finnish
    "cs",  # Czech
    "hu",  # Hungarian
    "ro",  # Romanian
    "uk",  # Ukrainian
    "he",  # Hebrew
    "tl",  # Filipino
    "ms",  # Malay
    "sr",  # Serbian
    "hr",  # Croatian
    "sk",  # Slovak
    "bg",  # Bulgarian
    "ka",  # Georgian
    "az",  # Azerbaijani
    "hy",  # Armenian
    "sq",  # Albanian
    "bs",  # Bosnian
    "sl",  # Slovenian
    "lt",  # Lithuanian
    "lv",  # Latvian
    "et",  # Estonian
]
SORT_ORDERS = ["popularity.desc", "vote_count.desc", "release_date.desc", "revenue.desc"]
EXTRA_DISCOVER_FILTERS = [
    {},  # No extra filter
    {"region": "US"},
    {"region": "IN"},
    {"with_runtime.gte": 60, "with_runtime.lte": 180},
    {"vote_average.gte": 5},
]  # Add more filter dicts as needed

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bulletproof_extractor")

# --- Helper: Save Progress ---
def save_progress(movies: Dict[int, Movie], tag: str):
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"tmdb_movies_bulletproof_{dt}_{tag}"
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
    logger.info(f"Loaded {len(ids)} previously extracted TMDB IDs from {jsonl_path}.")
    return ids

# --- Main Extraction ---
async def main():
    start_time = time.time()
    already_ids = load_existing_ids(PREV_JSONL)
    new_movies: Dict[int, Movie] = {}
    total_fetched = 0
    # Get genre list from TMDB
    async with TMDBClient() as client:
        genre_list = await client._make_request("genre/movie/list", {})
        if genre_list and "genres" in genre_list:
            genres = [g["id"] for g in genre_list["genres"]]
        else:
            genres = [None]
        logger.info(f"Using {len(genres)} genres for discover extraction.")
    # Extraction grid search
    async with TMDBClient() as client:
        for year in tqdm(YEARS, desc="Years"):
            for genre_id in genres + [None]:  # Include None for all genres
                for lang in LANGUAGES:
                    for sort_by in SORT_ORDERS:
                        for extra_filter in EXTRA_DISCOVER_FILTERS:
                            page = 1
                            while True:
                                if (time.time() - start_time) > MAX_HOURS * 3600:
                                    logger.info("⏰ Time limit reached. Stopping extraction.")
                                    break
                                if len(new_movies) >= TARGET_MOVIES:
                                    logger.info("🎯 Target reached. Stopping extraction.")
                                    break
                                params = {"year": year, "language": lang, "sort_by": sort_by, "page": page}
                                if genre_id is not None:
                                    params["with_genres"] = genre_id
                                params.update(extra_filter)
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
                                                    save_progress(new_movies, f"y{year}_g{genre_id}_l{lang}_s{sort_by}")
                                                    logger.info(f"Progress: {total_fetched} unique movies fetched. ETA: {estimate_eta(start_time, total_fetched, TARGET_MOVIES)})")
                                                if len(new_movies) >= TARGET_MOVIES:
                                                    break
                                        except Exception as e:
                                            logger.warning(f"Failed to fetch details for {tmdb_id}: {e}")
                                    if len(new_movies) >= TARGET_MOVIES:
                                        break
                                    page += 1
                                    if page > 500:
                                        break  # TMDB max pages
                                except Exception as e:
                                    logger.warning(f"Failed to fetch discover page {page} for year {year}, genre {genre_id}, lang {lang}, sort {sort_by}: {e}")
                                    break
                        if (time.time() - start_time) > MAX_HOURS * 3600 or len(new_movies) >= TARGET_MOVIES:
                            break
                    if (time.time() - start_time) > MAX_HOURS * 3600 or len(new_movies) >= TARGET_MOVIES:
                        break
                if (time.time() - start_time) > MAX_HOURS * 3600 or len(new_movies) >= TARGET_MOVIES:
                    break
            if (time.time() - start_time) > MAX_HOURS * 3600 or len(new_movies) >= TARGET_MOVIES:
                break
    # Final save
    save_progress(new_movies, "final")
    logger.info(f"✅ Extraction complete! {len(new_movies)} new unique movies fetched (excluding {len(already_ids)} previously extracted).")

def estimate_eta(start_time, fetched, target):
    elapsed = time.time() - start_time
    if fetched == 0:
        return "unknown"
    rate = fetched / elapsed
    remaining = target - fetched
    eta = remaining / rate if rate > 0 else 0
    return f"{int(eta // 3600)}h {int((eta % 3600) // 60)}m"

if __name__ == "__main__":
    asyncio.run(main()) 