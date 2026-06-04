from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("/report/pdf")
async def get_pdf() -> Response:
    return Response(content=b"%PDF-1.4 stub", media_type="application/pdf")
