#!/usr/bin/env python3
"""
Complete Training Script for Google Colab
Run this entire script in a single Colab cell or as a .py file
"""

# ============================================================================
# STEP 1: Setup - Mount Drive and Install Dependencies
# ============================================================================

print("=" * 70)
print("🚀 CineAI - Model Training on Google Colab")
print("=" * 70)

# Mount Google Drive (optional - uncomment if your project is in Drive)
# If you already uploaded/ cloned the project to Colab, you don't need this
"""
try:
    from google.colab import drive
    drive.mount('/content/drive')
    print("✅ Google Drive mounted")
except:
    print("ℹ️  Skipping drive mount (not needed if project is already in Colab)")
"""
print("ℹ️  Assuming project is already in Colab directory")

# Install dependencies
print("\n📦 Installing packages...")
import subprocess
import sys

packages_to_install = [
    "torch", "torchvision", "torchaudio",
    "--index-url", "https://download.pytorch.org/whl/cu118",
    "transformers", "pandas", "numpy", "scikit-learn", "tqdm"
]

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + packages_to_install)
print("✅ Packages installed!")

# ============================================================================
# STEP 2: Setup Paths
# ============================================================================

import os
from pathlib import Path
from glob import glob

# Navigate to project directory - EXPLICIT PATH
print(f"Starting directory: {os.getcwd()}")

# Try explicit path first (most common in Colab)
explicit_path = Path('/content/movie-recommendation-transformer')
if explicit_path.exists():
    os.chdir(explicit_path)
    project_path = explicit_path
    print(f"✅ Changed to: {os.getcwd()}")
else:
    # Try other common locations
    project_paths = [
        Path('/content/movie-recommendation-transformer'),
        Path(__file__).parent if '__file__' in globals() else Path.cwd(),
        Path.cwd(),
        Path('/content/drive/MyDrive/movie-recommendation-transformer'),
    ]
    
    project_path = None
    for path in project_paths:
        if path.exists():
            # Check if this looks like the project (has data/ directory)
            if (path / 'data').exists():
                project_path = path
                os.chdir(project_path)
                print(f"✅ Found project at: {os.getcwd()}")
                break
    
    if not project_path:
        print(f"\n⚠️  Project directory not found automatically.")
        print(f"Current directory: {os.getcwd()}")
        print("\n🔍 Searching for project...")
        
        # Quick search for data directory
        count = 0
        for root, dirs, files in os.walk('/content'):
            count += 1
            if count > 50:  # Limit search to first 50 directories
                break
            if 'data' in dirs and Path(root).name == 'movie-recommendation-transformer':
                os.chdir(root)
                project_path = Path(root)
                print(f"✅ Found project at: {os.getcwd()}")
                break
        
        if not project_path:
            print("\n❌ Project not found!")
            print("Please run this in Colab before the script:")
            print("   import os")
            print("   os.chdir('/content/movie-recommendation-transformer')")
            raise FileNotFoundError("Project directory not found. Please navigate to /content/movie-recommendation-transformer")

# ============================================================================
# STEP 3: Verify GPU and Data Files
# ============================================================================

import torch

# Check GPU
if torch.cuda.is_available():
    print(f"\n🎮 GPU: {torch.cuda.get_device_name(0)}")
    print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    device = 'cuda'
else:
    print("\n⚠️  No GPU detected. Training will be slow on CPU.")
    device = 'cpu'

# Check data files - search more thoroughly
print("\n📂 Checking data files...")
jsonl_path = None
csv_path = None

def find_file(pattern, search_dirs=None, max_depth=5):
    """Find file by pattern in search directories"""
    if search_dirs is None:
        search_dirs = [Path('.'), Path('/content')]
    
    found_files = []
    for search_dir in search_dirs:
        if not Path(search_dir).exists():
            continue
        # Use glob for pattern matching
        depth = 0
        for root, dirs, files in os.walk(search_dir):
            depth = root.count(os.sep) - str(search_dir).count(os.sep)
            if depth > max_depth:
                dirs.clear()  # Don't go deeper
                continue
            for file in files:
                if pattern in file.lower():
                    full_path = Path(root) / file
                    if full_path.exists():
                        found_files.append(str(full_path))
    return found_files

# Search for movie data file (try multiple patterns)
print("  Searching for movie data file...")
movie_patterns = [
    "tmdb_movies_50k",
    "tmdb_movies",
    "tmdb_complete_dataset",
    "movies.jsonl",
]

all_jsonl_files = []
for pattern in movie_patterns:
    found = find_file(pattern)
    all_jsonl_files.extend(found)

# Remove duplicates and prefer the largest file (likely the most complete)
if all_jsonl_files:
    # Sort by file size (largest first)
    jsonl_files_sorted = sorted(
        [(f, Path(f).stat().st_size) for f in set(all_jsonl_files)],
        key=lambda x: x[1],
        reverse=True
    )
    jsonl_path = jsonl_files_sorted[0][0]
    size = jsonl_files_sorted[0][1] / (1024 * 1024)  # MB
    print(f"  ✅ Movies: {jsonl_path} ({size:.1f} MB)")
else:
    # Try direct paths as fallback
    possible_jsonl_paths = [
        "data/raw/tmdb_movies_50k_20250711_011112.jsonl",
        "data/raw/tmdb_complete_dataset.jsonl",
        "data/raw/tmdb_movies_*.jsonl",
    ]
    
    for path_str in possible_jsonl_paths:
        # Handle wildcards
        if '*' in path_str:
            matches = glob(path_str)
            if matches:
                path = Path(matches[0])
                jsonl_path = str(path)
                size = path.stat().st_size / (1024 * 1024)
                print(f"  ✅ Movies: {jsonl_path} ({size:.1f} MB)")
                break
        else:
            path = Path(path_str)
            if path.exists():
                jsonl_path = str(path)
                size = path.stat().st_size / (1024 * 1024)
                print(f"  ✅ Movies: {jsonl_path} ({size:.1f} MB)")
                break

# Search for ratings CSV
print("  Searching for ratings data file...")
csv_patterns = [
    "realistic_synthetic_ratings",
    "synthetic_ratings",
    "ratings.csv",
]

all_csv_files = []
for pattern in csv_patterns:
    found = find_file(pattern)
    all_csv_files.extend(found)

if all_csv_files:
    csv_files_sorted = sorted(
        [(f, Path(f).stat().st_size) for f in set(all_csv_files)],
        key=lambda x: x[1],
        reverse=True
    )
    csv_path = csv_files_sorted[0][0]
    size = csv_files_sorted[0][1] / (1024 * 1024)
    print(f"  ✅ Ratings: {csv_path} ({size:.1f} MB)")
else:
    # Try direct paths
    possible_csv_paths = [
        "data/realistic_synthetic_ratings_new_data.csv",
        "data/synthetic_ratings.csv",
    ]
    for path_str in possible_csv_paths:
        path = Path(path_str)
        if path.exists():
            csv_path = str(path)
            size = path.stat().st_size / (1024 * 1024)
            print(f"  ✅ Ratings: {csv_path} ({size:.1f} MB)")
            break

# Final check
if not jsonl_path:
    print(f"\n  ❌ Movie data file not found!")
    print(f"  Current directory: {os.getcwd()}")
    print(f"  Contents of data/raw/: {os.listdir('data/raw') if Path('data/raw').exists() else 'Directory not found'}")
    print(f"  Searched for patterns: {movie_patterns}")
    raise FileNotFoundError("Movie data file not found. Please check the file exists in data/raw/")

if not csv_path:
    print(f"\n  ❌ Ratings CSV file not found!")
    print(f"  Current directory: {os.getcwd()}")
    raise FileNotFoundError("Ratings CSV file not found")

# ============================================================================
# STEP 4: Import Training Functions
# ============================================================================

print("\n📚 Loading training modules...")
import json
import numpy as np
import logging
from typing import List, Dict, Any

# Add project to path
if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

# Import models
from models.content_transformer import MovieContentTransformer, ContentBasedRecommender
from models.collaborative_filtering import MatrixFactorization, CollaborativeFilteringRecommender
from models.context_transformer import ReviewContextTransformer, ContextualRecommender
from models.ensemble_recommender import MovieRecommendationEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# STEP 5: Data Loading Functions
# ============================================================================

def load_movie_data(jsonl_path: str) -> List[Dict]:
    """Load movie data from JSONL file."""
    movies = []
    print(f"📖 Loading movies from {jsonl_path}...")
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                movies.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
            if line_num % 1000 == 0:
                print(f"   Loaded {line_num} movies...", end='\r')
    print(f"\n✅ Loaded {len(movies)} movies")
    return movies

def load_realistic_synthetic_interactions(csv_path: str) -> List[Dict]:
    """Load realistic synthetic user-movie interactions from CSV."""
    import pandas as pd
    print(f"📖 Loading ratings from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    interactions = []
    for _, row in df.iterrows():
        interaction = {
            'user_id': int(row['user_id']),
            'movie_id': int(row['movie_id']),
            'rating': float(row['rating']),
            'timestamp': str(row.get('timestamp', '2024-01-01T00:00:00Z'))
        }
        interactions.append(interaction)
    
    print(f"✅ Loaded {len(interactions)} interactions")
    print(f"   Users: {df['user_id'].nunique()}")
    print(f"   Movies: {df['movie_id'].nunique()}")
    print(f"   Avg rating: {df['rating'].mean():.2f}")
    
    return interactions

# ============================================================================
# STEP 6: Training Functions
# ============================================================================

def train_content_model(movies: List[Dict], device: str = 'cuda') -> ContentBasedRecommender:
    """Train the content-based transformer model."""
    logger.info("\n🎬 Training Content-Based Model...")
    
    model = MovieContentTransformer(
        model_name="distilbert-base-uncased",  # Faster than bert-base
        embedding_dim=768,
        max_length=512,
        dropout=0.1
    )
    
    model.to(device)
    model.eval()
    
    recommender = ContentBasedRecommender(model)
    recommender.add_movies(movies)
    
    logger.info("✅ Content-based model training completed!")
    return recommender

def train_collaborative_model(interactions: List[Dict], device: str = 'cuda') -> CollaborativeFilteringRecommender:
    """Train the collaborative filtering model."""
    logger.info("\n👥 Training Collaborative Filtering Model...")
    
    user_ids = list(set(interaction['user_id'] for interaction in interactions))
    movie_ids = list(set(interaction['movie_id'] for interaction in interactions))
    
    model = MatrixFactorization(
        num_users=len(user_ids),
        num_movies=len(movie_ids),
        embedding_dim=128,
        dropout=0.1
    )
    
    recommender = CollaborativeFilteringRecommender(model)
    recommender.build_interaction_matrix(interactions, user_ids, movie_ids)
    recommender.train(interactions, epochs=50, learning_rate=0.01, device=device)
    
    logger.info("✅ Collaborative filtering model training completed!")
    return recommender

def train_contextual_model(movies: List[Dict], device: str = 'cuda') -> ContextualRecommender:
    """Train the contextual transformer model."""
    logger.info("\n💬 Training Contextual Model (Reviews)...")
    
    model = ReviewContextTransformer(
        model_name="distilbert-base-uncased",
        embedding_dim=768,
        max_length=512,
        dropout=0.1
    )
    
    model.to(device)
    model.eval()
    
    recommender = ContextualRecommender(model)
    
    movies_with_reviews = [m for m in movies if m.get('reviews')]
    print(f"   Processing {len(movies_with_reviews)} movies with reviews...")
    
    for i, movie in enumerate(movies_with_reviews):
        recommender.add_movie_context(movie['tmdb_id'], movie['reviews'])
        if (i + 1) % 500 == 0:
            print(f"   Processed {i + 1}/{len(movies_with_reviews)} movies...", end='\r')
    print()
    
    logger.info("✅ Contextual model training completed!")
    return recommender

def create_recommendation_engine(
    movies: List[Dict],
    interactions: List[Dict],
    device: str = 'cuda'
) -> MovieRecommendationEngine:
    """Create and initialize the complete recommendation engine."""
    logger.info("\n🔧 Creating Recommendation Engine...")
    
    # Train individual models
    content_recommender = train_content_model(movies, device)
    collaborative_recommender = train_collaborative_model(interactions, device)
    contextual_recommender = train_contextual_model(movies, device)
    
    # Create ensemble engine
    engine = MovieRecommendationEngine(
        content_recommender=content_recommender,
        collaborative_recommender=collaborative_recommender,
        contextual_recommender=contextual_recommender
    )
    
    # Initialize from data
    engine.initialize_from_data(movies, interactions)
    
    logger.info("✅ Recommendation engine created successfully!")
    return engine

# ============================================================================
# STEP 7: Main Training Execution
# ============================================================================

def main():
    """Main training function."""
    print("\n" + "=" * 70)
    print("🎯 Starting Training...")
    print("=" * 70)
    
    # Load data
    movies = load_movie_data(jsonl_path)
    movies_with_reviews = sum(1 for m in movies if m.get('reviews'))
    print(f"📊 Dataset: {len(movies)} movies, {movies_with_reviews} with reviews")
    
    interactions = load_realistic_synthetic_interactions(csv_path)
    print(f"📊 Interactions: {len(interactions)} ratings from {len(set(i['user_id'] for i in interactions))} users")
    
    # Create recommendation engine
    engine = create_recommendation_engine(movies, interactions, device)
    
    # Test recommendations
    print("\n🧪 Testing recommendations...")
    try:
        test_recs = engine.get_recommendations(user_id=1, top_k=5, include_guarantees=True)
        print(f"✅ Generated {len(test_recs)} test recommendations")
        for i, rec in enumerate(test_recs[:3], 1):
            print(f"   {i}. Movie ID: {rec.get('movie_id')}, Score: {rec.get('ensemble_score', 0):.3f}")
    except Exception as e:
        print(f"⚠️  Test recommendations failed: {e}")
    
    # Save the engine
    save_path = "Checkpoints/recommendation_engine"
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n💾 Saving models to {save_path}...")
    engine.save_engine(save_path)
    
    print("\n" + "=" * 70)
    print("🎉 Training Completed Successfully!")
    print("=" * 70)
    print(f"\n📁 Models saved to:")
    print(f"   - {save_path}_ensemble.json")
    print(f"   - {save_path}_content_embeddings.npz")
    print(f"   - {save_path}_collaborative.pt")
    print(f"   - {save_path}_contexts.npz")
    
    # Verify files
    print("\n✅ Verifying saved files...")
    expected_files = [
        f"{save_path}_ensemble.json",
        f"{save_path}_content_embeddings.npz",
        f"{save_path}_collaborative.pt",
        f"{save_path}_contexts.npz"
    ]
    
    all_present = True
    total_size = 0
    for filepath in expected_files:
        if Path(filepath).exists():
            size = Path(filepath).stat().st_size / (1024 * 1024)  # MB
            total_size += size
            print(f"   ✅ {Path(filepath).name}: {size:.1f} MB")
        else:
            print(f"   ❌ {Path(filepath).name}: NOT FOUND!")
            all_present = False
    
    if all_present:
        print(f"\n📊 Total size: {total_size:.1f} MB")
        print("\n📥 Next steps:")
        print("   1. Create zip: !zip -r checkpoints.zip Checkpoints/")
        print("   2. Download from Files panel")
        print("   3. Extract in local project root")
        print("   4. Restart backend server")
    else:
        print("\n⚠️  Some files are missing. Check errors above.")
    
    return engine

# ============================================================================
# STEP 8: Run Training
# ============================================================================

if __name__ == "__main__":
    try:
        engine = main()
    except Exception as e:
        print(f"\n❌ Training failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise

