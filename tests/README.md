# Tests

Unit and integration tests for CineAI backend logic.

## Quick run (default — no ML checkpoints, no live server)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## With coverage

```bash
pytest --cov=backend/app --cov-report=term-missing
```

## Markers

| Marker | Meaning |
|--------|---------|
| *(default)* | Fast unit tests (auth, origin guard, mood fallback, JSON loaders) |
| `slow` | Loads PyTorch checkpoints — `pytest -m slow` |
| `integration` | Live backend or Groq API — skipped unless env vars set |

## Optional integration

```bash
# Live login smoke test (backend on :8000)
RUN_INTEGRATION_TESTS=1 pytest tests/test_login.py -m integration

# RAGAS eval (needs groq + ragas installed)
GROQ_API_KEY=... pytest tests/integration/test_ragas_eval.py -m integration
```

## Layout

- `test_auth.py` — password + JWT
- `test_origin_guard.py` — abuse / client header guard
- `test_api_smoke.py` — `/health` via TestClient
- `test_mood_service.py` — mood→criteria fallback
- `test_recommendation_regressions.py` — movie JSONL loaders, LLM parse helpers
- `test_mock_user_recommendation_diff.py` — CF vs RAG diff with fakes
- `test_model_loading.py` — full model load (`slow`)
- `test_login.py` — live login (`integration`)
- `integration/test_ragas_eval.py` — optional RAGAS smoke
