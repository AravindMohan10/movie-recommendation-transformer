"""
Enhanced Data Schema for CineAI Data Engine

This module defines the comprehensive data structures for movies, users,
interactions, and features used throughout the recommendation system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import json


class ContentType(Enum):
    """Types of content in the system."""
    MOVIE = "movie"
    TV_SHOW = "tv"
    DOCUMENTARY = "documentary"
    SHORT_FILM = "short"
    ANIMATION = "animation"


class Genre(Enum):
    """Movie genres with their TMDB IDs."""
    ACTION = 28
    ADVENTURE = 12
    ANIMATION = 16
    COMEDY = 35
    CRIME = 80
    DOCUMENTARY = 99
    DRAMA = 18
    FAMILY = 10751
    FANTASY = 14
    HISTORY = 36
    HORROR = 27
    MUSIC = 10402
    MYSTERY = 9648
    ROMANCE = 10749
    SCIENCE_FICTION = 878
    TV_MOVIE = 10770
    THRILLER = 53
    WAR = 10752
    WESTERN = 37


class InteractionType(Enum):
    """Types of user interactions."""
    VIEW = "view"
    RATE = "rate"
    LIKE = "like"
    DISLIKE = "dislike"
    WATCHLIST = "watchlist"
    SHARE = "share"
    REVIEW = "review"
    SEARCH = "search"
    CLICK = "click"
    HOVER = "hover"


@dataclass
class Person:
    """Represents a person (actor, director, etc.) in the movie industry."""
    id: int
    name: str
    known_for_department: str
    profile_path: Optional[str] = None
    popularity: float = 0.0
    gender: Optional[int] = None
    birthday: Optional[str] = None
    deathday: Optional[str] = None
    place_of_birth: Optional[str] = None
    biography: Optional[str] = None
    imdb_id: Optional[str] = None
    homepage: Optional[str] = None


@dataclass
class CastMember:
    """Represents a cast member in a movie."""
    person: Person
    character: str
    order: int
    credit_id: str


@dataclass
class CrewMember:
    """Represents a crew member in a movie."""
    person: Person
    job: str
    department: str
    credit_id: str


@dataclass
class ProductionCompany:
    """Represents a production company."""
    id: int
    name: str
    logo_path: Optional[str] = None
    origin_country: Optional[str] = None
    description: Optional[str] = None
    headquarters: Optional[str] = None
    homepage: Optional[str] = None


@dataclass
class ProductionCountry:
    """Represents a production country."""
    iso_3166_1: str
    name: str


@dataclass
class SpokenLanguage:
    """Represents a spoken language."""
    iso_639_1: str
    name: str
    english_name: str


@dataclass
class Video:
    """Represents a video (trailer, teaser, etc.)."""
    id: str
    key: str
    name: str
    site: str
    size: int
    type: str
    official: bool
    published_at: str
    iso_639_1: Optional[str] = None
    iso_3166_1: Optional[str] = None


@dataclass
class Image:
    """Represents an image (poster, backdrop, etc.)."""
    aspect_ratio: float
    file_path: str
    height: int
    width: int
    iso_639_1: Optional[str] = None
    vote_average: float = 0.0
    vote_count: int = 0


@dataclass
class Review:
    """Represents a movie review."""
    id: str
    author: str
    content: str
    url: str
    rating: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Movie:
    """Enhanced movie data structure with comprehensive information."""
    # Basic Information
    id: int
    title: str
    original_title: str
    overview: str
    status: str
    vote_average: float
    vote_count: int
    popularity: float
    
    # Optional Basic Information
    tagline: Optional[str] = None
    release_date: Optional[str] = None
    runtime: Optional[int] = None
    budget: Optional[int] = None
    revenue: Optional[int] = None
    
    # Content Details
    adult: bool = False
    video: bool = False
    original_language: str = "en"
    content_type: ContentType = ContentType.MOVIE
    
    # Media
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    homepage: Optional[str] = None
    imdb_id: Optional[str] = None
    
    # Relationships
    genres: List[Genre] = field(default_factory=list)
    cast: List[CastMember] = field(default_factory=list)
    crew: List[CrewMember] = field(default_factory=list)
    production_companies: List[ProductionCompany] = field(default_factory=list)
    production_countries: List[ProductionCountry] = field(default_factory=list)
    spoken_languages: List[SpokenLanguage] = field(default_factory=list)
    
    # Additional Content
    videos: List[Video] = field(default_factory=list)
    images: Dict[str, List[Image]] = field(default_factory=dict)
    reviews: List[Review] = field(default_factory=list)
    
    # Enhanced Features
    keywords: List[str] = field(default_factory=list)
    collections: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[int] = field(default_factory=list)
    similar: List[int] = field(default_factory=list)
    
    # Computed Features
    features: Dict[str, Any] = field(default_factory=dict)
    embeddings: Dict[str, List[float]] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.release_date, str):
            try:
                datetime.strptime(self.release_date, "%Y-%m-%d")
            except ValueError:
                self.release_date = None
    
    @property
    def year(self) -> Optional[int]:
        """Extract year from release date."""
        if self.release_date:
            try:
                return datetime.strptime(self.release_date, "%Y-%m-%d").year
            except ValueError:
                return None
        return None
    
    @property
    def directors(self) -> List[Person]:
        """Get directors from crew."""
        return [member.person for member in self.crew 
                if member.job.lower() in ['director', 'co-director']]
    
    @property
    def main_cast(self, limit: int = 5) -> List[CastMember]:
        """Get main cast members (top billed)."""
        return sorted(self.cast, key=lambda x: x.order)[:limit]
    
    @property
    def genre_names(self) -> List[str]:
        """Get genre names."""
        return [genre.name for genre in self.genres]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'original_title': self.original_title,
            'overview': self.overview,
            'tagline': self.tagline,
            'release_date': self.release_date,
            'runtime': self.runtime,
            'status': self.status,
            'vote_average': self.vote_average,
            'vote_count': self.vote_count,
            'popularity': self.popularity,
            'budget': self.budget,
            'revenue': self.revenue,
            'adult': self.adult,
            'video': self.video,
            'original_language': self.original_language,
            'content_type': self.content_type.value,
            'poster_path': self.poster_path,
            'backdrop_path': self.backdrop_path,
            'homepage': self.homepage,
            'imdb_id': self.imdb_id,
            'genres': [genre.value for genre in self.genres],
            'year': self.year,
            'directors': [person.name for person in self.directors],
            'main_cast': [member.person.name for member in self.main_cast],
            'features': self.features,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class User:
    """Enhanced user data structure."""
    id: int
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
    
    # Profile Information
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    
    # Preferences
    preferred_genres: List[Genre] = field(default_factory=list)
    preferred_languages: List[str] = field(default_factory=list)
    preferred_countries: List[str] = field(default_factory=list)
    content_rating_preference: str = "PG-13"
    watchlist_public: bool = False
    
    # Onboarding
    onboarding_completed: bool = False
    onboarding_step: int = 0
    onboarding_data: Dict[str, Any] = field(default_factory=dict)
    
    # Features
    features: Dict[str, Any] = field(default_factory=dict)
    embeddings: Dict[str, Any] = field(default_factory=dict)
    
    # Statistics
    total_watched: int = 0
    total_rated: int = 0
    total_reviews: int = 0
    average_rating: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'first_name': self.first_name,
            'last_name': self.last_name,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'location': self.location,
            'birth_date': self.birth_date,
            'gender': self.gender,
            'preferred_genres': [genre.value for genre in self.preferred_genres],
            'preferred_languages': self.preferred_languages,
            'preferred_countries': self.preferred_countries,
            'content_rating_preference': self.content_rating_preference,
            'watchlist_public': self.watchlist_public,
            'onboarding_completed': self.onboarding_completed,
            'onboarding_step': self.onboarding_step,
            'onboarding_data': self.onboarding_data,
            'features': self.features,
            'total_watched': self.total_watched,
            'total_rated': self.total_rated,
            'total_reviews': self.total_reviews,
            'average_rating': self.average_rating
        }


@dataclass
class Interaction:
    """User interaction with content."""
    id: int
    user_id: int
    movie_id: int
    interaction_type: InteractionType
    timestamp: datetime
    session_id: Optional[str] = None
    
    # Interaction-specific data
    rating: Optional[float] = None
    review_text: Optional[str] = None
    review_rating: Optional[float] = None
    watch_duration: Optional[int] = None  # seconds
    watch_progress: Optional[float] = None  # percentage
    search_query: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    device_type: Optional[str] = None
    platform: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'movie_id': self.movie_id,
            'interaction_type': self.interaction_type.value,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'rating': self.rating,
            'review_text': self.review_text,
            'review_rating': self.review_rating,
            'watch_duration': self.watch_duration,
            'watch_progress': self.watch_progress,
            'search_query': self.search_query,
            'context': self.context,
            'device_type': self.device_type,
            'platform': self.platform,
            'location': self.location,
            'ip_address': self.ip_address
        }


@dataclass
class Recommendation:
    """Movie recommendation for a user."""
    user_id: int
    movie_id: int
    score: float
    algorithm: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Recommendation metadata
    reason: Optional[str] = None
    confidence: float = 1.0
    diversity_score: float = 0.0
    novelty_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'user_id': self.user_id,
            'movie_id': self.movie_id,
            'score': self.score,
            'algorithm': self.algorithm,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'reason': self.reason,
            'confidence': self.confidence,
            'diversity_score': self.diversity_score,
            'novelty_score': self.novelty_score
        }


@dataclass
class FeatureVector:
    """Feature vector for machine learning models."""
    id: str
    entity_type: str  # 'movie', 'user', 'interaction'
    entity_id: int
    features: Dict[str, Union[float, int, str, List[float]]]
    timestamp: datetime
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'features': self.features,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version
        }


@dataclass
class SearchResult:
    """Search result with relevance information."""
    movie: Movie
    score: float
    match_type: str  # 'exact', 'fuzzy', 'semantic'
    matched_fields: List[str]
    highlights: Dict[str, List[str]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'movie': self.movie.to_dict(),
            'score': self.score,
            'match_type': self.match_type,
            'matched_fields': self.matched_fields,
            'highlights': self.highlights
        }


# Database table schemas
MOVIE_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    original_title TEXT,
    overview TEXT,
    tagline TEXT,
    release_date TEXT,
    runtime INTEGER,
    status TEXT,
    vote_average REAL,
    vote_count INTEGER,
    popularity REAL,
    budget INTEGER,
    revenue INTEGER,
    adult BOOLEAN DEFAULT FALSE,
    video BOOLEAN DEFAULT FALSE,
    original_language TEXT DEFAULT 'en',
    content_type TEXT DEFAULT 'movie',
    poster_path TEXT,
    backdrop_path TEXT,
    homepage TEXT,
    imdb_id TEXT,
    genres TEXT,  -- JSON array of genre IDs
    cast TEXT,    -- JSON array of cast data
    crew TEXT,    -- JSON array of crew data
    production_companies TEXT,  -- JSON array
    production_countries TEXT,  -- JSON array
    spoken_languages TEXT,      -- JSON array
    videos TEXT,               -- JSON array
    images TEXT,               -- JSON object
    reviews TEXT,              -- JSON array
    keywords TEXT,             -- JSON array
    collections TEXT,          -- JSON array
    recommendations TEXT,      -- JSON array
    similar TEXT,              -- JSON array
    features TEXT,             -- JSON object
    embeddings TEXT,           -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

USER_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_name TEXT,
    last_name TEXT,
    avatar_url TEXT,
    bio TEXT,
    location TEXT,
    birth_date TEXT,
    gender TEXT,
    preferred_genres TEXT,     -- JSON array
    preferred_languages TEXT,  -- JSON array
    preferred_countries TEXT,  -- JSON array
    content_rating_preference TEXT DEFAULT 'PG-13',
    watchlist_public BOOLEAN DEFAULT FALSE,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    onboarding_step INTEGER DEFAULT 0,
    onboarding_data TEXT,      -- JSON object
    features TEXT,             -- JSON object
    embeddings TEXT,           -- JSON object
    total_watched INTEGER DEFAULT 0,
    total_rated INTEGER DEFAULT 0,
    total_reviews INTEGER DEFAULT 0,
    average_rating REAL DEFAULT 0.0
);
"""

INTERACTION_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    interaction_type TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT,
    rating REAL,
    review_text TEXT,
    review_rating REAL,
    watch_duration INTEGER,
    watch_progress REAL,
    search_query TEXT,
    context TEXT,              -- JSON object
    device_type TEXT,
    platform TEXT,
    location TEXT,
    ip_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (movie_id) REFERENCES movies (id)
);
"""

RECOMMENDATION_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    score REAL NOT NULL,
    algorithm TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context TEXT,              -- JSON object
    reason TEXT,
    confidence REAL DEFAULT 1.0,
    diversity_score REAL DEFAULT 0.0,
    novelty_score REAL DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (movie_id) REFERENCES movies (id)
);
"""

FEATURE_VECTOR_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS feature_vectors (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    features TEXT NOT NULL,    -- JSON object
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version TEXT DEFAULT '1.0'
);
"""

# Indexes for better performance
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);",
    "CREATE INDEX IF NOT EXISTS idx_movies_release_date ON movies(release_date);",
    "CREATE INDEX IF NOT EXISTS idx_movies_popularity ON movies(popularity);",
    "CREATE INDEX IF NOT EXISTS idx_movies_vote_average ON movies(vote_average);",
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
    "CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON interactions(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_interactions_movie_id ON interactions(movie_id);",
    "CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_interactions_type ON interactions(interaction_type);",
    "CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_recommendations_movie_id ON recommendations(movie_id);",
    "CREATE INDEX IF NOT EXISTS idx_recommendations_score ON recommendations(score);",
    "CREATE INDEX IF NOT EXISTS idx_feature_vectors_entity ON feature_vectors(entity_type, entity_id);"
] 