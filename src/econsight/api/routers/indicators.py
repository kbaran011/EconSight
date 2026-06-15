from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from econsight.api.dependencies import get_cursor, get_db
from econsight.api.schemas import HealthScorePoint, HealthScoreResponse, IndicatorRow

router = APIRouter()

_INDICATOR_SQL = """
    SELECT period_date, gdp, cpi, unemployment_rate, ippi, retail_trade,
           overnight_rate, cadusd, bond_10yr, m2pp,
           cpi_yoy, yield_spread, unemployment_delta
    FROM marts.mart_monthly_macro_indicators
    ORDER BY period_date DESC
    LIMIT 36
"""

_HEALTH_SQL = """
    SELECT period_date, score, component_scores
    FROM marts.economic_health_score
    ORDER BY period_date ASC
"""


def _to_float(v: object) -> float | None:
    return float(v) if v is not None else None  # type: ignore[arg-type]


@router.get("/indicators", response_model=list[IndicatorRow])
async def get_indicators(
    conn: psycopg.AsyncConnection = Depends(get_db),
) -> list[IndicatorRow]:
    async with get_cursor(conn) as cur:
        await cur.execute(_INDICATOR_SQL)
        rows = await cur.fetchall()
        desc = cur.description or []
    cols = [d[0] for d in desc]
    result = [
        IndicatorRow(**{c: _to_float(v) if c != "period_date" else v
                        for c, v in zip(cols, row)})
        for row in rows
    ]
    return list(reversed(result))


@router.get("/health-score", response_model=HealthScoreResponse)
async def get_health_score(
    conn: psycopg.AsyncConnection = Depends(get_db),
) -> HealthScoreResponse:
    async with get_cursor(conn) as cur:
        await cur.execute(_HEALTH_SQL)
        rows = await cur.fetchall()
    history = [
        HealthScorePoint(
            period_date=r[0],
            score=float(r[1]),
            component_scores={k: float(v) for k, v in r[2].items()},
        )
        for r in rows
    ]
    latest = history[-1]
    return HealthScoreResponse(
        history=history,
        latest_score=latest.score,
        latest_components=latest.component_scores,
    )
