#!/usr/bin/env python3
"""
CineAI 50K Movie Data Extraction Script
Uses multiple TMDB API endpoints to extract 50,000 movies with complete data.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
from tqdm import tqdm

# Add the data_engine directory to the path
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


class MultiSourceDataExtractor:
    """Data extractor using multiple TMDB API endpoints to get 50K movies."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("data/raw")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    async def extract_50k_dataset(self, 
                                target_movies: int = 50000,
                                include_credits: bool = True,
                                include_reviews: bool = True,
                                include_videos: bool = False,
                                include_images: bool = False) -> Dict[str, Any]:
        """
        Extract 50K movies using multiple TMDB API endpoints.
        
        Args:
            target_movies: Target number of movies (default: 50K)
            include_credits: Include cast and crew data
            include_reviews: Include movie reviews
            include_videos: Include video data
            include_images: Include image data
        """
        logger.info(f"Starting 50K movie extraction using multiple sources...")
        
        client = TMDBClient()
        
        # Get movie IDs from multiple sources
        all_movie_ids = set()
        
        # Strategy 1: Popular movies (extended pages)
        logger.info("Strategy 1: Popular movies (extended pages)...")
        popular_ids = await self._get_extended_popular_movies(client, max_movies=15000)
        all_movie_ids.update(popular_ids)
        logger.info(f"Added {len(popular_ids)} popular movies")
        
        # Strategy 2: Top-rated movies (extended pages)
        logger.info("Strategy 2: Top-rated movies (extended pages)...")
        top_rated_ids = await self._get_extended_top_rated_movies(client, max_movies=15000)
        all_movie_ids.update(top_rated_ids)
        logger.info(f"Added {len(top_rated_ids)} top-rated movies")
        
        # Strategy 3: Now playing movies
        logger.info("Strategy 3: Now playing movies...")
        now_playing_ids = await self._get_now_playing_movies(client, max_movies=2000)
        all_movie_ids.update(now_playing_ids)
        logger.info(f"Added {len(now_playing_ids)} now-playing movies")
        
        # Strategy 4: Upcoming movies
        logger.info("Strategy 4: Upcoming movies...")
        upcoming_ids = await self._get_upcoming_movies(client, max_movies=2000)
        all_movie_ids.update(upcoming_ids)
        logger.info(f"Added {len(upcoming_ids)} upcoming movies")
        
        # Strategy 5: Movies by popular genres
        logger.info("Strategy 5: Movies by popular genres...")
        genre_ids = await self._get_movies_by_popular_genres(client, max_movies=16000)
        all_movie_ids.update(genre_ids)
        logger.info(f"Added {len(genre_ids)} genre-based movies")
        
        # Convert to list and limit to target
        movie_ids = list(all_movie_ids)[:target_movies]
        logger.info(f"Total unique movies to fetch: {len(movie_ids):,}")
        
        # Fetch detailed movie data
        movies_data = await self._fetch_movies_batch(
            client, movie_ids, include_credits, include_reviews, 
            include_videos, include_images
        )
        
        # Save data
        self._save_movies_data(movies_data)
        
        return {
            "total_movies": len(movies_data),
            "files_created": self._get_created_files(),
            "extraction_config": {
                "target_movies": target_movies,
                "include_credits": include_credits,
                "include_reviews": include_reviews,
                "include_videos": include_videos,
                "include_images": include_images
            }
        }
    
    async def _get_extended_popular_movies(self, client: TMDBClient, max_movies: int) -> List[int]:
        """Get popular movies from many pages."""
        movie_ids = []
        page = 1
        max_pages = max_movies // 20  # 20 movies per page
        
        with tqdm(total=max_movies, desc="Popular movies") as pbar:
            while len(movie_ids) < max_movies and page <= max_pages:
                try:
                    movies = await client.get_popular_movies(page=page)
                    if not movies:
                        break
                    
                    page_ids = [movie.id for movie in movies]
                    movie_ids.extend(page_ids)
                    pbar.update(len(page_ids))
                    page += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error fetching popular movies page {page}: {e}")
                    break
        
        return movie_ids[:max_movies]
    
    async def _get_extended_top_rated_movies(self, client: TMDBClient, max_movies: int) -> List[int]:
        """Get top-rated movies from many pages."""
        movie_ids = []
        page = 1
        max_pages = max_movies // 20  # 20 movies per page
        
        with tqdm(total=max_movies, desc="Top-rated movies") as pbar:
            while len(movie_ids) < max_movies and page <= max_pages:
                try:
                    movies = await client.get_top_rated_movies(page=page)
                    if not movies:
                        break
                    
                    page_ids = [movie.id for movie in movies]
                    movie_ids.extend(page_ids)
                    pbar.update(len(page_ids))
                    page += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error fetching top-rated movies page {page}: {e}")
                    break
        
        return movie_ids[:max_movies]
    
    async def _get_now_playing_movies(self, client: TMDBClient, max_movies: int) -> List[int]:
        """Get now playing movies."""
        try:
            movies = await client.get_now_playing_movies()
            return [movie.id for movie in movies[:max_movies]]
        except Exception as e:
            logger.warning(f"Error fetching now-playing movies: {e}")
            return []
    
    async def _get_upcoming_movies(self, client: TMDBClient, max_movies: int) -> List[int]:
        """Get upcoming movies."""
        try:
            movies = await client.get_upcoming_movies()
            return [movie.id for movie in movies[:max_movies]]
        except Exception as e:
            logger.warning(f"Error fetching upcoming movies: {e}")
            return []
    
    async def _get_movies_by_popular_genres(self, client: TMDBClient, max_movies: int) -> List[int]:
        """Get movies by popular genres."""
        movie_ids = []
        
        # Popular genres: Action, Comedy, Drama, Horror, Thriller, Romance, Sci-Fi, Adventure
        genres = [28, 35, 18, 27, 53, 10749, 878, 12]
        movies_per_genre = max_movies // len(genres)
        
        for genre_id in genres:
            genre_ids = []
            page = 1
            max_pages = movies_per_genre // 20
            
            with tqdm(total=movies_per_genre, desc=f"Genre {genre_id}") as pbar:
                while len(genre_ids) < movies_per_genre and page <= max_pages:
                    try:
                        movies = await client.get_movies_by_genre(genre_id, page=page)
                        if not movies:
                            break
                        
                        page_ids = [movie.id for movie in movies]
                        genre_ids.extend(page_ids)
                        pbar.update(len(page_ids))
                        page += 1
                        
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.warning(f"Error fetching genre {genre_id} page {page}: {e}")
                        break
            
            movie_ids.extend(genre_ids[:movies_per_genre])
        
        return movie_ids[:max_movies]
    
    async def _fetch_movies_batch(self, client: TMDBClient, movie_ids: List[int],
                                include_credits: bool, include_reviews: bool,
                                include_videos: bool, include_images: bool) -> List[Movie]:
        """Fetch detailed data for a batch of movies."""
        movies_data = []
        batch_size = DATA_CONFIG["batch_size"]
        
        with tqdm(total=len(movie_ids), desc="Fetching movie details") as pbar:
            for i in range(0, len(movie_ids), batch_size):
                batch_ids = movie_ids[i:i + batch_size]
                
                try:
                    batch_movies = await client.batch_get_movies(
                        batch_ids, 
                        max_concurrent=3,
                        include_credits=include_credits,
                        include_reviews=include_reviews,
                        include_videos=include_videos,
                        include_images=include_images
                    )
                    
                    # Filter out None values (failed requests)
                    batch_movies = [m for m in batch_movies if m is not None]
                    movies_data.extend(batch_movies)
                    
                    pbar.update(len(batch_ids))
                    pbar.set_postfix({
                        'successful': len(batch_movies),
                        'failed': len(batch_ids) - len(batch_movies),
                        'total': len(movies_data)
                    })
                    
                    # Rate limiting
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Error fetching batch {i//batch_size + 1}: {e}")
                    pbar.update(len(batch_ids))
                    continue
        
        return movies_data
    
    def _save_movies_data(self, movies_data: List[Movie]):
        """Save movies data to files."""
        logger.info(f"Saving {len(movies_data):,} movies to files...")
        
        # Convert to dictionaries
        movies_dict = []
        movies_with_reviews = 0
        for movie in tqdm(movies_data, desc="Converting to dict"):
            d = self._movie_to_dict(movie)
            if d["reviews"]:
                movies_with_reviews += 1
            movies_dict.append(d)
        
        # Save as JSONL
        jsonl_file = self.output_dir / f"tmdb_movies_50k_{self.timestamp}.jsonl"
        logger.info(f"Saving to {jsonl_file}...")
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for movie in tqdm(movies_dict, desc="Writing JSONL"):
                f.write(json.dumps(movie, ensure_ascii=False, default=str) + '\n')
        
        # Save as CSV (flattened)
        csv_file = self.output_dir / f"tmdb_movies_50k_{self.timestamp}.csv"
        logger.info(f"Saving to {csv_file}...")
        df = self._flatten_movies_data(movies_dict)
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        # Save metadata
        metadata = {
            "timestamp": self.timestamp,
            "total_movies": len(movies_data),
            "movies_with_reviews": movies_with_reviews,
            "files_created": [str(jsonl_file), str(csv_file)],
            "extraction_config": {
                "include_credits": True,
                "include_reviews": True,
                "include_videos": False,
                "include_images": False
            }
        }
        
        metadata_file = self.output_dir / f"extraction_metadata_50k_{self.timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"✅ Data saved successfully!")
        logger.info(f"   JSONL: {jsonl_file}")
        logger.info(f"   CSV: {csv_file}")
        logger.info(f"   Metadata: {metadata_file}")
        logger.info(f"   Movies with reviews: {movies_with_reviews}/{len(movies_data)}")
    
    def _movie_to_dict(self, movie: Movie) -> Dict[str, Any]:
        """Convert Movie object to dictionary."""
        movie_dict = {
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
        return movie_dict
    
    def _flatten_movies_data(self, movies_dict: List[Dict[str, Any]]) -> pd.DataFrame:
        """Flatten movies data for CSV export."""
        flattened_data = []
        
        for movie in tqdm(movies_dict, desc="Flattening data"):
            # Basic movie info
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
    
    def _get_created_files(self) -> List[str]:
        """Get list of files created in this extraction."""
        files = []
        for file in self.output_dir.glob(f"*{self.timestamp}*"):
            files.append(str(file))
        return files


async def main():
    """Main extraction function for 50K movies."""
    logger.info("🚀 Starting CineAI 50K Movie Data Extraction...")
    
    # Check if TMDB API key is set
    if not TMDB_CONFIG["api_key"]:
        logger.error("❌ TMDB_API_KEY environment variable is not set!")
        logger.info("Please set your TMDB API key:")
        logger.info("export TMDB_API_KEY='your_api_key_here'")
        return
    
    extractor = MultiSourceDataExtractor()
    
    try:
        # Extract 50K movies using multiple sources
        result = await extractor.extract_50k_dataset(
            target_movies=50000,
            include_credits=True,
            include_reviews=True,
            include_videos=False,
            include_images=False
        )
        
        logger.info("✅ 50K movie data extraction completed successfully!")
        logger.info(f"📊 Extracted {result['total_movies']:,} movies")
        logger.info(f"📁 Files created: {result['files_created']}")
        
    except Exception as e:
        logger.error(f"❌ 50K movie data extraction failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 