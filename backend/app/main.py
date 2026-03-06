# app/main.py
import asyncio
import logging
import os
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .limiter import limiter, LIMITER_AVAILABLE
from .routes import users
from .routes import recommendations
from .routes import movies

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

# CORS: use ALLOWED_ORIGINS env (comma-separated). Default includes production Vercel + localhost.
_DEFAULT_ORIGINS = "https://cineai-flame.vercel.app,http://localhost:5173,http://localhost:3000"
_origins_raw = os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS)
ALLOWED_ORIGINS = [x.strip() for x in _origins_raw.split(",") if x.strip()]
logger.info("CORS allowed_origins: %s", ALLOWED_ORIGINS)
# CORS middleware must be added BEFORE other middleware that might intercept requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Explicit OPTIONS handler for all routes (fallback if CORS middleware doesn't catch it)
# Must be exempt from rate limiting so preflight requests always work
@app.options("/{full_path:path}")
@limiter.exempt
async def options_handler(request: Request):
    """Handle OPTIONS preflight requests explicitly."""
    return {"message": "OK"}


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

def _sync_startup():
    """Blocking init: run in a thread so the event loop is not blocked and uvicorn can bind to 8080 immediately."""
    try:
        from .database import Base, engine
        from .models import (
            User,
            UserInteraction,
            Watchlist,
            PasswordResetToken,
            NewsArticle,
            OnboardingStatus,
            RecommendationSnapshot,
        )
        Base.metadata.create_all(bind=engine)
        logger.info(
            "Database tables initialized (Users, UserInteractions, Watchlist, PasswordResetToken, NewsArticle, OnboardingStatus, RecommendationSnapshot)"
        )
    except Exception as e:
        logger.exception("Database initialization error: %s", e)
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
        from .model_retraining import retraining_service
        retraining_service.start_scheduled_retraining()
        logger.info("Model retraining scheduler started")
    except Exception as e:
        logger.warning("Retraining scheduler: %s", e)


@app.on_event("startup")
async def startup_event():
    """Return immediately so uvicorn binds to 0.0.0.0:8080; run blocking init in a thread (not same event loop)."""
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _sync_startup)


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