# CineAI

Movie recommendation app that learns from your likes, ratings, and reviews.

**Tech:** FastAPI, React (Vite), PyTorch, collaborative filtering + content/RAG, ChromaDB, SQLite/Postgres. Deployed on Fly.io (backend) and Vercel (frontend).

## What it does

- Onboarding flow to capture genre and movie preferences
- Personalized recommendations (collaborative filtering + content/RAG)
- Watchlist, reviews, and “why this recommendation” explanations
- Hidden gems, mood search, and movie journeys

## Live

- **App:** [Add your Vercel URL after deploy]
- **API:** https://movie-recommendation-transformer.fly.dev
- **API docs:** https://movie-recommendation-transformer.fly.dev/docs

## Run locally

**Prerequisites:** Python 3.8+, Node 16+, 8GB+ RAM for the model.

```bash
# Backend (from project root)
cd backend
pip install -r requirements.txt   # or use a venv
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the helper script:
# ./scripts/start_backend.sh

# Frontend (other terminal)
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:5173  
- API: http://localhost:8000  
- API docs: http://localhost:8000/docs  

Copy `backend/.env.example` to `backend/.env` and set `SECRET_KEY`, `GROQ_API_KEY`, and optionally `TMDB_API_KEY`, Postgres, Resend (for password reset). See `backend/.env.example` for all options.

## Deploy (Vercel + Fly.io)

Step-by-step instructions are in [DEPLOY.md](DEPLOY.md): frontend on Vercel, backend on Fly.io, with env vars and health checks.

## Project layout

- `backend/` – FastAPI app (auth, recommendations, movies, RAG, LLM)
- `frontend/` – Vite + React
- `Checkpoints/` – Trained model weights (train separately or add your own)
- `data_engine/` – TMDB extraction and ETL (see `data_engine/README.md`)
- `scripts/` – Setup and start scripts
- `tests/` – Pytest unit tests (see `tests/README.md`)

## Tests

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                              # fast unit tests
pytest --cov=backend/app            # with coverage
pytest -m slow                      # loads ML checkpoints (optional)
```

## License

MIT.
