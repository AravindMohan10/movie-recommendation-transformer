"""
Collaborative Filtering Model using Matrix Factorization
Handles user-movie interactions and learns latent factors.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy.sparse import csr_matrix
import pickle


class MatrixFactorization(nn.Module):
    """
    Matrix Factorization model for collaborative filtering.
    Learns user and movie latent factors from interaction matrix.
    """
    
    def __init__(
        self,
        num_users: int,
        num_movies: int,
        embedding_dim: int = 128,
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.num_users = num_users
        self.num_movies = num_movies
        self.embedding_dim = embedding_dim
        
        # User and movie embeddings
        self.user_embeddings = nn.Embedding(num_users, embedding_dim)
        self.movie_embeddings = nn.Embedding(num_movies, embedding_dim)
        
        # User and movie biases
        self.user_biases = nn.Embedding(num_users, 1)
        self.movie_biases = nn.Embedding(num_movies, 1)
        
        # Global bias
        self.global_bias = nn.Parameter(torch.zeros(1))
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize embedding weights."""
        nn.init.normal_(self.user_embeddings.weight, std=0.1)
        nn.init.normal_(self.movie_embeddings.weight, std=0.1)
        nn.init.zeros_(self.user_biases.weight)
        nn.init.zeros_(self.movie_biases.weight)
    
    def forward(self, user_ids: torch.Tensor, movie_ids: torch.Tensor) -> torch.Tensor:
        """
        Forward pass to predict ratings.
        
        Args:
            user_ids: User IDs [batch_size]
            movie_ids: Movie IDs [batch_size]
        
        Returns:
            Predicted ratings [batch_size]
        """
        # Get embeddings
        user_emb = self.user_embeddings(user_ids)  # [batch_size, embedding_dim]
        movie_emb = self.movie_embeddings(movie_ids)  # [batch_size, embedding_dim]
        
        # Apply dropout
        user_emb = self.dropout(user_emb)
        movie_emb = self.dropout(movie_emb)
        
        # Element-wise product
        interaction = user_emb * movie_emb  # [batch_size, embedding_dim]
        
        # Sum over embedding dimension
        prediction = torch.sum(interaction, dim=1, keepdim=True)  # [batch_size, 1]
        
        # Add biases
        user_bias = self.user_biases(user_ids)  # [batch_size, 1]
        movie_bias = self.movie_biases(movie_ids)  # [batch_size, 1]
        
        prediction = prediction + user_bias + movie_bias + self.global_bias
        
        return prediction.squeeze()  # [batch_size]
    
    def get_user_embedding(self, user_id: int) -> np.ndarray:
        """Get user embedding."""
        with torch.no_grad():
            return self.user_embeddings(torch.tensor([user_id])).cpu().numpy()[0]
    
    def get_movie_embedding(self, movie_id: int) -> np.ndarray:
        """Get movie embedding."""
        with torch.no_grad():
            return self.movie_embeddings(torch.tensor([movie_id])).cpu().numpy()[0]


class CollaborativeFilteringRecommender:
    """
    Collaborative filtering recommendation system.
    """
    
    def __init__(self, model: MatrixFactorization):
        self.model = model
        self.user_id_map = {}  # user_id -> internal_id
        self.movie_id_map = {}  # movie_id -> internal_id
        self.reverse_user_map = {}  # internal_id -> user_id
        self.reverse_movie_map = {}  # internal_id -> movie_id
        self.interaction_matrix = None
    
    def build_interaction_matrix(
        self,
        interactions: List[Dict],
        user_ids: List[int],
        movie_ids: List[int]
    ):
        """
        Build interaction matrix from user-movie interactions.
        
        Args:
            interactions: List of interaction dicts with keys: user_id, movie_id, rating
            user_ids: List of all user IDs
            movie_ids: List of all movie IDs
        """
        # Create ID mappings
        for i, user_id in enumerate(user_ids):
            self.user_id_map[user_id] = i
            self.reverse_user_map[i] = user_id
        
        for i, movie_id in enumerate(movie_ids):
            self.movie_id_map[movie_id] = i
            self.reverse_movie_map[i] = movie_id
        
        # Build sparse matrix
        num_users = len(user_ids)
        num_movies = len(movie_ids)
        
        rows, cols, data = [], [], []
        
        for interaction in interactions:
            user_id = interaction['user_id']
            movie_id = interaction['movie_id']
            rating = interaction['rating']
            
            if user_id in self.user_id_map and movie_id in self.movie_id_map:
                internal_user_id = self.user_id_map[user_id]
                internal_movie_id = self.movie_id_map[movie_id]
                
                rows.append(internal_user_id)
                cols.append(internal_movie_id)
                data.append(rating)
        
        # Create sparse matrix
        self.interaction_matrix = csr_matrix(
            (data, (rows, cols)),
            shape=(num_users, num_movies)
        )
        
        print(f"Built interaction matrix: {num_users} users x {num_movies} movies")
        print(f"Total interactions: {len(data)}")
    
    def train(
        self,
        interactions: List[Dict],
        epochs: int = 100,
        learning_rate: float = 0.01,
        batch_size: int = 1024,
        device: str = 'cuda'
    ):
        """
        Train the collaborative filtering model.
        
        Args:
            interactions: List of interaction dicts
            epochs: Number of training epochs
            learning_rate: Learning rate
            batch_size: Batch size
            device: Device to train on
        """
        self.model.to(device)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        
        # Convert interactions to tensors
        user_ids = []
        movie_ids = []
        ratings = []
        
        for interaction in interactions:
            user_id = interaction['user_id']
            movie_id = interaction['movie_id']
            rating = interaction['rating']
            
            if user_id in self.user_id_map and movie_id in self.movie_id_map:
                internal_user_id = self.user_id_map[user_id]
                internal_movie_id = self.movie_id_map[movie_id]
                
                user_ids.append(internal_user_id)
                movie_ids.append(internal_movie_id)
                ratings.append(rating)
        
        user_ids = torch.tensor(user_ids, dtype=torch.long).to(device)
        movie_ids = torch.tensor(movie_ids, dtype=torch.long).to(device)
        ratings = torch.tensor(ratings, dtype=torch.float).to(device)
        
        num_interactions = len(user_ids)
        num_batches = (num_interactions + batch_size - 1) // batch_size
        
        print(f"Training for {epochs} epochs...")
        
        for epoch in range(epochs):
            self.model.train()
            total_loss = 0
            
            # Shuffle data
            indices = torch.randperm(num_interactions)
            user_ids_shuffled = user_ids[indices]
            movie_ids_shuffled = movie_ids[indices]
            ratings_shuffled = ratings[indices]
            
            for batch in range(num_batches):
                start_idx = batch * batch_size
                end_idx = min(start_idx + batch_size, num_interactions)
                
                batch_user_ids = user_ids_shuffled[start_idx:end_idx]
                batch_movie_ids = movie_ids_shuffled[start_idx:end_idx]
                batch_ratings = ratings_shuffled[start_idx:end_idx]
                
                # Forward pass
                predictions = self.model(batch_user_ids, batch_movie_ids)
                loss = criterion(predictions, batch_ratings)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            if (epoch + 1) % 10 == 0:
                avg_loss = total_loss / num_batches
                print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")
    
    def predict_rating(self, user_id: int, movie_id: int) -> float:
        """
        Predict rating for a user-movie pair.
        
        Args:
            user_id: User ID
            movie_id: Movie ID
        
        Returns:
            Predicted rating
        """
        if user_id not in self.user_id_map or movie_id not in self.movie_id_map:
            return 0.0
        
        internal_user_id = self.user_id_map[user_id]
        internal_movie_id = self.movie_id_map[movie_id]
        
        self.model.eval()
        with torch.no_grad():
            prediction = self.model(
                torch.tensor([internal_user_id]),
                torch.tensor([internal_movie_id])
            )
            return prediction.item()
    
    def recommend_for_user(
        self,
        user_id: int,
        top_k: int = 10,
        exclude_watched: Optional[List[int]] = None,
        candidate_movies: Optional[List[int]] = None
    ) -> List[Tuple[int, float]]:
        """
        Recommend movies for a user.
        
        Args:
            user_id: User ID
            top_k: Number of recommendations
            exclude_watched: List of movie IDs to exclude
            candidate_movies: Optional list to constrain candidates (if None, uses all movies)
        
        Returns:
            List of (movie_id, predicted_rating) tuples
        """
        if user_id not in self.user_id_map:
            return []
        
        exclude_set = set(exclude_watched or [])
        recommendations = []
        
        # Use candidate_movies if provided, otherwise use all movies (backward compatible)
        movie_candidates = candidate_movies if candidate_movies is not None else self.movie_id_map.keys()
        
        for movie_id in movie_candidates:
            # Only consider movies that exist in our model AND are in candidates
            if movie_id not in self.movie_id_map:
                continue
            if movie_id in exclude_set:
                continue
            
            predicted_rating = self.predict_rating(user_id, movie_id)
            recommendations.append((movie_id, predicted_rating))
        
        # Sort by predicted rating (descending)
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations[:top_k]
    
    def find_similar_users(
        self,
        user_id: int,
        top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Find users similar to the given user.
        
        Args:
            user_id: User ID
            top_k: Number of similar users
        
        Returns:
            List of (similar_user_id, similarity_score) tuples
        """
        if user_id not in self.user_id_map:
            return []
        
        user_embedding = self.model.get_user_embedding(self.user_id_map[user_id])
        similarities = []
        
        for other_user_id in self.user_id_map.keys():
            if other_user_id == user_id:
                continue
            
            other_embedding = self.model.get_user_embedding(self.user_id_map[other_user_id])
            similarity = np.dot(user_embedding, other_embedding)
            similarities.append((other_user_id, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def save_model(self, filepath: str):
        """Save the trained model."""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'user_id_map': self.user_id_map,
            'movie_id_map': self.movie_id_map,
            'reverse_user_map': self.reverse_user_map,
            'reverse_movie_map': self.reverse_movie_map
        }, filepath)
        print(f"Saved model to {filepath}")
    
    def load_model(self, filepath: str):
        """Load a trained model."""
        # Map CUDA tensors to CPU if CUDA is not available
        map_location = 'cpu' if not torch.cuda.is_available() else None
        checkpoint = torch.load(filepath, map_location=map_location)
        
        # Get actual dimensions from checkpoint
        state_dict = checkpoint['model_state_dict']
        num_users = state_dict['user_embeddings.weight'].shape[0]
        num_movies = state_dict['movie_embeddings.weight'].shape[0]
        embedding_dim = state_dict['user_embeddings.weight'].shape[1]
        
        # Reinitialize model with correct dimensions
        if (num_users != self.model.num_users or 
            num_movies != self.model.num_movies or
            embedding_dim != self.model.embedding_dim):
            self.model = MatrixFactorization(
                num_users=num_users,
                num_movies=num_movies,
                embedding_dim=embedding_dim,
                dropout=self.model.dropout.p if hasattr(self.model.dropout, 'p') else 0.1
            )
        
        self.model.load_state_dict(state_dict)
        self.user_id_map = checkpoint['user_id_map']
        self.movie_id_map = checkpoint['movie_id_map']
        self.reverse_user_map = checkpoint['reverse_user_map']
        self.reverse_movie_map = checkpoint['reverse_movie_map']
        print(f"Loaded model from {filepath} (users: {num_users}, movies: {num_movies})") 