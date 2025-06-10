import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pickle
import os
from typing import List, Dict, Optional, Tuple

class SelfAttention(nn.Module):
    def __init__(self, embed_dim, num_heads, dropout=0.1):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        assert self.head_dim * num_heads == embed_dim, "embed_dim must be divisible by num_heads"
        
        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)
        self.out_proj = nn.Linear(embed_dim, embed_dim)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x, mask=None):
        batch_size, seq_len, embed_dim = x.shape
        
        # Project to Q, K, V
        q = self.q_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        # Compute attention
        scores = torch.matmul(q, k.transpose(-2, -1)) / (self.head_dim ** 0.5)
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        # Apply attention to values
        attn_output = torch.matmul(attn_weights, v)
        attn_output = attn_output.transpose(1, 2).contiguous().view(batch_size, seq_len, embed_dim)
        attn_output = self.out_proj(attn_output)
        
        return attn_output

class PerformerRecSys(nn.Module):
    def __init__(self, num_users, num_movies, num_numeric, embedding_dim=128,
                 num_heads=4, dropout=0.1, seq_len=10, text_embedding_dim=384, mf_embedding_dim=32):
        super().__init__()
        
        # Embeddings
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.movie_embedding = nn.Embedding(num_movies, embedding_dim)
        self.position_embedding = nn.Embedding(seq_len, embedding_dim)
        
        # Attention layers
        self.attention_layers = nn.ModuleList([
            SelfAttention(embedding_dim, num_heads, dropout) for _ in range(2)
        ])
        
        # Feed forward layers
        self.feed_forward = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim * 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim * 2, embedding_dim)
        )
        
        # Layer normalization
        self.layer_norms = nn.ModuleList([
            nn.LayerNorm(embedding_dim) for _ in range(4)
        ])
        
        # Numeric features processing
        self.numeric_projection = nn.Linear(num_numeric, embedding_dim)
        
        # Text embedding processing
        self.text_projection = nn.Linear(text_embedding_dim, embedding_dim)
        
        # Matrix Factorization component (30% of the model)
        self.mf_user_embedding = nn.Embedding(num_users, mf_embedding_dim)
        self.mf_movie_embedding = nn.Embedding(num_movies, mf_embedding_dim)
        
        # Final prediction layers
        self.final_layers = nn.Sequential(
            nn.Linear(embedding_dim + mf_embedding_dim, embedding_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim, 1)
        )
        
        # Hybrid weights (70% deep learning, 30% collaborative filtering)
        self.transformer_weight = 0.7
        self.mf_weight = 0.3
        
    def forward(self, user_ids, movie_ids, watch_history, numeric_features, text_embeddings):
        batch_size = user_ids.shape[0]
        
        # User and movie embeddings
        user_emb = self.user_embedding(user_ids)  # [batch_size, embedding_dim]
        movie_emb = self.movie_embedding(movie_ids)  # [batch_size, embedding_dim]
        
        # Process watch history
        if watch_history is not None and watch_history.numel() > 0:
            # Get embeddings for watched movies
            watched_emb = self.movie_embedding(watch_history)  # [batch_size, seq_len, embedding_dim]
            
            # Add positional embeddings
            positions = torch.arange(watched_emb.size(1), device=watched_emb.device)
            pos_emb = self.position_embedding(positions).unsqueeze(0)
            watched_emb = watched_emb + pos_emb
            
            # Apply attention layers
            for i, attention in enumerate(self.attention_layers):
                # Self-attention
                attn_out = attention(watched_emb)
                watched_emb = self.layer_norms[i*2](watched_emb + attn_out)
                
                # Feed forward
                ff_out = self.feed_forward(watched_emb)
                watched_emb = self.layer_norms[i*2+1](watched_emb + ff_out)
            
            # Global average pooling
            history_emb = watched_emb.mean(dim=1)  # [batch_size, embedding_dim]
        else:
            history_emb = torch.zeros(batch_size, self.user_embedding.embedding_dim, device=user_ids.device)
        
        # Process numeric features
        if numeric_features is not None:
            numeric_emb = self.numeric_projection(numeric_features)
        else:
            numeric_emb = torch.zeros(batch_size, self.user_embedding.embedding_dim, device=user_ids.device)
        
        # Process text embeddings
        if text_embeddings is not None:
            text_emb = self.text_projection(text_embeddings)
        else:
            text_emb = torch.zeros(batch_size, self.user_embedding.embedding_dim, device=user_ids.device)
        
        # Combine all embeddings for transformer component
        transformer_input = user_emb + movie_emb + history_emb + numeric_emb + text_emb
        
        # Matrix Factorization component
        mf_user_emb = self.mf_user_embedding(user_ids)
        mf_movie_emb = self.mf_movie_embedding(movie_ids)
        mf_output = (mf_user_emb * mf_movie_emb).sum(dim=1, keepdim=True)
        
        # Combine transformer and MF outputs
        combined = torch.cat([transformer_input, mf_output], dim=1)
        
        # Final prediction
        prediction = self.final_layers(combined).squeeze(-1)
        
        return prediction

class HybridRecommendationModel:
    def __init__(self, model_path: str = "../Checkpoints/best_performer_mf_regularized.pt"):
        self.model = None
        self.model_path = model_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.load_model()
        
    def load_model(self):
        """Load the trained PerformerRecSys model"""
        try:
            if not os.path.exists(self.model_path):
                print(f"❌ Model file not found: {self.model_path}")
                return False
                
            # Load model state
            checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # Extract model parameters from checkpoint
            model_state = checkpoint.get('model_state_dict', checkpoint)
            
            # Get model dimensions from the state dict
            user_embedding_weight = model_state.get('user_embedding.weight', None)
            movie_embedding_weight = model_state.get('movie_embedding.weight', None)
            
            if user_embedding_weight is None or movie_embedding_weight is None:
                print("❌ Could not extract model dimensions from checkpoint")
                return False
                
            num_users = user_embedding_weight.shape[0]
            num_movies = movie_embedding_weight.shape[0]
            embedding_dim = user_embedding_weight.shape[1]
            
            # Create model with correct dimensions
            self.model = PerformerRecSys(
                num_users=num_users,
                num_movies=num_movies,
                num_numeric=10,  # Default value, adjust based on your data
                embedding_dim=embedding_dim,
                num_heads=4,
                dropout=0.1,
                seq_len=10,
                text_embedding_dim=384,
                mf_embedding_dim=32
            )
            
            # Load state dict
            self.model.load_state_dict(model_state)
            self.model.to(self.device)
            self.model.eval()
            
            print(f"✅ Successfully loaded PerformerRecSys model from {self.model_path}")
            print(f"   - Users: {num_users}")
            print(f"   - Movies: {num_movies}")
            print(f"   - Embedding dim: {embedding_dim}")
            print(f"   - Device: {self.device}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False
    
    def get_recommendations(self, user_id: int, user_preferences: Dict, 
                          available_movies: List[Dict], top_k: int = 10) -> List[Dict]:
        """Generate personalized recommendations using the trained model"""
        if self.model is None:
            print("❌ Model not loaded, using fallback recommendations")
            return self._fallback_recommendations(user_preferences, available_movies, top_k)
        
        try:
            # Convert user preferences to model inputs
            user_tensor = torch.tensor([user_id], device=self.device)
            
            # Create movie candidates tensor
            movie_ids = [movie.get('id', 0) for movie in available_movies]
            movie_tensor = torch.tensor(movie_ids, device=self.device)
            
            # Create dummy inputs for other features (you'll need to implement proper feature extraction)
            batch_size = len(movie_ids)
            watch_history = torch.zeros(batch_size, 10, device=self.device, dtype=torch.long)
            numeric_features = torch.zeros(batch_size, 10, device=self.device)
            text_embeddings = torch.zeros(batch_size, 384, device=self.device)
            
            # Get predictions
            with torch.no_grad():
                predictions = self.model(
                    user_tensor.repeat(batch_size),
                    movie_tensor,
                    watch_history,
                    numeric_features,
                    text_embeddings
                )
            
            # Sort by prediction scores
            scores = predictions.cpu().numpy()
            sorted_indices = np.argsort(scores)[::-1]
            
            # Return top-k recommendations
            recommendations = []
            for idx in sorted_indices[:top_k]:
                movie = available_movies[idx].copy()
                movie['prediction_score'] = float(scores[idx])
                recommendations.append(movie)
            
            print(f"✅ Generated {len(recommendations)} recommendations using PerformerRecSys model")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error generating recommendations: {e}")
            return self._fallback_recommendations(user_preferences, available_movies, top_k)
    
    def _fallback_recommendations(self, user_preferences: Dict, 
                                available_movies: List[Dict], top_k: int) -> List[Dict]:
        """Fallback recommendation system using content-based filtering"""
        if not user_preferences or not available_movies:
            return available_movies[:top_k]
        
        # Extract user preferences
        favorite_genres = user_preferences.get('favorite_genres', [])
        favorite_movies = user_preferences.get('favorite_movies', [])
        
        # Score movies based on preferences
        scored_movies = []
        for movie in available_movies:
            score = 0.0
            
            # Genre matching
            movie_genres = movie.get('genres', [])
            if isinstance(movie_genres, str):
                movie_genres = [g.strip() for g in movie_genres.split(',')]
            
            for genre in favorite_genres:
                if genre in movie_genres:
                    score += 2.0
            
            # Rating bonus
            rating = movie.get('rating', 0)
            score += rating * 0.5
            
            # Popularity bonus
            popularity = movie.get('popularity', 0)
            score += popularity * 0.1
            
            scored_movies.append((movie, score))
        
        # Sort by score and return top-k
        scored_movies.sort(key=lambda x: x[1], reverse=True)
        recommendations = [movie for movie, score in scored_movies[:top_k]]
        
        print(f"✅ Generated {len(recommendations)} fallback recommendations")
        return recommendations 