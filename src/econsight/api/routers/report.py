from __future__ import annotations

import asyncio

import psycopg
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from econsight.api.dependencies import get_db
from econsight.report.brief import generate_brief
from econsight.report.full_report import generate_full_report
from econsight.report.merger import merge_pdfs

router = APIRouter()


@router.get("/report/pdf")
async def get_pdf(conn: psycopg.AsyncConnection = Depends(get_db)) -> Response:
    brief_bytes, full_bytes = await asyncio.gather(
        generate_brief(conn),
        asyncio.to_thread(generate_full_report),
    )
    merged = merge_pdfs(brief_bytes, full_bytes)
    return Response(
        content=merged,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=econsight_report.pdf"},
    )
