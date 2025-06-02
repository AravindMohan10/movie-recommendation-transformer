import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
import pickle
import os

# Safely load big/messy CSV
df = pd.read_csv('data/combined_training_data.csv', engine='python')

# Convert numeric fields safely
numeric_cols = ['vote_average', 'avg_review_rating', 'vote_count', 'runtime', 'revenue', 'rating']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

print(f"Loaded combined dataframe with {len(df)} rows")

# Drop any rows with missing required numeric data
df = df.dropna(subset=['user_id', 'movie_id', 'rating'])

# Map user_ids and movie_ids to consecutive indices
user2idx = {id_: idx for idx, id_ in enumerate(df['user_id'].unique())}
movie2idx = {id_: idx for idx, id_ in enumerate(df['movie_id'].unique())}

df['user_idx'] = df['user_id'].map(user2idx)
df['movie_idx'] = df['movie_id'].map(movie2idx)

# Simple numerical normalization
df['vote_average'] = df['vote_average'] / 10.0
df['avg_review_rating'] = df['avg_review_rating'] / 10.0
df['popularity_score'] = df['vote_count'] / df['vote_count'].max()

# Create watch history mapping per user
watch_history = df.groupby('user_idx')['movie_idx'].apply(list).to_dict()

# Save mappings
os.makedirs('artifacts', exist_ok=True)
with open('artifacts/user2idx.pkl', 'wb') as f:
    pickle.dump(user2idx, f)
with open('artifacts/movie2idx.pkl', 'wb') as f:
    pickle.dump(movie2idx, f)

class MovieDataset(Dataset):
    def __init__(self, df, max_seq_length=10):
        self.df = df
        self.max_seq_length = max_seq_length

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        user_idx = row['user_idx']
        movie_idx = row['movie_idx']
        rating = row['rating']

        history = watch_history.get(user_idx, [])[:-1][-self.max_seq_length:]
        if len(history) < self.max_seq_length:
            history = [0] * (self.max_seq_length - len(history)) + history

        num_features = torch.tensor([
            row['vote_average'],
            row['avg_review_rating'],
            row['popularity_score'],
            row['runtime'] if not pd.isna(row['runtime']) else 0,
            row['revenue'] if not pd.isna(row['revenue']) else 0
        ], dtype=torch.float32)

        return {
            'user_idx': torch.tensor(user_idx, dtype=torch.long),
            'movie_idx': torch.tensor(movie_idx, dtype=torch.long),
            'history': torch.tensor(history, dtype=torch.long),
            'num_features': num_features,
            'rating': torch.tensor(rating, dtype=torch.float32)
        }

dataset = MovieDataset(df)
dataloader = DataLoader(dataset, batch_size=64, shuffle=True)

print("PyTorch dataset and dataloader ready")