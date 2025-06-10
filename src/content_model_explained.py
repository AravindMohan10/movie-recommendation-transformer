#!/usr/bin/env python3
"""
Content-Based Model - Theory and Implementation
Let me teach you every concept step by step!

WHAT IS CONTENT-BASED FILTERING?
================================
Think of it like this: If you liked "The Matrix" (sci-fi, action), 
you'll probably like "Blade Runner" (also sci-fi, action).

The model learns to understand what makes movies similar by looking at:
- Title and description text
- Genres (Action, Comedy, Drama, etc.)
- Cast and crew
- Other metadata

KEY INSIGHT: We convert all this information into numerical vectors (embeddings)
that capture the "essence" of each movie in mathematical space.
"""

import torch
import torch.nn as nn
import numpy as np
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity

class ContentBasedModel:
    """
    STEP-BY-STEP EXPLANATION:
    
    1. TEXT EMBEDDINGS (The Magic!)
       - Take movie text: "Star Wars is a sci-fi epic about space battles"
       - BERT converts this to 768 numbers: [0.1, -0.3, 0.8, ...]
       - Similar movies get similar numbers!
    
    2. SIMILARITY COMPUTATION
       - Use cosine similarity: measures angle between vectors
       - Close angle = similar movies
       - Far angle = different movies
    
    3. RECOMMENDATION
       - Find movies with smallest angles to what user liked
    """
    
    def __init__(self):
        print("🎯 LEARNING: Content-Based Filtering")
        print("="*50)
        print("CONCEPT: Use movie content (text, genres) to find similar movies")
        print("ADVANTAGE: Works for new users (cold-start problem)")
        print("HOW: Convert text → numbers → find similar numbers")
        print()
        
        # Use smaller model for MacBook compatibility
        self.tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
        self.model = AutoModel.from_pretrained('distilbert-base-uncased')
        self.model.eval()  # Set to evaluation mode
        
    def explain_embeddings(self):
        """
        Let me show you how text becomes numbers!
        """
        print("🔤 TEXT TO NUMBERS DEMO:")
        
        # Example movie descriptions
        movies = [
            "A sci-fi epic about space battles and the Force",
            "A romantic comedy about love in New York", 
            "A space adventure with robots and aliens"
        ]
        
        print("Input texts:")
        for i, movie in enumerate(movies):
            print(f"  {i+1}. {movie}")
        
        # Convert to embeddings
        embeddings = []
        for movie in movies:
            # Tokenize: Split text into pieces BERT understands
            tokens = self.tokenizer(movie, return_tensors='pt', padding=True, truncation=True)
            print(f"\nTokens for '{movie[:30]}...': {tokens['input_ids'][0][:10].tolist()}...")
            
            # Get embedding
            with torch.no_grad():
                output = self.model(**tokens)
                embedding = torch.mean(output.last_hidden_state, dim=1)
                embeddings.append(embedding)
                print(f"Embedding shape: {embedding.shape}")
                print(f"First 5 numbers: {embedding[0][:5].tolist()}")
        
        # Calculate similarities
        print("\n📊 SIMILARITY MATRIX:")
        print("(1.0 = identical, 0.0 = unrelated)")
        
        for i, emb1 in enumerate(embeddings):
            for j, emb2 in enumerate(embeddings):
                similarity = cosine_similarity(emb1.numpy(), emb2.numpy())[0][0]
                print(f"Movie {i+1} vs Movie {j+1}: {similarity:.3f}")
        
        print("\n💡 INSIGHT: Movies 1 and 3 (both sci-fi) should be more similar!")
    
    def explain_cosine_similarity(self):
        """
        Teach cosine similarity with simple examples
        """
        print("\n📐 COSINE SIMILARITY EXPLAINED:")
        print("="*40)
        
        # Simple 2D vectors for visualization
        vec1 = np.array([1, 0])    # Points right
        vec2 = np.array([1, 1])    # Points up-right  
        vec3 = np.array([0, 1])    # Points up
        vec4 = np.array([-1, 0])   # Points left
        
        vectors = [vec1, vec2, vec3, vec4]
        labels = ["Right", "Up-Right", "Up", "Left"]
        
        print("Vector directions:")
        for i, (vec, label) in enumerate(zip(vectors, labels)):
            print(f"  {label}: {vec}")
        
        print("\nSimilarity matrix:")
        for i, (vec1, label1) in enumerate(zip(vectors, labels)):
            for j, (vec2, label2) in enumerate(zip(vectors, labels)):
                # Cosine similarity formula: (A·B) / (|A|×|B|)
                dot_product = np.dot(vec1, vec2)
                magnitude1 = np.linalg.norm(vec1)
                magnitude2 = np.linalg.norm(vec2)
                similarity = dot_product / (magnitude1 * magnitude2)
                print(f"  {label1} vs {label2}: {similarity:.2f}")
        
        print("\n💡 INSIGHT:")
        print("  1.0 = Same direction (very similar)")
        print("  0.0 = Perpendicular (unrelated)")
        print(" -1.0 = Opposite direction (very different)")

def explain_memory_requirements():
    """
    Explain computational requirements for different setups
    """
    print("\n💻 COMPUTATIONAL REQUIREMENTS:")
    print("="*50)
    
    print("🔹 CONTENT MODEL:")
    print("  - Model size: ~67M parameters (DistilBERT)")
    print("  - Memory needed: ~2-4GB for inference")
    print("  - Training time: 30-60 minutes")
    print("  - MacBook M2 Pro: ✅ Should work fine")
    
    print("\n🔹 COLLABORATIVE MODEL:")
    print("  - Model size: ~5-10M parameters (Matrix Factorization)")
    print("  - Memory needed: ~1-2GB")
    print("  - Training time: 10-20 minutes")  
    print("  - MacBook M2 Pro: ✅ Definitely works")
    
    print("\n🔹 CONTEXTUAL MODEL (Reviews):")
    print("  - Model size: ~67M parameters (DistilBERT)")
    print("  - Memory needed: ~3-5GB")
    print("  - Training time: 45-90 minutes")
    print("  - MacBook M2 Pro: ⚠️ Might be tight on memory")
    
    print("\n🔹 ENSEMBLE MODEL:")
    print("  - Model size: ~1M parameters (combining weights)")
    print("  - Memory needed: ~500MB")
    print("  - Training time: 5-10 minutes")
    print("  - MacBook M2 Pro: ✅ Easy")
    
    print("\n🎯 RECOMMENDATION:")
    print("  Try Content + Collaborative on MacBook first")
    print("  Use Colab A100 for Contextual model if needed")
    print("  Colab Pro gives you ~25GB GPU memory!")

def create_colab_notebook():
    """
    Create a Colab notebook for training
    """
    notebook_content = '''
# Movie Recommendation System - Colab Training
# Run this in Google Colab with A100 GPU

# Install dependencies
!pip install transformers torch scikit-learn pandas numpy

# Mount Google Drive to save models
from google.colab import drive
drive.mount('/content/drive')

# Upload your data files to Drive first, then:
import torch
import pandas as pd

# Load your processed data
training_data = torch.load('/content/drive/MyDrive/processed_training_data_new.pt')

# Train models here...
# (We'll add the full training code next)

# Save trained models back to Drive
torch.save(trained_model, '/content/drive/MyDrive/content_model_trained.pt')
'''
    
    with open('../colab_training_notebook.py', 'w') as f:
        f.write(notebook_content)
    
    print("📄 Created colab_training_notebook.py")
    print("   Copy this to Google Colab for GPU training!")

def main():
    """
    Demonstrate content-based concepts without heavy computation
    """
    print("🎬 CONTENT-BASED RECOMMENDATION SYSTEM")
    print("🎓 EDUCATIONAL MODE - Learning Theory & Concepts")
    print("="*60)
    
    # Initialize model (lightweight demo)
    model = ContentBasedModel()
    
    # Teach embedding concepts
    model.explain_embeddings()
    
    # Teach similarity concepts  
    model.explain_cosine_similarity()
    
    # Explain computational requirements
    explain_memory_requirements()
    
    # Create Colab notebook
    create_colab_notebook()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Learn collaborative filtering theory")
    print("2. Understand ensemble methods")
    print("3. Set up Colab for GPU training")
    print("4. Train full models and get weights")

if __name__ == "__main__":
    main()

