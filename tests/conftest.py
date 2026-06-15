"""Shared pytest configuration: env + import path before app modules load."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Safe defaults for unit tests (must be set before backend.app imports).
os.environ.setdefault("ENV", "development")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_unit_tests")
os.environ.setdefault("DATABASE_PATH", ":memory:")
os.environ.setdefault("REQUIRE_BROWSER_ORIGIN", "false")
