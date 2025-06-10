#!/usr/bin/env python3
"""
Use a real DB user with interactions and run CF+RAG recommendations.
Run from project root: PYTHONPATH=. python scripts/check_real_user_rag.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Ensure RAG is used
os.environ["USE_RAG_LLM_RERANK"] = "true"


def main() -> None:
    from backend.app.database import SessionLocal
    from backend.app.models import User, UserInteraction
    from backend.app.model_service import MovieRecommendationModel

    db = SessionLocal()
    try:
        # Users with >= 1 like or review
        rows = (
            db.query(UserInteraction.user_id, UserInteraction.movie_id, UserInteraction.action, UserInteraction.review_text)
            .filter(UserInteraction.action.in_(("like", "favorite", "review")))
            .order_by(UserInteraction.user_id)
            .all()
        )
        by_user: Dict[int, List[Tuple[int, str, Optional[str]]]] = {}
        for r in rows:
            uid = int(r[0])
            mid = int(r[1])
            action = r[2]
            rev = (r[3] or "").strip() if r[3] else None
            if uid not in by_user:
                by_user[uid] = []
            by_user[uid].append((mid, action, rev))

        # Prefer users with both like and review; else any with >= 1
        warm = [u for u, recs in by_user.items() if recs]
        if not warm:
            print("❌ No user with like/favorite/review in DB.")
            return

        # Pick first warm user
        user_id = warm[0]
        recs = by_user[user_id]
        n_like = sum(1 for _, a, _ in recs if a in ("like", "favorite"))
        n_rev = sum(1 for _, a, t in recs if a == "review" and t)
        print(f"✅ Real warm user: user_id={user_id}")
        print(f"   n_likes+favorites={n_like}  n_reviews(with text)={n_rev}")
        print(f"   interactions: {[(m, a) for m, a, _ in recs[:15]]}{'...' if len(recs) > 15 else ''}")

        u = db.query(User).filter(User.user_id == user_id).first()
        if u:
            print(f"   username={u.username}  email={u.email}")
    finally:
        db.close()

    print("\n🤖 Loading model (CF+RAG)...")
    model = MovieRecommendationModel(use_redis=False)
    if model.engine is None:
        print("⚠️ Model not loaded; cannot get recs.")
        return

    db2 = SessionLocal()
    try:
        out = model.get_recommendations(
            user_id,
            n_recommendations=10,
            interaction_count=len(recs),
            db_session=db2,
            force_refresh=True,
        )
    finally:
        db2.close()

    print(f"\n📋 Top-10 CF+RAG recommendations for user_id={user_id}:")
    for i, r in enumerate(out, 1):
        mid = r.get("movie_id") or r.get("id")
        title = r.get("title", "?")
        print(f"   {i}. [{mid}] {title}")


if __name__ == "__main__":
    main()
