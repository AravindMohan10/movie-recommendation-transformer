#!/usr/bin/env python3
"""
Content-Based Recommendation Model
This teaches you how transformer embeddings work for recommendation systems.

Learning Goals:
1. Understanding BERT embeddings for text
2. Similarity computation with cosine similarity
3. Content-based recommendation logic
4. Handling the cold-start problem
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class ContentBasedRecommender:
    """
    Content-based recommendation using BERT embeddings.
    
    Key Concepts:
    1. Text Embeddings: Convert text to numerical vectors
    2. Semantic Similarity: Similar movies have similar embeddings
    3. Cold-start Solution: Works without user history
    """
    
    def __init__(self, model_name: str = 'distilbert-base-uncased'):
        """
        Initialize the content-based recommender.
        
        Learning: We use DistilBERT instead of full BERT because:
        - 40% smaller, 60% faster
        - Almost same performance
        - Better for production use
        """
        print(f"🤖 Initializing Content-Based Model with {model_name}")
        
        # Load pre-trained model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        
        # Set to evaluation mode (no training for now)
        self.model.eval()
        
        # Storage for movie embeddings
        self.movie_embeddings = None
        self.movie_to_idx = None
        self.idx_to_movie = None
        
        print("✅ Model loaded successfully!")
    
    def create_movie_embeddings(self, movies_df: pd.DataFrame) -> torch.Tensor:
        """
        Create embeddings for all movies using their content text.
        
        Learning: This is where the magic happens!
        We convert movie descriptions into 768-dimensional vectors
        that capture semantic meaning.
        """
        print("🎬 Creating movie embeddings...")
        
        movie_texts = movies_df['content_text'].tolist()
        movie_ids = movies_df['tmdb_id'].tolist()
        
        # Create mapping from movie ID to embedding index
        self.movie_to_idx = {movie_id: idx for idx, movie_id in enumerate(movie_ids)}
        self.idx_to_movie = {idx: movie_id for movie_id, idx in self.movie_to_idx.items()}
        
        embeddings = []
        batch_size = 16  # Process in batches to manage memory
        
        print(f"Processing {len(movie_texts)} movies in batches of {batch_size}...")
        
        with torch.no_grad():  # Don't compute gradients (we're not training)
            for i in range(0, len(movie_texts), batch_size):
                batch_texts = movie_texts[i:i + batch_size]
                batch_embeddings = self._encode_texts(batch_texts)
                embeddings.append(batch_embeddings)
                
                if (i // batch_size + 1) % 100 == 0:
                    print(f"   Processed {i + len(batch_texts)} movies...")
        
        # Combine all embeddings
        self.movie_embeddings = torch.cat(embeddings, dim=0)
        
        print(f"✅ Created embeddings: {self.movie_embeddings.shape}")
        print(f"   Each movie → {self.movie_embeddings.shape[1]} dimensional vector")
        
        return self.movie_embeddings
    
    def _encode_texts(self, texts: List[str]) -> torch.Tensor:
        """
        Encode a batch of texts into embeddings.
        
        Learning: This is how BERT transforms text into numbers:
        1. Tokenize: Split text into tokens (words/subwords)
        2. Encode: Pass through transformer layers
        3. Pool: Average all token embeddings to get sentence embedding
        """
        # Tokenize the texts
        inputs = self.tokenizer(
            texts,
            padding=True,           # Pad to same length
            truncation=True,        # Cut off if too long
            max_length=512,         # BERT's maximum input length
            return_tensors='pt'     # Return PyTorch tensors
        )
        
        # Get embeddings from BERT
        outputs = self.model(**inputs)
        
        # Extract the hidden states (embeddings for each token)
        hidden_states = outputs.last_hidden_state  # Shape: [batch_size, seq_len, 768]
        
        # Pool to get sentence-level embeddings
        # We use mean pooling: average across all tokens
        embeddings = torch.mean(hidden_states, dim=1)  # Shape: [batch_size, 768]
        
        return embeddings
    
    def find_similar_movies(self, movie_id: int, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Find movies similar to the given movie using cosine similarity.
        
        Learning: Cosine similarity measures the angle between vectors.
        Similar movies point in similar directions in the embedding space.
        
        Cosine similarity = (A · B) / (|A| × |B|)
        Range: -1 to 1, where 1 = identical, 0 = orthogonal, -1 = opposite
        """
        if self.movie_embeddings is None:
            raise ValueError("Movie embeddings not created yet!")
        
        if movie_id not in self.movie_to_idx:
            raise ValueError(f"Movie {movie_id} not found in dataset")
        
        # Get the target movie's embedding
        movie_idx = self.movie_to_idx[movie_id]
        target_embedding = self.movie_embeddings[movie_idx:movie_idx+1]  # Keep 2D shape
        
        # Calculate cosine similarities with all movies
        similarities = cosine_similarity(
            target_embedding.numpy(),
            self.movie_embeddings.numpy()
        )[0]  # Get the first (and only) row
        
        # Get top-k most similar movies (excluding the movie itself)
        similar_indices = np.argsort(similarities)[::-1]  # Sort descending
        
        results = []
        for idx in similar_indices:
            if len(results) >= top_k:
                break
            
            similar_movie_id = self.idx_to_movie[idx]
            similarity_score = similarities[idx]
            
            # Skip the movie itself
            if similar_movie_id != movie_id:
                results.append((similar_movie_id, similarity_score))
        
        return results
    
    def recommend_for_new_user(self, liked_genres: List[str], top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Recommend movies for a new user based on genre preferences.
        
        Learning: This solves the cold-start problem!
        Even without user history, we can recommend based on content.
        """
        if self.movie_embeddings is None:
            raise ValueError("Movie embeddings not created yet!")
        
        print(f"🎯 Generating recommendations for user who likes: {liked_genres}")
        
        # Create a "virtual movie" that represents user preferences
        genre_text = f"A movie with genres: {', '.join(liked_genres)}"
        
        with torch.no_grad():
            user_preference_embedding = self._encode_texts([genre_text])
        
        # Find movies most similar to user preferences
        similarities = cosine_similarity(
            user_preference_embedding.numpy(),
            self.movie_embeddings.numpy()
        )[0]
        
        # Get top-k recommendations
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        recommendations = []
        for idx in top_indices:
            movie_id = self.idx_to_movie[idx]
            similarity_score = similarities[idx]
            recommendations.append((movie_id, similarity_score))
        
        return recommendations
    
    def explain_recommendation(self, movie_id: int, similar_movie_id: int, movies_df: pd.DataFrame) -> str:
        """
        Explain why two movies are similar.
        
        Learning: Explainable AI is crucial for user trust.
        """
        movie1 = movies_df[movies_df['tmdb_id'] == movie_id].iloc[0]
        movie2 = movies_df[movies_df['tmdb_id'] == similar_movie_id].iloc[0]
        
        explanation = f"'{movie2['title']}' is similar to '{movie1['title']}' because:\n"
        
        # Compare genres
        genres1 = set(movie1['genre_names'])
        genres2 = set(movie2['genre_names'])
        common_genres = genres1.intersection(genres2)
        
        if common_genres:
            explanation += f"• Shared genres: {', '.join(common_genres)}\n"
        
        # Compare directors
        if movie1['director'] == movie2['director'] and movie1['director'] != "Unknown":
            explanation += f"• Same director: {movie1['director']}\n"
        
        # Compare cast
        cast1 = set(movie1['cast_names'])
        cast2 = set(movie2['cast_names'])
        common_cast = cast1.intersection(cast2)
        
        if common_cast:
            explanation += f"• Shared cast: {', '.join(list(common_cast)[:3])}\n"
        
        return explanation

def main():
    """Demonstrate content-based recommendation."""
    print("🎬 Content-Based Recommendation System")
    print("=" * 50)
    
    # Load processed data
    print("📂 Loading processed data...")
    training_data = torch.load('../data/processed_training_data_new.pt')
    movies_df = training_data['movies']
    
    # Initialize recommender
    recommender = ContentBasedRecommender()
    
    # Create embeddings for all movies
    recommender.create_movie_embeddings(movies_df)
    
    # Example 1: Find similar movies
    print("\n🔍 Example 1: Finding Similar Movies")
    sample_movie = movies_df.iloc[0]
    print(f"Finding movies similar to: '{sample_movie['title']}'")
    
    similar_movies = recommender.find_similar_movies(
        movie_id=sample_movie['tmdb_id'], 
        top_k=5
    )
    
    for movie_id, similarity in similar_movies:
        movie_info = movies_df[movies_df['tmdb_id'] == movie_id].iloc[0]
        print(f"  {similarity:.3f} - {movie_info['title']} ({movie_info['genres_string']})")
    
    # Example 2: Cold-start recommendation
    print("\n❄️ Example 2: Cold-Start Recommendation")
    user_genres = ['ACTION', 'SCIENCE_FICTION', 'ADVENTURE']
    recommendations = recommender.recommend_for_new_user(user_genres, top_k=5)
    
    for movie_id, similarity in recommendations:
        movie_info = movies_df[movies_df['tmdb_id'] == movie_id].iloc[0]
        print(f"  {similarity:.3f} - {movie_info['title']} ({movie_info['genres_string']})")
    
    # Save the trained model
    print("\n💾 Saving content model...")
    torch.save({
        'model_state_dict': recommender.model.state_dict(),
        'movie_embeddings': recommender.movie_embeddings,
        'movie_to_idx': recommender.movie_to_idx,
        'idx_to_movie': recommender.idx_to_movie
    }, '../models/content_model.pt')
    print("✅ Saved to ../models/content_model.pt")

if __name__ == "__main__":
    main()

