import pandas as pd

# Load full dataset
df = pd.read_csv('TMDB_movie_dataset_v11-2.csv')

# Drop duplicates by ID
df = df.drop_duplicates(subset='id')

import pandas as pd

final_df = pd.read_csv('balanced_50k_unique_tmdb_ids.csv')

print(f"✅ Total rows in file: {final_df.shape[0]}")

unique_count = final_df['id'].nunique()
print(f"✅ Unique TMDB IDs: {unique_count}")

print("\nSample IDs:")
print(final_df.head(100))

duplicates = final_df['id'].duplicated().sum()
print(f"Number of duplicate IDs: {duplicates}")