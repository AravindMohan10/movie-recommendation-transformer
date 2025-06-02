import pandas as pd
import torch
import numpy as np

# Load combined data
df = pd.read_csv('data/combined_training_data.csv', low_memory=False)
print(f"Loaded {len(df)} rows")

# Make sure watched_at is datetime
df['watched_at'] = pd.to_datetime(df['watched_at'], errors='coerce')

# Drop rows without timestamps
df = df.dropna(subset=['watched_at'])

# Sort by watched_at
df = df.sort_values(['user_id', 'watched_at'])

# Map user_id to index
unique_users = df['user_id'].unique()
user2idx = {uid: i for i, uid in enumerate(unique_users)}
num_users = len(unique_users)

# Map movie_id to index
unique_movies = df['movie_id'].unique()
movie2idx = {mid: i for i, mid in enumerate(unique_movies)}
num_movies = len(unique_movies)

# Prepare watch history (last 10 movie_idx per user)
max_seq_len = 10
watch_history = np.zeros((num_users, max_seq_len), dtype=np.int64)

for uid in unique_users:
    user_idx = user2idx[uid]
    user_movies = df[df['user_id'] == uid]['movie_id'].map(movie2idx).tolist()
    last_movies = user_movies[-max_seq_len:]
    padded = [0] * (max_seq_len - len(last_movies)) + last_movies
    watch_history[user_idx] = np.array(padded)

# Convert to tensor
watch_history_tensor = torch.tensor(watch_history, dtype=torch.long)
print(f"Built watch history tensor with shape {watch_history_tensor.shape}")

# Save
torch.save({
    'watch_history': watch_history_tensor,
    'user2idx': user2idx,
    'movie2idx': movie2idx
}, 'data/watch_history_tensor.pt')

print("Saved watch history tensor to data/watch_history_tensor.pt")