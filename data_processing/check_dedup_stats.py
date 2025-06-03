import pandas as pd

# === Inputs ===
metadata_file = 'TMDB_movie_dataset_v11-2.csv'  # replace with your actual metadata CSV file
recommendation_ids = [17895, 17578, 22819, 24070, 24005, 21352, 17744, 16269, 19759, 19178]

# === Load metadata ===
meta_df = pd.read_csv(metadata_file, low_memory=False)
print(f"Loaded metadata: {len(meta_df)} rows")

# Ensure movie_id type consistency
meta_df['id'] = meta_df['id'].astype(str)
recommendation_ids_str = [str(mid) for mid in recommendation_ids]

# Extract release year
meta_df['release_year'] = pd.to_datetime(meta_df['release_date'], errors='coerce').dt.year

# Filter for recommendations
matched = meta_df[meta_df['id'].isin(recommendation_ids_str)]

if matched.empty:
    print("⚠ No matches found! Check if 'id' format aligns between metadata and recommendations.")
else:
    print(f"Found {len(matched)} matches.")

    # Select relevant fields
    display_cols = ['id', 'title', 'genres', 'release_year', 'vote_average', 'popularity']
    matched_display = matched[display_cols]

    # Export to CSV
    matched_display.to_csv('enriched_recommendations.csv', index=False)
    print("📦 Exported enriched_recommendations.csv")

    # Print preview
    print("\nTop Enriched Recommendations:")
    print(matched_display.head(10))