# backend/app/database.py
import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()
logger = logging.getLogger(__name__)

# Force SQLite for now (can be overridden with POSTGRES env vars if needed)
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")

if USE_POSTGRES and DB_USER and DB_PASSWORD and DB_NAME:
    # Use PostgreSQL only if explicitly enabled and all vars are set
    DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    connect_args = {}
    logger.info("Using PostgreSQL")
else:
    # Default to SQLite; override with DATABASE_PATH for Fly.io volume (e.g. /data/cineai.db)
    db_path = os.getenv("DATABASE_PATH")
    if not db_path:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(BASE_DIR, "cineai.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    connect_args = {"check_same_thread": False}

# echo=True for SQL logging; pool_pre_ping to avoid "connection already closed" errors
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a SQLAlchemy Session,
    and ensures it’s closed when the request is done.
    Usage:
        def some_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()