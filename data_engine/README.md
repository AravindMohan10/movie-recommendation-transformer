# Data engine

ETL for movie data from TMDB. Used to build the catalog and training data.

**Setup:** Get a TMDB API key from [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api). Set `TMDB_API_KEY` in your env or run `./scripts/setup_data_extraction.sh`.

**Run extraction:** `python data_engine/extract_data.py` (or use the scripts in `scripts/`).

**Run ETL:** `python data_engine/etl_pipeline.py` after extraction. Output goes to the configured DB and processed files.

See `config.py` and `schema.py` for options and data shapes.
