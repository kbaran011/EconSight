from __future__ import annotations

import asyncio
from collections.abc import Sequence

import chromadb
from sentence_transformers import SentenceTransformer

from econsight.db.connection import PROJECT_ROOT

_CHROMA_PATH = str(PROJECT_ROOT / "models" / "chroma_db")
_COLLECTION_NAME = "phase2_report"
_MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


async def retrieve(question: str, top_k: int = 5) -> list[dict[str, str]]:
    model = await asyncio.to_thread(_get_model)
    embedding = await asyncio.to_thread(model.encode, [question])

    client = chromadb.PersistentClient(path=_CHROMA_PATH)
    collection = client.get_or_create_collection(_COLLECTION_NAME)
    count = collection.count()
    if count == 0:
        return []

    query_vec: list[Sequence[float]] = [embedding[0].tolist()]
    results = collection.query(
        query_embeddings=query_vec,
        n_results=min(top_k, count),
        include=["documents", "metadatas"],
    )
    docs = results.get("documents") or [[]]
    metas = results.get("metadatas") or [[]]
    chunks = []
    for doc, meta in zip(docs[0], metas[0]):
        title = str(meta.get("title", "")) if isinstance(meta, dict) else ""
        chunks.append({"title": title, "text": doc})
    return chunks
