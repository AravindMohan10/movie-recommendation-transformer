<p align="center">
  <img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/ChromaDB-FF6F61?style=for-the-badge" alt="ChromaDB"/>
  <img src="https://img.shields.io/badge/Groq_LLM-000000?style=for-the-badge" alt="Groq"/>
</p>

<h1 align="center">🎬 CineAI</h1>

<p align="center">
  <strong>AI-Powered Movie Recommendation Engine with Explainable Suggestions</strong>
</p>

<p align="center">
  A production-grade recommendation system combining <b>Collaborative Filtering</b>, <b>Content-Based Transformers</b>, and <b>RAG-powered explanations</b> to deliver personalized movie recommendations with natural language reasoning.
</p>

<p align="center">
  <a href="https://cineai-flame.vercel.app">🌐 Live Demo</a> •
  <a href="https://movie-recommendation-transformer.fly.dev/docs">📖 API Docs</a> •
  <a href="#features">✨ Features</a> •
  <a href="#architecture">🏗️ Architecture</a>
</p>

---

## 🎯 What Makes CineAI Different

Unlike basic recommendation systems that only use watch history, CineAI employs a **hybrid ensemble approach** with three distinct ML models working together:

| Model | Purpose | Technology |
|-------|---------|------------|
| **Collaborative Filtering** | "Users like you also watched..." | Matrix Factorization + PyTorch |
| **Content Transformer** | Semantic understanding of plots, genres, themes | DistilBERT embeddings |
| **Contextual RAG** | Review-aware recommendations + explanations | ChromaDB + Sentence Transformers |

**The result?** Recommendations that can explain *why* a movie was suggested — not just "similar users liked this" but specific reasoning like *"Because you enjoyed the psychological tension in Inception, you might like Shutter Island's mind-bending narrative."*

---

## ✨ Features

### 🎬 Smart Recommendations
- **Personalized picks** that improve with every interaction
- **Confidence scores** showing how certain the AI is about each suggestion
- **"Why this movie?"** — LLM-generated explanations grounded in your taste

### 🔍 Discovery Tools
- **Surprise Me** — Mood-based recommendations (cozy, thrilling, mind-bending)
- **Hidden Gems** — Underrated films matching your preferences
- **Movie Journeys** — Curated thematic collections

### 📝 Engagement
- **Reviews & Ratings** — Train the model with detailed feedback
- **Watchlist** — Save movies for later
- **Share** — Social sharing with custom movie cards

### 🔐 Production-Ready
- **JWT Authentication** with refresh tokens
- **Rate limiting** & origin guards against abuse
- **24-hour recommendation caching** with smart invalidation
- **Scheduled model retraining** pipeline

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     React + Vite + Tailwind                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │ Landing  │ │Dashboard │ │Onboarding│ │ Watchlist│ │ Profile  │  │   │
│  │  │   Page   │ │  + Recs  │ │   Flow   │ │   Page   │ │  + Auth  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                              Vercel Edge                                     │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │ HTTPS
┌────────────────────────────────────┼────────────────────────────────────────┐
│                              API LAYER                                       │
│  ┌─────────────────────────────────┴───────────────────────────────────┐   │
│  │                    FastAPI Application                               │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │   /auth     │ │   /recs     │ │  /movies    │ │  /reviews   │   │   │
│  │  │  JWT + Rate │ │ CF + RAG    │ │  Search +   │ │  CRUD +     │   │   │
│  │  │   Limits    │ │ + LLM Why   │ │  Details    │ │  Ratings    │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                               Fly.io                                         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                           ML / DATA LAYER                                    │
│                                    │                                         │
│  ┌──────────────────┬──────────────┴───────────┬──────────────────┐        │
│  │                  │                          │                  │        │
│  ▼                  ▼                          ▼                  ▼        │
│ ┌────────────┐ ┌────────────┐ ┌─────────────────────┐ ┌────────────┐      │
│ │Collaborative│ │  Content   │ │     RAG Service     │ │    LLM     │      │
│ │ Filtering  │ │Transformer │ │                     │ │  Service   │      │
│ │            │ │            │ │ ┌─────────────────┐ │ │            │      │
│ │ Matrix     │ │ DistilBERT │ │ │    ChromaDB     │ │ │   Groq     │      │
│ │ Factor-    │ │ Embeddings │ │ │ (Vector Store)  │ │ │  LLaMA 3   │      │
│ │ ization    │ │ 768-dim    │ │ │  50K+ movies    │ │ │            │      │
│ │            │ │            │ │ │  + reviews      │ │ │ Generates  │      │
│ │ User-Movie │ │ Plot/Genre │ │ └─────────────────┘ │ │ "Why this  │      │
│ │ Embeddings │ │ Similarity │ │                     │ │  movie?"   │      │
│ └─────┬──────┘ └──────┬─────┘ └──────────┬──────────┘ └──────┬─────┘      │
│       │               │                  │                   │            │
│       └───────────────┴─────────┬────────┴───────────────────┘            │
│                                 │                                          │
│                    ┌────────────▼────────────┐                            │
│                    │   Ensemble Recommender  │                            │
│                    │                         │                            │
│                    │  Confidence-weighted    │                            │
│                    │  score fusion with      │                            │
│                    │  dynamic reranking      │                            │
│                    └────────────┬────────────┘                            │
│                                 │                                          │
│              ┌──────────────────┼──────────────────┐                      │
│              ▼                  ▼                  ▼                      │
│       ┌────────────┐    ┌────────────┐    ┌────────────┐                 │
│       │ PostgreSQL │    │   Redis    │    │   SQLite   │                 │
│       │  (Prod)    │    │  (Cache)   │    │   (Dev)    │                 │
│       └────────────┘    └────────────┘    └────────────┘                 │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 ML Pipeline Deep Dive

### Data Collection & ETL
```
TMDB API → Extract 50K+ movies → Reviews + Metadata → JSONL Storage
              ↓
    Genre mapping, crew extraction, poster URLs
              ↓
    Synthetic user-movie interaction generation
              ↓
    Train/validation/test split (80/10/10)
```

### Model Training Pipeline
```python
# 1. Content-Based Model (Transformer)
MovieContentTransformer(DistilBERT) → 768-dim embeddings per movie

# 2. Collaborative Filtering (Matrix Factorization)
MatrixFactorization(users=10K, movies=50K, embedding_dim=128)

# 3. RAG Index (Semantic Search)
SentenceTransformer("all-MiniLM-L6-v2") → ChromaDB vector store
```

### Recommendation Flow
```
User Request → Load Interactions from DB
                    ↓
    ┌───────────────┴───────────────┐
    ▼                               ▼
CF Candidates (500)          Semantic Candidates (RAG)
    │                               │
    └───────────┬───────────────────┘
                ▼
        Merge & Deduplicate
                ↓
        RAG Reranker (review similarity)
                ↓
        Top-N Selection + Confidence Scoring
                ↓
        LLM Explanation Generation (Groq)
                ↓
        Cache (24h TTL) → Response
```

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | Async REST API with auto-docs |
| **PyTorch** | Neural network models |
| **Sentence Transformers** | Text embeddings |
| **ChromaDB** | Vector similarity search |
| **Groq (LLaMA 3)** | LLM for explanations |
| **SQLAlchemy** | ORM + migrations |
| **Redis** | Caching layer |
| **SlowAPI** | Rate limiting |

### Frontend
| Technology | Purpose |
|------------|---------|
| **React 19** | UI framework |
| **Vite** | Build tooling |
| **Tailwind CSS** | Styling |
| **Framer Motion** | Animations |
| **Three.js / R3F** | 3D effects |
| **React Router 7** | Navigation |

### Infrastructure
| Service | Purpose |
|---------|---------|
| **Fly.io** | Backend hosting (2GB RAM) |
| **Vercel** | Frontend CDN + Edge |
| **PostgreSQL** | Production database |
| **GitHub Actions** | CI/CD |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- 8GB+ RAM (for model inference)

### Quick Start

```bash
# Clone repository
git clone https://github.com/AravindMohan10/movie-recommendation-transformer.git
cd movie-recommendation-transformer

# Backend setup
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure API keys

# Start backend
uvicorn app.main:app --reload --port 8000

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Environment Variables

```bash
# backend/.env
SECRET_KEY=your-jwt-secret-key
GROQ_API_KEY=your-groq-api-key      # For LLM explanations
TMDB_API_KEY=your-tmdb-key          # For movie data
DATABASE_URL=postgresql://...        # Production DB
REDIS_URL=redis://...                # Caching (optional)
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/recommendations` | GET | Personalized movie recommendations |
| `/api/recommendations/hidden-gems` | GET | Underrated film suggestions |
| `/api/recommendations/surprise` | POST | Mood-based discovery |
| `/api/movies/search` | GET | Full-text movie search |
| `/api/movies/{id}` | GET | Movie details + cast |
| `/api/users/interactions` | POST | Record like/dislike/review |
| `/api/watchlist` | GET/POST/DELETE | Manage watchlist |

Full interactive docs: [API Documentation](https://movie-recommendation-transformer.fly.dev/docs)

---

## 🧪 Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run fast unit tests
pytest tests/ -v

# Run with coverage
pytest --cov=backend/app --cov-report=html

# Run slow tests (loads ML models)
pytest -m slow

# Run specific test file
pytest tests/test_recommendation_regressions.py -v
```

---

## 📁 Project Structure

```
movie-recommendation-transformer/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI application
│       ├── routes/              # API endpoints
│       │   ├── recommendations.py
│       │   ├── movies.py
│       │   └── users.py
│       ├── model_service.py     # ML inference
│       ├── rag_service.py       # Vector search
│       ├── llm_service.py       # Groq integration
│       └── auth.py              # JWT authentication
├── frontend/
│   └── src/
│       ├── pages/               # Route components
│       │   ├── Dashboard.jsx    # Main recommendation view
│       │   ├── LandingPage.jsx  # Marketing page
│       │   └── AuthPage.jsx     # Login/signup
│       └── Components/          # Reusable UI
├── models/
│   ├── ensemble_recommender.py  # Main recommendation engine
│   ├── collaborative_filtering.py
│   ├── content_transformer.py
│   └── context_transformer.py
├── data_engine/                 # TMDB ETL pipeline
├── Checkpoints/                 # Trained model weights
├── tests/                       # Pytest suite
└── scripts/                     # Utilities
```

---

## 🚢 Deployment

Detailed deployment instructions in [DEPLOY.md](DEPLOY.md).

**Quick overview:**
1. **Frontend** → Vercel (connect GitHub, auto-deploys)
2. **Backend** → Fly.io (`fly deploy`)
3. **Database** → Fly Postgres or Supabase
4. **RAG Index** → Pre-built in CI, bundled in Docker image

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Cold start (with model load) | ~8s |
| Warm recommendation request | <200ms |
| RAG retrieval (50 candidates) | ~50ms |
| LLM explanation generation | ~2s |
| 24h cache hit rate | >85% |

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/AravindMohan10">Aravind Mohan</a>
</p>
