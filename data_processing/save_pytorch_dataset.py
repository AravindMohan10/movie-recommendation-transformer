import torch
import pandas as pd
import numpy as np
import pickle
from sklearn.preprocessing import MinMaxScaler

# Load combined data
df = pd.read_csv('data/combined_training_data.csv', low_memory=False)
print(f"Loaded {len(df)} rows")

# Load encoders
with open('artifacts/user2idx.pkl', 'rb') as f:
    user2idx = pickle.load(f)
with open('artifacts/movie2idx.pkl', 'rb') as f:
    movie2idx = pickle.load(f)
with open('data/movie_id_to_embedding_idx.pkl', 'rb') as f:
    movie_id_to_emb_idx = pickle.load(f)

# Load overview embeddings (Sentence-BERT)
overview_embeddings = np.load('data/overview_embeddings.npy')

df['user_idx'] = df['user_id'].map(user2idx)
df['movie_idx'] = df['movie_id'].map(movie2idx)
df['embedding_idx'] = df['movie_id'].map(movie_id_to_emb_idx)

num_users = len(user2idx)
num_movies = len(movie2idx)
embedding_dim = overview_embeddings.shape[1]
print(f"Users: {num_users}, Movies: {num_movies}, Embedding dim: {embedding_dim}")

# Normalize rating
df['rating'] = df['rating'] / 10.0

# Normalize numeric features
num_features = ['vote_average', 'vote_count', 'runtime', 'revenue', 'release_year']

# Debug check — ensure columns are numeric
for col in num_features:
    if not pd.api.types.is_numeric_dtype(df[col]):
        print(f"⚠️ Column {col} is not numeric — trying to coerce...")
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Fill any NaNs introduced during coercion
df[num_features] = df[num_features].fillna(0)

# Apply scaler
scaler = MinMaxScaler()
df[num_features] = scaler.fit_transform(df[num_features])
print("Scaled numeric features")

# Final tensors
X_user = torch.tensor(df['user_idx'].values, dtype=torch.long)
X_movie = torch.tensor(df['movie_idx'].values, dtype=torch.long)
X_num = torch.tensor(df[num_features].values, dtype=torch.float)
X_emb_idx = torch.tensor(df['embedding_idx'].values, dtype=torch.long)
y_rating = torch.tensor(df['rating'].values, dtype=torch.float)
X_emb_matrix = torch.tensor(overview_embeddings, dtype=torch.float)

# Save package
final_data = {
    'X_user': X_user,
    'X_movie': X_movie,
    'X_num': X_num,
    'X_emb_idx': X_emb_idx,
    'X_emb_matrix': X_emb_matrix,
    'y_rating': y_rating,
    'user2idx': user2idx,
    'movie2idx': movie2idx,
    'movie_id_to_emb_idx': movie_id_to_emb_idx,
    'num_features': num_features,
    'num_users': num_users,
    'num_movies': num_movies,
    'embedding_dim': embedding_dim
}

torch.save(final_data, 'data/final_training_data_with_embeddings.pt')
print("Final dataset (with embeddings) saved to data/final_training_data_with_embeddings.pt")