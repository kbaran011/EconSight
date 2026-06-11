from __future__ import annotations

from datetime import datetime

import psycopg
from fastapi import APIRouter, Depends

from econsight.api.dependencies import get_cursor, get_db
from econsight.api.schemas import StatusResponse
from econsight.config import settings
from econsight.db.seed import SeedStatus, get_seed_status

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def get_status(
    conn: psycopg.AsyncConnection = Depends(get_db),
) -> StatusResponse:
    seed_status, seed_error = get_seed_status()

    async with get_cursor(conn) as cur:
        await cur.execute("SELECT COUNT(*) FROM marts.mart_monthly_macro_indicators")
        mart_row = await cur.fetchone()
        mart_count = int(mart_row[0]) if mart_row else 0

        await cur.execute(
            """
            SELECT period_date FROM marts.mart_monthly_macro_indicators
            ORDER BY period_date DESC LIMIT 1
            """
        )
        latest_mart = await cur.fetchone()

        await cur.execute(
            """
            SELECT status, rows_loaded, finished_at
            FROM meta.pipeline_runs
            WHERE status = 'success'
            ORDER BY finished_at DESC NULLS LAST
            LIMIT 1
            """
        )
        pipeline_row = await cur.fetchone()

    last_run_at: datetime | None = None
    last_run_rows: int | None = None
    if pipeline_row:
        last_run_rows = int(pipeline_row[1]) if pipeline_row[1] is not None else None
        last_run_at = pipeline_row[2]

    if mart_count > 0 and seed_status == SeedStatus.IDLE:
        seed_status = SeedStatus.READY

    return StatusResponse(
        seeding_status=seed_status.value,
        seeding_error=seed_error,
        mart_row_count=mart_count,
        latest_data_date=latest_mart[0] if latest_mart else None,
        last_pipeline_run_at=last_run_at,
        last_pipeline_rows=last_run_rows,
        groq_configured=bool(settings.groq_api_key),
    )
