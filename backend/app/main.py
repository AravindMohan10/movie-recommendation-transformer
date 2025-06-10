# app/main.py
import logging
import os
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .limiter import limiter, LIMITER_AVAILABLE
from .routes import users
from .routes import recommendations
from .routes import movies
from .model_retraining import retraining_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cineai")

app = FastAPI(title="CineAI API", version="1.0.0")
app.state.limiter = limiter
if LIMITER_AVAILABLE:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.errors import RateLimitExceeded
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
else:
    logger.warning("slowapi not installed: rate limiting disabled. Install with: pip install slowapi")

# CORS: use ALLOWED_ORIGINS env (comma-separated) or default to localhost
_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
ALLOWED_ORIGINS = [x.strip() for x in _origins_raw.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware (for tracing in production)
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# Include routers (recommendations and movies already have /api prefix)
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(recommendations.router, tags=["recommendations"])  # Already has /api prefix
app.include_router(movies.router, tags=["movies"])  # Already has /api prefix

# Import and include watchlist router
from .routes import watchlist
app.include_router(watchlist.router, tags=["watchlist"])  # Already has /api prefix

from .routes import reviews
app.include_router(reviews.router)

from .routes import news
app.include_router(news.router)

# Debug router: only in non-production (disabled when ENV=production)
ENV = os.getenv("ENV", "development").lower()
if ENV != "production":
    try:
        from .routes import debug
        app.include_router(debug.router, tags=["debug"])
        logger.info("Debug router enabled (ENV != production)")
    except Exception as e:
        logger.warning("Debug router not available: %s", e)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Create database tables if they don't exist
        from .database import Base, engine
        from .models import User, UserInteraction, Watchlist, PasswordResetToken, NewsArticle
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized (Users, UserInteractions, Watchlist, PasswordResetToken, NewsArticle)")
    except Exception as e:
        logger.exception("Database initialization error: %s", e)
        raise

    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        try:
            from monitor_recommendations import RecommendationMonitor
            db_path = os.path.join(project_root, "cineai.db")
            RecommendationMonitor(db_path=db_path)
            logger.info("Monitoring tables initialized")
        except Exception as e:
            logger.warning("Monitoring initialization: %s", e)
    except Exception as e:
        logger.warning("Monitoring setup: %s", e)

    try:
        retraining_service.start_scheduled_retraining()
        logger.info("Model retraining scheduler started")
    except Exception as e:
        logger.warning("Retraining scheduler: %s", e)

@app.get("/")
@limiter.exempt
async def root():
    return {"message": "Welcome to CineAI API", "version": "1.0.0"}

@app.get("/health")
@limiter.exempt
async def health_check():
    """Lightweight liveness check (no DB/model)."""
    return {"status": "healthy", "service": "CineAI API"}

@app.get("/ready")
@limiter.exempt
async def ready_check():
    """Readiness: DB connectivity. For k8s/load balancer."""
    from .database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "service": "CineAI API"}
    except Exception as e:
        logger.warning("Ready check failed: %s", e)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "detail": "Database unavailable"},
        )
    finally:
        db.close()