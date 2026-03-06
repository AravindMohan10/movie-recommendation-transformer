from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, UniqueConstraint, Boolean
from datetime import datetime, timezone
from .database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    signup_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserInteraction(Base):
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    movie_id = Column(Integer, nullable=False, index=True)
    action = Column(String, nullable=False)  # like, dislike, favorite, review
    rating = Column(Float, nullable=True)
    review_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Prevent duplicate interactions (same user, movie, action)
    __table_args__ = (
        UniqueConstraint('user_id', 'movie_id', 'action', name='unique_user_movie_action'),
    )


class Watchlist(Base):
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    movie_id = Column(Integer, nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Prevent duplicate watchlist entries
    __table_args__ = (
        UniqueConstraint('user_id', 'movie_id', name='unique_user_movie_watchlist'),
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    token = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    used = Column(Integer, default=0, nullable=False)  # 0 = not used, 1 = used
    
    # Prevent duplicate active tokens
    __table_args__ = (
        UniqueConstraint('user_id', 'token', name='unique_user_token'),
    )


class NewsArticle(Base):
    """User-provided movie news/articles for personalized digest."""
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String(1000), nullable=True)
    tags = Column(String(500), nullable=True)  # comma-separated e.g. "Sci-Fi, Drama, Nolan"
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class OnboardingStatus(Base):
    """Persisted onboarding status so prompts are consistent across logins."""
    __tablename__ = "onboarding_status"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False, index=True)
    completed = Column(Boolean, default=False, nullable=False)
    skipped = Column(Boolean, default=False, nullable=False)
    stage = Column(Integer, nullable=True)
    data = Column(Text, nullable=True)  # JSON string of onboarding preferences/progress
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class RecommendationSnapshot(Base):
    """Cached recommendation sets per user (e.g., main grid, hidden gems) with 24h TTL."""
    __tablename__ = "recommendation_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    kind = Column(String(50), nullable=False, default="primary")  # e.g. "primary", "hidden_gems"
    data = Column(Text, nullable=False)  # JSON payload with recommendations + metadata
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    metadata_json = Column(Text, nullable=True)  # optional extra fields (limit, model info, etc.)

    __table_args__ = (
        UniqueConstraint("user_id", "kind", name="uq_reco_snapshot_user_kind"),
    )