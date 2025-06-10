"""
ETL Pipeline for CineAI Data Engine

This module handles the Extract, Transform, Load pipeline for processing
movie data and preparing it for the recommendation system.
"""

import json
import logging
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re
from collections import Counter
import pickle

# Add the project root to the path
import sys
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data_engine.config import DATABASE_CONFIG, DATA_CONFIG, FEATURE_CONFIG, BASE_DIR, DATA_DIR
from data_engine.schema import Movie, Genre, Person, CastMember, CrewMember

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ETLPipeline:
    """Main ETL pipeline for processing movie data."""
    
    def __init__(self, data_dir: Optional[Path] = None, db_path: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.db_path = db_path or DATABASE_CONFIG["sqlite"]["path"]
        self.processed_dir = self.data_dir / "processed"
        self.processed_dir.mkdir(exist_ok=True)
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def run_pipeline(self, input_file: str) -> Dict[str, Any]:
        """
        Run the complete ETL pipeline.
        
        Args:
            input_file: Name of the input file (JSONL or CSV)
        
        Returns:
            Dictionary with pipeline results
        """
        logger.info("Starting ETL pipeline...")
        
        try:
            # Extract
            raw_data = self._extract_data(input_file)
            logger.info(f"Extracted {len(raw_data)} records")
            
            # Transform
            transformed_data = self._transform_data(raw_data)
            logger.info(f"Transformed {len(transformed_data)} records")
            
            # Feature Engineering
            engineered_data = self._engineer_features(transformed_data)
            logger.info(f"Feature engineering completed for {len(engineered_data)} records")
            
            # Load
            load_results = self._load_data(engineered_data)
            logger.info("Data loading completed")
            
            # Save processed data
            self._save_processed_data(engineered_data)
            
            return {
                "status": "success",
                "records_processed": len(engineered_data),
                "files_created": self._get_created_files(),
                "load_results": load_results,
                "timestamp": self.timestamp
            }
            
        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}")
            raise
    
    def _extract_data(self, input_file: str) -> List[Dict[str, Any]]:
        """Extract data from input file."""
        input_path = self.data_dir / "raw" / input_file
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        logger.info(f"Extracting data from {input_path}")
        
        if input_file.endswith('.jsonl'):
            return self._extract_jsonl(input_path)
        elif input_file.endswith('.csv'):
            return self._extract_csv(input_path)
        else:
            raise ValueError(f"Unsupported file format: {input_file}")
    
    def _extract_jsonl(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract data from JSONL file."""
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data
    
    def _extract_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract data from CSV file."""
        df = pd.read_csv(file_path)
        return df.to_dict('records')
    
    def _transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw data into clean, structured format."""
        logger.info("Transforming data...")
        
        transformed_data = []
        
        for record in raw_data:
            try:
                transformed_record = self._transform_movie_record(record)
                if transformed_record:
                    transformed_data.append(transformed_record)
            except Exception as e:
                logger.warning(f"Failed to transform record {record.get('tmdb_id', 'unknown')}: {e}")
                continue
        
        return transformed_data
    
    def _transform_movie_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform a single movie record."""
        # Basic validation
        if not record.get('tmdb_id') or not record.get('title'):
            return None
        
        # Clean and standardize text fields
        transformed = {
            'tmdb_id': int(record['tmdb_id']),
            'imdb_id': record.get('imdb_id'),
            'title': self._clean_text(record['title']),
            'original_title': self._clean_text(record.get('original_title', '')),
            'overview': self._clean_text(record.get('overview', '')),
            'tagline': self._clean_text(record.get('tagline', '')),
            'release_date': self._parse_date(record.get('release_date')),
            'runtime': self._parse_int(record.get('runtime')),
            'budget': self._parse_int(record.get('budget')),
            'revenue': self._parse_int(record.get('revenue')),
            'popularity': self._parse_float(record.get('popularity', 0)),
            'vote_average': self._parse_float(record.get('vote_average', 0)),
            'vote_count': self._parse_int(record.get('vote_count', 0)),
            'adult': bool(record.get('adult', False)),
            'video': bool(record.get('video', False)),
            'status': record.get('status', 'Unknown'),
            'poster_path': record.get('poster_path'),
            'backdrop_path': record.get('backdrop_path'),
            'homepage': record.get('homepage')
        }
        
        # Process genres
        transformed['genres'] = self._process_genres(record.get('genres', []))
        
        # Process production companies
        transformed['production_companies'] = self._process_production_companies(
            record.get('production_companies', [])
        )
        
        # Process countries and languages
        transformed['production_countries'] = self._process_countries(
            record.get('production_countries', [])
        )
        transformed['spoken_languages'] = self._process_languages(
            record.get('spoken_languages', [])
        )
        
        # Process cast and crew
        transformed['cast'] = self._process_cast(record.get('cast', []))
        transformed['crew'] = self._process_crew(record.get('crew', []))
        
        # Extract directors and writers
        transformed['directors'] = self._extract_directors(transformed['crew'])
        transformed['writers'] = self._extract_writers(transformed['crew'])
        
        # Calculate derived fields
        transformed['year'] = self._extract_year(transformed['release_date'])
        transformed['decade'] = self._calculate_decade(transformed['year'])
        transformed['is_english'] = self._is_english_movie(transformed['spoken_languages'])
        
        return transformed
    
    def _clean_text(self, text: str) -> str:
        """Clean and standardize text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\-.,!?()\'"&]', '', text)
        
        return text
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse and validate date string."""
        if not date_str:
            return None
        
        try:
            # Try to parse the date
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            return None
    
    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse integer value."""
        if value is None or value == "":
            return None
        
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _parse_float(self, value: Any) -> float:
        """Parse float value."""
        if value is None or value == "":
            return 0.0
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _process_genres(self, genres: List[Dict[str, Any]]) -> List[str]:
        """Process genres list."""
        if isinstance(genres, str):
            # Handle pipe-separated string
            return [g.strip() for g in genres.split('|') if g.strip()]
        elif isinstance(genres, list):
            # Handle list of dictionaries
            return [g.get('name', '') for g in genres if g.get('name')]
        else:
            return []
    
    def _process_production_companies(self, companies: List[Dict[str, Any]]) -> List[str]:
        """Process production companies."""
        if isinstance(companies, str):
            return [c.strip() for c in companies.split('|') if c.strip()]
        elif isinstance(companies, list):
            return [c.get('name', '') for c in companies if c.get('name')]
        else:
            return []
    
    def _process_countries(self, countries: List[Dict[str, Any]]) -> List[str]:
        """Process production countries."""
        if isinstance(countries, str):
            return [c.strip() for c in countries.split('|') if c.strip()]
        elif isinstance(countries, list):
            return [c.get('name', '') for c in countries if c.get('name')]
        else:
            return []
    
    def _process_languages(self, languages: List[Dict[str, Any]]) -> List[str]:
        """Process spoken languages."""
        if isinstance(languages, str):
            return [l.strip() for l in languages.split('|') if l.strip()]
        elif isinstance(languages, list):
            return [l.get('name', '') for l in languages if l.get('name')]
        else:
            return []
    
    def _process_cast(self, cast: List[Dict[str, Any]]) -> List[str]:
        """Process cast members."""
        if isinstance(cast, str):
            return [c.strip() for c in cast.split('|') if c.strip()]
        elif isinstance(cast, list):
            return [c.get('name', '') for c in cast if c.get('name')]
        else:
            return []
    
    def _process_crew(self, crew: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Process crew members."""
        if isinstance(crew, str):
            return []
        elif isinstance(crew, list):
            return [{'name': c.get('name', ''), 'job': c.get('job', '')} 
                   for c in crew if c.get('name')]
        else:
            return []
    
    def _extract_directors(self, crew: List[Dict[str, str]]) -> List[str]:
        """Extract directors from crew."""
        director_jobs = ['Director', 'Co-Director', 'Assistant Director']
        return [c['name'] for c in crew if c['job'] in director_jobs]
    
    def _extract_writers(self, crew: List[Dict[str, str]]) -> List[str]:
        """Extract writers from crew."""
        writer_jobs = ['Writer', 'Screenplay', 'Story', 'Novel']
        return [c['name'] for c in crew if c['job'] in writer_jobs]
    
    def _extract_year(self, release_date: str) -> Optional[int]:
        """Extract year from release date."""
        if not release_date:
            return None
        
        try:
            return datetime.strptime(release_date, "%Y-%m-%d").year
        except ValueError:
            return None
    
    def _calculate_decade(self, year: Optional[int]) -> Optional[str]:
        """Calculate decade from year."""
        if not year:
            return None
        
        decade_start = (year // 10) * 10
        return f"{decade_start}s"
    
    def _is_english_movie(self, languages: List[str]) -> bool:
        """Check if movie is primarily in English."""
        english_variants = ['English', 'en', 'en-US', 'en-GB']
        return any(lang in english_variants for lang in languages)
    
    def _engineer_features(self, transformed_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Engineer features for machine learning."""
        logger.info("Engineering features...")
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(transformed_data)
        
        # Text features
        df = self._engineer_text_features(df)
        
        # Categorical features
        df = self._engineer_categorical_features(df)
        
        # Numerical features
        df = self._engineer_numerical_features(df)
        
        # Interaction features
        df = self._engineer_interaction_features(df)
        
        # Convert back to list of dictionaries
        return df.to_dict('records')
    
    def _engineer_text_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer text-based features."""
        # Overview length
        df['overview_length'] = df['overview'].str.len()
        df['overview_word_count'] = df['overview'].str.split().str.len()
        
        # Title length
        df['title_length'] = df['title'].str.len()
        df['title_word_count'] = df['title'].str.split().str.len()
        
        # Tagline features
        df['has_tagline'] = df['tagline'].notna() & (df['tagline'] != '')
        df['tagline_length'] = df['tagline'].str.len()
        
        # Cast and crew features
        df['cast_count'] = df['cast'].str.len()
        df['crew_count'] = df['crew'].str.len()
        df['director_count'] = df['directors'].str.len()
        df['writer_count'] = df['writers'].str.len()
        
        return df
    
    def _engineer_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer categorical features."""
        # Genre features
        df['genre_count'] = df['genres'].str.len()
        df['primary_genre'] = df['genres'].str[0]  # First genre as primary
        
        # Production features
        df['production_company_count'] = df['production_companies'].str.len()
        df['country_count'] = df['production_countries'].str.len()
        df['language_count'] = df['spoken_languages'].str.len()
        
        # Status features
        df['status_encoded'] = pd.Categorical(df['status']).codes
        
        return df
    
    def _engineer_numerical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer numerical features."""
        # Budget and revenue features
        df['budget_log'] = np.log1p(df['budget'].fillna(0))
        df['revenue_log'] = np.log1p(df['revenue'].fillna(0))
        df['profit'] = df['revenue'] - df['budget']
        df['profit_log'] = np.log1p(df['profit'].fillna(0))
        df['roi'] = (df['revenue'] - df['budget']) / df['budget'].replace(0, 1)
        
        # Rating features
        df['vote_average_weighted'] = (df['vote_average'] * df['vote_count']) / (df['vote_count'] + 1000)
        df['rating_popularity'] = df['vote_average'] * np.log1p(df['vote_count'])
        
        # Time-based features
        current_year = datetime.now().year
        df['age'] = current_year - df['year']
        df['age_log'] = np.log1p(df['age'])
        
        return df
    
    def _engineer_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer interaction-based features."""
        # Popularity features
        df['popularity_rank'] = df['popularity'].rank(ascending=False)
        df['vote_count_rank'] = df['vote_count'].rank(ascending=False)
        
        # Budget efficiency
        df['budget_efficiency'] = df['revenue'] / df['budget'].replace(0, 1)
        
        # Genre popularity
        genre_popularity = df.groupby('primary_genre')['popularity'].mean()
        df['genre_popularity'] = df['primary_genre'].map(genre_popularity)
        
        return df
    
    def _load_data(self, engineered_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Load processed data into database."""
        logger.info("Loading data into database...")
        
        # Create database connection
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create tables if they don't exist
            self._create_tables(cursor)
            
            # Load movies
            movies_loaded = self._load_movies(cursor, engineered_data)
            
            # Load genres
            genres_loaded = self._load_genres(cursor, engineered_data)
            
            # Load people (cast and crew)
            people_loaded = self._load_people(cursor, engineered_data)
            
            # Load relationships
            relationships_loaded = self._load_relationships(cursor, engineered_data)
            
            conn.commit()
            
            return {
                "movies_loaded": movies_loaded,
                "genres_loaded": genres_loaded,
                "people_loaded": people_loaded,
                "relationships_loaded": relationships_loaded
            }
            
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _create_tables(self, cursor: sqlite3.Cursor):
        """Create database tables."""
        # Movies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                tmdb_id INTEGER PRIMARY KEY,
                imdb_id TEXT,
                title TEXT NOT NULL,
                original_title TEXT,
                overview TEXT,
                tagline TEXT,
                release_date TEXT,
                runtime INTEGER,
                budget INTEGER,
                revenue INTEGER,
                popularity REAL,
                vote_average REAL,
                vote_count INTEGER,
                adult BOOLEAN,
                video BOOLEAN,
                status TEXT,
                poster_path TEXT,
                backdrop_path TEXT,
                homepage TEXT,
                year INTEGER,
                decade TEXT,
                is_english BOOLEAN,
                overview_length INTEGER,
                overview_word_count INTEGER,
                title_length INTEGER,
                title_word_count INTEGER,
                has_tagline BOOLEAN,
                tagline_length INTEGER,
                cast_count INTEGER,
                crew_count INTEGER,
                director_count INTEGER,
                writer_count INTEGER,
                genre_count INTEGER,
                primary_genre TEXT,
                production_company_count INTEGER,
                country_count INTEGER,
                language_count INTEGER,
                status_encoded INTEGER,
                budget_log REAL,
                revenue_log REAL,
                profit INTEGER,
                profit_log REAL,
                roi REAL,
                vote_average_weighted REAL,
                rating_popularity REAL,
                age INTEGER,
                age_log REAL,
                popularity_rank REAL,
                vote_count_rank REAL,
                budget_efficiency REAL,
                genre_popularity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Genres table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                movie_count INTEGER DEFAULT 0
            )
        """)
        
        # People table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                movie_count INTEGER DEFAULT 0,
                director_count INTEGER DEFAULT 0,
                writer_count INTEGER DEFAULT 0,
                actor_count INTEGER DEFAULT 0
            )
        """)
        
        # Movie-genre relationships
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movie_genres (
                movie_id INTEGER,
                genre_id INTEGER,
                PRIMARY KEY (movie_id, genre_id),
                FOREIGN KEY (movie_id) REFERENCES movies (tmdb_id),
                FOREIGN KEY (genre_id) REFERENCES genres (id)
            )
        """)
        
        # Movie-person relationships
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movie_people (
                movie_id INTEGER,
                person_id INTEGER,
                role TEXT,  -- 'director', 'writer', 'actor'
                character_name TEXT,
                credit_order INTEGER,
                PRIMARY KEY (movie_id, person_id, role),
                FOREIGN KEY (movie_id) REFERENCES movies (tmdb_id),
                FOREIGN KEY (person_id) REFERENCES people (id)
            )
        """)
    
    def _load_movies(self, cursor: sqlite3.Cursor, data: List[Dict[str, Any]]) -> int:
        """Load movies into database."""
        # Prepare movie data
        movie_fields = [
            'tmdb_id', 'imdb_id', 'title', 'original_title', 'overview', 'tagline',
            'release_date', 'runtime', 'budget', 'revenue', 'popularity', 'vote_average',
            'vote_count', 'adult', 'video', 'status', 'poster_path', 'backdrop_path',
            'homepage', 'year', 'decade', 'is_english', 'overview_length', 'overview_word_count',
            'title_length', 'title_word_count', 'has_tagline', 'tagline_length',
            'cast_count', 'crew_count', 'director_count', 'writer_count', 'genre_count',
            'primary_genre', 'production_company_count', 'country_count', 'language_count',
            'status_encoded', 'budget_log', 'revenue_log', 'profit', 'profit_log', 'roi',
            'vote_average_weighted', 'rating_popularity', 'age', 'age_log', 'popularity_rank',
            'vote_count_rank', 'budget_efficiency', 'genre_popularity'
        ]
        
        movies_to_insert = []
        for record in data:
            movie_data = [record.get(field) for field in movie_fields]
            movies_to_insert.append(movie_data)
        
        # Insert movies
        placeholders = ','.join(['?' for _ in movie_fields])
        cursor.executemany(
            f"INSERT OR REPLACE INTO movies ({','.join(movie_fields)}) VALUES ({placeholders})",
            movies_to_insert
        )
        
        return len(movies_to_insert)
    
    def _load_genres(self, cursor: sqlite3.Cursor, data: List[Dict[str, Any]]) -> int:
        """Load genres into database."""
        # Collect all unique genres
        all_genres = set()
        for record in data:
            all_genres.update(record.get('genres', []))
        
        # Insert genres
        genres_inserted = 0
        for genre in all_genres:
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO genres (name) VALUES (?)",
                    (genre,)
                )
                genres_inserted += cursor.rowcount
            except Exception as e:
                logger.warning(f"Failed to insert genre {genre}: {e}")
        
        return genres_inserted
    
    def _load_people(self, cursor: sqlite3.Cursor, data: List[Dict[str, Any]]) -> int:
        """Load people into database."""
        # Collect all unique people
        all_people = set()
        for record in data:
            all_people.update(record.get('directors', []))
            all_people.update(record.get('writers', []))
            all_people.update(record.get('cast', []))
        
        # Insert people
        people_inserted = 0
        for person in all_people:
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO people (name) VALUES (?)",
                    (person,)
                )
                people_inserted += cursor.rowcount
            except Exception as e:
                logger.warning(f"Failed to insert person {person}: {e}")
        
        return people_inserted
    
    def _load_relationships(self, cursor: sqlite3.Cursor, data: List[Dict[str, Any]]) -> int:
        """Load relationships into database."""
        relationships_inserted = 0
        
        for record in data:
            movie_id = record['tmdb_id']
            
            # Load genre relationships
            for genre in record.get('genres', []):
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) "
                        "SELECT ?, id FROM genres WHERE name = ?",
                        (movie_id, genre)
                    )
                    relationships_inserted += cursor.rowcount
                except Exception as e:
                    logger.warning(f"Failed to insert genre relationship: {e}")
            
            # Load people relationships
            for director in record.get('directors', []):
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO movie_people (movie_id, person_id, role) "
                        "SELECT ?, id, 'director' FROM people WHERE name = ?",
                        (movie_id, director)
                    )
                    relationships_inserted += cursor.rowcount
                except Exception as e:
                    logger.warning(f"Failed to insert director relationship: {e}")
            
            for writer in record.get('writers', []):
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO movie_people (movie_id, person_id, role) "
                        "SELECT ?, id, 'writer' FROM people WHERE name = ?",
                        (movie_id, writer)
                    )
                    relationships_inserted += cursor.rowcount
                except Exception as e:
                    logger.warning(f"Failed to insert writer relationship: {e}")
            
            for i, actor in enumerate(record.get('cast', [])):
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO movie_people (movie_id, person_id, role, credit_order) "
                        "SELECT ?, id, 'actor', ? FROM people WHERE name = ?",
                        (movie_id, i, actor)
                    )
                    relationships_inserted += cursor.rowcount
                except Exception as e:
                    logger.warning(f"Failed to insert actor relationship: {e}")
        
        return relationships_inserted
    
    def _save_processed_data(self, engineered_data: List[Dict[str, Any]]):
        """Save processed data to files."""
        logger.info("Saving processed data...")
        
        # Save as pickle for fast loading
        pickle_file = self.processed_dir / f"processed_movies_{self.timestamp}.pkl"
        with open(pickle_file, 'wb') as f:
            pickle.dump(engineered_data, f)
        
        # Save as JSON for inspection
        json_file = self.processed_dir / f"processed_movies_{self.timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(engineered_data, f, indent=2, default=str)
        
        # Save metadata
        metadata = {
            "timestamp": self.timestamp,
            "total_records": len(engineered_data),
            "files_created": [str(pickle_file), str(json_file)],
            "feature_columns": list(engineered_data[0].keys()) if engineered_data else []
        }
        
        metadata_file = self.processed_dir / f"etl_metadata_{self.timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)
    
    def _get_created_files(self) -> List[str]:
        """Get list of files created in this ETL run."""
        files = []
        for file in self.processed_dir.glob(f"*{self.timestamp}*"):
            files.append(str(file))
        return files


def main():
    """Main ETL function."""
    logger.info("Starting CineAI ETL pipeline...")
    
    # Find the most recent input file
    raw_dir = DATA_DIR / "raw"
    input_files = list(raw_dir.glob("tmdb_movies_*.jsonl"))
    
    if not input_files:
        logger.error("No input files found in data/raw/")
        logger.info("Please run the data extraction first:")
        logger.info("python data_engine/extract_data.py")
        return
    
    # Use the most recent file
    latest_file = max(input_files, key=lambda x: x.stat().st_mtime)
    logger.info(f"Using input file: {latest_file.name}")
    
    pipeline = ETLPipeline()
    
    try:
        result = pipeline.run_pipeline(latest_file.name)
        logger.info("ETL pipeline completed successfully!")
        logger.info(f"Processed {result['records_processed']} records")
        logger.info(f"Files created: {result['files_created']}")
        
    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main() 