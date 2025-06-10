#!/usr/bin/env python3
"""
Run CF-only and CF+RAG for the same real DB user, compare Top-20, list RAG-only items.
No metrics. Answers: (1) Is Top-20 different? (2) Do RAG-only items make semantic sense?
(RAG injects up to 20 movies; comparing Top-20 gives them room to show up.)
Run from project root: PYTHONPATH=. python scripts/compare_cf_vs_rag_real_user.py --compare
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def _run_mode(mode: str, output_json: Path, user_id: int) -> None:
    env = os.environ.copy()
    env["USE_RAG_LLM_RERANK"] = "true" if mode == "cf-rag" else "false"
    env["PYTHONPATH"] = str(project_root)
    subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "compare_cf_vs_rag_real_user.py"),
            "--mode", mode,
            "--output-json", str(output_json),
            "--user-id", str(user_id),
        ],
        cwd=str(project_root),
        env=env,
        check=True,
    )


N_COMPARE = 20  # Compare Top-20 so RAG-injected items can appear


def _run_single(mode: str, output_json: Path, user_id: int) -> None:
    """Run one mode (cf-only or cf-rag), write Top-N to output_json."""
    os.environ["USE_RAG_LLM_RERANK"] = "true" if mode == "cf-rag" else "false"
    from backend.app.database import SessionLocal
    from backend.app.models import UserInteraction
    from backend.app.model_service import MovieRecommendationModel

    db = SessionLocal()
    try:
        rows = (
            db.query(UserInteraction.user_id, UserInteraction.movie_id, UserInteraction.action, UserInteraction.review_text)
            .filter(UserInteraction.action.in_(("like", "favorite", "review")))
            .order_by(UserInteraction.user_id)
            .all()
        )
        by_user = {}
        for r in rows:
            uid = int(r[0])
            mid = int(r[1])
            action = r[2]
            rev = (r[3] or "").strip() if r[3] else None
            if uid not in by_user:
                by_user[uid] = []
            by_user[uid].append((mid, action, rev))
        warm = [u for u, recs in by_user.items() if recs]
        if not warm or user_id not in warm:
            raise RuntimeError(f"User {user_id} not warm or no warm users.")
        recs = by_user[user_id]
    finally:
        db.close()

    model = MovieRecommendationModel(use_redis=False)
    if model.engine is None:
        raise RuntimeError("Model not loaded.")
    db2 = SessionLocal()
    try:
        out = model.get_recommendations(
            user_id,
            n_recommendations=N_COMPARE,
            interaction_count=len(recs),
            db_session=db2,
            force_refresh=True,
        )
    finally:
        db2.close()

    top_n = [{"movie_id": r.get("movie_id") or r.get("id"), "title": r.get("title", "?")} for r in out]
    md = getattr(model, "movie_data", {}) or {}
    liked_ids = [mid for mid, _a, _r in recs]
    liked_sample = []
    for mid in liked_ids[:25]:
        m = md.get(mid) or md.get(str(mid))
        t = (m.get("title") if m else None) or "?"
        liked_sample.append({"movie_id": mid, "title": t})
    with open(output_json, "w") as f:
        json.dump({"user_id": user_id, "mode": mode, "top20": top_n, "liked_sample": liked_sample}, f, indent=2)


def _main_compare() -> None:
    from backend.app.database import SessionLocal
    from backend.app.models import UserInteraction

    db = SessionLocal()
    try:
        rows = (
            db.query(UserInteraction.user_id)
            .filter(UserInteraction.action.in_(("like", "favorite", "review")))
            .distinct()
            .order_by(UserInteraction.user_id)
            .all()
        )
        warm = [int(r[0]) for r in rows]
    finally:
        db.close()

    if not warm:
        print("❌ No warm user in DB.")
        return
    user_id = warm[0]
    print(f"✅ Real warm user: user_id={user_id}\n")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
        path_cf = f1.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
        path_rag = f2.name
    try:
        print("🔹 Running CF-only...")
        _run_mode("cf-only", Path(path_cf), user_id)
        print("🔹 Running CF+RAG...")
        _run_mode("cf-rag", Path(path_rag), user_id)

        with open(path_cf) as f:
            cf = json.load(f)
        with open(path_rag) as g:
            rag = json.load(g)
    finally:
        Path(path_cf).unlink(missing_ok=True)
        Path(path_rag).unlink(missing_ok=True)

    top_key = "top20"
    cf_list = cf.get(top_key) or cf.get("top10", [])
    rag_list = rag.get(top_key) or rag.get("top10", [])
    cf_ids = [x["movie_id"] for x in cf_list]
    rag_ids = [x["movie_id"] for x in rag_list]
    cf_set = set(cf_ids)
    rag_set = set(rag_ids)

    rag_only = [x for x in rag_list if x["movie_id"] not in cf_set]
    cf_only = [x for x in cf_list if x["movie_id"] not in rag_set]
    n_diff = len(rag_only) + len(cf_only)

    print("\n" + "=" * 60)
    print("1. Is the Top-20 different from CF+RAG?")
    print("=" * 60)
    print(f"   CF-only Top-20:  {cf_ids}")
    print(f"   CF+RAG Top-20:   {rag_ids}")
    print(f"   Different items: {n_diff} (RAG-only: {len(rag_only)}, CF-only: {len(cf_only)})")
    if n_diff >= 3:
        print("   ✅ Success: 3+ items different.")
    else:
        print("   ⚠️ Fewer than 3 items different.")

    print("\n" + "=" * 60)
    print("2. RAG-only items (in CF+RAG Top-20, not in CF-only) — semantic sense?")
    print("=" * 60)
    if not rag_only:
        print("   None (Top-20 identical).")
    else:
        for x in rag_only:
            print(f"   • [{x['movie_id']}] {x['title']}")
        print("\n   (Compare to user's likes below — do these fit?)")

    liked = rag.get("liked_sample", cf.get("liked_sample", []))
    if liked:
        sample = [f"[{x['movie_id']}] {x['title']}" for x in liked[:15]]
        print("\n   User's likes (sample): " + ", ".join(sample) + ("..." if len(liked) > 15 else ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true", help="Run CF-only and CF+RAG, compare Top-20")
    ap.add_argument("--mode", choices=("cf-only", "cf-rag"), help="Internal: run one mode")
    ap.add_argument("--output-json", type=Path, help="Internal: write results here")
    ap.add_argument("--user-id", type=int, help="Internal: user to use")
    args = ap.parse_args()

    if args.mode and args.output_json is not None and args.user_id is not None:
        _run_single(args.mode, args.output_json, args.user_id)
        return

    if args.compare:
        _main_compare()
        return

    print("Use --compare to run CF-only vs CF+RAG and compare Top-20.")


if __name__ == "__main__":
    main()
