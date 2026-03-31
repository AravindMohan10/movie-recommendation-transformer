import json
import sys
import types
from pathlib import Path


def _ensure_torch_stub():
    if "torch" in sys.modules:
        return
    torch_stub = types.ModuleType("torch")
    torch_stub.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_stub.device = lambda name: name
    nn_stub = types.ModuleType("torch.nn")
    torch_stub.nn = nn_stub
    sys.modules["torch"] = torch_stub
    sys.modules["torch.nn"] = nn_stub
    if "numpy" not in sys.modules:
        sys.modules["numpy"] = types.ModuleType("numpy")


def _make_model_service_instance():
    # Avoid heavy __init__ (model load); tests only need helper methods.
    _ensure_torch_stub()
    from backend.app.model_service import MovieRecommendationModel

    return MovieRecommendationModel.__new__(MovieRecommendationModel)


def test_load_movies_from_jsonl(tmp_path: Path):
    _ensure_torch_stub()
    from backend.app.model_service import MovieRecommendationModel

    svc = _make_model_service_instance()
    movie_file = tmp_path / "movies.jsonl"
    movie_file.write_text(
        "\n".join(
            [
                json.dumps({"tmdb_id": 1, "title": "One"}),
                json.dumps({"id": 2, "title": "Two"}),
                "not-json",
                "",
            ]
        ),
        encoding="utf-8",
    )

    movies = MovieRecommendationModel._load_movies_from_path(svc, movie_file)
    assert len(movies) == 2
    assert movies[0]["title"] == "One"
    assert movies[1]["title"] == "Two"


def test_load_movies_from_json_array(tmp_path: Path):
    _ensure_torch_stub()
    from backend.app.model_service import MovieRecommendationModel

    svc = _make_model_service_instance()
    movie_file = tmp_path / "movies.jsonl"
    movie_file.write_text(
        json.dumps(
            [
                {"tmdb_id": 10, "title": "Ten"},
                {"id": 11, "title": "Eleven"},
            ]
        ),
        encoding="utf-8",
    )

    movies = MovieRecommendationModel._load_movies_from_path(svc, movie_file)
    assert len(movies) == 2
    assert {m.get("title") for m in movies} == {"Ten", "Eleven"}


def test_load_movies_from_wrapped_results(tmp_path: Path):
    _ensure_torch_stub()
    from backend.app.model_service import MovieRecommendationModel

    svc = _make_model_service_instance()
    movie_file = tmp_path / "movies.jsonl"
    movie_file.write_text(
        json.dumps(
            {
                "results": [
                    {"tmdb_id": 21, "title": "Twenty One"},
                    {"tmdb_id": 22, "title": "Twenty Two"},
                ]
            }
        ),
        encoding="utf-8",
    )

    movies = MovieRecommendationModel._load_movies_from_path(svc, movie_file)
    assert len(movies) == 2
    assert movies[0]["tmdb_id"] == 21


def test_parse_numbered_why_lines_filters_none():
    from backend.app.llm_service import _parse_numbered_why_lines

    raw = "\n".join(
        [
            "1. Strong fit with your sci-fi preferences.",
            "2. NONE",
            "3) Similar users liked this character-driven drama.",
        ]
    )
    parsed = _parse_numbered_why_lines(raw, expected=3)

    assert parsed[0] == "Strong fit with your sci-fi preferences."
    assert parsed[1] is None
    assert parsed[2] == "Similar users liked this character-driven drama."

