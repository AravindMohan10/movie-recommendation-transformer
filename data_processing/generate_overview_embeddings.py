import pandas as pd
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
import os

# Paths
input_csv = 'data/combined_training_data.csv'
output_npy = 'data/overview_embeddings.npy'

# Load CSV
df = pd.read_csv(input_csv, low_memory=False)
print(f"Loaded {len(df)} rows")

# Drop duplicates by movie_id to avoid redundant computations
unique_movies = df[['movie_id', 'overview']].drop_duplicates(subset='movie_id')
print(f"Found {len(unique_movies)} unique movies")

# Initialize Sentence-BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')  # small & fast (384 dims), or try 'all-mpnet-base-v2' (768 dims)
print("Loaded SentenceTransformer model")

# Generate embeddings
embeddings = []
for idx, row in unique_movies.iterrows():
    overview = str(row['overview']) if pd.notnull(row['overview']) else ""
    emb = model.encode(overview)
    embeddings.append(emb)

embeddings = np.array(embeddings)
print(f"Generated embeddings shape: {embeddings.shape}")

# Map movie_id → embedding index
movie_id_to_idx = {movie_id: i for i, movie_id in enumerate(unique_movies['movie_id'].values)}

# Save embeddings and mapping
np.save(output_npy, embeddings)
with open('data/movie_id_to_embedding_idx.pkl', 'wb') as f:
    import pickle
    pickle.dump(movie_id_to_idx, f)

print(f"Saved embeddings to {output_npy}")
print(f"Saved movie_id to embedding index map to data/movie_id_to_embedding_idx.pkl")