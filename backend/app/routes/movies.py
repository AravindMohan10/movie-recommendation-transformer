from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
import json
import logging
import os
import random
from pathlib import Path

import requests

router = APIRouter(prefix="/api/movies", tags=["movies"])
logger = logging.getLogger(__name__)

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
TMDB_BASE = "https://api.themoviedb.org/3"

# Cache for movie data
_movie_cache = None
_movie_cache_path = None

def load_movie_data():
    """Load movie data from JSONL file and cache it"""
    global _movie_cache, _movie_cache_path
    
    # Path to the movie data file
    # __file__ is backend/app/routes/movies.py
    # So: backend/app/routes -> backend/app -> backend -> project_root (one more parent)
    BASE_DIR = Path(__file__).parent.parent.parent.parent
    
    # Try multiple possible paths
    possible_paths = [
        BASE_DIR / "data" / "raw" / "tmdb_movies_50k_20250711_011112.jsonl",
        BASE_DIR / "data" / "raw" / "tmdb_complete_dataset.jsonl",  # Fallback to complete dataset
        BASE_DIR / "data" / "raw" / "tmdb_movies_20250629_202104.jsonl",  # Another fallback
    ]
    
    movie_file = None
    for path in possible_paths:
        if path.exists():
            movie_file = path
            break
    
    if not movie_file:
        # Try to find any tmdb jsonl file
        data_dir = BASE_DIR / "data" / "raw"
        if data_dir.exists():
            jsonl_files = list(data_dir.glob("tmdb_movies*.jsonl"))
            if jsonl_files:
                movie_file = jsonl_files[0]
                logger.info("Using movie file: %s", movie_file)
    
    # Only reload if file changed or cache is empty
    if _movie_cache is None or (movie_file and _movie_cache_path != str(movie_file)):
        _movie_cache = []
        if movie_file:
            _movie_cache_path = str(movie_file)
        
        if not movie_file or not movie_file.exists():
            logger.warning("Movie data file not found. Searched: %s", possible_paths)
            return []
        try:
            with open(movie_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        movie = json.loads(line.strip())
                        _movie_cache.append(movie)
                    except json.JSONDecodeError:
                        continue
            logger.info("Loaded %d movies", len(_movie_cache))
        except Exception as e:
            logger.exception("Error loading movies")
            return []
    
    return _movie_cache


def _search_tmdb(query: str, limit: int = 20) -> List[Dict]:
    """Search TMDB API. Returns list of items in our search result shape. Empty if no key or error."""
    if not TMDB_API_KEY:
        return []
    try:
        r = requests.get(
            f"{TMDB_BASE}/search/movie",
            params={"api_key": TMDB_API_KEY, "query": query, "language": "en-US"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        raw = data.get("results") or []
        out = []
        for m in raw[:limit]:
            rd = m.get("release_date") or ""
            release_year = int(rd[:4]) if len(rd) >= 4 else None
            genres_list = m.get("genre_ids") or []
            genre_names = _tmdb_genre_ids_to_names(genres_list)
            out.append({
                "id": m.get("id"),
                "tmdb_id": m.get("id"),
                "title": m.get("title") or "Unknown",
                "original_title": m.get("original_title"),
                "release_year": release_year,
                "poster_path": m.get("poster_path"),
                "overview": (m.get("overview") or "")[:200],
                "vote_average": m.get("vote_average") or 0,
                "genres": genre_names,
            })
        return out
    except Exception as e:
        logger.warning("TMDB search error: %s", e)
        return []


# TMDB genre id -> name (main ones). Full list: https://developer.themoviedb.org/reference/genre-movie-list
_TMDB_GENRES = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
}
# Special "genre" for older movies (main recs are 1980+)
CLASSICS_GENRE = "Classics (Pre-1980)"
CLASSICS_CUTOFF_YEAR = 1980


def _tmdb_genre_ids_to_names(ids: List[int]) -> List[str]:
    return [_TMDB_GENRES[i] for i in ids if i in _TMDB_GENRES]


def _get_tmdb_movie(movie_id: int) -> Optional[Dict]:
    """Fetch single movie from TMDB by id. Returns our get-by-id shape or None."""
    if not TMDB_API_KEY:
        return None
    try:
        r = requests.get(
            f"{TMDB_BASE}/movie/{movie_id}",
            params={"api_key": TMDB_API_KEY, "language": "en-US"},
            timeout=10,
        )
        r.raise_for_status()
        m = r.json()
        rd = m.get("release_date") or ""
        release_year = int(rd[:4]) if len(rd) >= 4 else None
        genres_list = m.get("genres") or []
        if genres_list and isinstance(genres_list[0], dict):
            genres = [g.get("name", "") for g in genres_list if g.get("name")]
        else:
            genres = []
        return {
            "id": m.get("id"),
            "title": m.get("title") or "Unknown",
            "poster_path": m.get("poster_path"),
            "overview": (m.get("overview") or "")[:400],
            "release_date": m.get("release_date"),
            "release_year": release_year,
            "vote_average": m.get("vote_average") or 0,
            "genres": genres,
        }
    except Exception as e:
        logger.warning("TMDB get movie error: %s", e)
        return None


@router.get("/search")
async def search_movies(
    query: str = Query(..., min_length=2, description="Search query for movie title")
) -> Dict:
    """
    Search for movies by title
    
    Returns movies matching the search query
    """
    try:
        q = query.strip()
        if not q:
            return {"results": [], "source": "catalog"}

        if TMDB_API_KEY:
            results = _search_tmdb(q, limit=20)
            if results:
                return {"results": results, "source": "tmdb"}

        movies = load_movie_data()
        if not movies:
            return {"results": [], "source": "catalog"}

        query_lower = q.lower()
        
        # Search through movie titles
        results = []
        for movie in movies:
            title = movie.get("title", "").lower()
            original_title = (movie.get("original_title") or "").lower()
            
            # Check if query matches title or original title
            if query_lower in title or query_lower in original_title:
                # Extract release year
                release_date = movie.get("release_date", "")
                release_year = None
                if release_date and len(release_date) >= 4:
                    try:
                        release_year = int(release_date[:4])
                    except ValueError:
                        pass
                
                # Format genres - handle both list of dicts and list of strings
                genres_list = movie.get("genres", [])
                if genres_list and isinstance(genres_list[0], dict):
                    genres = [g.get("name", "") for g in genres_list]
                elif isinstance(genres_list, list):
                    genres = [str(g) for g in genres_list if g]
                else:
                    genres = []
                
                # Format result
                result = {
                    "id": movie.get("tmdb_id"),
                    "title": movie.get("title", "Unknown"),
                    "original_title": movie.get("original_title"),
                    "release_year": release_year,
                    "poster_path": movie.get("poster_path"),
                    "overview": movie.get("overview", "")[:200] if movie.get("overview") else "",  # First 200 chars
                    "vote_average": movie.get("vote_average", 0),
                    "genres": genres
                }
                results.append(result)
                
                # Limit results to 20 for performance
                if len(results) >= 20:
                    break
        
        # Sort by relevance (exact match first, then by popularity)
        results.sort(key=lambda x: (
            0 if query_lower in x["title"].lower() else 1,  # Exact match first
            -x.get("vote_average", 0)  # Then by rating
        ))
        
        return {"results": results, "source": "catalog"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching movies: {str(e)}")


def _is_documentary(movie_data: dict) -> bool:
    """True if movie is a documentary (excluded from random / surprise)."""
    genres = movie_data.get("genres") or []
    for g in genres:
        if isinstance(g, dict):
            gid, gname = g.get("id"), (g.get("name") or "")
            if gid == 99 or str(gname).upper() == "DOCUMENTARY":
                return True
        elif isinstance(g, str) and "documentary" in g.lower():
            return True
    return False


def _is_adult(movie_data: dict) -> bool:
    """True if movie is marked adult (excluded from browse)."""
    return movie_data.get("adult") is True


def _movie_has_genre(movie_data: dict, genre_query: str) -> bool:
    """True if movie has the given genre (case-insensitive; normalizes SCIENCE FICTION etc.)."""
    if not genre_query or not movie_data:
        return False
    q = str(genre_query).strip().upper().replace(" ", "_").replace("-", "_")
    genres_list = movie_data.get("genres") or []
    for g in genres_list:
        if isinstance(g, dict):
            gname = (g.get("name") or "").strip().upper().replace(" ", "_")
            if gname == q:
                return True
            # Map common variants
            if q == "SCIENCE_FICTION" and gname in ("SCIENCE FICTION", "SCI-FI", "SCI_FI"):
                return True
            if gname == "SCIENCE_FICTION" and q in ("SCIENCE FICTION", "SCI-FI", "SCI_FI"):
                return True
        elif isinstance(g, str):
            gn = g.strip().upper().replace(" ", "_")
            if gn == q:
                return True
    return False


def _release_year(movie_data: dict) -> Optional[int]:
    """Extract release year from movie dict. Returns None if missing or invalid."""
    rd = movie_data.get("release_date") or movie_data.get("release_year")
    if not rd:
        return None
    s = str(rd)[:4]
    if len(s) == 4 and s.isdigit():
        return int(s)
    return None


INDIAN_GENRE = "Indian"

def _is_indian_movie(m: dict) -> bool:
    """True if movie has India in production_countries."""
    pc = m.get("production_countries")
    if not pc:
        return False
    if isinstance(pc, list):
        for c in pc:
            if isinstance(c, dict):
                name = (c.get("name") or "").upper()
                iso = (c.get("iso_3166_1") or "").upper()
                if "INDIA" in name or iso == "IN":
                    return True
            elif isinstance(c, str) and "india" in c.lower():
                return True
    elif isinstance(pc, str):
        return "india" in pc.lower()
    return False


@router.get("/genres")
async def get_genres() -> Dict:
    """Return list of all genre names (for browse-by-genre). Includes Classics (Pre-1980), Indian."""
    return {"genres": list(_TMDB_GENRES.values()) + [CLASSICS_GENRE, INDIAN_GENRE]}


# Quality controls for by-genre: avoid obscure/niche titles with inflated ratings
MIN_VOTE_COUNT_BY_GENRE = 100   # only movies with at least this many votes
MIN_VOTE_AVERAGE_BY_GENRE = 6.0  # minimum rating to include
BAYESIAN_MIN_VOTES = 100         # for weighted score (pull low-vote toward global avg)
GLOBAL_AVG = 7.0                 # prior for weighted score


def _weighted_score(vote_average: float, vote_count: int) -> float:
    """Bayesian-style score so well-voted movies rank above low-vote high-average titles."""
    vc = max(0, vote_count)
    va = vote_average or 0
    return (vc / (vc + BAYESIAN_MIN_VOTES)) * va + (BAYESIAN_MIN_VOTES / (vc + BAYESIAN_MIN_VOTES)) * GLOBAL_AVG


@router.get("/by-genre")
async def get_movies_by_genre(
    genre: str = Query(..., min_length=1, description="Genre name e.g. Action, Drama, or Classics (Pre-1980)"),
    limit: int = Query(50, ge=1, le=200),
) -> Dict:
    """Return movies from the full catalog in this genre. Classics (Pre-1980) = release year < 1980. Quality filters: min votes, min rating, exclude docs (unless Documentary), weighted sort."""
    movies = load_movie_data()
    if not movies:
        return {"movies": [], "genre": genre.strip(), "total": 0}
    genre_clean = genre.strip()
    is_documentary_genre = genre_clean.lower() == "documentary"
    is_classics_genre = genre_clean == CLASSICS_GENRE
    is_indian_genre = genre_clean == INDIAN_GENRE
    matching = []
    for m in movies:
        if _is_adult(m):
            continue
        if is_indian_genre:
            if not _is_indian_movie(m):
                continue
        elif is_classics_genre:
            yr = _release_year(m)
            if yr is None or yr >= CLASSICS_CUTOFF_YEAR:
                continue
        else:
            if not _movie_has_genre(m, genre_clean):
                continue
        vote_count = (m.get("vote_count") or 0) or 0
        vote_avg = (m.get("vote_average") or 0) or 0
        if vote_count < MIN_VOTE_COUNT_BY_GENRE:
            continue
        if vote_avg < MIN_VOTE_AVERAGE_BY_GENRE:
            continue
        if not is_documentary_genre and _is_documentary(m):
            continue
        matching.append(m)
    matching.sort(
        key=lambda x: (
            -_weighted_score(x.get("vote_average") or 0, x.get("vote_count") or 0),
            -(x.get("vote_count") or 0),
        )
    )
    selected = matching[:limit]
    out = []
    for m in selected:
        mid = m.get("tmdb_id") or m.get("id")
        genres_list = m.get("genres") or []
        if genres_list and isinstance(genres_list[0], dict):
            gnames = [g.get("name", "") for g in genres_list if isinstance(g, dict)]
        else:
            gnames = [str(g) for g in genres_list if g]
        pp = m.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w342{pp}" if pp and str(pp).strip() and not str(pp).startswith("http") else (pp or None)
        out.append({
            "id": mid,
            "movie_id": mid,
            "title": m.get("title", "Unknown"),
            "poster_path": m.get("poster_path"),
            "poster_url": poster_url,
            "overview": (m.get("overview") or "")[:300],
            "vote_average": m.get("vote_average") or 0,
            "release_year": int(str(m.get("release_date", ""))[:4]) if m.get("release_date") and len(str(m.get("release_date"))) >= 4 else None,
            "genres": gnames,
            "genre": gnames[0] if gnames else "Unknown",
        })
    return {"movies": out, "genre": genre_clean, "total": len(out)}


@router.get("/journey")
async def get_movie_journey(
    seed: int = Query(..., description="Starting movie ID (TMDB)"),
    limit: int = Query(5, ge=3, le=5),
) -> Dict:
    """Movie journey: 3–5 films with explicit reason per step (director, theme, era). Each film validated in catalog."""
    from ..journey_service import get_journey
    movies = load_movie_data()
    if not movies:
        return {"journey": [], "total": 0}
    movie_data = {}
    for m in movies:
        mid = m.get("tmdb_id") or m.get("id")
        if mid is not None:
            movie_data[int(mid)] = m
            movie_data[str(mid)] = m
    journey = get_journey(int(seed), movie_data, max_steps=limit)
    out = []
    for step in journey:
        mid = step["movie_id"]
        m = movie_data.get(mid) or movie_data.get(str(mid))
        if not m:
            continue
        pp = m.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w342{pp}" if pp and str(pp).strip() and not str(pp).startswith("http") else (pp or None)
        out.append({
            "movie_id": mid,
            "title": m.get("title", "Unknown"),
            "poster_url": poster_url,
            "overview": (m.get("overview") or "")[:200],
            "reason": step["reason"],
            "reason_detail": step["reason_detail"],
        })
    return {"journey": out, "total": len(out)}


@router.get("/random")
async def get_random_movies(limit: int = Query(10, ge=1, le=30)) -> Dict:
    """Public. Truly random good movies (no documentaries). For landing page."""
    movies = load_movie_data()
    pool = []
    for m in movies:
        if _is_documentary(m):
            continue
        vote_avg = (m.get("vote_average") or 0) or 0
        vote_count = (m.get("vote_count") or 0) or 0
        if vote_avg < 7.0 or vote_count < 100:
            continue
        pool.append(m)
    random.shuffle(pool)
    selected = pool[:limit]
    out = []
    for m in selected:
        pid = m.get("tmdb_id") or m.get("id")
        pp = m.get("poster_path")
        if pp and str(pp).strip():
            url = pp if str(pp).startswith("http") else f"https://image.tmdb.org/t/p/w300{pp}"
        else:
            title = (m.get("title") or "Movie")[:20].replace(" ", "+")
            url = f"https://via.placeholder.com/300/1a1a1a/666?text={title}"
        out.append({"id": pid, "title": m.get("title", ""), "poster_url": url})
    return {"movies": out}


@router.get("/{movie_id}")
async def get_movie_by_id(movie_id: int) -> Dict:
    """Public: get a single movie by id (for share page). Tries local catalog, then TMDB if not found."""
    movies = load_movie_data()
    for m in movies:
        mid = m.get("tmdb_id") or m.get("id")
        if mid is not None and int(mid) == int(movie_id):
            pp = m.get("poster_path")
            poster_url = None
            if pp and str(pp).strip() and str(pp) != "None":
                pp = str(pp).strip()
                poster_url = pp if pp.startswith("http") else f"https://image.tmdb.org/t/p/w342{pp}" if pp.startswith("/") else f"https://image.tmdb.org/t/p/w342/{pp}"
            return {
                "id": mid,
                "title": m.get("title", "Unknown"),
                "poster_path": m.get("poster_path"),
                "poster_url": poster_url,
                "overview": (m.get("overview") or "")[:400],
                "release_date": m.get("release_date"),
                "vote_average": m.get("vote_average", 0),
                "genres": m.get("genres", []),
            }
    tmdb_m = _get_tmdb_movie(movie_id)
    if tmdb_m:
        pp = tmdb_m.get("poster_path")
        if pp and str(pp).strip():
            pp = str(pp).strip()
            tmdb_m["poster_url"] = pp if pp.startswith("http") else f"https://image.tmdb.org/t/p/w342{pp}" if pp.startswith("/") else f"https://image.tmdb.org/t/p/w342/{pp}"
        else:
            tmdb_m["poster_url"] = None
        return tmdb_m
    raise HTTPException(status_code=404, detail="Movie not found")

