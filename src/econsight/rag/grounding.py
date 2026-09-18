from __future__ import annotations

import re
from typing import Any, Protocol

import numpy as np

DEFAULT_THRESHOLD = 0.45  # cosine similarity below this => sentence unsupported

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_CITATION_RE = re.compile(r"\[(\d+)\]")


class Encoder(Protocol):
    def encode(self, texts: list[str]) -> Any: ...


def split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENTENCE_RE.split(text.strip()) if s.strip()]
    return parts


def parse_citations(sentence: str) -> set[int]:
    return {int(m) for m in _CITATION_RE.findall(sentence)}


def _cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-12)
    b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-12)
    return a @ b.T


def build_report(
    answer: str,
    chunks: list[dict[str, str]],
    encoder: Encoder,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    sentences = split_sentences(answer)
    sources = [
        {
            "chunk_id": i + 1,
            "title": c.get("title", "") or f"Source {i + 1}",
            "snippet": (c.get("text", "")[:240]),
        }
        for i, c in enumerate(chunks)
    ]
    if not sentences or not chunks:
        return {"groundedness": None, "sentences": [], "sources": sources}

    chunk_vecs = np.asarray(encoder.encode([c.get("text", "") for c in chunks]), float)
    clean = [_CITATION_RE.sub("", s).strip() for s in sentences]
    sent_vecs = np.asarray(encoder.encode(clean), float)
    sims = _cosine(sent_vecs, chunk_vecs)  # (n_sent, n_chunk)

    out_sentences = []
    supported_count = 0
    for i, sentence in enumerate(sentences):
        best_idx = int(np.argmax(sims[i]))
        best_sim = float(sims[i][best_idx])
        supported = best_sim >= threshold
        supported_count += int(supported)
        out_sentences.append(
            {
                "text": sentence,
                "supported": supported,
                "similarity": round(best_sim, 3),
                "best_source_title": sources[best_idx]["title"],
                "cited_chunk_ids": sorted(parse_citations(sentence)),
            }
        )
    groundedness = supported_count / len(sentences)
    return {
        "groundedness": round(groundedness, 3),
        "sentences": out_sentences,
        "sources": sources,
    }
