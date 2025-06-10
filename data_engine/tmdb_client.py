"""
Enhanced TMDB API Client for CineAI Data Engine

This module provides comprehensive integration with The Movie Database (TMDB) API,
including rate limiting, caching, error handling, and batch processing.
"""

import asyncio
import aiohttp
import time
import json
import logging
from typing import Dict, List, Optional, Any, Union, Generator
from pathlib import Path
from dataclasses import asdict
import pandas as pd

from config import TMDB_CONFIG
from schema import Movie, Person, CastMember, CrewMember, ProductionCompany, ProductionCountry, SpokenLanguage, Video, Image, Review, Genre, ContentType

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for TMDB API requests."""
    
    def __init__(self, requests_per_second: int = 10, requests_per_minute: int = 40):
        self.requests_per_second = requests_per_second
        self.requests_per_minute = requests_per_minute
        self.last_request_time = 0
        self.request_times = []
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        current_time = time.time()
        
        # Remove old requests from tracking
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        # Check minute limit
        if len(self.request_times) >= self.requests_per_minute:
            wait_time = 60 - (current_time - self.request_times[0])
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Check second limit
        time_since_last = current_time - self.last_request_time
        if time_since_last < 1.0 / self.requests_per_second:
            wait_time = (1.0 / self.requests_per_second) - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_times.append(current_time)


class TMDBClient:
    """Enhanced TMDB API client with comprehensive features."""
    
    def __init__(self, api_key: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None):
        self.api_key = api_key or TMDB_CONFIG["api_key"]
        self.base_url = TMDB_CONFIG["base_url"]
        self.image_base_url = TMDB_CONFIG["image_base_url"]
        self.language = TMDB_CONFIG["language"]
        self.region = TMDB_CONFIG["region"]
        self.timeout = TMDB_CONFIG["timeout"]
        self.max_retries = TMDB_CONFIG["max_retries"]
        
        self.rate_limiter = RateLimiter(
            TMDB_CONFIG["rate_limit"]["requests_per_second"],
            TMDB_CONFIG["rate_limit"]["requests_per_minute"]
        )
        
        self.session = session
        self._session_owner = session is None
        
        # Cache for API responses
        self._cache = {}
        self._cache_ttl = TMDB_CONFIG.get("cache_ttl", 3600)
    
    async def __aenter__(self):
        if self._session_owner and not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session_owner and self.session:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a rate-limited request to TMDB API."""
        # Ensure session exists
        if not self.session:
            if self._session_owner:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )
            else:
                raise RuntimeError("No session available and not session owner")
        
        await self.rate_limiter.wait_if_needed()
        
        # Check cache first
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        if cache_key in self._cache:
            cache_time, cache_data = self._cache[cache_key]
            if time.time() - cache_time < self._cache_ttl:
                return cache_data
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        params = params or {}
        params.update({
            "api_key": self.api_key,
            "language": self.language,
            "region": self.region
        })
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Cache the response
                        self._cache[cache_key] = (time.time(), data)
                        return data
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        error_text = await response.text()
                        logger.error(f"API request failed: {response.status} - {error_text}")
                        response.raise_for_status()
            except Exception as e:
                logger.error(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception("Max retries exceeded")
    
    async def get_movie(self, movie_id: int, include_credits: bool = True, include_videos: bool = True, 
                       include_images: bool = True, include_reviews: bool = True) -> Movie:
        """Get comprehensive movie data by ID."""
        logger.info(f"Fetching movie {movie_id}")
        
        # Get basic movie data
        movie_data = await self._make_request(f"movie/{movie_id}")
        
        # Get additional data if requested
        if include_credits:
            credits_data = await self._make_request(f"movie/{movie_id}/credits")
            movie_data.update(credits_data)
        
        if include_videos:
            videos_data = await self._make_request(f"movie/{movie_id}/videos")
            movie_data["videos"] = videos_data.get("results", [])
        
        if include_images:
            images_data = await self._make_request(f"movie/{movie_id}/images")
            movie_data["images"] = images_data
        
        if include_reviews:
            reviews_data = await self._make_request(f"movie/{movie_id}/reviews")
            movie_data["reviews"] = reviews_data.get("results", [])
        
        return self._parse_movie_data(movie_data)
    
    async def get_movie_credits(self, movie_id: int) -> Dict[str, List]:
        """Get cast and crew for a movie."""
        data = await self._make_request(f"movie/{movie_id}/credits")
        return {
            "cast": data.get("cast", []),
            "crew": data.get("crew", [])
        }
    
    async def get_movie_videos(self, movie_id: int) -> List[Video]:
        """Get videos (trailers, teasers, etc.) for a movie."""
        data = await self._make_request(f"movie/{movie_id}/videos")
        return [self._parse_video_data(video) for video in data.get("results", [])]
    
    async def get_movie_images(self, movie_id: int) -> Dict[str, List[Image]]:
        """Get images (posters, backdrops, etc.) for a movie."""
        data = await self._make_request(f"movie/{movie_id}/images")
        return {
            "posters": [self._parse_image_data(img) for img in data.get("posters", [])],
            "backdrops": [self._parse_image_data(img) for img in data.get("backdrops", [])],
            "logos": [self._parse_image_data(img) for img in data.get("logos", [])]
        }
    
    async def get_movie_reviews(self, movie_id: int, page: int = 1) -> List[Review]:
        """Get reviews for a movie."""
        data = await self._make_request(f"movie/{movie_id}/reviews", {"page": page})
        return [self._parse_review_data(review) for review in data.get("results", [])]
    
    async def get_movie_recommendations(self, movie_id: int, page: int = 1) -> List[int]:
        """Get movie recommendations based on a movie."""
        data = await self._make_request(f"movie/{movie_id}/recommendations", {"page": page})
        return [movie["id"] for movie in data.get("results", [])]
    
    async def get_movie_similar(self, movie_id: int, page: int = 1) -> List[int]:
        """Get similar movies."""
        data = await self._make_request(f"movie/{movie_id}/similar", {"page": page})
        return [movie["id"] for movie in data.get("results", [])]
    
    async def search_movies(self, query: str, page: int = 1, include_adult: bool = False) -> List[Movie]:
        """Search for movies by title."""
        params = {
            "query": query,
            "page": page,
            "include_adult": include_adult
        }
        data = await self._make_request("search/movie", params)
        return [self._parse_movie_data(movie) for movie in data.get("results", [])]
    
    async def get_popular_movies(self, page: int = 1) -> List[Movie]:
        """Get popular movies."""
        try:
            data = await self._make_request("movie/popular", {"page": page})
            return [self._parse_movie_data(movie) for movie in data.get("results", [])]
        except Exception as e:
            logger.error(f"Failed to get popular movies page {page}: {e}")
            return []
    
    async def get_top_rated_movies(self, page: int = 1) -> List[Movie]:
        """Get top rated movies."""
        try:
            data = await self._make_request("movie/top_rated", {"page": page})
            return [self._parse_movie_data(movie) for movie in data.get("results", [])]
        except Exception as e:
            logger.error(f"Failed to get top-rated movies page {page}: {e}")
            return []
    
    async def get_now_playing_movies(self, page: int = 1) -> List[Movie]:
        """Get movies currently in theaters."""
        try:
            data = await self._make_request("movie/now_playing", {"page": page})
            return [self._parse_movie_data(movie) for movie in data.get("results", [])]
        except Exception as e:
            logger.error(f"Failed to get now-playing movies page {page}: {e}")
            return []
    
    async def get_upcoming_movies(self, page: int = 1) -> List[Movie]:
        """Get upcoming movies."""
        data = await self._make_request("movie/upcoming", {"page": page})
        return [self._parse_movie_data(movie) for movie in data.get("results", [])]
    
    async def get_movies_by_genre(self, genre_id: int, page: int = 1) -> List[Movie]:
        """Get movies by genre."""
        data = await self._make_request("discover/movie", {
            "with_genres": genre_id,
            "page": page,
            "sort_by": "popularity.desc"
        })
        return [self._parse_movie_data(movie) for movie in data.get("results", [])]
    
    async def get_person(self, person_id: int) -> Person:
        """Get person details."""
        data = await self._make_request(f"person/{person_id}")
        return self._parse_person_data(data)
    
    async def get_person_movies(self, person_id: int) -> List[Dict[str, Any]]:
        """Get movies a person has worked on."""
        data = await self._make_request(f"person/{person_id}/movie_credits")
        return data.get("cast", []) + data.get("crew", [])
    
    async def batch_get_movies(self, movie_ids: List[int], max_concurrent: int = 5,
                              include_credits: bool = True, include_reviews: bool = True,
                              include_videos: bool = False, include_images: bool = False) -> List[Movie]:
        """Get multiple movies concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def get_movie_with_semaphore(movie_id: int) -> Optional[Movie]:
            async with semaphore:
                try:
                    return await self.get_movie(movie_id, include_credits=include_credits, 
                                               include_videos=include_videos, 
                                               include_images=include_images, 
                                               include_reviews=include_reviews)
                except Exception as e:
                    logger.error(f"Failed to fetch movie {movie_id}: {e}")
                    return None
        
        tasks = [get_movie_with_semaphore(movie_id) for movie_id in movie_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        movies = []
        for result in results:
            if isinstance(result, Movie):
                movies.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Exception in batch fetch: {result}")
        
        return movies
    
    def _parse_movie_data(self, data: Dict[str, Any]) -> Movie:
        """Parse raw movie data into Movie object."""
        # Parse genres
        genres = []
        if "genres" in data:
            for genre_data in data["genres"]:
                try:
                    # Find genre by value (ID)
                    genre_id = genre_data["id"]
                    genre = next((g for g in Genre if g.value == genre_id), None)
                    if genre:
                        genres.append(genre)
                    else:
                        logger.warning(f"Unknown genre ID: {genre_id}")
                except Exception as e:
                    logger.warning(f"Error parsing genre {genre_data}: {e}")
        
        # Parse cast
        cast = []
        if "cast" in data:
            for cast_data in data["cast"][:10]:  # Limit to top 10
                person = self._parse_person_data(cast_data)
                cast.append(CastMember(
                    person=person,
                    character=cast_data.get("character", ""),
                    order=cast_data.get("order", 0),
                    credit_id=cast_data.get("credit_id", "")
                ))
        
        # Parse crew
        crew = []
        if "crew" in data:
            for crew_data in data["crew"]:
                person = self._parse_person_data(crew_data)
                crew.append(CrewMember(
                    person=person,
                    job=crew_data.get("job", ""),
                    department=crew_data.get("department", ""),
                    credit_id=crew_data.get("credit_id", "")
                ))
        
        # Parse production companies
        production_companies = []
        if "production_companies" in data:
            for company_data in data["production_companies"]:
                production_companies.append(ProductionCompany(
                    id=company_data["id"],
                    name=company_data["name"],
                    logo_path=company_data.get("logo_path"),
                    origin_country=company_data.get("origin_country")
                ))
        
        # Parse production countries
        production_countries = []
        if "production_countries" in data:
            for country_data in data["production_countries"]:
                production_countries.append(ProductionCountry(
                    iso_3166_1=country_data["iso_3166_1"],
                    name=country_data["name"]
                ))
        
        # Parse spoken languages
        spoken_languages = []
        if "spoken_languages" in data:
            for lang_data in data["spoken_languages"]:
                spoken_languages.append(SpokenLanguage(
                    iso_639_1=lang_data["iso_639_1"],
                    name=lang_data["name"],
                    english_name=lang_data.get("english_name", lang_data["name"])
                ))
        
        # Parse videos
        videos = []
        if "videos" in data:
            for video_data in data["videos"]:
                videos.append(self._parse_video_data(video_data))
        
        # Parse images
        images = {}
        if "images" in data:
            for image_type, image_list in data["images"].items():
                if isinstance(image_list, list):
                    images[image_type] = [self._parse_image_data(img) for img in image_list]
                else:
                    logger.warning(f"Expected list for images[{image_type}], got {type(image_list)}: {image_list}")
        
        # Parse reviews
        reviews = []
        if "reviews" in data:
            for review_data in data["reviews"]:
                reviews.append(self._parse_review_data(review_data))
        
        return Movie(
            id=data["id"],
            title=data["title"],
            original_title=data.get("original_title", data["title"]),
            overview=data.get("overview", ""),
            status=data.get("status", "Released"),
            vote_average=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0),
            popularity=data.get("popularity", 0.0),
            tagline=data.get("tagline"),
            release_date=data.get("release_date"),
            runtime=data.get("runtime"),
            budget=data.get("budget"),
            revenue=data.get("revenue"),
            adult=data.get("adult", False),
            video=data.get("video", False),
            original_language=data.get("original_language", "en"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            homepage=data.get("homepage"),
            imdb_id=data.get("imdb_id"),
            genres=genres,
            cast=cast,
            crew=crew,
            production_companies=production_companies,
            production_countries=production_countries,
            spoken_languages=spoken_languages,
            videos=videos,
            images=images,
            reviews=reviews
        )
    
    def _parse_person_data(self, data: Dict[str, Any]) -> Person:
        """Parse raw person data into Person object."""
        return Person(
            id=data["id"],
            name=data["name"],
            known_for_department=data.get("known_for_department", ""),
            profile_path=data.get("profile_path"),
            popularity=data.get("popularity", 0.0),
            gender=data.get("gender"),
            birthday=data.get("birthday"),
            deathday=data.get("deathday"),
            place_of_birth=data.get("place_of_birth"),
            biography=data.get("biography"),
            imdb_id=data.get("imdb_id"),
            homepage=data.get("homepage")
        )
    
    def _parse_video_data(self, data: Dict[str, Any]) -> Video:
        """Parse raw video data into Video object."""
        return Video(
            id=data["id"],
            key=data["key"],
            name=data["name"],
            site=data["site"],
            size=data["size"],
            type=data["type"],
            official=data.get("official", False),
            published_at=data["published_at"],
            iso_639_1=data.get("iso_639_1"),
            iso_3166_1=data.get("iso_3166_1")
        )
    
    def _parse_image_data(self, data: Dict[str, Any]) -> Image:
        """Parse raw image data into Image object."""
        return Image(
            aspect_ratio=data["aspect_ratio"],
            file_path=data["file_path"],
            height=data["height"],
            width=data["width"],
            iso_639_1=data.get("iso_639_1"),
            vote_average=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0)
        )
    
    def _parse_review_data(self, data: Dict[str, Any]) -> Review:
        """Parse raw review data into Review object."""
        return Review(
            id=data["id"],
            author=data["author"],
            content=data["content"],
            url=data["url"],
            rating=data.get("rating"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def get_image_url(self, file_path: str, size: str = "w500") -> str:
        """Get full URL for an image."""
        if not file_path:
            return ""
        return f"{self.image_base_url}{size}{file_path}"
    
    def get_video_url(self, key: str, site: str = "YouTube") -> str:
        """Get full URL for a video."""
        if site.lower() == "youtube":
            return f"https://www.youtube.com/watch?v={key}"
        elif site.lower() == "vimeo":
            return f"https://vimeo.com/{key}"
        else:
            return key


async def main():
    """Example usage of the TMDB client."""
    async with TMDBClient() as client:
        # Get a specific movie
        movie = await client.get_movie(550)  # Fight Club
        print(f"Movie: {movie.title} ({movie.year})")
        print(f"Genres: {[g.name for g in movie.genres]}")
        print(f"Directors: {[d.name for d in movie.directors]}")
        
        # Search for movies
        search_results = await client.search_movies("Inception")
        print(f"Found {len(search_results)} movies matching 'Inception'")
        
        # Get popular movies
        popular_movies = await client.get_popular_movies()
        print(f"Top popular movies: {[m.title for m in popular_movies[:5]]}")


if __name__ == "__main__":
    asyncio.run(main()) 