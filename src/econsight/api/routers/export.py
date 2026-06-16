from __future__ import annotations

import csv
import io

import psycopg
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from econsight.api.dependencies import get_cursor, get_db_readonly

router = APIRouter()


def _csv_response(
    headers: list[str], rows: list[tuple[object, ...]], filename: str
) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/indicators.csv", response_class=StreamingResponse)
async def export_indicators(
    conn: psycopg.AsyncConnection = Depends(get_db_readonly),
) -> StreamingResponse:
    """All 36 months of the macro mart as CSV — ready for Power BI Web connector."""
    sql = """
        SELECT period_date, gdp, cpi, unemployment_rate, ippi, retail_trade,
               overnight_rate, cadusd, bond_10yr, m2pp,
               cpi_yoy, yield_spread, unemployment_delta
        FROM marts.mart_monthly_macro_indicators
        ORDER BY period_date ASC
    """
    async with get_cursor(conn) as cur:
        await cur.execute(sql)
        rows = await cur.fetchall()
        headers = [d[0] for d in (cur.description or [])]
    return _csv_response(headers, rows, "indicators.csv")


@router.get("/export/health-score.csv", response_class=StreamingResponse)
async def export_health_score(
    conn: psycopg.AsyncConnection = Depends(get_db_readonly),
) -> StreamingResponse:
    """Full health score history as CSV."""
    sql = """
        SELECT period_date, score
        FROM marts.economic_health_score
        ORDER BY period_date ASC
    """
    async with get_cursor(conn) as cur:
        await cur.execute(sql)
        rows = await cur.fetchall()
        headers = [d[0] for d in (cur.description or [])]
    return _csv_response(headers, rows, "health-score.csv")


@router.get("/export/forecasts.csv", response_class=StreamingResponse)
async def export_forecasts(
    conn: psycopg.AsyncConnection = Depends(get_db_readonly),
) -> StreamingResponse:
    """All forecast rows as CSV (all targets, all horizons)."""
    sql = """
        SELECT period_date, target, horizon_months, model_type,
               point_forecast, p10, p50, p90,
               scenario_base, scenario_upside, scenario_downside
        FROM marts.mart_forecasts
        ORDER BY target, period_date ASC
    """
    async with get_cursor(conn) as cur:
        await cur.execute(sql)
        rows = await cur.fetchall()
        headers = [d[0] for d in (cur.description or [])]
    return _csv_response(headers, rows, "forecasts.csv")
