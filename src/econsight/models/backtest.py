from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import numpy as np
import pandas as pd

from econsight.config import configure_logging, get_logger
from econsight.db.connection import db_connection
from econsight.models.backtest_metrics import (
    diebold_mariano,
    mae,
    mase,
    rmse,
    skill_score,
)
from econsight.models.features import build_feature_matrix, load_mart
from econsight.models.xgb_model import HORIZONS, TARGETS, make_estimator

_TARGET_COLS = ["cpi", "unemployment_rate", "overnight_rate"]


@dataclass
class Fold:
    origin_date: date
    target_date: date
    y_true: float
    y_pred: float
    max_train_target_date: date | None = None


def build_pairs(
    levels: pd.DataFrame, X: pd.DataFrame, target: str, horizon: int
) -> pd.DataFrame:
    """One row per origin that has a realized target `horizon` steps ahead.

    Columns: target_date, y_true — indexed by origin_date. Positional stepping
    (matches the existing `series.shift(-h)` convention in forecaster.py).
    """
    idx = list(levels.index)
    pos = {d: i for i, d in enumerate(idx)}
    rows: list[tuple[date, date, float]] = []
    for d in X.index:
        p = pos[d]
        tp = p + horizon
        if tp >= len(idx):
            continue
        rows.append((d, idx[tp], float(levels[target].iloc[tp])))
    return (
        pd.DataFrame(rows, columns=["origin_date", "target_date", "y_true"])
        .set_index("origin_date")
    )


class BacktestModel(Protocol):
    name: str

    def predict(
        self,
        train_levels: pd.DataFrame,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        x_origin: pd.DataFrame,
        target: str,
        horizon: int,
    ) -> float: ...


@dataclass
class NaiveRW:
    name: str = "naive_rw"

    def predict(
        self,
        train_levels: pd.DataFrame,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        x_origin: pd.DataFrame,
        target: str,
        horizon: int,
    ) -> float:
        return float(train_levels[target].iloc[-1])  # y_t


@dataclass
class SeasonalNaive:
    name: str = "seasonal_naive"

    def predict(
        self,
        train_levels: pd.DataFrame,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        x_origin: pd.DataFrame,
        target: str,
        horizon: int,
    ) -> float:
        # value at (target_date - 12 months) == position len-1 + horizon - 12
        offset = 13 - horizon
        s = train_levels[target]
        if len(s) < offset:
            return float(s.iloc[-1])  # fallback for very short windows
        return float(s.iloc[-offset])


@dataclass
class XGBBacktest:
    name: str = "xgboost"

    def predict(
        self,
        train_levels: pd.DataFrame,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        x_origin: pd.DataFrame,
        target: str,
        horizon: int,
    ) -> float:
        model = make_estimator()
        model.fit(X_train, y_train, verbose=False)
        return float(model.predict(x_origin)[0])


@dataclass
class VARBacktest:
    name: str = "var"

    def predict(
        self,
        train_levels: pd.DataFrame,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        x_origin: pd.DataFrame,
        target: str,
        horizon: int,
    ) -> float:
        from econsight.models.var_model import VARModel

        var = VARModel()
        var.fit(train_levels)
        last = {c: float(train_levels[c].iloc[-1]) for c in _TARGET_COLS}
        # predict_levels reconstructs a LEVEL forecast for both branches (see Task 4b),
        # so it is comparable to y_true; a raw var.predict() on the differenced branch
        # would return a month-over-month change and produce a spurious units mismatch.
        return float(var.predict_levels(last, [horizon])[horizon][target])


def walk_forward(
    levels: pd.DataFrame,
    X: pd.DataFrame,
    target: str,
    horizon: int,
    models: list[BacktestModel],
    min_train: int,
    min_fit: int = 8,
) -> dict[str, list[Fold]]:
    """Expanding-window rolling-origin backtest.

    For each origin, training pairs are restricted to those whose target_date is
    <= origin (the leakage-free `t - h` cutoff). Predicts the value at origin+h.
    """
    pairs = build_pairs(levels, X, target, horizon)
    results: dict[str, list[Fold]] = {m.name: [] for m in models}
    origins = list(pairs.index)

    for origin in origins[min_train:]:
        target_date = pairs.loc[origin, "target_date"]
        y_true = float(pairs.loc[origin, "y_true"])
        train_mask = pairs["target_date"] <= origin
        train_origins = pairs.index[train_mask]
        if len(train_origins) < min_fit:
            continue
        max_train_td = pairs.loc[train_mask, "target_date"].max()

        X_train = X.loc[train_origins]
        y_train = pairs.loc[train_mask, "y_true"].astype(float)
        train_levels = levels.loc[:origin]
        x_origin = X.loc[[origin]]

        for m in models:
            try:
                pred = m.predict(
                    train_levels, X_train, y_train, x_origin, target, horizon
                )
            except Exception:
                continue  # e.g. VAR singular matrix — skip this fold for this model
            results[m.name].append(
                Fold(origin, target_date, y_true, pred, max_train_td)
            )
    return results


def evaluate_target_horizon(
    levels: pd.DataFrame,
    X: pd.DataFrame,
    target: str,
    horizon: int,
    models: list[BacktestModel],
    min_train: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run the backtest and return (metric rows, prediction rows) as plain dicts."""
    folds_by_model = walk_forward(levels, X, target, horizon, models, min_train)
    # MASE scale = naive one-step MAE on the TRAINING portion only (levels up to the first
    # backtest origin), so the test window never leaks into the denominator (spec A.2).
    first_origin = min(
        (f.origin_date for folds in folds_by_model.values() for f in folds),
        default=None,
    )
    scale_series = (
        levels[target].loc[:first_origin].tolist()
        if first_origin is not None
        else levels[target].tolist()
    )

    # Random-walk baseline, keyed by target_date for alignment
    rw_folds = folds_by_model.get("naive_rw", [])
    rw_err = {f.target_date: (f.y_true - f.y_pred) for f in rw_folds}
    rw_rmse = rmse(
        [f.y_true for f in rw_folds], [f.y_pred for f in rw_folds]
    ) if rw_folds else float("nan")

    metric_rows: list[dict[str, Any]] = []
    pred_rows: list[dict[str, Any]] = []
    for name, folds in folds_by_model.items():
        if not folds:
            continue
        y_true = [f.y_true for f in folds]
        y_pred = [f.y_pred for f in folds]
        m_rmse = rmse(y_true, y_pred)
        # align model vs RW errors on shared target_dates for DM
        shared = [f.target_date for f in folds if f.target_date in rw_err]
        model_err = [
            f.y_true - f.y_pred for f in folds if f.target_date in rw_err
        ]
        base_err = [rw_err[td] for td in shared]
        dm_stat, dm_p = (
            diebold_mariano(model_err, base_err, horizon=horizon)
            if name != "naive_rw" and shared
            else (float("nan"), None)
        )
        metric_rows.append(
            {
                "target": target,
                "horizon_months": horizon,
                "model_type": name,
                "baseline": "random_walk",
                "n_folds": len(folds),
                "mae": mae(y_true, y_pred),
                "rmse": m_rmse,
                "mase": mase(y_true, y_pred, scale_series),
                "skill_score_vs_rw": skill_score(m_rmse, rw_rmse),
                "dm_stat": None if np.isnan(dm_stat) else dm_stat,
                "dm_pvalue": dm_p,
                "backtest_start": folds[0].target_date,
                "backtest_end": folds[-1].target_date,
            }
        )
        for f in folds:
            pred_rows.append(
                {
                    "target": target,
                    "horizon_months": horizon,
                    "model_type": name,
                    "origin_date": f.origin_date,
                    "target_date": f.target_date,
                    "y_true": f.y_true,
                    "y_pred": f.y_pred,
                }
            )
    return metric_rows, pred_rows


_MIN_TRAIN_DEFAULT = 48

_METRIC_UPSERT = """
    INSERT INTO marts.model_backtests
        (target, horizon_months, model_type, baseline, n_folds, mae, rmse, mase,
         skill_score_vs_rw, dm_stat, dm_pvalue, backtest_start, backtest_end)
    VALUES (%(target)s, %(horizon_months)s, %(model_type)s, %(baseline)s, %(n_folds)s,
            %(mae)s, %(rmse)s, %(mase)s, %(skill_score_vs_rw)s, %(dm_stat)s,
            %(dm_pvalue)s, %(backtest_start)s, %(backtest_end)s)
    ON CONFLICT (target, horizon_months, model_type) DO UPDATE SET
        baseline = EXCLUDED.baseline, n_folds = EXCLUDED.n_folds, mae = EXCLUDED.mae,
        rmse = EXCLUDED.rmse, mase = EXCLUDED.mase,
        skill_score_vs_rw = EXCLUDED.skill_score_vs_rw, dm_stat = EXCLUDED.dm_stat,
        dm_pvalue = EXCLUDED.dm_pvalue, backtest_start = EXCLUDED.backtest_start,
        backtest_end = EXCLUDED.backtest_end, created_at = now()
"""

_PRED_UPSERT = """
    INSERT INTO marts.backtest_predictions
        (target, horizon_months, model_type, origin_date, target_date, y_true, y_pred)
    VALUES (%(target)s, %(horizon_months)s, %(model_type)s, %(origin_date)s,
            %(target_date)s, %(y_true)s, %(y_pred)s)
    ON CONFLICT (target, horizon_months, model_type, target_date) DO UPDATE SET
        origin_date = EXCLUDED.origin_date, y_true = EXCLUDED.y_true,
        y_pred = EXCLUDED.y_pred, created_at = now()
"""


def _default_min_train(n_pairs: int) -> int:
    """Keep >= ~20 folds when data is short."""
    if n_pairs - _MIN_TRAIN_DEFAULT >= 20:
        return _MIN_TRAIN_DEFAULT
    return max(24, n_pairs // 2)


async def run_backtest() -> None:
    configure_logging()
    log = get_logger(__name__)
    log.info("backtest.start")

    async with db_connection() as conn:
        levels = await load_mart(conn)
        X = build_feature_matrix(levels)
        models: list[BacktestModel] = [
            NaiveRW(), SeasonalNaive(), VARBacktest(), XGBBacktest()
        ]
        all_metrics: list[dict[str, Any]] = []
        all_preds: list[dict[str, Any]] = []
        for target in TARGETS:
            for horizon in HORIZONS:
                pairs_n = len(X) - horizon
                min_train = _default_min_train(pairs_n)
                metrics, preds = evaluate_target_horizon(
                    levels, X, target, horizon, models, min_train
                )
                all_metrics.extend(metrics)
                all_preds.extend(preds)
                log.info("backtest.cell", target=target, horizon=horizon,
                         folds=metrics[0]["n_folds"] if metrics else 0)

        async with conn.cursor() as cur:
            await cur.executemany(_METRIC_UPSERT, all_metrics)
            await cur.executemany(_PRED_UPSERT, all_preds)
        await conn.commit()
        log.info("backtest.persisted", metrics=len(all_metrics), preds=len(all_preds))


if __name__ == "__main__":
    asyncio.run(run_backtest())
