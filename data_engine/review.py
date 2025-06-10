#!/usr/bin/env python3
"""
Movie Dataset Quality Report Script
Analyzes a TMDB JSONL movie dataset for completeness, diversity, and review coverage.
"""
import json
import sys
import glob
from collections import Counter, defaultdict
from pathlib import Path

# --- Config ---
def get_latest_jsonl(pattern="data/raw/tmdb_movies_full_*.jsonl"):
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None

jsonl_path = sys.argv[1] if len(sys.argv) > 1 else get_latest_jsonl()
if not jsonl_path:
    print("No JSONL file found!")
    sys.exit(1)

print(f"\n🔍 Analyzing: {jsonl_path}\n")

# --- Load Data ---
movies = []
with open(jsonl_path, "r") as f:
    for line in f:
        try:
            movies.append(json.loads(line))
        except Exception as e:
            print(f"⚠️  Skipping malformed line: {e}")

print(f"Total movies loaded: {len(movies)}\n")

# --- Sample Inspection ---
if movies:
    print("Sample keys:", list(movies[0].keys()))
    print("Sample movie:", json.dumps(movies[0], indent=2)[:500], "...\n")

# --- Field Completeness ---
fields = ["title", "release_date", "genres", "overview", "reviews", "cast", "crew"]
missing = {field: 0 for field in fields}
for m in movies:
    for field in fields:
        v = m.get(field)
        if not v or (isinstance(v, list) and not v):
            missing[field] += 1
print("Missing/empty fields:")
for field in fields:
    print(f"  {field:12}: {missing[field]:5} ({missing[field]/len(movies)*100:.1f}%)")
print()

# --- Year, Genre, Language Distribution ---
years = [m.get("release_date", "")[:4] for m in movies if m.get("release_date")]
genres = [g["name"] for m in movies for g in m.get("genres", [])]
languages = [l["name"] for m in movies for l in m.get("spoken_languages", [])]
print("Year distribution (top 10):", Counter(years).most_common(10))
print("Genre distribution (top 10):", Counter(genres).most_common(10))
print("Language distribution (top 10):", Counter(languages).most_common(10))
print()

# --- Review Coverage ---
num_with_reviews = sum(1 for m in movies if m.get("reviews"))
total_reviews = sum(len(m.get("reviews", [])) for m in movies)
avg_reviews = total_reviews / len(movies) if movies else 0
print(f"Movies with reviews: {num_with_reviews} ({num_with_reviews/len(movies)*100:.1f}%)")
print(f"Total reviews: {total_reviews}")
print(f"Average reviews per movie: {avg_reviews:.2f}\n")

# --- Cast/Crew/Director Coverage ---
num_with_cast = sum(1 for m in movies if m.get("cast"))
num_with_crew = sum(1 for m in movies if m.get("crew"))
print(f"Movies with cast: {num_with_cast} ({num_with_cast/len(movies)*100:.1f}%)")
print(f"Movies with crew: {num_with_crew} ({num_with_crew/len(movies)*100:.1f}%)\n")

# --- Director Coverage ---
director_count = 0
for m in movies:
    crew = m.get("crew", [])
    if any(c.get("job", "").lower() == "director" for c in crew):
        director_count += 1
print(f"Movies with director info: {director_count} ({director_count/len(movies)*100:.1f}%)\n")

# --- Summary ---
print("--- SUMMARY ---")
print(f"Total movies: {len(movies)}")
for field in fields:
    print(f"{field:12}: missing {missing[field]:5} ({missing[field]/len(movies)*100:.1f}%)")
print(f"Movies with reviews: {num_with_reviews} ({num_with_reviews/len(movies)*100:.1f}%)")
print(f"Movies with cast: {num_with_cast} ({num_with_cast/len(movies)*100:.1f}%)")
print(f"Movies with crew: {num_with_crew} ({num_with_crew/len(movies)*100:.1f}%)")
print(f"Movies with director info: {director_count} ({director_count/len(movies)*100:.1f}%)")
print(f"Year range: {min(years) if years else 'N/A'} - {max(years) if years else 'N/A'}")
print(f"Top genres: {Counter(genres).most_common(5)}")
print(f"Top languages: {Counter(languages).most_common(5)}")
print(f"Average reviews per movie: {avg_reviews:.2f}")
print("----------------\n")