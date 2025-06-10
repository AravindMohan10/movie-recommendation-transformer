#!/usr/bin/env python3
"""
Evaluation metrics for recommendation model quality.
Implements Precision@K, Recall@K, NDCG, and other standard metrics.
Supports CF-only vs CF+RAG ablation via --ablate.

Eval population: users with num_likes + num_reviews >= 1 (warm) vs cold. Logs
num_users_total, num_users_with_text_signal. CF+RAG runs only on warm users;
assert (n_liked > 0 or n_reviewed > 0) per user — fail-fast on RAG-inactive.

--ablate reports two cohorts: Cohort A (cold, CF-only; fallback safety), Cohort B
(warm, CF-only vs CF+RAG; % RAG activation, % Top-20 differs, examples).

Run from project root:
  PYTHONPATH=. python evaluate_model.py [--output path.json] [--use-rag|--no-use-rag]
  PYTHONPATH=. python evaluate_model.py --ablate   # Cohort A + B tables
  PYTHONPATH=. python evaluate_model.py --dry-run  # No model load; synthetic recs only
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path
import json
import numpy as np
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _norm_mid(x) -> Optional[int]:
    """Normalize movie ID to int for consistent evaluation."""
    if x is None:
        return None
    try:
        return int(x)
    except (ValueError, TypeError):
        return None

class RecommendationEvaluator:
    """
    Evaluate recommendation model quality using standard metrics.
    """
    
    def __init__(self, test_interactions: List[Dict], all_movies: Set[int]):
        """
        Initialize evaluator.
        
        Args:
            test_interactions: List of {user_id, movie_id, rating} dicts for testing
            all_movies: Set of all movie IDs in catalog
        """
        self.test_interactions = test_interactions
        self.all_movies = all_movies
        
        # Build test sets: user -> movies they rated highly (>= 7.0)
        self.user_relevant_movies = defaultdict(set)
        self.user_all_ratings = defaultdict(list)
        
        for interaction in test_interactions:
            user_id = interaction['user_id']
            movie_id = interaction['movie_id']
            rating = interaction.get('rating', 0)
            
            self.user_all_ratings[user_id].append((movie_id, rating))
            if rating >= 7.0:  # Consider ratings >= 7 as "relevant"
                self.user_relevant_movies[user_id].add(movie_id)
        
        logger.info(f"Built test sets: {len(self.user_relevant_movies)} users with relevant movies")
    
    def precision_at_k(self, recommended: List[int], relevant: Set[int], k: int) -> float:
        """
        Calculate Precision@K.
        
        Args:
            recommended: List of recommended movie IDs
            relevant: Set of relevant (actually liked) movie IDs
            k: Number of top recommendations to consider
        
        Returns:
            Precision@K score (0.0 to 1.0)
        """
        if k == 0 or len(recommended) == 0:
            return 0.0
        
        top_k = recommended[:k]
        if len(top_k) == 0:
            return 0.0
        
        relevant_count = sum(1 for movie_id in top_k if movie_id in relevant)
        return relevant_count / len(top_k)
    
    def recall_at_k(self, recommended: List[int], relevant: Set[int], k: int) -> float:
        """
        Calculate Recall@K.
        
        Args:
            recommended: List of recommended movie IDs
            relevant: Set of relevant (actually liked) movie IDs
            k: Number of top recommendations to consider
        
        Returns:
            Recall@K score (0.0 to 1.0)
        """
        if len(relevant) == 0:
            return 0.0
        
        top_k = recommended[:k] if len(recommended) >= k else recommended
        if len(top_k) == 0:
            return 0.0
        
        relevant_count = sum(1 for movie_id in top_k if movie_id in relevant)
        return relevant_count / len(relevant)
    
    def ndcg_at_k(self, recommended: List[int], relevant: Set[int], 
                   ratings: Dict[int, float], k: int) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain@K.
        
        Args:
            recommended: List of recommended movie IDs
            relevant: Set of relevant movie IDs
            ratings: Dict of {movie_id: rating} for relevant movies
            k: Number of top recommendations to consider
        
        Returns:
            NDCG@K score (0.0 to 1.0)
        """
        if len(relevant) == 0:
            return 0.0
        
        top_k = recommended[:k] if len(recommended) >= k else recommended
        
        # Calculate DCG
        dcg = 0.0
        for i, movie_id in enumerate(top_k, 1):
            if movie_id in relevant:
                rating = ratings.get(movie_id, 0)
                dcg += (2 ** rating - 1) / np.log2(i + 1)
        
        # Calculate IDCG (Ideal DCG)
        ideal_ratings = sorted([ratings.get(mid, 0) for mid in relevant], reverse=True)
        idcg = 0.0
        for i, rating in enumerate(ideal_ratings[:k], 1):
            idcg += (2 ** rating - 1) / np.log2(i + 1)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def coverage(self, recommended_all_users: Dict[int, List[int]]) -> float:
        """
        Calculate catalog coverage - % of movies recommended at least once.
        
        Args:
            recommended_all_users: Dict of {user_id: [movie_ids]}
        
        Returns:
            Coverage score (0.0 to 1.0)
        """
        all_recommended = set()
        for user_recs in recommended_all_users.values():
            all_recommended.update(user_recs)
        
        if len(self.all_movies) == 0:
            return 0.0
        
        return len(all_recommended) / len(self.all_movies)
    
    def diversity(self, recommended: List[int], movie_genres: Dict[int, List[str]]) -> float:
        """
        Calculate diversity - average pairwise dissimilarity.
        
        Args:
            recommended: List of recommended movie IDs
            movie_genres: Dict of {movie_id: [genres]}
        
        Returns:
            Diversity score (0.0 to 1.0)
        """
        if len(recommended) < 2:
            return 0.0
        
        # Simple Jaccard diversity based on genres
        genre_sets = []
        for movie_id in recommended[:10]:  # Top 10 for efficiency
            genres = set(movie_genres.get(movie_id, []))
            if genres:
                genre_sets.append(genres)
        
        if len(genre_sets) < 2:
            return 0.0
        
        # Calculate average pairwise Jaccard distance
        total_distance = 0.0
        pairs = 0
        
        for i in range(len(genre_sets)):
            for j in range(i + 1, len(genre_sets)):
                intersection = len(genre_sets[i] & genre_sets[j])
                union = len(genre_sets[i] | genre_sets[j])
                if union > 0:
                    jaccard = intersection / union
                    distance = 1 - jaccard  # Distance = 1 - similarity
                    total_distance += distance
                    pairs += 1
        
        return total_distance / pairs if pairs > 0 else 0.0
    
    def evaluate(self, user_recommendations: Dict[int, List[int]], 
                 movie_genres: Dict[int, List[str]] = None,
                 k_values: List[int] = [5, 10, 20]) -> Dict[str, float]:
        """
        Evaluate recommendations for all users.
        
        Args:
            user_recommendations: Dict of {user_id: [recommended_movie_ids]}
            movie_genres: Optional dict of {movie_id: [genres]} for diversity
            k_values: List of K values to evaluate at
        
        Returns:
            Dict of metric_name: score
        """
        results = {}
        
        # Get user ratings for NDCG
        user_ratings = {}
        for user_id, ratings_list in self.user_all_ratings.items():
            user_ratings[user_id] = {mid: rating for mid, rating in ratings_list}
        
        # Initialize movie_genres if not provided
        if movie_genres is None:
            movie_genres = {}
        
        # Calculate metrics for each K
        for k in k_values:
            precisions = []
            recalls = []
            ndcgs = []
            diversities = []
            
            for user_id, recommended in user_recommendations.items():
                if user_id not in self.user_relevant_movies:
                    continue
                
                relevant = self.user_relevant_movies[user_id]
                ratings = user_ratings.get(user_id, {})
                
                # Precision@K
                prec = self.precision_at_k(recommended, relevant, k)
                precisions.append(prec)
                
                # Recall@K
                rec = self.recall_at_k(recommended, relevant, k)
                recalls.append(rec)
                
                # NDCG@K
                if ratings:
                    ndcg = self.ndcg_at_k(recommended, relevant, ratings, k)
                    ndcgs.append(ndcg)
                
                # Diversity@K
                if movie_genres:
                    div = self.diversity(recommended[:k], movie_genres)
                    if div > 0:
                        diversities.append(div)
            
            # Average metrics
            if precisions:
                results[f'Precision@{k}'] = np.mean(precisions)
            if recalls:
                results[f'Recall@{k}'] = np.mean(recalls)
            if ndcgs:
                results[f'NDCG@{k}'] = np.mean(ndcgs)
            if diversities:
                results[f'Diversity@{k}'] = np.mean(diversities)
        
        # Overall coverage
        results['Coverage'] = self.coverage(user_recommendations)
        
        return results


def load_test_data():
    """Load test interaction data."""
    ratings_path = project_root / "data" / "realistic_synthetic_ratings_new_data.csv"
    
    if not ratings_path.exists():
        logger.warning(f"Ratings file not found: {ratings_path}")
        return None, None
    
    import pandas as pd
    df = pd.read_csv(ratings_path)
    
    # Take 20% as test set
    test_df = df.sample(frac=0.2, random_state=42)
    
    interactions = []
    for _, row in test_df.iterrows():
        interactions.append({
            'user_id': int(row['user_id']),
            'movie_id': int(row['movie_id']),
            'rating': float(row['rating'])
        })
    
    all_movies = set(int(x) for x in df['movie_id'].unique())

    logger.info(f"Loaded {len(interactions)} test interactions")
    logger.info(f"Total unique movies: {len(all_movies)}")
    
    return interactions, all_movies


def get_user_signal_counts(
    db_session,
    user_ids: List[int],
) -> Dict[int, Tuple[int, int]]:
    """(n_liked, n_reviewed) per user. liked = like + favorite. Users not in DB get (0,0)."""
    out: Dict[int, Tuple[int, int]] = {uid: (0, 0) for uid in user_ids}
    if not db_session or not user_ids:
        return out
    try:
        from backend.app.models import UserInteraction
        rows = (
            db_session.query(UserInteraction.user_id, UserInteraction.action, UserInteraction.review_text)
            .filter(UserInteraction.user_id.in_(user_ids))
            .all()
        )
        # aggregate
        for r in rows:
            uid = int(r[0])
            if uid not in out:
                continue
            n_liked, n_rev = out[uid]
            if r[1] in ("like", "favorite"):
                n_liked += 1
            elif r[1] == "review" and (r[2] or "").strip():
                n_rev += 1
            out[uid] = (n_liked, n_rev)
    except Exception as e:
        logger.warning("get_user_signal_counts failed: %s", e)
    return out


def load_movie_genres():
    """Load movie genres for diversity calculation."""
    movie_file = project_root / "data" / "raw" / "tmdb_movies_50k_20250711_011112.jsonl"
    if not movie_file.exists():
        movie_file = project_root / "data" / "raw" / "tmdb_complete_dataset.jsonl"
    
    if not movie_file.exists():
        logger.warning("Movie data file not found")
        return {}
    
    genres_map: Dict[int, List[str]] = {}
    with open(movie_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                movie = json.loads(line.strip())
                raw = movie.get('tmdb_id') or movie.get('id')
                movie_id = _norm_mid(raw)
                if movie_id is not None:
                    genres = movie.get('genres', [])
                    if isinstance(genres, list) and len(genres) > 0:
                        if isinstance(genres[0], dict):
                            genre_names = [g.get('name', '') for g in genres if isinstance(g, dict)]
                        else:
                            genre_names = [str(g) for g in genres]
                        genres_map[movie_id] = genre_names
            except Exception:
                continue

    logger.info(f"Loaded genres for {len(genres_map)} movies")
    return genres_map


def generate_recommendations_for_evaluation(
    model_service,
    user_ids: List[int],
    n_recommendations: int = 20,
    force_refresh: bool = True,
    db_session=None,
    use_rag: bool = False,
    signal_counts: Optional[Dict[int, Tuple[int, int]]] = None,
    warm_ids: Optional[Set[int]] = None,
) -> Tuple[Dict[int, List[int]], Dict[int, bool]]:
    """Generate recommendations. use_rag=True: only warm users, assert each has signal; collect RAG activation."""
    user_recommendations: Dict[int, List[int]] = {}
    rag_activation: Dict[int, bool] = {}
    signal_counts = signal_counts or {}
    warm_set = warm_ids or set()

    if use_rag:
        user_ids = [u for u in user_ids if u in warm_set]
        print(f"\n🎬 Generating CF+RAG recommendations for {len(user_ids)} warm users (RAG-eligible only)...")
    else:
        print(f"\n🎬 Generating recommendations for {len(user_ids)} users...")

    for i, user_id in enumerate(user_ids, 1):
        if i % 50 == 0 or i == len(user_ids):
            print(f"   Processed {i}/{len(user_ids)} users...")

        if use_rag:
            n_liked, n_reviewed = signal_counts.get(user_id, (0, 0))
            assert (n_liked > 0 or n_reviewed > 0), "RAG inactive user in RAG eval"

        try:
            recs = model_service.get_recommendations(
                user_id,
                n_recommendations,
                interaction_count=0,
                db_session=db_session,
                force_refresh=force_refresh,
            )
            ids: List[int] = []
            for rec in recs:
                mid = rec.get("movie_id") or rec.get("id")
                n = _norm_mid(mid)
                if n is not None:
                    ids.append(n)
            user_recommendations[user_id] = ids
            if use_rag:
                from backend.app.rag_reranker import _last_rag_activation
                rag_activation[user_id] = _last_rag_activation.get(user_id, False)
        except Exception as e:
            logger.warning("Error getting recommendations for user %s: %s", user_id, e)
            user_recommendations[user_id] = []

    return user_recommendations, rag_activation


def _run_single_evaluation(
    use_rag: bool,
    output_path: Path,
    output_per_user: Optional[Path] = None,
    output_activation: Optional[Path] = None,
    cohort_file: Optional[Path] = None,
) -> Dict[str, float]:
    """Run one evaluation pass (CF-only or CF+RAG). USE_RAG_LLM_RERANK must be set before import."""
    os.environ["USE_RAG_LLM_RERANK"] = "true" if use_rag else "false"

    test_interactions, all_movies = load_test_data()
    if test_interactions is None:
        raise RuntimeError("Could not load test data.")
    movie_genres = load_movie_genres()
    evaluator = RecommendationEvaluator(test_interactions, all_movies)

    from backend.app.database import SessionLocal
    from backend.app.model_service import MovieRecommendationModel

    model_service = MovieRecommendationModel(use_redis=False)
    if model_service.engine is None:
        print("⚠️  Models not loaded. Using fallback recommendations.")

    candidate_ids = list(evaluator.user_relevant_movies.keys())[:100]
    db = SessionLocal()
    try:
        signal_counts = get_user_signal_counts(db, candidate_ids)
        warm_ids = {u for u in candidate_ids if (signal_counts[u][0] + signal_counts[u][1]) >= 1}
        cold_ids = [u for u in candidate_ids if u not in warm_ids]
        warm_list = sorted(warm_ids)
        num_users_total = len(candidate_ids)
        num_users_with_text_signal = len(warm_ids)
        print(f"\n📊 Eval population: num_users_total={num_users_total}  num_users_with_text_signal={num_users_with_text_signal}")

        if cohort_file is not None:
            cohort_data = {"cold": cold_ids, "warm": warm_list}
            with open(cohort_file, "w") as f:
                json.dump(cohort_data, f, indent=2)

        if use_rag:
            user_ids_to_run = warm_list
            if not user_ids_to_run:
                raise RuntimeError("CF+RAG eval requires >= 1 warm user (num_likes+num_reviews>=1). None found.")
        else:
            user_ids_to_run = candidate_ids

        user_recommendations, rag_activation = generate_recommendations_for_evaluation(
            model_service,
            user_ids_to_run,
            n_recommendations=20,
            force_refresh=True,
            db_session=db,
            use_rag=use_rag,
            signal_counts=signal_counts,
            warm_ids=warm_ids,
        )
    finally:
        db.close()

    if output_per_user is not None:
        per_user_json = {str(uid): ids for uid, ids in user_recommendations.items()}
        with open(output_per_user, "w") as f:
            json.dump(per_user_json, f, indent=2)
        print(f"💾 Per-user recs saved to: {output_per_user}")
    if output_activation is not None and use_rag and rag_activation:
        act_json = {str(uid): bool(v) for uid, v in rag_activation.items()}
        with open(output_activation, "w") as f:
            json.dump(act_json, f, indent=2)
        print(f"💾 RAG activation saved to: {output_activation}")

    return evaluator.evaluate(user_recommendations, movie_genres, k_values=[5, 10, 20])


def _run_dry_run(output_path: Path) -> None:
    """Skip model load; run evaluator on synthetic recs to verify pipeline and ID handling."""
    print("=" * 70)
    print("📊 Dry run (no model load) — synthetic recommendations")
    print("=" * 70)
    print("\n📂 Loading test data...")
    test_interactions, all_movies = load_test_data()
    if test_interactions is None:
        print("❌ Could not load test data.")
        sys.exit(1)
    print("📂 Loading movie genres...")
    movie_genres = load_movie_genres()
    print("\n🔧 Initializing evaluator...")
    evaluator = RecommendationEvaluator(test_interactions, all_movies)
    test_user_ids = list(evaluator.user_relevant_movies.keys())[:100]
    all_list = list(all_movies)

    # Synthetic recs: for each user, recommend some of their relevant movies + random others
    user_recommendations: Dict[int, List[int]] = {}
    rng = np.random.default_rng(42)
    for uid in test_user_ids:
        rel = list(evaluator.user_relevant_movies[uid])
        others = [m for m in all_list if m not in rel]
        n_rel = min(5, len(rel))
        n_other = max(0, 20 - n_rel)
        pick_rel = list(rng.choice(rel, size=n_rel, replace=False)) if len(rel) >= n_rel and n_rel else list(rel)
        n_o = min(n_other, len(others))
        pick_other = list(rng.choice(others, size=n_o, replace=False)) if n_o and others else []
        user_recommendations[uid] = list(pick_rel) + list(pick_other)
        rng.shuffle(user_recommendations[uid])

    print(f"\n👥 Evaluating on {len(test_user_ids)} users (synthetic recs)...")
    results = evaluator.evaluate(user_recommendations, movie_genres, k_values=[5, 10, 20])
    _print_results(results, "DRY-RUN RESULTS (synthetic)")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {output_path}\n")


def _print_results(results: Dict[str, float], title: str = "EVALUATION RESULTS") -> None:
    """Print metrics to stdout."""
    print("\n" + "=" * 70)
    print(f"📊 {title}")
    print("=" * 70)
    print("\n🎯 Accuracy Metrics:")
    for metric in [
        "Precision@5", "Precision@10", "Precision@20",
        "Recall@5", "Recall@10", "Recall@20",
        "NDCG@5", "NDCG@10", "NDCG@20",
    ]:
        if metric in results:
            print(f"   {metric:15s}: {results[metric]:.3f} ({results[metric]:.1%})")
    print("\n🌟 Quality Metrics:")
    for metric in ["Diversity@5", "Diversity@10", "Diversity@20", "Coverage"]:
        if metric in results:
            print(f"   {metric:15s}: {results[metric]:.3f} ({results[metric]:.1%})")


def _run_ablation() -> None:
    """Run CF-only and CF+RAG via subprocesses. Report Cohort A (cold) and Cohort B (warm) tables."""
    out_cf = project_root / "evaluation_cf_only.json"
    out_rag = project_root / "evaluation_cf_rag.json"
    out_cf_per_user = project_root / "evaluation_cf_only_per_user.json"
    out_rag_per_user = project_root / "evaluation_cf_rag_per_user.json"
    out_activation = project_root / "evaluation_cf_rag_activation.json"
    cohort_file = project_root / "ablation_cohorts.json"
    env = os.environ.copy()
    base = [sys.executable, str(Path(__file__).resolve())]

    print("=" * 70)
    print("📊 RAG Ablation: CF-only vs CF+RAG (Cohort A cold / Cohort B warm)")
    print("=" * 70)

    print("\n🔹 Run 1: CF-only (cold + warm)...")
    env["USE_RAG_LLM_RERANK"] = "false"
    subprocess.run(
        base + [
            "--output", str(out_cf),
            "--output-per-user", str(out_cf_per_user),
            "--cohort-file", str(cohort_file),
            "--no-use-rag",
        ],
        cwd=str(project_root),
        env=env,
        check=True,
    )

    print("\n🔹 Run 2: CF+RAG (warm only, fail-fast on RAG-inactive)...")
    env["USE_RAG_LLM_RERANK"] = "true"
    subprocess.run(
        base + [
            "--output", str(out_rag),
            "--output-per-user", str(out_rag_per_user),
            "--output-activation", str(out_activation),
            "--cohort-file", str(cohort_file),
            "--use-rag",
        ],
        cwd=str(project_root),
        env=env,
        check=True,
    )

    # Load cohort + per-user outputs
    with open(cohort_file) as f:
        cohorts = json.load(f)
    cold = [int(u) for u in cohorts["cold"]]
    warm = [int(u) for u in cohorts["warm"]]

    with open(out_cf_per_user) as f:
        cf_per = json.load(f)
    with open(out_rag_per_user) as g:
        rag_per = json.load(g)
    act_raw: Dict[str, bool] = {}
    if out_activation.exists():
        with open(out_activation) as h:
            act_raw = json.load(h)

    # Build evaluator for cohort metrics
    test_interactions, all_movies = load_test_data()
    if test_interactions is None:
        raise RuntimeError("Could not load test data.")
    movie_genres = load_movie_genres()
    evaluator = RecommendationEvaluator(test_interactions, all_movies)
    k_values = [5, 10, 20]
    metrics = [
        "Precision@5", "Precision@10", "Precision@20",
        "Recall@5", "Recall@10", "Recall@20",
        "NDCG@5", "NDCG@10", "NDCG@20",
        "Diversity@5", "Diversity@10", "Diversity@20", "Coverage",
    ]

    # Cohort A: Cold users — CF-only (validates fallback safety)
    cf_cold = {str(u): cf_per[str(u)] for u in cold if str(u) in cf_per}
    if cf_cold:
        recs_cold = {int(u): ids for u, ids in cf_cold.items()}
        res_a = evaluator.evaluate(recs_cold, movie_genres, k_values=k_values)
        print("\n" + "=" * 70)
        print("📊 Cohort A: Cold users (CF-only by design)")
        print("=" * 70)
        print(f"   n = {len(cf_cold)} users (no likes/reviews). Expect no RAG; fallback safety.")
        _print_results(res_a, "Cohort A — CF-only")
    else:
        print("\n📊 Cohort A: No cold users (skip).")

    # Cohort B: Warm users — CF-only vs CF+RAG
    cf_warm = {str(u): cf_per[str(u)] for u in warm if str(u) in cf_per}
    rag_warm = {str(u): rag_per[str(u)] for u in warm if str(u) in rag_per}
    if not cf_warm or not rag_warm:
        print("\n📊 Cohort B: Insufficient warm users or RAG output (skip).")
    else:
        recs_cf_warm = {int(u): ids for u, ids in cf_warm.items()}
        recs_rag_warm = {int(u): ids for u, ids in rag_warm.items()}
        res_cf = evaluator.evaluate(recs_cf_warm, movie_genres, k_values=k_values)
        res_rag = evaluator.evaluate(recs_rag_warm, movie_genres, k_values=k_values)
        print("\n" + "=" * 70)
        print("📊 Cohort B: Warm users (RAG-eligible)")
        print("=" * 70)
        print(f"   n = {len(rag_warm)} users (num_likes + num_reviews >= 1).")
        print(f"\n   {'Metric':<18} {'CF-only':>10} {'CF+RAG':>10} {'Δ':>10}")
        print("   " + "-" * 50)
        for m in metrics:
            if m not in res_cf or m not in res_rag:
                continue
            a, b = res_cf[m], res_rag[m]
            delta = b - a
            sign = "+" if delta >= 0 else ""
            print(f"   {m:<18} {a:>10.3f} {b:>10.3f} {sign}{delta:>9.3f}")
        print("   " + "-" * 50)

        # % RAG activation, % Top-20 differs, qualitative examples
        n_warm = len(rag_warm)
        n_act = sum(1 for u in rag_warm if act_raw.get(str(u), False))
        pct_act = (n_act / n_warm * 100) if n_warm else 0.0
        same_top20 = 0
        diff_top20 = 0
        examples_diff: List[int] = []
        for u in rag_warm:
            uid = int(u)
            if u not in cf_warm:
                continue
            top_cf = set((cf_warm[u])[:20])
            top_rag = set((rag_warm[u])[:20])
            if top_cf == top_rag:
                same_top20 += 1
            else:
                diff_top20 += 1
                if len(examples_diff) < 5:
                    examples_diff.append(uid)
        pct_diff = (diff_top20 / n_warm * 100) if n_warm else 0.0
        print(f"\n   % users where RAG activates:     {pct_act:.1f}% ({n_act}/{n_warm})")
        print(f"   % users where Top-20 differs:    {pct_diff:.1f}% ({diff_top20}/{n_warm})")
        if examples_diff:
            print(f"   Example user_ids (different):   {examples_diff}")

    print("\n💾 CF-only saved to:", out_cf)
    print("💾 CF+RAG saved to:", out_rag)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate recommendation model (Precision@K, NDCG, etc.).")
    parser.add_argument("--output", "-o", type=Path, default=project_root / "evaluation_results.json",
                        help="Output JSON path for metrics")
    parser.add_argument("--output-per-user", type=Path, default=None,
                        help="Output JSON path for per-user recommendations (used in --ablate)")
    parser.add_argument("--output-activation", type=Path, default=None,
                        help="Output JSON path for RAG activation per user (CF+RAG ablation only)")
    parser.add_argument("--cohort-file", type=Path, default=None,
                        help="Write cold/warm cohorts to this JSON (ablation)")
    parser.add_argument("--use-rag", action="store_true", default=True,
                        help="Use CF+RAG (default). Ignored if --ablate.")
    parser.add_argument("--no-use-rag", action="store_false", dest="use_rag",
                        help="Use CF-only. Ignored if --ablate.")
    parser.add_argument("--ablate", action="store_true",
                        help="Run CF-only and CF+RAG, save both, print Cohort A/B tables.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip model load; run evaluator on fake recs to check pipeline.")
    args = parser.parse_args()

    if args.dry_run:
        _run_dry_run(args.output)
        return
    if args.ablate:
        _run_ablation()
        return

    print("=" * 70)
    print("📊 Recommendation Model Evaluation")
    print("=" * 70)
    print("\n📂 Loading test data...")
    print("📂 Loading movie genres...")
    print("\n🔧 Initializing evaluator...")
    print("\n🤖 Loading recommendation model...")

    os.environ["USE_RAG_LLM_RERANK"] = "true" if args.use_rag else "false"
    try:
        results = _run_single_evaluation(
            args.use_rag,
            args.output,
            output_per_user=args.output_per_user,
            output_activation=args.output_activation,
            cohort_file=args.cohort_file,
        )
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Evaluation failed: %s", e)
        sys.exit(1)

    _print_results(results)
    print("\n💡 Interpretation:")
    print("   - Precision@K: % of recommendations that are relevant (higher is better)")
    print("   - Recall@K: % of relevant items found (higher is better)")
    print("   - NDCG@K: Ranking quality considering position (higher is better, max 1.0)")
    print("   - Diversity@K: How different recommendations are (higher is better)")
    print("   - Coverage: % of catalog recommended (higher is better)")
    print("=" * 70)

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {args.output}\n")


if __name__ == "__main__":
    main()

