"""
Data Extraction Module for CineAI

This module handles the extraction of fresh data from TMDB API and other sources.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data_engine.tmdb_client import TMDBClient
from data_engine.config import TMDB_CONFIG, DATA_CONFIG, BASE_DIR, DATA_DIR
from data_engine.schema import Movie, Person, Review

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataExtractor:
    """Main data extraction class for fetching data from various sources."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or DATA_DIR / "raw"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate TMDB API key
        if not TMDB_CONFIG["api_key"]:
            raise ValueError("TMDB_API_KEY environment variable is required")
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    async def extract_tmdb_data(self, 
                               max_movies: Optional[int] = None,
                               include_credits: bool = True,
                               include_reviews: bool = False,
                               include_videos: bool = False,
                               include_images: bool = False) -> Dict[str, Any]:
        """
        Extract comprehensive movie data from TMDB API.
        
        Args:
            max_movies: Maximum number of movies to fetch (None for all)
            include_credits: Whether to include cast and crew data
            include_reviews: Whether to include movie reviews
            include_videos: Whether to include video data (trailers, etc.)
            include_images: Whether to include image data (posters, backdrops)
        """
        logger.info("Starting TMDB data extraction...")
        
        async with TMDBClient() as client:
            # Get popular movies first
            popular_movies = await self._get_popular_movies(client, max_movies)
            
            # Get top rated movies
            top_rated_movies = await self._get_top_rated_movies(client, max_movies)
            
            # Get now playing movies
            now_playing_movies = await self._get_now_playing_movies(client, max_movies)
            
            # Combine and deduplicate
            all_movie_ids = list(set(popular_movies + top_rated_movies + now_playing_movies))
            
            if max_movies:
                all_movie_ids = all_movie_ids[:max_movies]
            
            logger.info(f"Fetching detailed data for {len(all_movie_ids)} movies...")
            
            # Fetch detailed movie data
            movies_data = await self._fetch_movies_batch(
                client, all_movie_ids, include_credits, include_reviews, 
                include_videos, include_images
            )
            
            # Save data
            self._save_movies_data(movies_data)
            
            return {
                "total_movies": len(movies_data),
                "timestamp": self.timestamp,
                "files_created": self._get_created_files()
            }
    
    async def _get_popular_movies(self, client: TMDBClient, max_movies: Optional[int] = None) -> List[int]:
        """Get popular movie IDs."""
        logger.info("Fetching popular movies...")
        movie_ids = []
        page = 1
        
        while True:
            try:
                movies = await client.get_popular_movies(page=page)
                if not movies:
                    break
                    
                movie_ids.extend([movie.id for movie in movies])
                
                if max_movies and len(movie_ids) >= max_movies:
                    movie_ids = movie_ids[:max_movies]
                    break
                    
                page += 1
                
                # Limit to first 5 pages for popular movies
                if page > 5:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching popular movies page {page}: {e}")
                break
        
        logger.info(f"Found {len(movie_ids)} popular movies")
        return movie_ids
    
    async def _get_top_rated_movies(self, client: TMDBClient, max_movies: Optional[int] = None) -> List[int]:
        """Get top rated movie IDs."""
        logger.info("Fetching top rated movies...")
        movie_ids = []
        page = 1
        
        while True:
            try:
                movies = await client.get_top_rated_movies(page=page)
                if not movies:
                    break
                    
                movie_ids.extend([movie.id for movie in movies])
                
                if max_movies and len(movie_ids) >= max_movies:
                    movie_ids = movie_ids[:max_movies]
                    break
                    
                page += 1
                
                # Limit to first 3 pages for top rated movies
                if page > 3:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching top rated movies page {page}: {e}")
                break
        
        logger.info(f"Found {len(movie_ids)} top rated movies")
        return movie_ids
    
    async def _get_now_playing_movies(self, client: TMDBClient, max_movies: Optional[int] = None) -> List[int]:
        """Get now playing movie IDs."""
        logger.info("Fetching now playing movies...")
        movie_ids = []
        page = 1
        
        while True:
            try:
                movies = await client.get_now_playing_movies(page=page)
                if not movies:
                    break
                    
                movie_ids.extend([movie.id for movie in movies])
                
                if max_movies and len(movie_ids) >= max_movies:
                    movie_ids = movie_ids[:max_movies]
                    break
                    
                page += 1
                
                # Limit to first 2 pages for now playing movies
                if page > 2:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching now playing movies page {page}: {e}")
                break
        
        logger.info(f"Found {len(movie_ids)} now playing movies")
        return movie_ids
    
    async def _fetch_movies_batch(self, client: TMDBClient, movie_ids: List[int],
                                include_credits: bool, include_reviews: bool,
                                include_videos: bool, include_images: bool) -> List[Movie]:
        """Fetch detailed data for a batch of movies."""
        movies_data = []
        
        # Process in batches to avoid overwhelming the API
        batch_size = DATA_CONFIG["batch_size"]
        
        for i in tqdm(range(0, len(movie_ids), batch_size), desc="Fetching movies"):
            batch_ids = movie_ids[i:i + batch_size]
            
            try:
                batch_movies = await client.batch_get_movies(
                    batch_ids, 
                    max_concurrent=5
                )
                
                # Filter out None values (failed requests)
                batch_movies = [m for m in batch_movies if m is not None]
                movies_data.extend(batch_movies)
                
                logger.info(f"Fetched {len(batch_movies)} movies from batch {i//batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Error fetching batch {i//batch_size + 1}: {e}")
                continue
        
        return movies_data
    
    def _save_movies_data(self, movies_data: List[Movie]):
        """Save movies data to files."""
        logger.info(f"Saving {len(movies_data)} movies to files...")
        
        # Convert to dictionaries
        movies_dict = [self._movie_to_dict(movie) for movie in movies_data]
        
        # Save as JSONL
        jsonl_file = self.output_dir / f"tmdb_movies_{self.timestamp}.jsonl"
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for movie in movies_dict:
                f.write(json.dumps(movie, ensure_ascii=False, default=str) + '\n')
        
        # Save as CSV (flattened)
        csv_file = self.output_dir / f"tmdb_movies_{self.timestamp}.csv"
        df = self._flatten_movies_data(movies_dict)
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        # Save metadata
        metadata = {
            "timestamp": self.timestamp,
            "total_movies": len(movies_data),
            "files_created": [str(jsonl_file), str(csv_file)],
            "extraction_config": {
                "include_credits": True,
                "include_reviews": False,
                "include_videos": False,
                "include_images": False
            }
        }
        
        metadata_file = self.output_dir / f"extraction_metadata_{self.timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"Data saved to {jsonl_file} and {csv_file}")
    
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
            "reviews": [{"id": r.id, "author": r.author, "content": r.content, "rating": r.rating, "created_at": r.created_at} for r in movie.reviews] if movie.reviews else [],
            "poster_path": movie.poster_path,
            "backdrop_path": movie.backdrop_path,
            "homepage": movie.homepage
        }
    
    def _flatten_movies_data(self, movies_dict: List[Dict[str, Any]]) -> pd.DataFrame:
        """Flatten movies data for CSV export."""
        flattened_data = []
        
        for movie in movies_dict:
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
    """Main extraction function."""
    logger.info("Starting CineAI data extraction...")
    
    # Check if TMDB API key is set
    if not TMDB_CONFIG["api_key"]:
        logger.error("TMDB_API_KEY environment variable is not set!")
        logger.info("Please set your TMDB API key:")
        logger.info("export TMDB_API_KEY='your_api_key_here'")
        return
    
    extractor = DataExtractor()
    
    try:
        # Extract TMDB data (limit to 1000 movies for testing)
        result = await extractor.extract_tmdb_data(
            max_movies=1000,  # Start with 1000 movies for testing
            include_credits=True,
            include_reviews=True,  # Enable reviews
            include_videos=False,
            include_images=False
        )
        
        logger.info("Data extraction completed successfully!")
        logger.info(f"Extracted {result['total_movies']} movies")
        logger.info(f"Files created: {result['files_created']}")
        
    except Exception as e:
        logger.error(f"Data extraction failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 