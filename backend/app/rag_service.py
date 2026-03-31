"""
RAG service over movie reviews.
- Index: movie_id, title, overview + review text per movie.
- Retrieve similar reviews by query (e.g. user's liked movies' reviews).
- Expose per-movie embeddings for Option B (review-aware reranking).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_rag_service: Optional["RAGService"] = None


def get_rag_service() -> "RAGService":
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


class RAGService:
    """RAG over movie reviews: Chroma + sentence-transformers."""

    COLLECTION_NAME = "movie_reviews"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    # Keep default modest for production CPU machines; can be overridden by env.
    MAX_MOVIES_INDEXED = int(os.getenv("RAG_MAX_MOVIES_INDEXED", "3000"))
    INDEX_BATCH_SIZE = int(os.getenv("RAG_INDEX_BATCH_SIZE", "2000"))
    CHUNK_MAX_CHARS = 12_000

    def __init__(self) -> None:
        self._embedder: Any = None
        self._chroma_client: Any = None
        self._collection: Any = None
        self._movie_embeddings: Dict[int, Any] = {}
        self._base_dir = Path(__file__).resolve().parent.parent.parent
        volume_rag = Path("/data/rag/chroma_db")
        bundled_rag = self._base_dir / "data" / "rag" / "chroma_db"

        def _has_chroma_data(p: Path) -> bool:
            """Check if path has a populated Chroma db. Empty dbs (e.g. from failed init) are tiny."""
            if not p.exists():
                return False
            db_file = p / "chroma.sqlite3"
            if not db_file.exists():
                return any(p.glob("*.sqlite3")) or any(p.glob("*.db"))
            # Prebuilt index is ~130MB; empty Chroma db is <1MB
            return db_file.stat().st_size > 1_000_000

        # Prefer volume if it has real data; else use bundled (prebuilt in CI); else volume for writing
        if Path("/data").exists():
            if _has_chroma_data(volume_rag):
                self._chroma_path = volume_rag
            elif _has_chroma_data(bundled_rag):
                self._chroma_path = bundled_rag
                logger.info("RAG: using bundled index (volume empty)")
            else:
                self._chroma_path = volume_rag
        else:
            self._chroma_path = bundled_rag
        self._index_built = False

    def _ensure_embedder(self) -> None:
        if self._embedder is not None:
            return
        from sentence_transformers import SentenceTransformer

        self._embedder = SentenceTransformer(self.EMBEDDING_MODEL)
        logger.info("RAG: loaded embedding model %s", self.EMBEDDING_MODEL)

    def _ensure_chroma(self) -> None:
        if self._chroma_client is not None:
            return
        import chromadb
        from chromadb.config import Settings

        self._chroma_path.mkdir(parents=True, exist_ok=True)
        self._chroma_client = chromadb.PersistentClient(
            path=str(self._chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )
        logger.info("RAG: Chroma at %s", self._chroma_path)

    def _movie_data_paths(self) -> List[Path]:
        paths = [
            self._base_dir / "data" / "raw" / "tmdb_movies_50k_20250711_011112.jsonl",
            self._base_dir / "data" / "raw" / "tmdb_complete_dataset.jsonl",
        ]
        return [p for p in paths if p.exists()]

    def _load_movies_with_reviews(self) -> List[Dict[str, Any]]:
        movies: List[Dict[str, Any]] = []
        for path in self._movie_data_paths():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if len(movies) >= self.MAX_MOVIES_INDEXED:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        m = json.loads(line)
                    except Exception:
                        continue
                    rid = m.get("tmdb_id") or m.get("id")
                    if not rid:
                        continue
                    reviews = m.get("reviews") or []
                    overview = (m.get("overview") or "")[:2000]
                    if not reviews and not overview:
                        continue
                    movies.append({
                        "movie_id": int(rid) if isinstance(rid, str) and str(rid).isdigit() else int(rid),
                        "title": m.get("title") or "",
                        "overview": overview,
                        "reviews": reviews,
                    })
            if movies:
                break
        return movies

    def _doc_text(self, m: Dict[str, Any]) -> str:
        parts = [m["overview"]] if m["overview"] else []
        for r in m["reviews"]:
            c = (r.get("content") or "").strip()
            if c:
                parts.append(c)
        raw = "\n\n".join(parts)
        return raw[: self.CHUNK_MAX_CHARS] if raw else ""

    def build_index(self) -> bool:
        self._ensure_embedder()
        self._ensure_chroma()
        movies = self._load_movies_with_reviews()
        if not movies:
            logger.warning("RAG: no movies with reviews found")
            return False

        ids: List[str] = []
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for m in movies:
            text = self._doc_text(m)
            if not text:
                continue
            mid = m["movie_id"]
            ids.append(f"movie_{mid}")
            texts.append(text)
            metadatas.append({"movie_id": mid, "title": (m["title"] or "")[:200]})

        if not ids:
            logger.warning("RAG: no valid documents")
            return False

        import numpy as np

        embs = self._embedder.encode(texts, show_progress_bar=len(texts) > 500)
        embeddings_list = [e.tolist() for e in embs]

        try:
            self._chroma_client.delete_collection(name=self.COLLECTION_NAME)
        except Exception:
            pass
        self._collection = self._chroma_client.create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "movie reviews and overviews"},
        )

        # Chroma limits batch size; env-configurable for slower machines.
        chunk_size = max(500, self.INDEX_BATCH_SIZE)
        for b in range(0, len(ids), chunk_size):
            end = min(b + chunk_size, len(ids))
            self._collection.add(
                ids=ids[b:end],
                documents=texts[b:end],
                metadatas=metadatas[b:end],
                embeddings=embeddings_list[b:end],
            )
            logger.info("RAG: added batch %d–%d", b, end)

        self._index_built = True
        self._movie_embeddings.clear()
        for i, meta in enumerate(metadatas):
            mid = meta.get("movie_id")
            if mid is not None and i < len(embs):
                self._movie_embeddings[int(mid)] = np.array(embs[i], dtype=np.float32)
        logger.info("RAG: indexed %d movies", len(ids))
        return True

    def _ensure_index(self) -> bool:
        """Return True if index is ready. Never block on build_index() during requests (would take 10-30 min)."""
        if self._index_built and self._collection is not None:
            return True
        self._ensure_chroma()
        try:
            self._collection = self._chroma_client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "movie reviews and overviews"},
            )
            if self._collection.count() > 0:
                self._index_built = True
                return True
        except Exception as e:
            logger.debug("RAG: _ensure_index chroma check failed: %s", e)
        # Index empty or missing: do NOT build during request (would block 10-30 min on CPU).
        # Use CF-only recommendations. Build index separately via: scripts/build_rag_index.py
        logger.info("RAG: index empty or missing, skipping RAG (using CF-only). Build via scripts/build_rag_index.py")
        return False

    def retrieve_similar(
        self, query: str, top_k: int = 50
    ) -> List[Tuple[int, float, str]]:
        """Returns [(movie_id, score, text), ...]. Score in [0,1]-like similarity."""
        self._ensure_chroma()
        if not self._ensure_index():
            return []
        self._ensure_embedder()
        try:
            q_emb = self._embedder.encode([query])
            n = min(top_k, self._collection.count())
            if n <= 0:
                return []
            res = self._collection.query(
                query_embeddings=q_emb.tolist(),
                n_results=n,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning("RAG: retrieve failed: %s", e)
            return []

        out: List[Tuple[int, float, str]] = []
        distances = res.get("distances", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        docs = res.get("documents", [[]])[0]
        for d, meta, doc in zip(distances, metas, docs):
            mid = meta.get("movie_id")
            if mid is None:
                continue
            sim = 1.0 / (1.0 + float(d)) if d else 1.0
            out.append((int(mid), sim, (doc or "")[:2000]))
        return out

    def get_movie_embedding(self, movie_id: int) -> Any:
        """Return embedding for Option B reranking. None if unknown."""
        self._ensure_embedder()
        self._ensure_chroma()
        if not self._ensure_index():
            return None
        if movie_id in self._movie_embeddings:
            return self._movie_embeddings[movie_id]
        try:
            res = self._collection.get(
                ids=[f"movie_{movie_id}"],
                include=["embeddings"],
            )
            embs = res.get("embeddings")
            if embs and len(embs) > 0:
                import numpy as np

                arr = np.array(embs[0], dtype=np.float32)
                self._movie_embeddings[movie_id] = arr
                return arr
        except Exception:
            pass
        return None

    def get_document_for_movie(self, movie_id: int) -> Optional[str]:
        """Return the single RAG document (overview + reviews) for this movie, or None if not in index."""
        self._ensure_chroma()
        if not self._ensure_index():
            return None
        try:
            res = self._collection.get(
                ids=[f"movie_{movie_id}"],
                include=["documents"],
            )
            docs = res.get("documents") or []
            first = docs[0] if docs else None
            if isinstance(first, list):
                first = first[0] if first else None
            if first:
                return (first or "")[:4000]
        except Exception as e:
            logger.debug("RAG: get_document_for_movie failed for %s: %s", movie_id, e)
        return None
