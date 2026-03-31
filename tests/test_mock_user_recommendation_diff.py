from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import types


def _seed_users_and_interactions(session):
    from backend.app.models import User, UserInteraction

    users = [
        User(user_id=1001, username="action_fan", email="action@example.com", hashed_password="x"),
        User(user_id=1002, username="romance_fan", email="romance@example.com", hashed_password="x"),
    ]
    session.add_all(users)
    session.flush()

    # User 1001: action/sci-fi taste
    session.add_all(
        [
            UserInteraction(user_id=1001, movie_id=1, action="like", rating=9.0),
            UserInteraction(user_id=1001, movie_id=2, action="favorite", rating=9.5),
            UserInteraction(
                user_id=1001,
                movie_id=1,
                action="review",
                rating=9.0,
                review_text="Loved the intense action sequences and sci-fi vibe.",
            ),
        ]
    )

    # User 1002: romance/drama taste
    session.add_all(
        [
            UserInteraction(user_id=1002, movie_id=3, action="like", rating=8.5),
            UserInteraction(user_id=1002, movie_id=4, action="favorite", rating=9.2),
            UserInteraction(
                user_id=1002,
                movie_id=3,
                action="review",
                rating=8.8,
                review_text="Great emotional arc and tender romantic chemistry.",
            ),
        ]
    )
    session.commit()


def _movie_data_fixture():
    # Minimal shape used by reranker query/title helpers.
    return {
        "1": {"title": "Galactic Strike", "overview": "A fast-paced sci-fi action war.", "reviews": [{"content": "Explosive fights in space."}]},
        "2": {"title": "Neon Pursuit", "overview": "Cyberpunk action thriller with chases.", "reviews": [{"content": "Relentless action and high stakes."}]},
        "3": {"title": "Moonlit Letters", "overview": "A heartfelt romance drama.", "reviews": [{"content": "Tender romance and emotional writing."}]},
        "4": {"title": "Autumn Promise", "overview": "Romantic drama about second chances.", "reviews": [{"content": "Warm romance and human connection."}]},
        "5": {"title": "Sky Hunters", "overview": "Military action adventure.", "reviews": [{"content": "Action-heavy aerial combat."}]},
        "6": {"title": "Quiet Harbor", "overview": "Gentle romance by the sea.", "reviews": [{"content": "Soft romance with emotional depth."}]},
    }


class _FakeRAGService:
    def __init__(self):
        self._embedder = None  # keep reranker on non-embedding path

    def retrieve_similar(self, query: str, top_k: int = 50):
        q = (query or "").lower()
        if "action" in q or "sci-fi" in q or "space" in q:
            return [
                (5, 0.95, "Action-heavy aerial combat and tactical missions."),
            ]
        if "romance" in q or "emotional" in q or "tender" in q:
            return [
                (6, 0.95, "Gentle romance with strong emotional connection."),
            ]
        return []

    def get_movie_embedding(self, movie_id: int):
        return None


def _top_ids(reranked, top_k=5):
    return [x["movie_id"] for x in reranked[:top_k]]


def _jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def _ensure_model_service_import_stubs():
    if "torch" not in sys.modules:
        torch_stub = types.ModuleType("torch")
        torch_stub.cuda = types.SimpleNamespace(is_available=lambda: False)
        torch_stub.device = lambda name: name
        nn_stub = types.ModuleType("torch.nn")
        torch_stub.nn = nn_stub
        sys.modules["torch"] = torch_stub
        sys.modules["torch.nn"] = nn_stub
    if "numpy" not in sys.modules:
        sys.modules["numpy"] = types.ModuleType("numpy")


def test_mock_users_produce_different_recommendation_sets(monkeypatch):
    from backend.app.database import Base
    import backend.app.models  # noqa: F401 - ensure model tables are registered on Base.metadata
    from backend.app import rag_service
    from backend.app.rag_reranker import rerank

    # Isolated in-memory DB
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    try:
        _seed_users_and_interactions(session)
        movie_data = _movie_data_fixture()
        cf_candidates = [(1, 0.95), (2, 0.90), (3, 0.85), (4, 0.80)]

        monkeypatch.setattr(rag_service, "get_rag_service", lambda: _FakeRAGService())

        recs_action = rerank(
            user_id=1001,
            cf_candidates=cf_candidates,
            movie_data=movie_data,
            db_session=session,
            valid_movie_ids=[1, 2, 3, 4, 5, 6],
        )
        recs_romance = rerank(
            user_id=1002,
            cf_candidates=cf_candidates,
            movie_data=movie_data,
            db_session=session,
            valid_movie_ids=[1, 2, 3, 4, 5, 6],
        )

        top_action = _top_ids(recs_action, top_k=5)
        top_romance = _top_ids(recs_romance, top_k=5)
        overlap = _jaccard(top_action, top_romance)

        # The injected candidate should reflect each user's taste profile.
        assert 5 in top_action, f"Expected action profile to include movie 5, got {top_action}"
        assert 6 in top_romance, f"Expected romance profile to include movie 6, got {top_romance}"

        # They should not be nearly identical.
        assert overlap < 0.80, f"Expected recommendation sets to differ meaningfully, overlap={overlap:.2f}"
    finally:
        session.close()


def test_same_user_recommendations_are_stable_for_same_inputs(monkeypatch):
    from backend.app.database import Base
    import backend.app.models  # noqa: F401 - ensure model tables are registered on Base.metadata
    from backend.app import rag_service
    from backend.app.rag_reranker import rerank

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    try:
        _seed_users_and_interactions(session)
        movie_data = _movie_data_fixture()
        cf_candidates = [(1, 0.95), (2, 0.90), (3, 0.85), (4, 0.80)]
        monkeypatch.setattr(rag_service, "get_rag_service", lambda: _FakeRAGService())

        recs_first = rerank(
            user_id=1001,
            cf_candidates=cf_candidates,
            movie_data=movie_data,
            db_session=session,
            valid_movie_ids=[1, 2, 3, 4, 5, 6],
        )
        recs_second = rerank(
            user_id=1001,
            cf_candidates=cf_candidates,
            movie_data=movie_data,
            db_session=session,
            valid_movie_ids=[1, 2, 3, 4, 5, 6],
        )

        top_first = _top_ids(recs_first, top_k=5)
        top_second = _top_ids(recs_second, top_k=5)

        assert top_first == top_second, (
            "Expected stable recommendations for same user+inputs; "
            f"first={top_first}, second={top_second}"
        )
    finally:
        session.close()


def test_semantic_candidates_are_generated_from_user_reviews(monkeypatch):
    from backend.app.database import Base
    import backend.app.models  # noqa: F401 - ensure model tables are registered on Base.metadata
    from backend.app import rag_service

    _ensure_model_service_import_stubs()
    from backend.app.model_service import MovieRecommendationModel

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    try:
        _seed_users_and_interactions(session)
        monkeypatch.setattr(rag_service, "get_rag_service", lambda: _FakeRAGService())

        svc = MovieRecommendationModel.__new__(MovieRecommendationModel)
        svc.movie_data = _movie_data_fixture()

        sem_action = svc._get_semantic_candidates(
            user_id=1001,
            db_session=session,
            valid_movie_ids=[1, 2, 3, 4, 5, 6],
            exclude_ids=[1, 2],  # exclude watched likes
        )
        sem_romance = svc._get_semantic_candidates(
            user_id=1002,
            db_session=session,
            valid_movie_ids=[1, 2, 3, 4, 5, 6],
            exclude_ids=[3, 4],  # exclude watched likes
        )

        mids_action = [mid for mid, _ in sem_action]
        mids_romance = [mid for mid, _ in sem_romance]
        assert 5 in mids_action, f"Expected action semantic candidate 5, got {mids_action}"
        assert 6 in mids_romance, f"Expected romance semantic candidate 6, got {mids_romance}"
        assert mids_action != mids_romance
    finally:
        session.close()

