#!/usr/bin/env python3
"""
Simple FastAPI app for CineAI authentication
"""

from fastapi import FastAPI, HTTPException, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
import sqlite3
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import random
import json
import pandas as pd
import sys
import numpy as np
import pickle

# Add the parent directory to the path to import the model
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import the recommendation model
try:
    from model.recommendation_model import HybridRecommendationModel
    recommendation_model = HybridRecommendationModel()
    print("✅ Successfully imported recommendation model")
except Exception as e:
    print(f"❌ Model file not found: {e}")
    recommendation_model = None

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    user_id: int
    username: str
    email: EmailStr

# Password hashing (bcrypt only uses first 72 bytes)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _truncate_password_for_bcrypt(password: str) -> str:
    b = password.encode("utf-8")[:72]
    return b.decode("utf-8", errors="ignore")

# JWT settings
ALGORITHM = "HS256"
SECRET_KEY = "dev_secret_key_change_in_production"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    print("✅ Database initialized")
    load_movie_data()
    load_model_data()
    yield
    # Shutdown
    print("🛑 Server shutting down")

app = FastAPI(title="CineAI API", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database functions
def get_db():
    # Create a new connection for each request to avoid threading issues
    conn = sqlite3.connect("../cineai.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database"""
    conn = sqlite3.connect("../cineai.db", check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR UNIQUE NOT NULL,
            email VARCHAR UNIQUE NOT NULL,
            hashed_password VARCHAR NOT NULL,
            signup_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            onboarding_completed BOOLEAN DEFAULT FALSE,
            onboarding_data TEXT DEFAULT '{}',
            favorite_genres TEXT DEFAULT '[]',
            favorite_movies TEXT DEFAULT '[]'
        )
    ''')
    
    # Add onboarding columns if they don't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN onboarding_data TEXT DEFAULT '{}'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN favorite_genres TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN favorite_movies TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.commit()
    conn.close()

def get_user_by_email(db, email: str):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    return cursor.fetchone()

def get_user_by_username(db, username: str):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    return cursor.fetchone()

def create_user(db, user: UserCreate):
    hashed_pw = pwd_context.hash(_truncate_password_for_bcrypt(user.password))
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
        (user.username, user.email, hashed_pw)
    )
    db.commit()
    
    # Get the created user
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (cursor.lastrowid,))
    return cursor.fetchone()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_truncate_password_for_bcrypt(plain_password), hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(request: Request, db = Depends(get_db)):
    # Check Authorization header
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]

    # Fall back to cookie
    if not token:
        token = request.cookies.get("cineai_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (int(user_id),))
    user = cursor.fetchone()
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

# API endpoints
@app.post("/api/signup", response_model=UserOut)
def signup(user: UserCreate, db = Depends(get_db)):
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already taken.")
    
    created_user = create_user(db, user)
    return UserOut(
        user_id=created_user["user_id"],
        username=created_user["username"],
        email=created_user["email"]
    )

@app.post("/api/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db = Depends(get_db)
):
    try:
        login_str = form_data.username
        user = get_user_by_email(db, login_str) or get_user_by_username(db, login_str)
        
        if not user or not verify_password(form_data.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Incorrect username/email or password")
        
        token_data = {"sub": str(user["user_id"])}
        access_token = create_access_token(token_data)
        
        # Set cookie
        response.set_cookie(
            key="cineai_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
            path="/"
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Login error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie("cineai_token", path="/")
    return {"msg": "Logged out"}

@app.get("/api/me", response_model=UserOut)
def get_me(current_user = Depends(get_current_user)):
    return UserOut(
        user_id=current_user["user_id"],
        username=current_user["username"],
        email=current_user["email"]
    )

@app.get("/")
async def root():
    return {"message": "Welcome to CineAI API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "CineAI Backend is running"}

@app.get("/api/health")
async def api_health_check():
    return {"status": "healthy", "message": "CineAI API is running"}

@app.get("/api/recommendations/onboarding/status")
def get_onboarding_status(current_user = Depends(get_current_user), db = Depends(get_db)):
    """Get onboarding status for current user"""
    try:
        cursor = db.cursor()
        
        # First, ensure the onboarding columns exist
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE")
            db.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN onboarding_data TEXT DEFAULT '{}'")
            db.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Now get the user's onboarding status
        cursor.execute("SELECT onboarding_completed, onboarding_data FROM users WHERE user_id = ?", (current_user["user_id"],))
        result = cursor.fetchone()
        
        if result:
            # Handle NULL values - if onboarding_completed is NULL, treat as False
            onboarding_completed = bool(result["onboarding_completed"]) if result["onboarding_completed"] is not None else False
            onboarding_data = json.loads(result["onboarding_data"]) if result["onboarding_data"] and result["onboarding_data"] != '{}' else {}
            
            return {
                "onboarding_completed": onboarding_completed,
                "onboarding_data": onboarding_data
            }
        else:
            return {
                "onboarding_completed": False,
                "onboarding_data": {}
            }
    except Exception as e:
        print(f"Error getting onboarding status: {e}")
        # Return False for onboarding_completed to allow user to complete onboarding
        return {
            "onboarding_completed": False,
            "onboarding_data": {}
        }

@app.post("/api/recommendations/onboarding/complete")
def complete_onboarding(
    onboarding_data: dict,
    current_user = Depends(get_current_user), 
    db = Depends(get_db)
):
    """Mark onboarding as completed"""
    cursor = db.cursor()
    
    # Ensure the column exists
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE")
        db.commit()
    except:
        # Column might already exist
        pass
    
    cursor.execute("UPDATE users SET onboarding_completed = TRUE WHERE user_id = ?", (current_user["user_id"],))
    db.commit()
    return {"message": "Onboarding completed successfully"}

@app.post("/api/recommendations/onboarding/update")
def update_onboarding(
    onboarding_data: dict,
    current_user = Depends(get_current_user), 
    db = Depends(get_db)
):
    """Update onboarding data and mark as completed"""
    cursor = db.cursor()
    
    # Ensure the columns exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE")
        db.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN onboarding_data TEXT DEFAULT '{}'")
        db.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Store the onboarding data as JSON and mark as completed
    onboarding_data_json = json.dumps(onboarding_data)
    cursor.execute(
        "UPDATE users SET onboarding_completed = TRUE, onboarding_data = ? WHERE user_id = ?", 
        (onboarding_data_json, current_user["user_id"])
    )
    db.commit()
    return {"message": "Onboarding updated and completed successfully"}

@app.get("/api/recommendations")
def get_recommendations(current_user: dict = Depends(get_current_user), db = Depends(get_db), limit: int = 10):
    """Get personalized movie recommendations"""
    try:
        # Get user onboarding status and preferences
        cursor = db.cursor()
        
        # First check if onboarding columns exist, if not create them
        try:
            cursor.execute("SELECT onboarding_completed FROM users WHERE user_id = ?", (current_user["user_id"],))
        except sqlite3.OperationalError:
            # Add missing columns
            cursor.execute("ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE")
            cursor.execute("ALTER TABLE users ADD COLUMN onboarding_data TEXT DEFAULT '{}'")
            cursor.execute("ALTER TABLE users ADD COLUMN favorite_genres TEXT DEFAULT '[]'")
            cursor.execute("ALTER TABLE users ADD COLUMN favorite_movies TEXT DEFAULT '[]'")
            db.commit()
            cursor.execute("SELECT onboarding_completed FROM users WHERE user_id = ?", (current_user["user_id"],))
        
        result = cursor.fetchone()
        onboarding_completed = result and result["onboarding_completed"] if result else False
        
        # Get recommendations based on onboarding status
        if onboarding_completed:
            recommendations = get_personalized_recommendations(current_user["user_id"], limit, db)
        else:
            recommendations = get_fallback_recommendations(limit)
        
        return {
            "recommendations": recommendations,
            "onboarding_completed": onboarding_completed,
            "total_count": len(recommendations)
        }
        
    except Exception as e:
        print(f"❌ Error getting recommendations: {e}")
        return {
            "recommendations": get_fallback_recommendations(limit),
            "onboarding_completed": False,
            "total_count": 0,
            "error": "Failed to get personalized recommendations"
        }

def get_content_based_recommendations(user_preferences: dict, available_movies: list, limit: int) -> list:
    """Content-based recommendation system using user preferences"""
    if not user_preferences or not available_movies:
        return available_movies[:limit]
    
    # Extract preferences
    favorite_genres = user_preferences.get('favorite_genres', [])
    favorite_movies = user_preferences.get('favorite_movies', [])
    preferred_directors = user_preferences.get('preferred_directors', [])
    
    # Score movies based on preferences
    scored_movies = []
    for movie in available_movies:
        score = 0.0
        
        # Genre matching (highest weight)
        movie_genres = movie.get('genres', [])
        if isinstance(movie_genres, str):
            movie_genres = [g.strip() for g in movie_genres.split(',')]
        
        for genre in favorite_genres:
            if genre in movie_genres:
                score += 3.0
        
        # Director matching
        movie_director = movie.get('director', '').lower()
        for director in preferred_directors:
            if director.lower() in movie_director:
                score += 2.0
        
        # Rating bonus
        rating = movie.get('rating', 0)
        score += rating * 0.5
        
        # Popularity bonus
        popularity = movie.get('popularity', 0)
        score += popularity * 0.1
        
        # Release year bonus (prefer newer movies)
        release_year = movie.get('release_year', 0)
        if release_year >= 2000:
            score += 0.5
        
        scored_movies.append((movie, score))
    
    # Sort by score and return top-k
    scored_movies.sort(key=lambda x: x[1], reverse=True)
    recommendations = [movie for movie, score in scored_movies[:limit]]
    
    print(f"✅ Generated {len(recommendations)} content-based recommendations")
    return recommendations

@app.get("/api/movies/search")
def search_movies(query: str):
    """Search movies by title - no authentication required"""
    if not movie_data is not None:
        return []
    
    if len(query.strip()) < 2:
        return []
    
    query = query.strip().lower()
    print(f"🔍 Searching for: '{query}' in {len(movie_data)} movies")
    
    # Multi-strategy search
    exact_matches = movie_data[movie_data['title'].str.lower() == query]
    starts_with = movie_data[movie_data['title'].str.lower().str.startswith(query)]
    contains = movie_data[movie_data['title'].str.lower().str.contains(query, na=False)]
    
    print(f"📊 Exact matches: {len(exact_matches)}")
    print(f"📊 Starts with matches: {len(starts_with)}")
    print(f"📊 Contains matches: {len(contains)}")
    
    # Combine and deduplicate
    all_matches = pd.concat([exact_matches, starts_with, contains]).drop_duplicates(subset=['id'])
    
    # Sort by relevance (exact matches first, then popularity)
    all_matches['relevance'] = 0
    all_matches.loc[all_matches['title'].str.lower() == query, 'relevance'] = 3
    all_matches.loc[all_matches['title'].str.lower().str.startswith(query), 'relevance'] = 2
    all_matches.loc[all_matches['title'].str.lower().str.contains(query), 'relevance'] = 1
    
    all_matches = all_matches.sort_values(['relevance', 'vote_average', 'popularity'], ascending=[False, False, False])
    
    print(f"📊 Total unique matches after deduplication: {len(all_matches)}")
    
    # Format results
    results = []
    for _, movie in all_matches.head(20).iterrows():
        results.append({
            "id": int(movie['id']),
            "title": movie['title'],
            "year": movie.get('release_year'),
            "director": movie.get('director', 'Unknown'),
            "genres": movie.get('genres_list', []),
            "poster_url": movie.get('poster_url'),
            "overview": str(movie.get('overview', ''))[:100] + "..." if len(str(movie.get('overview', ''))) > 100 else str(movie.get('overview', '')),
            "vote_average": float(movie.get('vote_average', 0)),
            "popularity": float(movie.get('popularity', 0))
        })
    
    print(f"✅ Returning {len(results)} results for query '{query}'")
    return results

def load_movie_data():
    """Load TMDB movie dataset"""
    global movie_data
    try:
        movie_data = pd.read_csv("../TMDB_movie_dataset_v11-2.csv")
        print(f"✅ Loaded {len(movie_data)} movies from TMDB dataset")
        
        # Clean and process the data
        movie_data = movie_data.dropna(subset=['title', 'id'])
        movie_data['id'] = movie_data['id'].astype(int)
        
        # Process genres
        movie_data['genres_list'] = movie_data['genres'].apply(
            lambda x: [g.strip() for g in str(x).split(',')] if pd.notnull(x) and str(x) != 'nan' else []
        )
        
        # Process director information - try multiple approaches
        movie_data['director'] = "Unknown"  # Default value
        
        print("🔍 No crew information found, trying alternative sources...")
        
        # Check if there's a director column
        if 'director' in movie_data.columns:
            print("✅ Using existing director column")
            # Keep existing director data
        else:
            # Try to extract from other columns
            if 'crew' in movie_data.columns:
                print("✅ Found crew column, extracting directors...")
                movie_data['director'] = movie_data['crew'].apply(extract_director)
            elif 'production_companies' in movie_data.columns:
                print("⚠️  Using production companies as fallback for director info")
                movie_data['director'] = movie_data['production_companies'].apply(
                    lambda x: str(x).split(',')[0] if pd.notnull(x) and str(x) != 'nan' else "Unknown"
                )
            else:
                print("⚠️  No director information available, setting all to 'Unknown'")
        
        # Ensure poster paths are complete URLs
        if 'poster_path' in movie_data.columns:
            movie_data['poster_url'] = movie_data['poster_path'].apply(
                lambda x: f"https://image.tmdb.org/t/p/w500{x}" if pd.notnull(x) and str(x) != 'nan' and str(x) != '' else None
            )
        else:
            movie_data['poster_url'] = None
            print("⚠️  Poster path column not found, setting all poster URLs to None")
        
        # Add year extraction for better movie identification
        movie_data['release_year'] = movie_data['release_date'].apply(
            lambda x: int(str(x)[:4]) if pd.notnull(x) and str(x) != 'nan' else 1900
        )
        
        # Try to get director information for top-rated movies using TMDB API
        print("🎬 Attempting to get director info for top movies...")
        try:
            # Get top 100 movies by rating
            top_movies = movie_data.sort_values(['vote_average', 'vote_count'], ascending=[False, False]).head(100)
            
            # For now, we'll use a simple approach - in production you'd use the TMDB API
            # For popular movies, we can try to infer directors from titles or use a lookup
            director_lookup = {
                'The Shawshank Redemption': 'Frank Darabont',
                'The Godfather': 'Francis Ford Coppola',
                'The Dark Knight': 'Christopher Nolan',
                'Pulp Fiction': 'Quentin Tarantino',
                'Fight Club': 'David Fincher',
                'Inception': 'Christopher Nolan',
                'The Matrix': 'Lana Wachowski',
                'Goodfellas': 'Martin Scorsese',
                'The Silence of the Lambs': 'Jonathan Demme',
                'Interstellar': 'Christopher Nolan',
                'The Departed': 'Martin Scorsese',
                'The Green Mile': 'Frank Darabont',
                'The Prestige': 'Christopher Nolan',
                'Forrest Gump': 'Robert Zemeckis',
                'The Lion King': 'Roger Allers',
                'Spirited Away': 'Hayao Miyazaki',
                'The Pianist': 'Roman Polanski',
                'Parasite': 'Bong Joon-ho',
                'Joker': 'Todd Phillips',
                '1917': 'Sam Mendes'
            }
            
            # Update director information for known movies
            for title, director in director_lookup.items():
                mask = movie_data['title'] == title
                if mask.any():
                    movie_data.loc[mask, 'director'] = director
            
            print(f"✅ Updated director info for {len(director_lookup)} popular movies")
            
        except Exception as e:
            print(f"⚠️  Could not update director info: {e}")
        
        print(f"✅ Successfully processed movie data with {len(movie_data)} movies")
        print(f"📊 Director info available for: {(movie_data['director'] != 'Unknown').sum()} movies")
        
    except Exception as e:
        print(f"❌ Error loading movie data: {e}")
        movie_data = None

def extract_director(crew_str):
    """Extract director name from crew JSON string"""
    try:
        if pd.isna(crew_str) or crew_str == 'nan':
            return "Unknown"
        
        # Try to parse as JSON
        crew_data = json.loads(crew_str)
        for person in crew_data:
            if person.get('job') == 'Director':
                return person.get('name', 'Unknown')
        return "Unknown"
    except:
        return "Unknown"

def load_model_data():
    """Load the trained model and related data"""
    global recommendation_model, movie2idx, idx2movie, embeddings_matrix
    
    if recommendation_model is None:
        print("❌ Recommendation model not available")
        return
    
    try:
        # Load movie mappings
        with open("../Checkpoints/movie2idx.pkl", "rb") as f:
            movie2idx = pickle.load(f)
        with open("../Checkpoints/idx2movie.pkl", "rb") as f:
            idx2movie = pickle.load(f)
        
        # Load embeddings
        embeddings_matrix = np.load("../Checkpoints/X_emb_matrix.npy")
        
        print("✅ Successfully loaded model data")
        print(f"   - Movie mappings: {len(movie2idx)} movies")
        print(f"   - Embeddings matrix: {embeddings_matrix.shape}")
        
    except Exception as e:
        print(f"❌ Error loading model data: {e}")
        recommendation_model = None

def get_personalized_recommendations(user_id: int, limit: int = 10, db = None):
    """Get personalized recommendations based on user preferences"""
    if movie_data is None:
        return get_fallback_recommendations(limit)
    
    try:
        # Get user's onboarding data to understand preferences
        user_preferences = get_user_preferences(user_id, db)
        
        if not user_preferences:
            return get_fallback_recommendations(limit)
        
        # Get favorite genres from onboarding
        favorite_genres = user_preferences.get('genres', [])
        favorite_movies = user_preferences.get('favorite_movies', [])
        
        # Filter movies by favorite genres first
        if favorite_genres:
            genre_filter = movie_data['genres_list'].apply(
                lambda genres: any(genre in favorite_genres for genre in genres)
            )
            filtered_movies = movie_data[genre_filter]
        else:
            filtered_movies = movie_data
        
        # Remove movies that user already selected in onboarding
        if favorite_movies:
            # Extract movie titles from "Title (Year)" format
            selected_titles = [movie.split(' (')[0] for movie in favorite_movies]
            filtered_movies = filtered_movies[
                ~filtered_movies['title'].isin(selected_titles)
            ]
        
        # Sort by rating and popularity for better quality
        filtered_movies = filtered_movies.sort_values(
            ['vote_average', 'vote_count'], 
            ascending=[False, False]
        )
        
        # Get top 100 movies for model processing (to avoid too many candidates)
        top_candidates = filtered_movies.head(100)
        
        # Convert to list of dictionaries for model
        available_movies = []
        for _, row in top_candidates.iterrows():
            movie = {
                "id": int(row['id']),
                "title": row['title'],
                "overview": str(row.get('overview', ''))[:200] + "..." if len(str(row.get('overview', ''))) > 200 else str(row.get('overview', '')),
                "poster_url": row.get('poster_url'),
                "rating": float(row.get('vote_average', 0)),
                "genres": row.get('genres_list', [])[:3],
                "director": row.get('director', 'Unknown'),
                "release_year": int(row.get('release_year', 1900)),
                "vote_count": int(row.get('vote_count', 0)),
                "popularity": float(row.get('popularity', 0))
            }
            available_movies.append(movie)
        
        # Use trained model if available
        if recommendation_model is not None and recommendation_model.model is not None:
            print(f"🎯 Using trained PerformerRecSys model for user {user_id}")
            try:
                recommendations = recommendation_model.get_recommendations(
                    user_id=user_id,
                    user_preferences=user_preferences,
                    available_movies=available_movies,
                    top_k=limit
                )
                if recommendations:
                    return recommendations
            except Exception as e:
                print(f"❌ Model recommendation failed: {e}")
        
        # Fallback to improved content-based filtering
        print("🔄 Using improved content-based recommendations")
        return get_improved_content_based_recommendations(user_preferences, available_movies, limit)
        
    except Exception as e:
        print(f"Error getting personalized recommendations: {e}")
        return get_fallback_recommendations(limit)

def get_improved_content_based_recommendations(user_preferences: dict, available_movies: list, limit: int) -> list:
    """Improved content-based recommendation system"""
    if not user_preferences or not available_movies:
        return available_movies[:limit]
    
    # Extract preferences
    favorite_genres = user_preferences.get('genres', [])
    favorite_movies = user_preferences.get('favorite_movies', [])
    
    # Score movies based on preferences
    scored_movies = []
    for movie in available_movies:
        score = 0.0
        
        # Genre matching (highest weight)
        movie_genres = movie.get('genres', [])
        if isinstance(movie_genres, str):
            movie_genres = [g.strip() for g in movie_genres.split(',')]
        
        for genre in favorite_genres:
            if genre in movie_genres:
                score += 5.0  # Increased weight for genre matching
        
        # Rating bonus (higher weight for highly rated movies)
        rating = movie.get('rating', 0)
        if rating >= 8.0:
            score += 3.0
        elif rating >= 7.0:
            score += 2.0
        elif rating >= 6.0:
            score += 1.0
        
        # Vote count bonus (more votes = more reliable rating)
        vote_count = movie.get('vote_count', 0)
        if vote_count >= 10000:
            score += 2.0
        elif vote_count >= 1000:
            score += 1.0
        
        # Release year bonus (prefer newer movies but not too new)
        release_year = movie.get('release_year', 0)
        if 1990 <= release_year <= 2023:
            score += 1.0
        
        # Popularity bonus
        popularity = movie.get('popularity', 0)
        score += popularity * 0.01
        
        scored_movies.append((movie, score))
    
    # Sort by score and return top-k
    scored_movies.sort(key=lambda x: x[1], reverse=True)
    recommendations = [movie for movie, score in scored_movies[:limit]]
    
    print(f"✅ Generated {len(recommendations)} improved content-based recommendations")
    return recommendations

def get_user_preferences(user_id: int, db = None):
    """Get user preferences from onboarding data"""
    try:
        # Use provided db connection or create a new one
        if db is None:
            conn = sqlite3.connect("../cineai.db", check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            should_close = True
        else:
            cursor = db.cursor()
            should_close = False
        
        cursor.execute("SELECT onboarding_data FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result and result["onboarding_data"]:
            preferences = json.loads(result["onboarding_data"])
            if should_close:
                conn.close()
            return preferences
        
        if should_close:
            conn.close()
        return {}
        
    except Exception as e:
        print(f"Error getting user preferences: {e}")
        return {}

def get_fallback_recommendations(limit: int = 10):
    """Get fallback recommendations when model is not available"""
    if movie_data is None:
        return []
    
    try:
        # Get top-rated movies
        top_movies = movie_data.sort_values(['vote_average', 'vote_count'], ascending=[False, False]).head(limit)
        
        formatted_recommendations = []
        for _, movie in top_movies.iterrows():
            formatted_recommendations.append({
                "id": int(movie['id']),
                "title": movie['title'],
                "overview": str(movie.get('overview', ''))[:200] + "..." if len(str(movie.get('overview', ''))) > 200 else str(movie.get('overview', '')),
                "poster_url": movie.get('poster_url'),
                "rating": float(movie.get('vote_average', 0)),
                "genres": movie.get('genres_list', [])[:3],
                "director": movie.get('director', 'Unknown'),
                "release_year": int(movie.get('release_year', 1900)),
                "vote_count": int(movie.get('vote_count', 0))
            })
        
        return formatted_recommendations
        
    except Exception as e:
        print(f"Error getting fallback recommendations: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CineAI Simple Backend...")
    print("   API: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print("   Press Ctrl+C to stop")
    print()
    
    # Run the server directly without reload to avoid the warning
    uvicorn.run(
        "simple_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    ) 