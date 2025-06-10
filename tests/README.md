# Tests

- `test_login.py` – quick check that the login endpoint works (backend must be running).
- `test_model_loading.py` – loads the recommendation model and generates sample recs (run from project root).
- `test_mood_service.py` – unit tests for mood-to-criteria logic.

Run from project root: `python tests/test_login.py`, `python tests/test_model_loading.py`, or `pytest tests/`.
