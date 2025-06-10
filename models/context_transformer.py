"""
Contextual Transformer Model for Review Analysis
Analyzes user reviews to understand contextual preferences and improve recommendations.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import defaultdict


class ReviewContextTransformer(nn.Module):
    """
    Contextual transformer for analyzing user reviews and extracting preferences.
    """
    
    def __init__(
        self,
        model_name: str = "bert-base-uncased",
        embedding_dim: int = 768,
        max_length: int = 512,
        dropout: float = 0.1,
        num_sentiment_classes: int = 3  # negative, neutral, positive
    ):
        super().__init__()
        
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.max_length = max_length
        self.dropout = dropout
        
        # Load pre-trained transformer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.transformer = AutoModel.from_pretrained(model_name)
        
        # Freeze transformer layers (optional)
        for param in self.transformer.parameters():
            param.requires_grad = False
        
        # Sentiment classification head
        self.sentiment_classifier = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim // 2, num_sentiment_classes)
        )
        
        # Preference extraction layers
        self.preference_extractor = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim, embedding_dim)
        )
        
        # Context aggregation
        self.context_aggregator = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=embedding_dim,
                nhead=8,
                dim_feedforward=2048,
                dropout=dropout,
                batch_first=True
            ),
            num_layers=2
        )
        
        # Output projection
        self.output_projection = nn.Linear(embedding_dim, embedding_dim)
        self.layer_norm = nn.LayerNorm(embedding_dim)
    
    def encode_review(self, review_text: str) -> torch.Tensor:
        """
        Encode a single review text.
        """
        inputs = self.tokenizer(
            review_text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        if next(self.parameters()).is_cuda:
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.transformer(**inputs)
        
        return outputs.last_hidden_state[:, 0, :]  # [1, embedding_dim]
    
    def forward(
        self,
        reviews: List[str],
        ratings: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass to analyze reviews and extract preferences.
        
        Args:
            reviews: List of review texts
            ratings: Optional ratings tensor [batch_size]
        
        Returns:
            Tuple of (preference_embeddings, sentiment_logits)
        """
        batch_size = len(reviews)
        
        # Encode all reviews
        review_embeddings = []
        for review in reviews:
            embedding = self.encode_review(review)
            review_embeddings.append(embedding)
        
        review_embeddings = torch.cat(review_embeddings, dim=0)  # [batch_size, embedding_dim]
        
        # Extract preferences
        preference_embeddings = self.preference_extractor(review_embeddings)
        
        # Aggregate context across reviews
        preference_embeddings = preference_embeddings.unsqueeze(1)  # [batch_size, 1, embedding_dim]
        context_embeddings = self.context_aggregator(preference_embeddings)
        context_embeddings = context_embeddings.squeeze(1)  # [batch_size, embedding_dim]
        
        # Output projection and normalization
        output_embeddings = self.output_projection(context_embeddings)
        output_embeddings = self.layer_norm(output_embeddings)
        
        # Sentiment classification
        sentiment_logits = self.sentiment_classifier(review_embeddings)
        
        return output_embeddings, sentiment_logits
    
    def get_user_preferences(self, user_reviews: List[Dict]) -> np.ndarray:
        """
        Extract user preferences from their reviews.
        
        Args:
            user_reviews: List of review dicts with 'content' and 'rating' keys
        
        Returns:
            User preference embedding
        """
        if not user_reviews:
            return np.zeros(self.embedding_dim)
        
        reviews = [review['content'] for review in user_reviews]
        ratings = torch.tensor([review['rating'] for review in user_reviews], dtype=torch.float)
        
        self.eval()
        with torch.no_grad():
            preference_embeddings, _ = self.forward(reviews, ratings)
            
            # Average preferences across all reviews
            avg_preferences = torch.mean(preference_embeddings, dim=0)
            return avg_preferences.cpu().numpy()
    
    def analyze_sentiment(self, review_text: str) -> Tuple[int, float]:
        """
        Analyze sentiment of a review.
        
        Args:
            review_text: Review text
        
        Returns:
            Tuple of (sentiment_class, confidence)
        """
        self.eval()
        with torch.no_grad():
            embedding = self.encode_review(review_text)
            sentiment_logits = self.sentiment_classifier(embedding)
            sentiment_probs = F.softmax(sentiment_logits, dim=1)
            
            sentiment_class = torch.argmax(sentiment_probs, dim=1).item()
            confidence = torch.max(sentiment_probs, dim=1)[0].item()
            
            return sentiment_class, confidence


class ContextualRecommender:
    """
    Contextual recommendation system based on review analysis.
    """
    
    def __init__(self, model: ReviewContextTransformer):
        self.model = model
        self.user_preferences = {}  # user_id -> preference_embedding
        self.movie_contexts = {}  # movie_id -> context_embedding
        self.user_reviews = defaultdict(list)  # user_id -> list of reviews
    
    def add_user_reviews(self, user_id: int, reviews: List[Dict]):
        """
        Add reviews for a user.
        
        Args:
            user_id: User ID
            reviews: List of review dicts with 'content', 'rating', 'movie_id' keys
        """
        self.user_reviews[user_id].extend(reviews)
        
        # Extract user preferences
        user_preference = self.model.get_user_preferences(reviews)
        self.user_preferences[user_id] = user_preference
        
        print(f"Added {len(reviews)} reviews for user {user_id}")
    
    def add_movie_context(self, movie_id: int, reviews: List[Dict]):
        """
        Add context for a movie based on its reviews.
        
        Args:
            movie_id: Movie ID
            reviews: List of review dicts with 'content' key
        """
        if not reviews:
            return
        
        review_texts = [review['content'] for review in reviews]
        
        self.model.eval()
        with torch.no_grad():
            context_embeddings, _ = self.model.forward(review_texts)
            avg_context = torch.mean(context_embeddings, dim=0)
            self.movie_contexts[movie_id] = avg_context.cpu().numpy()
    
    def recommend_based_on_context(
        self,
        user_id: int,
        movie_candidates: List[int],
        top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Recommend movies based on contextual preferences.
        
        Args:
            user_id: User ID
            movie_candidates: List of candidate movie IDs
            top_k: Number of recommendations
        
        Returns:
            List of (movie_id, contextual_score) tuples
        """
        if user_id not in self.user_preferences:
            return []
        
        user_preference = self.user_preferences[user_id]
        recommendations = []
        
        for movie_id in movie_candidates:
            if movie_id not in self.movie_contexts:
                continue
            
            movie_context = self.movie_contexts[movie_id]
            
            # Compute contextual similarity
            similarity = np.dot(user_preference, movie_context)
            recommendations.append((movie_id, similarity))
        
        # Sort by similarity (descending)
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations[:top_k]
    
    def analyze_user_sentiment(self, user_id: int) -> Dict:
        """
        Analyze sentiment patterns for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with sentiment analysis results
        """
        if user_id not in self.user_reviews:
            return {}
        
        reviews = self.user_reviews[user_id]
        sentiment_counts = defaultdict(int)
        total_confidence = 0
        
        for review in reviews:
            sentiment_class, confidence = self.model.analyze_sentiment(review['content'])
            sentiment_counts[sentiment_class] += 1
            total_confidence += confidence
        
        sentiment_labels = ['Negative', 'Neutral', 'Positive']
        
        return {
            'sentiment_distribution': {
                sentiment_labels[i]: count for i, count in sentiment_counts.items()
            },
            'avg_confidence': total_confidence / len(reviews) if reviews else 0,
            'total_reviews': len(reviews)
        }
    
    def get_contextual_explanation(
        self,
        user_id: int,
        movie_id: int
    ) -> str:
        """
        Generate contextual explanation for a recommendation.
        
        Args:
            user_id: User ID
            movie_id: Movie ID
        
        Returns:
            Explanation string
        """
        if user_id not in self.user_preferences or movie_id not in self.movie_contexts:
            return "Insufficient data for explanation"
        
        user_preference = self.user_preferences[user_id]
        movie_context = self.movie_contexts[movie_id]
        
        # Analyze user's recent reviews for context
        recent_reviews = self.user_reviews[user_id][-3:]  # Last 3 reviews
        if recent_reviews:
            recent_sentiment = self.analyze_user_sentiment(user_id)
            dominant_sentiment = max(recent_sentiment['sentiment_distribution'].items(), 
                                   key=lambda x: x[1])[0]
            
            return f"Based on your {dominant_sentiment.lower()} reviews, this movie aligns with your preferences."
        
        return "This movie matches your viewing patterns and preferences."
    
    def save_contexts(self, filepath: str):
        """Save user preferences and movie contexts."""
        np.savez(
            filepath,
            user_preferences=dict(self.user_preferences),
            movie_contexts=dict(self.movie_contexts)
        )
        print(f"Saved contexts to {filepath}")
    
    def load_contexts(self, filepath: str):
        """Load user preferences and movie contexts."""
        data = np.load(filepath, allow_pickle=True)
        self.user_preferences = data['user_preferences'].item()
        self.movie_contexts = data['movie_contexts'].item()
        print(f"Loaded contexts from {filepath}")


class ReviewAnalyzer:
    """
    Utility class for analyzing review patterns and extracting insights.
    """
    
    def __init__(self, model: ReviewContextTransformer):
        self.model = model
    
    def extract_keywords(self, reviews: List[str], top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Extract key terms from reviews.
        
        Args:
            reviews: List of review texts
            top_k: Number of keywords to extract
        
        Returns:
            List of (keyword, frequency) tuples
        """
        # Simple keyword extraction (can be enhanced with more sophisticated methods)
        word_freq = defaultdict(int)
        
        for review in reviews:
            words = review.lower().split()
            for word in words:
                if len(word) > 3:  # Filter short words
                    word_freq[word] += 1
        
        # Sort by frequency
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return keywords[:top_k]
    
    def analyze_review_patterns(self, user_reviews: List[Dict]) -> Dict:
        """
        Analyze patterns in user reviews.
        
        Args:
            user_reviews: List of review dicts
        
        Returns:
            Dictionary with analysis results
        """
        if not user_reviews:
            return {}
        
        # Sentiment analysis
        sentiments = []
        ratings = []
        
        for review in user_reviews:
            sentiment_class, confidence = self.model.analyze_sentiment(review['content'])
            sentiments.append(sentiment_class)
            ratings.append(review.get('rating', 0))
        
        # Extract keywords
        review_texts = [review['content'] for review in user_reviews]
        keywords = self.extract_keywords(review_texts)
        
        return {
            'avg_sentiment': np.mean(sentiments),
            'sentiment_std': np.std(sentiments),
            'avg_rating': np.mean(ratings),
            'rating_std': np.std(ratings),
            'top_keywords': keywords,
            'total_reviews': len(user_reviews)
        } 