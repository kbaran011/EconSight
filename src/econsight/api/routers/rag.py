from fastapi import APIRouter

from econsight.api.schemas import RAGRequest, RAGResponse

router = APIRouter()


@router.post("/rag/query", response_model=RAGResponse)
async def query_rag(body: RAGRequest) -> RAGResponse:
    return RAGResponse(answer="Coming soon", sources=[], query_type="narrative")
