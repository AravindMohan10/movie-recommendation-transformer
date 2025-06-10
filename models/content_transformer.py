"""
Content-Based Transformer Model for Movie Understanding
Uses BERT/XLNet to understand movie semantics and content similarity.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
from typing import Dict, List, Optional, Tuple
import numpy as np


class MovieContentTransformer(nn.Module):
    """
    Content-based transformer for movie understanding.
    Processes movie overview, tagline, reviews, genres, cast/crew to generate embeddings.
    """
    
    def __init__(
        self,
        model_name: str = "bert-base-uncased",
        embedding_dim: int = 768,
        max_length: int = 512,
        dropout: float = 0.1,
        num_genres: int = 19,
        num_layers: int = 2
    ):
        super().__init__()
        
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.max_length = max_length
        self.dropout = dropout
        
        # Load pre-trained transformer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.transformer = AutoModel.from_pretrained(model_name)
        
        # Freeze transformer layers (optional - can be fine-tuned)
        for param in self.transformer.parameters():
            param.requires_grad = False
        
        # Genre embedding layer
        self.genre_embedding = nn.Embedding(num_genres, embedding_dim)
        
        # Additional processing layers
        self.content_projection = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim, embedding_dim)
        )
        
        # Multi-layer transformer for final processing
        self.final_transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=embedding_dim,
                nhead=8,
                dim_feedforward=2048,
                dropout=dropout,
                batch_first=True
            ),
            num_layers=num_layers
        )
        
        # Output projection
        self.output_projection = nn.Linear(embedding_dim, embedding_dim)
        
        # Layer normalization
        self.layer_norm = nn.LayerNorm(embedding_dim)
        
    def preprocess_text(self, movie_data: Dict) -> str:
        """
        Preprocess movie text data into a single string for transformer input.
        """
        text_parts = []
        
        # Add title
        if movie_data.get('title'):
            text_parts.append(f"Title: {movie_data['title']}")
        
        # Add tagline
        if movie_data.get('tagline'):
            text_parts.append(f"Tagline: {movie_data['tagline']}")
        
        # Add overview
        if movie_data.get('overview'):
            text_parts.append(f"Overview: {movie_data['overview']}")
        
        # Add genres (handle multiple formats)
        if movie_data.get('genres'):
            genres_list = movie_data['genres']
            if isinstance(genres_list, list) and len(genres_list) > 0:
                if isinstance(genres_list[0], dict):
                    genres = [g.get('name', '') for g in genres_list if isinstance(g, dict)]
                elif isinstance(genres_list[0], str):
                    genres = genres_list
                else:
                    genres = [str(g) for g in genres_list]
                if genres:
                    text_parts.append(f"Genres: {', '.join(genres)}")
            elif isinstance(genres_list, str):
                text_parts.append(f"Genres: {genres_list}")
        
        # Add cast (top 5) - handle multiple formats
        if movie_data.get('cast'):
            cast_list = movie_data['cast']
            if isinstance(cast_list, list) and len(cast_list) > 0:
                if isinstance(cast_list[0], dict):
                    cast = [c.get('name', '') for c in cast_list[:5] if isinstance(c, dict)]
                elif isinstance(cast_list[0], str):
                    cast = cast_list[:5]
                else:
                    cast = [str(c) for c in cast_list[:5]]
                if cast:
                    text_parts.append(f"Cast: {', '.join(cast)}")
            elif isinstance(cast_list, str):
                text_parts.append(f"Cast: {cast_list}")
        
        # Add directors - handle multiple formats
        if movie_data.get('crew'):
            crew_list = movie_data['crew']
            if isinstance(crew_list, list) and len(crew_list) > 0:
                if isinstance(crew_list[0], dict):
                    directors = [c.get('name', '') for c in crew_list 
                                if isinstance(c, dict) and c.get('job') in ['Director', 'Co-Director']]
                elif isinstance(crew_list, str):
                    directors = [crew_list]  # Single director as string
                else:
                    directors = []
                if directors:
                    text_parts.append(f"Directors: {', '.join(directors)}")
            elif isinstance(crew_list, str):
                text_parts.append(f"Directors: {crew_list}")
        
        # Add reviews (first 2 reviews) - handle multiple formats
        if movie_data.get('reviews'):
            reviews_list = movie_data['reviews']
            if isinstance(reviews_list, list) and len(reviews_list) > 0:
                if isinstance(reviews_list[0], dict):
                    reviews = [r.get('content', r.get('review', ''))[:200] 
                              for r in reviews_list[:2] if isinstance(r, dict)]
                elif isinstance(reviews_list[0], str):
                    reviews = [r[:200] for r in reviews_list[:2]]
                else:
                    reviews = []
                if reviews:
                    text_parts.append(f"Reviews: {' '.join(reviews)}")
            elif isinstance(reviews_list, str):
                text_parts.append(f"Reviews: {reviews_list[:200]}")
        
        return " | ".join(text_parts)
    
    def encode_text(self, text: str) -> torch.Tensor:
        """
        Encode text using the transformer model.
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # Move to device
        if next(self.parameters()).is_cuda:
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Get transformer outputs
        with torch.no_grad():
            outputs = self.transformer(**inputs)
        
        # Use [CLS] token representation
        return outputs.last_hidden_state[:, 0, :]  # [batch_size, embedding_dim]
    
    def forward(
        self,
        movie_data: List[Dict],
        genre_ids: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass to generate movie embeddings.
        
        Args:
            movie_data: List of movie dictionaries
            genre_ids: Tensor of genre IDs [batch_size]
        
        Returns:
            Movie embeddings [batch_size, embedding_dim]
        """
        batch_size = len(movie_data)
        
        # Process text for each movie
        text_embeddings = []
        for movie in movie_data:
            text = self.preprocess_text(movie)
            embedding = self.encode_text(text)
            text_embeddings.append(embedding)
        
        text_embeddings = torch.cat(text_embeddings, dim=0)  # [batch_size, embedding_dim]
        
        # Add genre embeddings if provided
        if genre_ids is not None:
            genre_embeddings = self.genre_embedding(genre_ids)  # [batch_size, embedding_dim]
            text_embeddings = text_embeddings + genre_embeddings
        
        # Apply content projection
        content_embeddings = self.content_projection(text_embeddings)
        
        # Apply final transformer layers
        # Add sequence dimension for transformer
        content_embeddings = content_embeddings.unsqueeze(1)  # [batch_size, 1, embedding_dim]
        
        # Apply transformer
        final_embeddings = self.final_transformer(content_embeddings)
        final_embeddings = final_embeddings.squeeze(1)  # [batch_size, embedding_dim]
        
        # Output projection and normalization
        output_embeddings = self.output_projection(final_embeddings)
        output_embeddings = self.layer_norm(output_embeddings)
        
        # L2 normalize for cosine similarity
        output_embeddings = F.normalize(output_embeddings, p=2, dim=1)
        
        return output_embeddings
    
    def get_movie_embedding(self, movie_data: Dict) -> np.ndarray:
        """
        Get embedding for a single movie.
        
        Args:
            movie_data: Movie dictionary
        
        Returns:
            Movie embedding as numpy array
        """
        self.eval()
        with torch.no_grad():
            embedding = self.forward([movie_data])
            return embedding.cpu().numpy()[0]
    
    def compute_similarity(self, movie1: Dict, movie2: Dict) -> float:
        """
        Compute cosine similarity between two movies.
        
        Args:
            movie1: First movie dictionary
            movie2: Second movie dictionary
        
        Returns:
            Cosine similarity score
        """
        emb1 = self.get_movie_embedding(movie1)
        emb2 = self.get_movie_embedding(movie2)
        
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)


class ContentBasedRecommender:
    """
    Content-based recommendation system using the transformer model.
    """
    
    def __init__(self, model: MovieContentTransformer):
        self.model = model
        self.movie_embeddings = {}
        self.movie_data = {}
    
    def add_movies(self, movies: List[Dict]):
        """
        Add movies to the recommendation system.
        
        Args:
            movies: List of movie dictionaries
        """
        print(f"Computing embeddings for {len(movies)} movies...")
        
        for movie in movies:
            movie_id = movie['tmdb_id']
            self.movie_data[movie_id] = movie
            
            # Compute embedding
            embedding = self.model.get_movie_embedding(movie)
            self.movie_embeddings[movie_id] = embedding
        
        print(f"Added {len(movies)} movies to recommendation system")
    
    def recommend_similar(
        self,
        movie_id: int,
        top_k: int = 10,
        exclude_watched: Optional[List[int]] = None
    ) -> List[Tuple[int, float]]:
        """
        Recommend similar movies based on content.
        
        Args:
            movie_id: ID of the reference movie
            top_k: Number of recommendations
            exclude_watched: List of movie IDs to exclude
        
        Returns:
            List of (movie_id, similarity_score) tuples
        """
        if movie_id not in self.movie_embeddings:
            raise ValueError(f"Movie {movie_id} not found in recommendation system")
        
        reference_embedding = self.movie_embeddings[movie_id]
        similarities = []
        
        exclude_set = set(exclude_watched or [])
        
        for other_id, other_embedding in self.movie_embeddings.items():
            if other_id == movie_id or other_id in exclude_set:
                continue
            
            similarity = np.dot(reference_embedding, other_embedding)
            similarities.append((other_id, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def get_movie_embedding(self, movie_id: int) -> np.ndarray:
        """
        Get embedding for a specific movie.
        
        Args:
            movie_id: Movie ID
        
        Returns:
            Movie embedding
        """
        return self.movie_embeddings.get(movie_id)
    
    def save_embeddings(self, filepath: str):
        """
        Save movie embeddings to file.
        
        Args:
            filepath: Path to save embeddings
        """
        np.savez(
            filepath,
            movie_ids=list(self.movie_embeddings.keys()),
            embeddings=list(self.movie_embeddings.values())
        )
        print(f"Saved embeddings to {filepath}")
    
    def load_embeddings(self, filepath: str, movies: List[Dict]):
        """
        Load movie embeddings from file.
        
        Args:
            filepath: Path to embeddings file
            movies: List of movie dictionaries
        """
        data = np.load(filepath)
        movie_ids = data['movie_ids']
        embeddings = data['embeddings']
        
        # Create movie data mapping
        movie_data_map = {movie['tmdb_id']: movie for movie in movies}
        
        for movie_id, embedding in zip(movie_ids, embeddings):
            if movie_id in movie_data_map:
                self.movie_embeddings[movie_id] = embedding
                self.movie_data[movie_id] = movie_data_map[movie_id]
        
        print(f"Loaded {len(self.movie_embeddings)} embeddings from {filepath}") 