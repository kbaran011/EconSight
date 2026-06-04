from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from econsight.api.dependencies import get_cursor, get_db
from econsight.api.schemas import ForecastPoint

router = APIRouter()

_FORECAST_SQL = """
    SELECT period_date, target, horizon_months, model_type, point_forecast,
           p10, p50, p90, scenario_base, scenario_upside, scenario_downside
    FROM marts.model_forecasts
    ORDER BY target, horizon_months, model_type
"""


def _f(v: object) -> float | None:
    return float(v) if v is not None else None  # type: ignore[arg-type]


@router.get("/forecasts", response_model=list[ForecastPoint])
async def get_forecasts(
    conn: psycopg.AsyncConnection = Depends(get_db),
) -> list[ForecastPoint]:
    async with get_cursor(conn) as cur:
        await cur.execute(_FORECAST_SQL)
        rows = await cur.fetchall()
    return [
        ForecastPoint(
            period_date=r[0], target=r[1], horizon_months=r[2], model_type=r[3],
            point_forecast=float(r[4]),
            p10=_f(r[5]), p50=_f(r[6]), p90=_f(r[7]),
            scenario_base=_f(r[8]), scenario_upside=_f(r[9]), scenario_downside=_f(r[10]),
        )
        for r in rows
    ]
