from __future__ import annotations

import asyncio
from pathlib import Path

import chromadb
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

from econsight.config import get_logger
from econsight.db.connection import PROJECT_ROOT

logger = get_logger(__name__)

_REPORT_PATH = PROJECT_ROOT / "notebooks" / "phase2_report.html"
_CHROMA_PATH = str(PROJECT_ROOT / "models" / "chroma_db")
_COLLECTION_NAME = "phase2_report"
_MODEL_NAME = "all-MiniLM-L6-v2"


def _parse_report(html_path: Path) -> list[dict[str, str]]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    chunks: list[dict[str, str]] = []
    current_title = "Introduction"
    current_texts: list[str] = []

    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "td"]):
        if tag.name in ("h1", "h2", "h3"):
            if current_texts:
                chunks.append({"title": current_title, "text": " ".join(current_texts)})
                current_texts = []
            current_title = tag.get_text(strip=True)
        else:
            text = tag.get_text(strip=True)
            if text:
                current_texts.append(text)

    if current_texts:
        chunks.append({"title": current_title, "text": " ".join(current_texts)})

    return [c for c in chunks if len(c["text"]) > 50]


async def ingest_if_needed() -> None:
    if not _REPORT_PATH.exists():
        logger.warning("rag.report_missing", path=str(_REPORT_PATH))
        return

    client = chromadb.PersistentClient(path=_CHROMA_PATH)
    collection = client.get_or_create_collection(_COLLECTION_NAME)

    if collection.count() > 0:
        logger.info("rag.already_ingested", count=collection.count())
        return

    logger.info("rag.ingesting", path=str(_REPORT_PATH))
    chunks = await asyncio.to_thread(_parse_report, _REPORT_PATH)
    model = await asyncio.to_thread(SentenceTransformer, _MODEL_NAME)

    texts = [c["text"] for c in chunks]
    embeddings_array = await asyncio.to_thread(model.encode, texts)

    collection.add(
        documents=texts,
        embeddings=[e.tolist() for e in embeddings_array],
        metadatas=[{"title": c["title"]} for c in chunks],
        ids=[f"chunk_{i}" for i in range(len(chunks))],
    )
    logger.info("rag.ingested", chunks=len(chunks))
