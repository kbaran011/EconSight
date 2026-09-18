from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import numpy as np
import pandas as pd

from econsight.models.xgb_model import make_estimator

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

    def predict(self, train_levels, X_train, y_train, x_origin, target, horizon) -> float:
        return float(train_levels[target].iloc[-1])  # y_t


@dataclass
class SeasonalNaive:
    name: str = "seasonal_naive"

    def predict(self, train_levels, X_train, y_train, x_origin, target, horizon) -> float:
        # value at (target_date - 12 months) == position len-1 + horizon - 12
        offset = 13 - horizon
        s = train_levels[target]
        if len(s) < offset:
            return float(s.iloc[-1])  # fallback for very short windows
        return float(s.iloc[-offset])


@dataclass
class XGBBacktest:
    name: str = "xgboost"

    def predict(self, train_levels, X_train, y_train, x_origin, target, horizon) -> float:
        model = make_estimator()
        model.fit(X_train, y_train, verbose=False)
        return float(model.predict(x_origin)[0])


@dataclass
class VARBacktest:
    name: str = "var"

    def predict(self, train_levels, X_train, y_train, x_origin, target, horizon) -> float:
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
