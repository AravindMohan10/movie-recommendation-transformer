#!/usr/bin/env python3
"""
CineAI Smart Data Extraction Script
Efficiently extracts high-quality movie data for recommendation engines.
Focuses on quality over quantity with smart sampling strategies.
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Smart extraction parameters
TARGET_MOVIES = 30000  # Quality over quantity
PROGRESS_SAVE_INTERVAL = 100  # Save every 100 movies
RATE_LIMIT_DELAY = 1.1  # Slight delay to respect rate limits

# Path to previous extraction (if any)
PREV_JSONL = RAW_DIR / "tmdb_movies_50k_20250711_011112.jsonl"  # Your existing 14.7K

class SmartDataExtractor:
    """Smart data extractor that focuses on quality and efficiency."""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = RAW_DIR / f"tmdb_movies_smart_{self.timestamp}.jsonl"
        self.progress_file = RAW_DIR / f"extraction_progress_{self.timestamp}.json"
        self.existing_ids = self._load_existing_ids()
        
    def _load_existing_ids(self) -> Set[int]:
        """Load IDs from previous extraction to avoid duplicates."""
        ids = set()
        if PREV_JSONL.exists():
            logger.info(f"Loading existing IDs from {PREV_JSONL}")
            with open(PREV_JSONL, 'r') as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                        if "tmdb_id" in obj:
                            ids.add(int(obj["tmdb_id"]))
                    except:
                        continue
            logger.info(f"Loaded {len(ids)} existing movie IDs")
        return ids
    
    async def extract_smart_dataset(self) -> Dict[str, Any]:
        """Extract high-quality movie dataset using smart strategies."""
        logger.info(f"🚀 Starting Smart Data Extraction (Target: {TARGET_MOVIES:,} movies)")
        logger.info(f"📁 Output: {self.output_file}")
        
        client = TMDBClient()
        collected_movies = []
        start_time = time.time()
        
        # Strategy 1: High-quality popular movies (well-rated, good vote counts)
        logger.info("📊 Strategy 1: High-quality popular movies...")
        popular_movies = await self._get_quality_popular_movies(client, max_movies=8000)
        collected_movies.extend(popular_movies)
        await self._save_progress(collected_movies, "popular")
        
        # Strategy 2: Critically acclaimed movies (high ratings)
        logger.info("🏆 Strategy 2: Critically acclaimed movies...")
        acclaimed_movies = await self._get_critically_acclaimed_movies(client, max_movies=8000)
        collected_movies.extend(acclaimed_movies)
        await self._save_progress(collected_movies, "acclaimed")
        
        # Strategy 3: Diverse genre representation
        logger.info("🎭 Strategy 3: Diverse genre movies...")
        genre_movies = await self._get_diverse_genre_movies(client, max_movies=8000)
        collected_movies.extend(genre_movies)
        await self._save_progress(collected_movies, "genres")
        
        # Strategy 4: Recent and upcoming movies
        logger.info("🎬 Strategy 4: Recent and upcoming movies...")
        recent_movies = await self._get_recent_movies(client, max_movies=3000)
        collected_movies.extend(recent_movies)
        await self._save_progress(collected_movies, "recent")
        
        # Strategy 5: International cinema (non-English)
        logger.info("🌍 Strategy 5: International cinema...")
        international_movies = await self._get_international_movies(client, max_movies=3000)
        collected_movies.extend(international_movies)
        await self._save_progress(collected_movies, "international")
        
        # Final save
        await self._save_final_dataset(collected_movies)
        
        elapsed_time = time.time() - start_time
        return {
            "total_movies": len(collected_movies),
            "elapsed_time_hours": elapsed_time / 3600,
            "output_file": str(self.output_file),
            "quality_metrics": self._calculate_quality_metrics(collected_movies)
        }
    
    async def _get_quality_popular_movies(self, client: TMDBClient, max_movies: int) -> List[Movie]:
        """Get popular movies with quality filters."""
        movies = []
        page = 1
        
        with tqdm(total=max_movies, desc="Popular movies") as pbar:
            while len(movies) < max_movies and page <= 400:  # 400 pages = 8000 movies
                try:
                    page_movies = await client.get_popular_movies(page=page)
                    if not page_movies:
                        break
                    
                    # Filter for quality
                    quality_movies = [
                        m for m in page_movies 
                        if m.vote_count >= 100 and m.vote_average >= 6.0
                        and m.id not in self.existing_ids
                    ]
                    
                    # Get full details for quality movies
                    for movie in quality_movies:
                        if len(movies) >= max_movies:
                            break
                        
                        try:
                            full_movie = await client.get_movie_details(
                                movie.id, 
                                include_credits=True, 
                                include_reviews=True
                            )
                            if full_movie:
                                movies.append(full_movie)
                                self.existing_ids.add(movie.id)
                                pbar.update(1)
                                
                                # Save progress periodically
                                if len(movies) % PROGRESS_SAVE_INTERVAL == 0:
                                    await self._save_progress(movies, "popular")
                                
                        except Exception as e:
                            logger.warning(f"Error fetching movie {movie.id}: {e}")
                            continue
                        
                        await asyncio.sleep(RATE_LIMIT_DELAY)
                    
                    page += 1
                    
                except Exception as e:
                    logger.warning(f"Error fetching popular page {page}: {e}")
                    break
        
        logger.info(f"✅ Collected {len(movies)} quality popular movies")
        return movies
    
    async def _get_critically_acclaimed_movies(self, client: TMDBClient, max_movies: int) -> List[Movie]:
        """Get critically acclaimed movies (high ratings)."""
        movies = []
        page = 1
        
        with tqdm(total=max_movies, desc="Critically acclaimed") as pbar:
            while len(movies) < max_movies and page <= 400:
                try:
                    page_movies = await client.get_top_rated_movies(page=page)
                    if not page_movies:
                        break
                    
                    # Filter for high quality
                    quality_movies = [
                        m for m in page_movies 
                        if m.vote_count >= 200 and m.vote_average >= 7.0
                        and m.id not in self.existing_ids
                    ]
                    
                    for movie in quality_movies:
                        if len(movies) >= max_movies:
                            break
                        
                        try:
                            full_movie = await client.get_movie_details(
                                movie.id, 
                                include_credits=True, 
                                include_reviews=True
                            )
                            if full_movie:
                                movies.append(full_movie)
                                self.existing_ids.add(movie.id)
                                pbar.update(1)
                                
                                if len(movies) % PROGRESS_SAVE_INTERVAL == 0:
                                    await self._save_progress(movies, "acclaimed")
                                
                        except Exception as e:
                            logger.warning(f"Error fetching movie {movie.id}: {e}")
                            continue
                        
                        await asyncio.sleep(RATE_LIMIT_DELAY)
                    
                    page += 1
                    
                except Exception as e:
                    logger.warning(f"Error fetching top-rated page {page}: {e}")
                    break
        
        logger.info(f"✅ Collected {len(movies)} critically acclaimed movies")
        return movies
    
    async def _get_diverse_genre_movies(self, client: TMDBClient, max_movies: int) -> List[Movie]:
        """Get diverse movies across different genres."""
        movies = []
        
        # Key genres for diversity
        genres = [
            {"id": 28, "name": "Action"},
            {"id": 35, "name": "Comedy"},
            {"id": 18, "name": "Drama"},
            {"id": 27, "name": "Horror"},
            {"id": 53, "name": "Thriller"},
            {"id": 10749, "name": "Romance"},
            {"id": 878, "name": "Science Fiction"},
            {"id": 12, "name": "Adventure"},
            {"id": 16, "name": "Animation"},
            {"id": 80, "name": "Crime"},
            {"id": 99, "name": "Documentary"},
            {"id": 10751, "name": "Family"},
            {"id": 14, "name": "Fantasy"},
            {"id": 36, "name": "History"},
            {"id": 10402, "name": "Music"},
            {"id": 9648, "name": "Mystery"},
            {"id": 10752, "name": "War"},
            {"id": 37, "name": "Western"}
        ]
        
        movies_per_genre = max_movies // len(genres)
        
        for genre in genres:
            if len(movies) >= max_movies:
                break
                
            logger.info(f"🎭 Fetching {genre['name']} movies...")
            genre_movies = await self._get_movies_by_genre(
                client, genre["id"], genre["name"], movies_per_genre
            )
            movies.extend(genre_movies)
            
            await self._save_progress(movies, f"genre_{genre['name']}")
        
        logger.info(f"✅ Collected {len(movies)} diverse genre movies")
        return movies
    
    async def _get_movies_by_genre(self, client: TMDBClient, genre_id: int, genre_name: str, max_movies: int) -> List[Movie]:
        """Get movies by specific genre using discover endpoint."""
        movies = []
        page = 1
        
        with tqdm(total=max_movies, desc=f"{genre_name} movies") as pbar:
            while len(movies) < max_movies and page <= 100:
                try:
                    # Use discover endpoint with genre filter
                    discover_params = {
                        "with_genres": genre_id,
                        "sort_by": "popularity.desc",
                        "page": page,
                        "vote_count.gte": 50,
                        "vote_average.gte": 5.5
                    }
                    
                    page_movies = await client.discover_movies(discover_params)
                    if not page_movies:
                        break
                    
                    for movie in page_movies:
                        if len(movies) >= max_movies:
                            break
                        
                        if movie.id not in self.existing_ids:
                            try:
                                full_movie = await client.get_movie_details(
                                    movie.id, 
                                    include_credits=True, 
                                    include_reviews=True
                                )
                                if full_movie:
                                    movies.append(full_movie)
                                    self.existing_ids.add(movie.id)
                                    pbar.update(1)
                                    
                            except Exception as e:
                                logger.warning(f"Error fetching movie {movie.id}: {e}")
                                continue
                            
                            await asyncio.sleep(RATE_LIMIT_DELAY)
                    
                    page += 1
                    
                except Exception as e:
                    logger.warning(f"Error fetching {genre_name} page {page}: {e}")
                    break
        
        return movies
    
    async def _get_recent_movies(self, client: TMDBClient, max_movies: int) -> List[Movie]:
        """Get recent and upcoming movies."""
        movies = []
        
        # Get now playing
        try:
            now_playing = await client.get_now_playing_movies()
            for movie in now_playing[:max_movies//2]:
                if movie.id not in self.existing_ids:
                    try:
                        full_movie = await client.get_movie_details(
                            movie.id, 
                            include_credits=True, 
                            include_reviews=True
                        )
                        if full_movie:
                            movies.append(full_movie)
                            self.existing_ids.add(movie.id)
                    except:
                        continue
                    await asyncio.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            logger.warning(f"Error fetching now playing: {e}")
        
        # Get upcoming
        try:
            upcoming = await client.get_upcoming_movies()
            for movie in upcoming[:max_movies//2]:
                if movie.id not in self.existing_ids and len(movies) < max_movies:
                    try:
                        full_movie = await client.get_movie_details(
                            movie.id, 
                            include_credits=True, 
                            include_reviews=True
                        )
                        if full_movie:
                            movies.append(full_movie)
                            self.existing_ids.add(movie.id)
                    except:
                        continue
                    await asyncio.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            logger.warning(f"Error fetching upcoming: {e}")
        
        logger.info(f"✅ Collected {len(movies)} recent/upcoming movies")
        return movies
    
    async def _get_international_movies(self, client: TMDBClient, max_movies: int) -> List[Movie]:
        """Get international movies (non-English)."""
        movies = []
        
        # Languages for international cinema
        languages = ["fr", "es", "de", "it", "ja", "ko", "zh", "hi", "ta", "fa", "ru", "pt"]
        
        movies_per_lang = max_movies // len(languages)
        
        for lang in languages:
            if len(movies) >= max_movies:
                break
                
            logger.info(f"🌍 Fetching {lang} language movies...")
            lang_movies = await self._get_movies_by_language(
                client, lang, movies_per_lang
            )
            movies.extend(lang_movies)
        
        logger.info(f"✅ Collected {len(movies)} international movies")
        return movies
    
    async def _get_movies_by_language(self, client: TMDBClient, language: str, max_movies: int) -> List[Movie]:
        """Get movies by specific language."""
        movies = []
        page = 1
        
        with tqdm(total=max_movies, desc=f"{language} movies") as pbar:
            while len(movies) < max_movies and page <= 50:
                try:
                    discover_params = {
                        "with_original_language": language,
                        "sort_by": "popularity.desc",
                        "page": page,
                        "vote_count.gte": 30,
                        "vote_average.gte": 5.0
                    }
                    
                    page_movies = await client.discover_movies(discover_params)
                    if not page_movies:
                        break
                    
                    for movie in page_movies:
                        if len(movies) >= max_movies:
                            break
                        
                        if movie.id not in self.existing_ids:
                            try:
                                full_movie = await client.get_movie_details(
                                    movie.id, 
                                    include_credits=True, 
                                    include_reviews=True
                                )
                                if full_movie:
                                    movies.append(full_movie)
                                    self.existing_ids.add(movie.id)
                                    pbar.update(1)
                                    
                            except Exception as e:
                                logger.warning(f"Error fetching movie {movie.id}: {e}")
                                continue
                            
                            await asyncio.sleep(RATE_LIMIT_DELAY)
                    
                    page += 1
                    
                except Exception as e:
                    logger.warning(f"Error fetching {language} page {page}: {e}")
                    break
        
        return movies
    
    async def _save_progress(self, movies: List[Movie], stage: str):
        """Save progress to file."""
        if not movies:
            return
            
        progress_data = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "total_movies": len(movies),
            "last_movie_id": movies[-1].id if movies else None
        }
        
        with open(self.progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
        
        logger.info(f"💾 Progress saved: {len(movies)} movies ({stage})")
    
    async def _save_final_dataset(self, movies: List[Movie]):
        """Save final dataset to files."""
        logger.info(f"💾 Saving final dataset: {len(movies)} movies...")
        
        # Save as JSONL
        with open(self.output_file, 'w', encoding='utf-8') as f:
            for movie in tqdm(movies, desc="Saving JSONL"):
                movie_dict = self._movie_to_dict(movie)
                f.write(json.dumps(movie_dict, ensure_ascii=False, default=str) + '\n')
        
        # Save as CSV
        csv_file = self.output_file.with_suffix('.csv')
        movies_dict = [self._movie_to_dict(m) for m in movies]
        df = self._flatten_movies_data(movies_dict)
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        # Save metadata
        metadata = {
            "timestamp": self.timestamp,
            "total_movies": len(movies),
            "files_created": [str(self.output_file), str(csv_file)],
            "quality_metrics": self._calculate_quality_metrics(movies),
            "extraction_strategy": "smart_quality_focused"
        }
        
        metadata_file = RAW_DIR / f"smart_extraction_metadata_{self.timestamp}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"✅ Dataset saved successfully!")
        logger.info(f"   JSONL: {self.output_file}")
        logger.info(f"   CSV: {csv_file}")
        logger.info(f"   Metadata: {metadata_file}")
    
    def _movie_to_dict(self, movie: Movie) -> Dict[str, Any]:
        """Convert Movie object to dictionary."""
        return {
            "tmdb_id": movie.id,
            "imdb_id": movie.imdb_id,
            "title": movie.title,
            "original_title": movie.original_title,
            "overview": movie.overview,
            "tagline": movie.tagline,
            "release_date": movie.release_date,
            "runtime": movie.runtime,
            "budget": movie.budget,
            "revenue": movie.revenue,
            "popularity": movie.popularity,
            "vote_average": movie.vote_average,
            "vote_count": movie.vote_count,
            "adult": movie.adult,
            "video": movie.video,
            "status": movie.status,
            "genres": [{"id": g.value, "name": g.name} for g in movie.genres],
            "production_companies": [{"id": c.id, "name": c.name, "logo_path": c.logo_path, "origin_country": c.origin_country} for c in movie.production_companies],
            "production_countries": [{"iso_3166_1": c.iso_3166_1, "name": c.name} for c in movie.production_countries],
            "spoken_languages": [{"iso_639_1": l.iso_639_1, "name": l.name} for l in movie.spoken_languages],
            "cast": [{"id": c.person.id, "name": c.person.name, "character": c.character, "order": c.order} for c in movie.cast],
            "crew": [{"id": c.person.id, "name": c.person.name, "job": c.job, "department": c.department} for c in movie.crew],
            "poster_path": movie.poster_path,
            "backdrop_path": movie.backdrop_path,
            "homepage": movie.homepage,
            "reviews": [
                {
                    "id": r.id,
                    "author": r.author,
                    "content": r.content,
                    "url": r.url,
                    "rating": r.rating,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at
                } for r in getattr(movie, "reviews", [])
            ]
        }
    
    def _flatten_movies_data(self, movies_dict: List[Dict[str, Any]]) -> pd.DataFrame:
        """Flatten movies data for CSV export."""
        flattened_data = []
        
        for movie in tqdm(movies_dict, desc="Flattening data"):
            flat_movie = {
                "tmdb_id": movie["tmdb_id"],
                "imdb_id": movie["imdb_id"],
                "title": movie["title"],
                "original_title": movie["original_title"],
                "overview": movie["overview"],
                "tagline": movie["tagline"],
                "release_date": movie["release_date"],
                "runtime": movie["runtime"],
                "budget": movie["budget"],
                "revenue": movie["revenue"],
                "popularity": movie["popularity"],
                "vote_average": movie["vote_average"],
                "vote_count": movie["vote_count"],
                "adult": movie["adult"],
                "video": movie["video"],
                "status": movie["status"],
                "poster_path": movie["poster_path"],
                "backdrop_path": movie["backdrop_path"],
                "homepage": movie["homepage"]
            }
            
            # Flatten genres
            genres = [g["name"] for g in movie["genres"]]
            flat_movie["genres"] = "|".join(genres)
            flat_movie["genre_ids"] = "|".join([str(g["id"]) for g in movie["genres"]])
            
            # Flatten production companies
            companies = [c["name"] for c in movie["production_companies"]]
            flat_movie["production_companies"] = "|".join(companies)
            
            # Flatten countries
            countries = [c["name"] for c in movie["production_countries"]]
            flat_movie["production_countries"] = "|".join(countries)
            
            # Flatten languages
            languages = [l["name"] for l in movie["spoken_languages"]]
            flat_movie["spoken_languages"] = "|".join(languages)
            
            # Flatten cast (top 10)
            cast = [c["name"] for c in movie["cast"][:10]]
            flat_movie["cast"] = "|".join(cast)
            
            # Flatten crew (directors, writers)
            directors = [c["name"] for c in movie["crew"] if c["job"] in ["Director", "Co-Director"]]
            writers = [c["name"] for c in movie["crew"] if c["job"] in ["Writer", "Screenplay", "Story"]]
            flat_movie["directors"] = "|".join(directors)
            flat_movie["writers"] = "|".join(writers)
            
            flattened_data.append(flat_movie)
        
        return pd.DataFrame(flattened_data)
    
    def _calculate_quality_metrics(self, movies: List[Movie]) -> Dict[str, Any]:
        """Calculate quality metrics for the dataset."""
        if not movies:
            return {}
        
        vote_averages = [m.vote_average for m in movies if m.vote_average > 0]
        vote_counts = [m.vote_count for m in movies if m.vote_count > 0]
        runtimes = [m.runtime for m in movies if m.runtime and m.runtime > 0]
        
        movies_with_reviews = sum(1 for m in movies if hasattr(m, 'reviews') and m.reviews)
        movies_with_overview = sum(1 for m in movies if m.overview and len(m.overview.strip()) > 0)
        
        return {
            "total_movies": len(movies),
            "avg_vote_average": sum(vote_averages) / len(vote_averages) if vote_averages else 0,
            "avg_vote_count": sum(vote_counts) / len(vote_counts) if vote_counts else 0,
            "avg_runtime": sum(runtimes) / len(runtimes) if runtimes else 0,
            "movies_with_reviews": movies_with_reviews,
            "movies_with_overview": movies_with_overview,
            "review_coverage": movies_with_reviews / len(movies) if movies else 0,
            "overview_coverage": movies_with_overview / len(movies) if movies else 0
        }


async def main():
    """Main extraction function."""
    logger.info("🚀 Starting CineAI Smart Data Extraction...")
    
    # Check if TMDB API key is set
    if not TMDB_CONFIG["api_key"]:
        logger.error("❌ TMDB_API_KEY environment variable is not set!")
        logger.info("Please set your TMDB API key:")
        logger.info("export TMDB_API_KEY='your_api_key_here'")
        return
    
    extractor = SmartDataExtractor()
    
    try:
        # Extract smart dataset
        result = await extractor.extract_smart_dataset()
        
        logger.info("✅ Smart data extraction completed successfully!")
        logger.info(f"📊 Extracted {result['total_movies']:,} high-quality movies")
        logger.info(f"⏱️  Time taken: {result['elapsed_time_hours']:.1f} hours")
        logger.info(f"📁 Output: {result['output_file']}")
        
        # Quality metrics
        metrics = result['quality_metrics']
        logger.info(f"🎯 Quality Metrics:")
        logger.info(f"   Average Rating: {metrics['avg_vote_average']:.2f}")
        logger.info(f"   Average Vote Count: {metrics['avg_vote_count']:.0f}")
        logger.info(f"   Movies with Reviews: {metrics['movies_with_reviews']:,}")
        logger.info(f"   Review Coverage: {metrics['review_coverage']:.1%}")
        
    except Exception as e:
        logger.error(f"❌ Smart data extraction failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 