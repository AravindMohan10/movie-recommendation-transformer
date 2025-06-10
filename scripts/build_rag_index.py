#!/usr/bin/env python3
"""
Prebuild RAG (Chroma) index from movie reviews.
Run from project root with moodenv activated. Required for CF+RAG recommendations.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def main() -> int:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))
    from app.rag_service import get_rag_service

    print("Building RAG index (Chroma + sentence-transformers)...")
    rag = get_rag_service()
    ok = rag.build_index()
    if ok:
        print("RAG index built successfully.")
        return 0
    print("RAG index build failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
