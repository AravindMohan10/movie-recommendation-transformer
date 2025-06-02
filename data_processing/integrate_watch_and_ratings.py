import pandas as pd
import numpy as np
import torch
import pickle

# Load combined training data
df = pd.read_csv('data/combined_training_data.csv', low_memory=False)
print(f"Loaded {len(df)} combined rows")

# Load synthetic ratings
synthetic_df = pd.read_csv('data/synthetic_ratings.csv')
print(f"Loaded {len(synthetic_df)} synthetic ratings")

df['user_id'] = df['user_id'].astype(str)
df['movie_id'] = df['movie_id'].astype(str)
synthetic_df['user_id'] = synthetic_df['user_id'].astype(str)
synthetic_df['movie_id'] = synthetic_df['movie_id'].astype(str)

# Merge synthetic ratings into main df
df = df.merge(synthetic_df[['user_id', 'movie_id', 'rating']],
              on=['user_id', 'movie_id'], how='left',
              suffixes=('', '_synthetic'))

# Replace rating if synthetic exists, else fallback to original
if 'rating_synthetic' in df.columns:
    df['rating'] = df['rating_synthetic'].fillna(df['rating'])
    print("Using synthetic ratings where available")
else:
    print("No synthetic_rating column found — using original rating")

# Load watch history tensor + mappings
watch_data = torch.load('data/watch_history_tensor.pt')
watch_history_tensor = watch_data['watch_history']
user2idx_watch = watch_data['user2idx']
movie2idx_watch = watch_data['movie2idx']

# Align user/movie mappings
user2idx = {uid: i for i, uid in enumerate(df['user_id'].unique())}
movie2idx = {mid: i for i, mid in enumerate(df['movie_id'].unique())}
num_users = len(user2idx)
num_movies = len(movie2idx)

# Map user/movie to indices
df['user_idx'] = df['user_id'].map(user2idx)
df['movie_idx'] = df['movie_id'].map(movie2idx)

# Normalize numeric features
num_features = ['vote_average', 'vote_count', 'runtime', 'revenue', 'release_year']
df[num_features] = df[num_features].apply(pd.to_numeric, errors='coerce').fillna(0)
df[num_features] = (df[num_features] - df[num_features].min()) / (df[num_features].max() - df[num_features].min())

# Build tensors
X_user = torch.tensor(df['user_idx'].values, dtype=torch.long)
X_movie = torch.tensor(df['movie_idx'].values, dtype=torch.long)
X_num = torch.tensor(df[num_features].values, dtype=torch.float)
y_rating = torch.tensor(df['rating'].values, dtype=torch.float)

# Load or prepare text embeddings
X_emb_matrix = np.load('data/overview_embeddings.npy')
X_emb_matrix = torch.tensor(X_emb_matrix, dtype=torch.float)
movie_id_to_emb_idx = {mid: i for i, mid in enumerate(df['movie_id'].unique())}
X_emb_idx = torch.tensor(df['movie_id'].map(movie_id_to_emb_idx).values, dtype=torch.long)

# Align watch history (if user mapping changed)
aligned_watch_history = torch.zeros((num_users, watch_history_tensor.shape[1]), dtype=torch.long)
for uid, old_idx in user2idx_watch.items():
    if uid in user2idx:
        new_idx = user2idx[uid]
        aligned_watch_history[new_idx] = watch_history_tensor[old_idx]

# Save final package
final_data = {
    'X_user': X_user,
    'X_movie': X_movie,
    'X_num': X_num,
    'X_emb_idx': X_emb_idx,
    'X_emb_matrix': X_emb_matrix,
    'watch_history': aligned_watch_history,
    'y_rating': y_rating,
    'user2idx': user2idx,
    'movie2idx': movie2idx,
    'num_features': num_features,
    'num_users': num_users,
    'num_movies': num_movies
}

torch.save(final_data, 'data/final_training_data_with_watch.pt')
print("Final dataset saved to data/final_training_data_with_watch.pt")