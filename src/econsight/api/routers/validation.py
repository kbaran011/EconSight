from __future__ import annotations

import math
from typing import Any

import psycopg
from fastapi import APIRouter, Depends, Query

from econsight.api.dependencies import get_cursor, get_db
from econsight.api.schemas import (
    BacktestMetric,
    BacktestPredictionPoint,
    BacktestPredictionSeries,
    ValidationSummary,
)

router = APIRouter()

_MIN_FOLDS = 12

_METRICS_SQL = """
    SELECT target, horizon_months, model_type, baseline, n_folds, mae, rmse, mase,
           skill_score_vs_rw, dm_stat, dm_pvalue, backtest_start, backtest_end
    FROM marts.model_backtests
    ORDER BY target, horizon_months, model_type
"""

_PRED_SQL = """
    SELECT target_date, model_type, y_true, y_pred
    FROM marts.backtest_predictions
    WHERE target = %s AND horizon_months = %s
    ORDER BY model_type, target_date
"""


def _f(v: object) -> float | None:
    if v is None:
        return None
    f = float(v)  # type: ignore[arg-type]
    # NaN serializes to the non-standard JSON `NaN` token; return None instead.
    return None if math.isnan(f) else f


def _row_to_metric(r: tuple[Any, ...]) -> BacktestMetric:
    n_folds = int(r[4])
    return BacktestMetric(
        target=r[0], horizon_months=r[1], model_type=r[2], baseline=r[3],
        n_folds=n_folds, mae=_f(r[5]), rmse=_f(r[6]), mase=_f(r[7]),
        skill_score_vs_rw=_f(r[8]), dm_stat=_f(r[9]), dm_pvalue=_f(r[10]),
        backtest_start=r[11], backtest_end=r[12],
        low_confidence=n_folds < _MIN_FOLDS,
    )


@router.get("/validation/metrics", response_model=list[BacktestMetric])
async def get_metrics(
    conn: psycopg.AsyncConnection = Depends(get_db),
) -> list[BacktestMetric]:
    async with get_cursor(conn) as cur:
        await cur.execute(_METRICS_SQL)
        rows = await cur.fetchall()
    return [_row_to_metric(r) for r in rows]


@router.get("/validation/predictions", response_model=BacktestPredictionSeries)
async def get_predictions(
    target: str = Query(...),
    horizon: int = Query(...),
    conn: psycopg.AsyncConnection = Depends(get_db),
) -> BacktestPredictionSeries:
    async with get_cursor(conn) as cur:
        await cur.execute(_PRED_SQL, (target, horizon))
        rows = await cur.fetchall()
    points = [
        BacktestPredictionPoint(
            target_date=r[0], model_type=r[1], y_true=float(r[2]), y_pred=float(r[3])
        )
        for r in rows
    ]
    return BacktestPredictionSeries(
        target=target, horizon_months=horizon, points=points
    )


@router.get("/validation/summary", response_model=ValidationSummary)
async def get_summary(
    conn: psycopg.AsyncConnection = Depends(get_db),
) -> ValidationSummary:
    async with get_cursor(conn) as cur:
        await cur.execute(_METRICS_SQL)
        rows = await cur.fetchall()
    metrics = [_row_to_metric(r) for r in rows]

    contenders = [m for m in metrics if m.model_type not in ("naive_rw",)]
    beating = [
        m for m in contenders
        if m.mase is not None and m.mase < 1.0
        and m.skill_score_vs_rw is not None and m.skill_score_vs_rw > 0
    ]
    best: BacktestMetric | None = None
    best_val = float("-inf")
    for m in contenders:
        if m.skill_score_vs_rw is not None and m.skill_score_vs_rw > best_val:
            best_val = m.skill_score_vs_rw
            best = m
    total_folds = sum(m.n_folds for m in metrics if m.model_type == "naive_rw")
    starts = [m.backtest_start for m in metrics if m.backtest_start]
    ends = [m.backtest_end for m in metrics if m.backtest_end]
    return ValidationSummary(
        total_configs=len({(m.target, m.horizon_months) for m in metrics}),
        configs_beating_rw=len(beating),
        best_skill_score=best.skill_score_vs_rw if best else None,
        best_config=(
            f"{best.target} h{best.horizon_months} {best.model_type}" if best else None
        ),
        total_folds=total_folds,
        backtest_start=min(starts) if starts else None,
        backtest_end=max(ends) if ends else None,
        low_confidence=any(m.low_confidence for m in metrics),
    )
