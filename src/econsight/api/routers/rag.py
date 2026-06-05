from __future__ import annotations

from fastapi import APIRouter

from econsight.api.schemas import RAGRequest, RAGResponse
from econsight.rag.query_engine import answer

router = APIRouter()


@router.post("/rag/query", response_model=RAGResponse)
async def query_rag(body: RAGRequest) -> RAGResponse:
    return await answer(body.question)
