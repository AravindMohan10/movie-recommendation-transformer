#!/usr/bin/env python3
"""
Collaborative Filtering Model - Theory and Implementation
The most powerful recommendation technique when you have user data!

WHAT IS COLLABORATIVE FILTERING?
================================
Think of it like this: "People who liked what you liked also liked this."

Two main approaches:
1. USER-BASED: Find users similar to you, recommend what they liked
2. ITEM-BASED: Find movies similar to what you liked, recommend those

We use MATRIX FACTORIZATION - the Netflix Prize winning approach!

THE CORE IDEA:
- Users have hidden preferences (latent factors)
- Movies have hidden characteristics (latent factors)  
- Rating = User preferences × Movie characteristics
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt

class CollaborativeFilteringExplained:
    """
    STEP-BY-STEP EXPLANATION OF MATRIX FACTORIZATION:
    
    1. THE RATING MATRIX (Sparse)
       Users × Movies = Ratings
       Most entries are missing (users haven't rated most movies)
    
    2. MATRIX FACTORIZATION
       Break the big matrix into two smaller matrices:
       - User matrix: Users × Latent Factors
       - Movie matrix: Movies × Latent Factors
    
    3. PREDICTION
       Rating = User vector × Movie vector (dot product)
    
    4. TRAINING
       Learn the latent factors to minimize prediction error
    """
    
    def __init__(self, num_users: int, num_movies: int, latent_dim: int = 64):
        self.num_users = num_users
        self.num_movies = num_movies
        self.latent_dim = latent_dim
        
        print("🤝 LEARNING: Collaborative Filtering")
        print("="*50)
        print("CONCEPT: Learn from user behavior patterns")
        print("STRENGTH: Discovers hidden preferences and connections")
        print("WEAKNESS: Needs user history (cold-start problem)")
        print(f"SETUP: {num_users} users, {num_movies} movies, {latent_dim} latent factors")
        print()
    
    def explain_the_problem(self):
        """
        Show the fundamental problem collaborative filtering solves
        """
        print("🎯 THE RECOMMENDATION PROBLEM:")
        print("="*40)
        
        # Create a small example rating matrix
        print("Example Rating Matrix (5 users × 5 movies):")
        print("(0 = not rated, 1-5 = rating)")
        
        example_matrix = np.array([
            [5, 3, 0, 1, 0],  # User 1: Loves movie 1, hates movie 4
            [4, 0, 0, 1, 0],  # User 2: Similar to User 1
            [1, 1, 0, 5, 2],  # User 3: Opposite taste
            [1, 0, 0, 4, 0],  # User 4: Similar to User 3
            [0, 1, 5, 0, 0],  # User 5: Loves movie 3
        ])
        
        print("        M1  M2  M3  M4  M5")
        for i, row in enumerate(example_matrix):
            print(f"User {i+1}: {row}")
        
        print("\n🔍 PATTERNS WE CAN DISCOVER:")
        print("• Users 1 & 2: Similar taste (high rating for M1, low for M4)")
        print("• Users 3 & 4: Similar taste (low rating for M1, high for M4)")  
        print("• User 5: Unique taste (loves M3)")
        
        print("\n❓ PREDICTION CHALLENGE:")
        print("What would User 1 rate Movie 5? We can guess based on similar users!")
        
        return example_matrix
    
    def explain_matrix_factorization(self):
        """
        Explain how matrix factorization works with simple math
        """
        print("\n🧮 MATRIX FACTORIZATION EXPLAINED:")
        print("="*45)
        
        print("THE IDEA: Break big matrix into two smaller matrices")
        print()
        print("Original Matrix (Users × Movies):")
        print("┌─────────────────┐")
        print("│ 5  3  ?  1  ? │← User 1")  
        print("│ 4  ?  ?  1  ? │← User 2")
        print("│ 1  1  ?  5  2 │← User 3")
        print("└─────────────────┘")
        print("  ↑  ↑  ↑  ↑  ↑")
        print(" M1 M2 M3 M4 M5")
        
        print("\nFACTORIZE INTO:")
        print()
        print("User Matrix      Movie Matrix")
        print("(Users × Factors) × (Factors × Movies)")
        print()
        print("┌─────────┐    ┌─────────────────┐")
        print("│ 0.8 0.1 │    │ 0.9 0.7 0.1 0.2 0.3 │")
        print("│ 0.7 0.2 │ ×  │ 0.2 0.1 0.8 0.9 0.4 │")  
        print("│ 0.1 0.9 │    └─────────────────┘")
        print("└─────────┘")
        print(" Factor 1,2      Movies 1,2,3,4,5")
        
        print("\n💡 INTERPRETATION OF FACTORS:")
        print("Factor 1: 'Action/Adventure preference'")
        print("Factor 2: 'Romance/Drama preference'")
        print()
        print("User 1: High Factor 1, Low Factor 2 → Likes action")
        print("User 3: Low Factor 1, High Factor 2 → Likes romance")
        
    def create_simple_model(self):
        """
        Create a simple matrix factorization model
        """
        print("\n🏗️ BUILDING THE MODEL:")
        print("="*30)
        
        class MatrixFactorization(nn.Module):
            def __init__(self, num_users, num_movies, latent_dim):
                super().__init__()
                
                # User embeddings: each user gets a vector of latent factors
                self.user_embeddings = nn.Embedding(num_users, latent_dim)
                
                # Movie embeddings: each movie gets a vector of latent factors  
                self.movie_embeddings = nn.Embedding(num_movies, latent_dim)
                
                # Bias terms (some users rate higher, some movies are better)
                self.user_bias = nn.Embedding(num_users, 1)
                self.movie_bias = nn.Embedding(num_movies, 1)
                self.global_bias = nn.Parameter(torch.tensor(0.0))
                
                # Initialize with small random values
                nn.init.normal_(self.user_embeddings.weight, std=0.1)
                nn.init.normal_(self.movie_embeddings.weight, std=0.1)
                nn.init.normal_(self.user_bias.weight, std=0.1)
                nn.init.normal_(self.movie_bias.weight, std=0.1)
            
            def forward(self, user_ids, movie_ids):
                # Get user and movie vectors
                user_vecs = self.user_embeddings(user_ids)    # [batch, latent_dim]
                movie_vecs = self.movie_embeddings(movie_ids)  # [batch, latent_dim]
                
                # Compute dot product (element-wise multiply then sum)
                interaction = torch.sum(user_vecs * movie_vecs, dim=1)  # [batch]
                
                # Add bias terms
                user_b = self.user_bias(user_ids).squeeze()    # [batch]
                movie_b = self.movie_bias(movie_ids).squeeze()  # [batch]
                
                # Final prediction
                rating_pred = interaction + user_b + movie_b + self.global_bias
                
                return rating_pred
        
        # Create model instance
        model = MatrixFactorization(
            num_users=self.num_users,
            num_movies=self.num_movies, 
            latent_dim=self.latent_dim
        )
        
        print(f"✅ Created model with:")
        print(f"   User embeddings: {self.num_users} × {self.latent_dim}")
        print(f"   Movie embeddings: {self.num_movies} × {self.latent_dim}")
        print(f"   Total parameters: {sum(p.numel() for p in model.parameters()):,}")
        
        return model
    
    def explain_training_process(self):
        """
        Explain how we train the model
        """
        print("\n🎓 TRAINING PROCESS:")
        print("="*25)
        
        print("1. FORWARD PASS:")
        print("   • Get user and movie embeddings")
        print("   • Compute dot product → predicted rating")
        print("   • Add bias terms")
        
        print("\n2. LOSS CALCULATION:")
        print("   • Compare predicted vs actual rating")
        print("   • Use Mean Squared Error (MSE)")
        print("   • Loss = (predicted - actual)²")
        
        print("\n3. BACKWARD PASS:")
        print("   • Calculate gradients")
        print("   • Update embeddings to reduce loss")
        print("   • Repeat for all user-movie pairs")
        
        print("\n4. REGULARIZATION:")
        print("   • Prevent overfitting")
        print("   • Add penalty for large weights")
        print("   • L2 regularization: λ × ||weights||²")
        
    def demonstrate_predictions(self):
        """
        Show how predictions work with actual numbers
        """
        print("\n🔮 PREDICTION EXAMPLE:")
        print("="*25)
        
        # Simulate trained embeddings
        print("After training, suppose we learned:")
        print()
        print("User 1 embedding: [0.8, 0.1, 0.3]  ← Likes action/adventure")
        print("Movie 1 embedding: [0.9, 0.1, 0.2] ← Action movie")
        print("Movie 2 embedding: [0.1, 0.9, 0.8] ← Romance movie")
        
        user1 = np.array([0.8, 0.1, 0.3])
        movie1 = np.array([0.9, 0.1, 0.2])  # Action
        movie2 = np.array([0.1, 0.9, 0.8])  # Romance
        
        # Compute predictions
        pred1 = np.dot(user1, movie1)
        pred2 = np.dot(user1, movie2)
        
        print(f"\nPredicted rating for User 1 × Movie 1: {pred1:.2f}")
        print(f"Predicted rating for User 1 × Movie 2: {pred2:.2f}")
        
        print(f"\n💡 User 1 prefers Movie 1 ({pred1:.2f}) over Movie 2 ({pred2:.2f})")
        print("This makes sense - action lover prefers action movie!")

def explain_cold_start_problem():
    """
    Explain the limitation of collaborative filtering
    """
    print("\n❄️ THE COLD START PROBLEM:")
    print("="*35)
    
    print("PROBLEM: What about new users with no rating history?")
    print()
    print("Collaborative filtering needs:")
    print("• User's past ratings")
    print("• Similar users' behavior")
    print("• Interaction patterns")
    
    print("\nBut new users have:")
    print("• No ratings")
    print("• No similarity data")
    print("• No interaction history")
    
    print("\n🎯 SOLUTIONS:")
    print("1. Content-based fallback (use movie features)")
    print("2. Popularity-based recommendations")
    print("3. Quick onboarding (ask for preferences)")
    print("4. Hybrid approach (combine multiple methods)")

def main():
    """
    Educational walkthrough of collaborative filtering
    """
    print("🎬 COLLABORATIVE FILTERING RECOMMENDATION")
    print("🎓 EDUCATIONAL MODE - Learning Theory & Implementation")
    print("="*65)
    
    # Create explainer with our dataset dimensions
    explainer = CollaborativeFilteringExplained(
        num_users=10000,
        num_movies=14778,
        latent_dim=64
    )
    
    # Teach the concepts step by step
    explainer.explain_the_problem()
    explainer.explain_matrix_factorization()
    
    # Build and explain the model
    model = explainer.create_simple_model()
    explainer.explain_training_process()
    explainer.demonstrate_predictions()
    
    # Explain limitations
    explain_cold_start_problem()
    
    print("\n🎯 KEY TAKEAWAYS:")
    print("1. Collaborative filtering learns user preferences")
    print("2. Matrix factorization finds hidden patterns")
    print("3. Works great for users with rating history")
    print("4. Struggles with new users (cold-start)")
    print("5. Perfect for MacBook M2 Pro training!")

if __name__ == "__main__":
    main()

