from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import pandas as pd
import psycopg
from psycopg.types.json import Jsonb

from econsight.config import configure_logging, get_logger
from econsight.db.connection import PROJECT_ROOT, db_connection
from econsight.models.composite import CompositeScorer
from econsight.models.features import build_feature_matrix, load_mart
from econsight.models.monte_carlo import SimulationResult, simulate
from econsight.models.var_model import VARModel
from econsight.models.xgb_model import HORIZONS, TARGETS, XGBForecastModel

_ARTEFACTS = PROJECT_ROOT / "models" / "artefacts"

# Forecast row type: date, target, horizon, model, point, p10, p50, p90, base, upside, downside
OptFloat = float | None
ForecastRow = (
    tuple[date, str, int, str, float, OptFloat, OptFloat, OptFloat, OptFloat, OptFloat, OptFloat]
)

_FORECAST_UPSERT = """
    INSERT INTO marts.model_forecasts
        (period_date, target, horizon_months, model_type, point_forecast,
         p10, p50, p90, scenario_base, scenario_upside, scenario_downside)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (period_date, target, horizon_months, model_type) DO UPDATE SET
        point_forecast    = EXCLUDED.point_forecast,
        p10               = EXCLUDED.p10,
        p50               = EXCLUDED.p50,
        p90               = EXCLUDED.p90,
        scenario_base     = EXCLUDED.scenario_base,
        scenario_upside   = EXCLUDED.scenario_upside,
        scenario_downside = EXCLUDED.scenario_downside,
        created_at        = now()
"""

_HEALTH_UPSERT = """
    INSERT INTO marts.economic_health_score (period_date, score, component_scores)
    VALUES (%s, %s, %s)
    ON CONFLICT (period_date) DO UPDATE SET
        score            = EXCLUDED.score,
        component_scores = EXCLUDED.component_scores,
        updated_at       = now()
"""


def _next_month(last_date: date) -> date:
    month = last_date.month % 12 + 1
    year = last_date.year + (1 if last_date.month == 12 else 0)
    return date(year, month, 1)


async def upsert_forecasts(
    conn: psycopg.AsyncConnection[Any],
    var_forecasts: dict[int, dict[str, float]],
    xgb_models: dict[tuple[str, int], XGBForecastModel],
    X: pd.DataFrame,
    sim: SimulationResult,
) -> None:
    forecast_date = _next_month(X.index[-1])
    rows: list[ForecastRow] = []
    # VAR rows — MC columns are NULL
    for h, targets in var_forecasts.items():
        for target, point in targets.items():
            rows.append((forecast_date, target, h, "var", point,
                         None, None, None, None, None, None))
    # XGBoost rows — include MC bands and scenarios
    for (target, h), model in xgb_models.items():
        point = model.predict(X)
        band = sim.bands[(target, h)]
        scenario_base = sim.scenarios["base"][target]
        scenario_up = sim.scenarios["upside"][target]
        scenario_dn = sim.scenarios["downside"][target]
        rows.append((
            forecast_date, target, h, "xgboost", point,
            band["p10"], band["p50"], band["p90"],
            scenario_base, scenario_up, scenario_dn,
        ))
    async with conn.cursor() as cur:
        await cur.executemany(_FORECAST_UPSERT, rows)


async def upsert_health_scores(
    conn: psycopg.AsyncConnection[Any],
    scores: pd.DataFrame,
) -> None:
    rows = [
        (idx, float(row["score"]), Jsonb(row["component_scores"]))
        for idx, row in scores.iterrows()
    ]
    async with conn.cursor() as cur:
        await cur.executemany(_HEALTH_UPSERT, rows)


async def run_models() -> None:
    configure_logging()
    log = get_logger(__name__)
    log.info("phase2.start")

    async with db_connection() as conn:
        df_raw = await load_mart(conn)
        log.info("data.loaded", rows=len(df_raw))

        X = build_feature_matrix(df_raw)
        log.info("features.built", cols=X.shape[1])

        # VAR/VECM
        var = VARModel()
        var.fit(df_raw)
        var_forecasts = var.predict(horizons=HORIZONS)
        log.info("var.done")

        # XGBoost — 6 models (3 targets × 2 horizons)
        xgb_models: dict[tuple[str, int], XGBForecastModel] = {}
        for target in TARGETS:
            for h in HORIZONS:
                y = df_raw[target].shift(-h).dropna()
                common = X.index.intersection(y.index)
                model = XGBForecastModel(target=target, horizon=h)
                metrics = model.fit(X.loc[common], y.loc[common])
                xgb_models[(target, h)] = model
                log.info("xgb.fitted", target=target, horizon=h,
                         test_rmse=round(metrics.test_rmse, 4))

        # Monte Carlo
        sim = simulate(xgb_models, X)
        log.info("monte_carlo.done")

        # Composite score
        scorer = CompositeScorer()
        scorer.fit(df_raw)
        scores = scorer.score(df_raw)
        log.info("composite.done",
                 latest_score=round(float(scores["score"].iloc[-1]), 1))

        # Persist to DB
        await upsert_forecasts(conn, var_forecasts, xgb_models, X, sim)
        await upsert_health_scores(conn, scores)
        await conn.commit()
        log.info("db.persisted")

        # Save artefacts
        _ARTEFACTS.mkdir(parents=True, exist_ok=True)
        var.save(_ARTEFACTS / "var_model.pkl")
        for (target, h), model in xgb_models.items():
            model.save(_ARTEFACTS / f"xgb_{target}_h{h}.pkl")
        scorer.save(_ARTEFACTS / "composite_scorer.pkl")
        log.info("artefacts.saved", path=str(_ARTEFACTS))

        log.info("phase2.complete")


if __name__ == "__main__":
    asyncio.run(run_models())
