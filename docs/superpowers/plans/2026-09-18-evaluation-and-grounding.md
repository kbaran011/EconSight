# Forecast Evaluation, Validation & RAG Grounding — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add rigorous forecast evaluation (walk-forward backtest vs. naive baselines with MASE / skill score / Diebold–Mariano) and RAG answer-grounding evidence (per-sentence attribution, groundedness score, executed-SQL), surfaced through new API endpoints and UI.

**Architecture:** Pure metric/grounding math lives in dependency-light modules that are unit-tested offline. A model-agnostic walk-forward engine reuses the existing `VARModel`/`XGBForecastModel`/`features.py`, persists results to two new `marts` tables, and is exposed via a `/api/validation` router and a `Validation` page. RAG grounding wraps the existing `query_engine` and extends `RAGResponse` with optional, backward-compatible fields rendered in the `Ask` page.

**Tech Stack:** Python 3.12, numpy/pandas, scipy.stats (already transitively present via statsmodels), xgboost, statsmodels, FastAPI + Pydantic, psycopg (async), pytest; React + TypeScript + Vite + Recharts + TanStack Query.

**Spec:** `docs/superpowers/specs/2026-09-18-evaluation-and-grounding-design.md`

---

## Conventions (read before starting)

- Run backend tests from repo root: `pytest tests/... -v` (project uses `pytest-asyncio`, async tests need no decorator per existing config).
- Frontend checks from `frontend/`: `npm run build` (runs `tsc -b` then `vite build`) and `npm run lint`.
- Commit after every green step. Commit message trailer for this repo:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` (no other Co-Authored-By line).
- **Assumption (matches existing code):** after the `data_complete` filter, mart rows are contiguous monthly observations. The existing pipeline already relies on this (`y = series.shift(-h)` in `forecaster.py`). Horizons step positionally.

## File Structure

**Create (backend):**
- `src/econsight/models/backtest_metrics.py` — pure functions: `mae`, `rmse`, `mase`, `skill_score`, `diebold_mariano`. No DB, no models.
- `src/econsight/models/backtest.py` — walk-forward engine, model adapters, `run_backtest()` runner + upserts.
- `src/econsight/api/routers/validation.py` — `/api/validation/{metrics,predictions,summary}`.
- `src/econsight/rag/grounding.py` — sentence attribution + groundedness (embedding model only).

**Modify (backend):**
- `src/econsight/models/xgb_model.py` — extract `make_estimator()` factory (DRY, reused by backtest).
- `src/econsight/models/var_model.py` — add `predict_levels()` so the VAR (differenced) branch returns level forecasts comparable to `y_true` (VECM branch already returns levels). Does not change `fit`/`predict`.
- `src/econsight/db/schema.sql` — two new tables + grants.
- `src/econsight/db/seed.py` — run backtest in the seed path behind an empty-table guard.
- `src/econsight/api/schemas.py` — `BacktestMetric`, `BacktestPredictionSeries`, `ValidationSummary`, `SourceSnippet`, `SentenceAttribution`, extended `RAGResponse`, `StatusResponse.backtest_row_count`.
- `src/econsight/api/main.py` — register validation router.
- `src/econsight/api/routers/status.py` — add `backtest_row_count`.
- `src/econsight/rag/retriever.py` — return chunk text so grounding can re-embed (already returns text; add nothing unless needed).
- `src/econsight/rag/query_engine.py` — attach grounding to narrative answers, executed SQL to sql answers.

**Create (tests):**
- `tests/test_models/test_backtest_metrics.py`, `tests/test_models/test_backtest.py`
- `tests/test_api/test_validation.py`
- `tests/test_rag/__init__.py`, `tests/test_rag/test_grounding.py`

**Create (frontend):**
- `frontend/src/pages/Validation.tsx`
**Modify (frontend):**
- `frontend/src/api/client.ts` (types + fetchers), `frontend/src/App.tsx` (route + nav), `frontend/src/pages/Ask.tsx` (grounding UI).

---

## Phase 1 — Backtest metrics (pure math, TDD)

### Task 1: MAE / RMSE / MASE / skill score

**Files:**
- Create: `src/econsight/models/backtest_metrics.py`
- Test: `tests/test_models/test_backtest_metrics.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models/test_backtest_metrics.py
import numpy as np
import pytest

from econsight.models.backtest_metrics import mae, rmse, mase, skill_score


def test_mae_rmse_basic():
    y = [1.0, 2.0, 3.0]
    p = [1.0, 2.0, 5.0]        # errors 0,0,2
    assert mae(y, p) == pytest.approx(2 / 3)
    assert rmse(y, p) == pytest.approx((4 / 3) ** 0.5)


def test_mase_scales_by_naive_mae():
    # scale series diffs are all 1.0 -> naive MAE = 1.0 -> MASE == MAE
    scale_series = [10.0, 11.0, 12.0, 13.0, 14.0]
    y = [20.0, 22.0]
    p = [20.0, 20.0]           # MAE = 1.0
    assert mase(y, p, scale_series) == pytest.approx(1.0)


def test_mase_below_one_means_beats_naive():
    scale_series = [0.0, 2.0, 4.0, 6.0]   # naive MAE = 2.0
    y = [10.0, 10.0]
    p = [10.5, 9.5]            # MAE = 0.5 -> MASE = 0.25
    assert mase(y, p, scale_series) == pytest.approx(0.25)


def test_mase_zero_scale_returns_nan():
    assert np.isnan(mase([1.0], [1.0], [5.0, 5.0, 5.0]))


def test_skill_score_sign():
    assert skill_score(rmse_model=0.5, rmse_baseline=1.0) == pytest.approx(0.5)
    assert skill_score(rmse_model=2.0, rmse_baseline=1.0) == pytest.approx(-1.0)
    assert np.isnan(skill_score(rmse_model=1.0, rmse_baseline=0.0))
```

- [ ] **Step 2: Run — expect FAIL** (`ModuleNotFoundError`)

Run: `pytest tests/test_models/test_backtest_metrics.py -v`

- [ ] **Step 3: Implement**

```python
# src/econsight/models/backtest_metrics.py
from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def _arr(x: Sequence[float]) -> np.ndarray:
    return np.asarray(x, dtype=float)


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    return float(np.mean(np.abs(_arr(y_true) - _arr(y_pred))))


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    return float(np.sqrt(np.mean((_arr(y_true) - _arr(y_pred)) ** 2)))


def mase(
    y_true: Sequence[float], y_pred: Sequence[float], scale_series: Sequence[float]
) -> float:
    """Mean Absolute Scaled Error (Hyndman & Koehler).

    Scale = MAE of the one-step naive forecast on ``scale_series`` (the target's
    in-sample level history). MASE < 1 means the model beats the naive benchmark.
    """
    scale = float(np.mean(np.abs(np.diff(_arr(scale_series)))))
    if not np.isfinite(scale) or scale == 0.0:
        return float("nan")
    return mae(y_true, y_pred) / scale


def skill_score(rmse_model: float, rmse_baseline: float) -> float:
    """1 - RMSE_model / RMSE_baseline. Positive => better than baseline."""
    if not np.isfinite(rmse_baseline) or rmse_baseline == 0.0:
        return float("nan")
    return 1.0 - rmse_model / rmse_baseline
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest tests/test_models/test_backtest_metrics.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/econsight/models/backtest_metrics.py tests/test_models/test_backtest_metrics.py
git commit -m "feat: MAE/RMSE/MASE/skill-score metrics for backtesting"
```

### Task 2: Diebold–Mariano test (HAC variance for overlapping horizons)

**Files:**
- Modify: `src/econsight/models/backtest_metrics.py`
- Test: `tests/test_models/test_backtest_metrics.py`

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_models/test_backtest_metrics.py
from econsight.models.backtest_metrics import diebold_mariano


def test_dm_detects_clear_superiority():
    rng = np.random.default_rng(0)
    n = 60
    base_err = rng.normal(0, 1.0, n)
    model_err = rng.normal(0, 0.3, n)      # clearly smaller errors
    stat, p = diebold_mariano(model_err, base_err, horizon=1)
    assert stat < 0          # negative => model loss < baseline loss
    assert p is not None and p < 0.05


def test_dm_no_difference_is_insignificant():
    rng = np.random.default_rng(1)
    e = rng.normal(0, 1.0, 60)
    stat, p = diebold_mariano(e.copy(), e.copy(), horizon=1)
    assert p is None or p > 0.05     # identical losses -> n/a or non-significant


def test_dm_small_sample_returns_none_pvalue():
    stat, p = diebold_mariano([0.1, 0.2, 0.3], [0.2, 0.3, 0.4], horizon=1)
    assert p is None


def test_dm_horizon_uses_autocovariance_terms():
    # Should run without error for h>1 and return a finite stat
    rng = np.random.default_rng(2)
    base_err = rng.normal(0, 1.0, 50)
    model_err = rng.normal(0, 0.5, 50)
    stat, p = diebold_mariano(model_err, base_err, horizon=3)
    assert np.isfinite(stat)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest tests/test_models/test_backtest_metrics.py -k dm -v`

- [ ] **Step 3: Implement (append to `backtest_metrics.py`)**

```python
from scipy import stats  # add near top imports


def diebold_mariano(
    model_errors: Sequence[float],
    baseline_errors: Sequence[float],
    horizon: int = 1,
    power: int = 2,
) -> tuple[float, float | None]:
    """Diebold–Mariano test with Harvey–Leybourne–Newbold small-sample correction.

    Loss differential d = |model_err|^power - |baseline_err|^power.
    Negative mean(d) => the model has lower loss (is better). For horizon > 1 the
    forecasts overlap, so the long-run variance of the mean includes autocovariances
    up to lag ``horizon - 1``. Returns (dm_statistic, p_value); p_value is None when
    the sample is too small or the variance is degenerate.
    """
    e1 = np.asarray(model_errors, dtype=float)
    e2 = np.asarray(baseline_errors, dtype=float)
    d = np.abs(e1) ** power - np.abs(e2) ** power
    n = d.size
    if n < 8:
        return (float("nan"), None)
    d_bar = float(np.mean(d))
    dev = d - d_bar
    gamma0 = float(np.mean(dev**2))
    acov = 0.0
    for k in range(1, horizon):
        if k < n:
            acov += float(np.mean(dev[k:] * dev[:-k]))
    var_dbar = (gamma0 + 2.0 * acov) / n
    if not np.isfinite(var_dbar) or var_dbar <= 0.0:
        return (float("nan"), None)
    dm = d_bar / np.sqrt(var_dbar)
    # HLN correction factor
    factor = (n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n
    if factor <= 0:
        return (float(dm), None)
    dm_hln = float(dm * np.sqrt(factor))
    p_value = float(2.0 * stats.t.cdf(-abs(dm_hln), df=n - 1))
    return (dm_hln, p_value)
```

- [ ] **Step 4: Run — expect PASS**; then full metrics file green:

Run: `pytest tests/test_models/test_backtest_metrics.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/econsight/models/backtest_metrics.py tests/test_models/test_backtest_metrics.py
git commit -m "feat: Diebold-Mariano test with HLN correction and HAC variance"
```

---

## Phase 2 — Walk-forward engine

### Task 3: XGB estimator factory (DRY refactor)

**Files:**
- Modify: `src/econsight/models/xgb_model.py`

- [ ] **Step 1: Extract factory.** Add above the class:

```python
def make_estimator() -> XGBRegressor:
    """Canonical XGBoost hyperparameters, shared by training and backtesting."""
    return XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
        n_jobs=-1,
    )
```

- [ ] **Step 2: Use it in `XGBForecastModel.fit`.** Replace the inline `XGBRegressor(...)` construction with `self._model = make_estimator()`.

- [ ] **Step 3: Run existing model tests — expect PASS (no behavior change)**

Run: `pytest tests/test_models/test_xgb_model.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/econsight/models/xgb_model.py
git commit -m "refactor: extract make_estimator() for reuse in backtesting"
```

### Task 4: Walk-forward pair builder + no-look-ahead

**Files:**
- Create: `src/econsight/models/backtest.py`
- Test: `tests/test_models/test_backtest.py`

- [ ] **Step 1: Write failing tests** (pure, synthetic; no DB, no real models)

```python
# tests/test_models/test_backtest.py
import numpy as np
import pandas as pd
import pytest

from econsight.models.backtest import build_pairs, walk_forward, NaiveRW, SeasonalNaive


def _levels(n=40):
    idx = pd.date_range("2015-01-01", periods=n, freq="MS").date
    # simple trending series per target
    data = {
        "cpi": np.linspace(100, 140, n),
        "unemployment_rate": np.linspace(7, 5, n),
        "overnight_rate": np.linspace(0.5, 4.5, n),
    }
    return pd.DataFrame(data, index=pd.Index(idx, name="period_date"))


def test_build_pairs_target_date_is_h_ahead():
    lv = _levels(12)
    X = pd.DataFrame({"f": range(len(lv))}, index=lv.index)
    pairs = build_pairs(lv, X, "cpi", horizon=3)
    # first origin's target date is 3 rows ahead; last h rows have no target
    assert pairs.iloc[0]["target_date"] == lv.index[3]
    assert len(pairs) == len(lv) - 3


def test_walk_forward_no_lookahead_invariant():
    """Every training pair used at an origin must have target_date <= origin."""
    lv = _levels(40)
    X = pd.DataFrame({"f": np.arange(len(lv), dtype=float)}, index=lv.index)
    horizon = 3
    seen = walk_forward(lv, X, "cpi", horizon, models=[NaiveRW()], min_train=12)
    # walk_forward exposes the audited training window via the recorded folds;
    # assert the naive RW prediction equals the level at the origin (y_t)
    for fold in seen["naive_rw"]:
        origin_level = lv.loc[fold.origin_date, "cpi"]
        assert fold.y_pred == pytest.approx(origin_level)


def test_walk_forward_records_training_audit():
    lv = _levels(30)
    X = pd.DataFrame({"f": np.arange(len(lv), dtype=float)}, index=lv.index)
    horizon = 1
    folds = walk_forward(lv, X, "cpi", horizon, models=[NaiveRW()], min_train=10)["naive_rw"]
    for f in folds:
        # audit: max training target_date must not exceed the origin
        assert f.max_train_target_date <= f.origin_date


def test_seasonal_naive_uses_value_12_months_before_target():
    lv = _levels(30)
    X = pd.DataFrame({"f": np.arange(len(lv), dtype=float)}, index=lv.index)
    folds = walk_forward(lv, X, "cpi", 1, models=[SeasonalNaive()], min_train=14)["seasonal_naive"]
    f = folds[0]
    # target_date - 12 months value
    tpos = list(lv.index).index(f.target_date)
    assert f.y_pred == pytest.approx(lv["cpi"].iloc[tpos - 12])
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest tests/test_models/test_backtest.py -v`

- [ ] **Step 3: Implement engine**

```python
# src/econsight/models/backtest.py
from __future__ import annotations

from dataclasses import dataclass, field
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
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest tests/test_models/test_backtest.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/econsight/models/backtest.py tests/test_models/test_backtest.py
git commit -m "feat: leakage-free walk-forward engine with naive/VAR/XGB adapters"
```

### Task 5: Aggregate folds into metrics

**Files:**
- Modify: `src/econsight/models/backtest.py`
- Test: `tests/test_models/test_backtest.py`

- [ ] **Step 1: Add failing test**

```python
# append to tests/test_models/test_backtest.py
from econsight.models.backtest import Fold, evaluate_target_horizon


def test_evaluate_produces_metrics_and_skill_vs_rw():
    lv = _levels(40)
    X = pd.DataFrame({"f": np.arange(len(lv), dtype=float)}, index=lv.index)
    metrics, preds = evaluate_target_horizon(
        lv, X, "cpi", 1, models=[NaiveRW(), SeasonalNaive()], min_train=14
    )
    names = {m["model_type"] for m in metrics}
    assert {"naive_rw", "seasonal_naive"} <= names
    rw = next(m for m in metrics if m["model_type"] == "naive_rw")
    assert rw["skill_score_vs_rw"] == pytest.approx(0.0)   # RW vs itself
    assert rw["n_folds"] > 0
    assert all("target_date" in p for p in preds)
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement (append)**

```python
from econsight.models.backtest_metrics import (
    diebold_mariano,
    mae,
    mase,
    rmse,
    skill_score,
)


def evaluate_target_horizon(
    levels: pd.DataFrame,
    X: pd.DataFrame,
    target: str,
    horizon: int,
    models: list[BacktestModel],
    min_train: int,
) -> tuple[list[dict], list[dict]]:
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

    metric_rows: list[dict] = []
    pred_rows: list[dict] = []
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
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest tests/test_models/test_backtest.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/econsight/models/backtest.py tests/test_models/test_backtest.py
git commit -m "feat: aggregate backtest folds into metrics + prediction rows"
```

### Task 4b: VAR level reconstruction (`predict_levels`)

**Files:**
- Modify: `src/econsight/models/var_model.py`
- Test: `tests/test_models/test_var_model.py`

**Why:** the non-cointegrated branch fits `VAR(data.diff())` and `predict()` returns forecasts
in *differenced* space (month-over-month changes), while the backtest compares against level
`y_true`. `predict_levels()` reconstructs levels (VECM branch already returns levels), so VAR
is evaluated fairly. `fit`/`predict` are untouched — existing tests stay green.

- [ ] **Step 1: Add failing tests** (deterministic — monkeypatch `predict` to isolate the
  reconstruction logic; no statsmodels fit needed)

```python
# append to tests/test_models/test_var_model.py
def test_predict_levels_var_branch_cumsums_diffs(monkeypatch):
    from econsight.models.var_model import VARModel

    m = VARModel()
    m._model_type = "var"
    per_step = {
        1: {"cpi": 0.5, "unemployment_rate": 0.0, "overnight_rate": 0.0},
        2: {"cpi": 0.5, "unemployment_rate": 0.0, "overnight_rate": 0.0},
        3: {"cpi": 0.5, "unemployment_rate": 0.0, "overnight_rate": 0.0},
    }
    monkeypatch.setattr(m, "predict", lambda horizons: per_step)
    last = {"cpi": 100.0, "unemployment_rate": 6.0, "overnight_rate": 4.0}
    out = m.predict_levels(last, [1, 3])
    assert out[1]["cpi"] == pytest.approx(100.5)   # 100 + 0.5
    assert out[3]["cpi"] == pytest.approx(101.5)   # 100 + 0.5*3


def test_predict_levels_vecm_branch_passthrough(monkeypatch):
    from econsight.models.var_model import VARModel

    m = VARModel()
    m._model_type = "vecm"
    per_step = {1: {"cpi": 137.0, "unemployment_rate": 5.5, "overnight_rate": 4.2}}
    monkeypatch.setattr(m, "predict", lambda horizons: per_step)
    out = m.predict_levels({"cpi": 100.0, "unemployment_rate": 6.0, "overnight_rate": 4.0}, [1])
    assert out[1]["cpi"] == pytest.approx(137.0)   # already a level
```

Ensure `import pytest` is present at the top of `tests/test_models/test_var_model.py`.

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest tests/test_models/test_var_model.py -k predict_levels -v`

- [ ] **Step 3: Implement — add method to `VARModel` (uses existing `_TARGET_COLS`)**

```python
    def predict_levels(
        self, last_levels: dict[str, float], horizons: list[int]
    ) -> dict[int, dict[str, float]]:
        """Level forecasts comparable across branches.

        VECM already forecasts levels (passthrough). The non-cointegrated branch fits on
        first differences, so its per-step forecasts are changes; reconstruct the level as
        last_level + cumulative sum of forecast diffs up to each horizon.
        """
        max_h = max(horizons)
        per_step = self.predict(horizons=list(range(1, max_h + 1)))
        result: dict[int, dict[str, float]] = {}
        if self._model_type == "vecm":
            for h in horizons:
                result[h] = {c: float(per_step[h][c]) for c in _TARGET_COLS}
        else:
            for h in horizons:
                result[h] = {
                    c: float(last_levels[c])
                    + sum(float(per_step[k][c]) for k in range(1, h + 1))
                    for c in _TARGET_COLS
                }
        return result
```

- [ ] **Step 4: Run — expect PASS (new + existing VAR tests)**

Run: `pytest tests/test_models/test_var_model.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/econsight/models/var_model.py tests/test_models/test_var_model.py
git commit -m "feat: VARModel.predict_levels for fair level-space backtesting"
```

---

## Phase 3 — Schema + persistence + runner

### Task 6: Schema migration

**Files:**
- Modify: `src/econsight/db/schema.sql`

- [ ] **Step 1: Append tables + grants** (idempotent), after `marts.economic_health_score`:

```sql
-- marts.model_backtests
CREATE TABLE IF NOT EXISTS marts.model_backtests (
    id                bigserial   PRIMARY KEY,
    target            text        NOT NULL,
    horizon_months    int         NOT NULL,
    model_type        text        NOT NULL,
    baseline          text        NOT NULL,
    n_folds           int         NOT NULL,
    mae               numeric,
    rmse              numeric,
    mase              numeric,
    skill_score_vs_rw numeric,
    dm_stat           numeric,
    dm_pvalue         numeric,
    backtest_start    date,
    backtest_end      date,
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (target, horizon_months, model_type)
);

-- marts.backtest_predictions
CREATE TABLE IF NOT EXISTS marts.backtest_predictions (
    id             bigserial   PRIMARY KEY,
    target         text        NOT NULL,
    horizon_months int         NOT NULL,
    model_type     text        NOT NULL,
    origin_date    date        NOT NULL,
    target_date    date        NOT NULL,
    y_true         numeric     NOT NULL,
    y_pred         numeric     NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (target, horizon_months, model_type, target_date)
);
```

The existing `GRANT SELECT ON ALL TABLES IN SCHEMA marts` + `ALTER DEFAULT PRIVILEGES`
block at the end of the file already covers new tables for `econsight_reader` (it runs
after these CREATEs). Leave that block last.

- [ ] **Step 2: Verify SQL parses** (if a local DB is available):

Run: `python -c "import pathlib,re; print('ok' if 'model_backtests' in pathlib.Path('src/econsight/db/schema.sql').read_text() else 'missing')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/econsight/db/schema.sql
git commit -m "feat: add model_backtests and backtest_predictions tables"
```

### Task 7: `run_backtest()` runner + upserts

**Files:**
- Modify: `src/econsight/models/backtest.py`

- [ ] **Step 1: Implement runner (append).** Mirrors `forecaster.run_models()` structure.

```python
import asyncio
from typing import Any

import psycopg

from econsight.config import configure_logging, get_logger
from econsight.db.connection import db_connection
from econsight.models.features import build_feature_matrix, load_mart
from econsight.models.xgb_model import HORIZONS, TARGETS

_MIN_TRAIN_DEFAULT = 48
_MIN_FOLDS = 12  # below this, results are flagged low_confidence downstream

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
```

- [ ] **Step 2: Sanity import**

Run: `python -c "from econsight.models.backtest import run_backtest; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/econsight/models/backtest.py
git commit -m "feat: run_backtest() runner persisting metrics + predictions"
```

### Task 8: Seed integration

**Files:**
- Modify: `src/econsight/db/seed.py`

- [ ] **Step 1: Add a backtest count helper** near `_forecast_row_count`:

```python
async def _backtest_row_count(conn: psycopg.AsyncConnection) -> int:
    async with conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM marts.model_backtests")
        row = await cur.fetchone()
    return int(row[0]) if row else 0
```

- [ ] **Step 2: In `_run_seed`, after the models block** (inside `if settings.auto_seed_models:`), add a backtest run guarded by empty-table check:

```python
            async with db_connection() as conn:
                backtest_count = await _backtest_row_count(conn)
            if backtest_count == 0:
                logger.info("seed.backtest_start")
                from econsight.models.backtest import run_backtest

                await run_backtest()
                logger.info("seed.backtest_done")
```

- [ ] **Step 3: Run seed module import + existing seed tests**

Run: `pytest tests/test_api/test_status.py -v`
Expected: PASS (no behavior change without a live seed).

- [ ] **Step 4: Commit**

```bash
git add src/econsight/db/seed.py
git commit -m "feat: run backtest during auto-seed behind empty-table guard"
```

---

## Phase 4 — Validation API

### Task 9: Schemas

**Files:**
- Modify: `src/econsight/api/schemas.py`

- [ ] **Step 1: Add schemas**

```python
class BacktestMetric(BaseModel):
    target: str
    horizon_months: int
    model_type: str
    baseline: str
    n_folds: int
    mae: float | None = None
    rmse: float | None = None
    mase: float | None = None
    skill_score_vs_rw: float | None = None
    dm_stat: float | None = None
    dm_pvalue: float | None = None
    backtest_start: date | None = None
    backtest_end: date | None = None
    low_confidence: bool = False


class BacktestPredictionPoint(BaseModel):
    target_date: date
    model_type: str
    y_true: float
    y_pred: float


class BacktestPredictionSeries(BaseModel):
    target: str
    horizon_months: int
    points: list[BacktestPredictionPoint]


class ValidationSummary(BaseModel):
    total_configs: int
    configs_beating_rw: int
    best_skill_score: float | None = None
    best_config: str | None = None
    total_folds: int
    backtest_start: date | None = None
    backtest_end: date | None = None
    low_confidence: bool = False
```

- [ ] **Step 2: Run schema import**

Run: `python -c "from econsight.api.schemas import ValidationSummary, BacktestMetric; print('ok')"`

- [ ] **Step 3: Commit**

```bash
git add src/econsight/api/schemas.py
git commit -m "feat: validation API schemas"
```

### Task 10: Validation router (API tests first)

**Files:**
- Create: `src/econsight/api/routers/validation.py`
- Modify: `src/econsight/api/main.py`
- Test: `tests/test_api/test_validation.py`

- [ ] **Step 1: Write failing API tests** (mock the cursor like `test_forecasts.py`)

```python
# tests/test_api/test_validation.py
from datetime import date
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient


def _mock_conn(rows, cols):
    mock_cur = AsyncMock()
    mock_cur.fetchall = AsyncMock(return_value=rows)
    mock_cur.description = [(c,) for c in cols]
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_conn


async def test_metrics_endpoint_returns_rows():
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

    cols = ["target", "horizon_months", "model_type", "baseline", "n_folds",
            "mae", "rmse", "mase", "skill_score_vs_rw", "dm_stat", "dm_pvalue",
            "backtest_start", "backtest_end"]
    rows = [("cpi", 1, "xgboost", "random_walk", 50, 0.4, 0.5, 0.7, 0.25,
             -2.1, 0.03, date(2018, 1, 1), date(2025, 12, 1))]

    async def override_db():
        yield _mock_conn(rows, cols)

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/validation/metrics")
    app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body[0]["model_type"] == "xgboost"
    assert body[0]["mase"] == 0.7
    assert body[0]["low_confidence"] is False   # n_folds 50 >= 12


async def test_metrics_low_confidence_flag():
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

    cols = ["target", "horizon_months", "model_type", "baseline", "n_folds",
            "mae", "rmse", "mase", "skill_score_vs_rw", "dm_stat", "dm_pvalue",
            "backtest_start", "backtest_end"]
    rows = [("cpi", 3, "var", "random_walk", 6, 0.4, 0.5, 1.2, -0.1,
             0.5, 0.6, date(2024, 1, 1), date(2025, 12, 1))]

    async def override_db():
        yield _mock_conn(rows, cols)

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/validation/metrics")
    app.dependency_overrides.clear()
    assert r.json()[0]["low_confidence"] is True   # n_folds 6 < 12


async def test_summary_counts_configs_beating_rw():
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

    cols = ["target", "horizon_months", "model_type", "baseline", "n_folds",
            "mae", "rmse", "mase", "skill_score_vs_rw", "dm_stat", "dm_pvalue",
            "backtest_start", "backtest_end"]
    rows = [
        ("cpi", 1, "xgboost", "random_walk", 50, 0.4, 0.5, 0.7, 0.25, -2.1, 0.03,
         date(2018, 1, 1), date(2025, 12, 1)),
        ("cpi", 1, "naive_rw", "random_walk", 50, 0.5, 0.6, 1.0, 0.0, None, None,
         date(2018, 1, 1), date(2025, 12, 1)),
        ("cpi", 1, "var", "random_walk", 50, 0.7, 0.8, 1.3, -0.3, 1.0, 0.4,
         date(2018, 1, 1), date(2025, 12, 1)),
    ]

    async def override_db():
        yield _mock_conn(rows, cols)

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/validation/summary")
    app.dependency_overrides.clear()
    body = r.json()
    # only xgboost has mase<1 and skill>0 among non-naive models
    assert body["configs_beating_rw"] == 1
    assert body["best_config"] == "cpi h1 xgboost"
```

- [ ] **Step 2: Run — expect FAIL (404)**

Run: `pytest tests/test_api/test_validation.py -v`

- [ ] **Step 3: Implement router**

```python
# src/econsight/api/routers/validation.py
from __future__ import annotations

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
    return float(v) if v is not None else None  # type: ignore[arg-type]


def _row_to_metric(r: tuple) -> BacktestMetric:
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
    best = max(
        (m for m in contenders if m.skill_score_vs_rw is not None),
        key=lambda m: m.skill_score_vs_rw,
        default=None,
    )
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
```

- [ ] **Step 4: Register router in `main.py`** — add `validation` to the import and
`app.include_router(validation.router, prefix="/api")`.

- [ ] **Step 5: Run — expect PASS**

Run: `pytest tests/test_api/test_validation.py -v`

- [ ] **Step 6: Add `backtest_row_count` to status** — in `schemas.py` add
`backtest_row_count: int = 0` to `StatusResponse`; in `routers/status.py` query
`SELECT COUNT(*) FROM marts.model_backtests` and pass it. Run `pytest tests/test_api/test_status.py -v`.

- [ ] **Step 7: Commit**

```bash
git add src/econsight/api/routers/validation.py src/econsight/api/main.py \
        src/econsight/api/schemas.py src/econsight/api/routers/status.py \
        tests/test_api/test_validation.py
git commit -m "feat: /api/validation endpoints + backtest_row_count in status"
```

---

## Phase 5 — RAG grounding (pure, stubbed embeddings)

### Task 11: Grounding scorer

**Files:**
- Create: `src/econsight/rag/grounding.py`
- Test: `tests/test_rag/__init__.py`, `tests/test_rag/test_grounding.py`

- [ ] **Step 1: Write failing tests** (inject a fake encoder — no real model download)

```python
# tests/test_rag/test_grounding.py
import numpy as np

from econsight.rag.grounding import (
    build_report,
    parse_citations,
    split_sentences,
)


def test_split_sentences_basic():
    s = split_sentences("CPI rose. Rates held steady! Why? Because inflation.")
    assert len(s) == 4


def test_parse_citations_extracts_indices():
    assert parse_citations("Inflation eased [1] then rose [3].") == {1, 3}
    assert parse_citations("No citations here.") == set()


class _FakeEncoder:
    """Encodes text as a 2-d vector by keyword, so cosine similarity is controllable."""
    def encode(self, texts):
        out = []
        for t in texts:
            t = t.lower()
            out.append([1.0, 0.0] if "inflation" in t else [0.0, 1.0])
        return np.array(out)


def test_build_report_flags_unsupported_sentence():
    chunks = [
        {"title": "Inflation", "text": "Inflation eased over the quarter."},
    ]
    answer = "Inflation eased steadily [1]. Unemployment surged unexpectedly."
    report = build_report(answer, chunks, encoder=_FakeEncoder(), threshold=0.5)
    # sentence 1 matches the inflation chunk; sentence 2 does not
    assert report["sentences"][0]["supported"] is True
    assert report["sentences"][1]["supported"] is False
    assert 0.0 <= report["groundedness"] <= 1.0
    assert report["groundedness"] == 0.5
    assert report["sources"][0]["chunk_id"] == 1


def test_build_report_empty_answer():
    report = build_report("", [], encoder=_FakeEncoder())
    assert report["groundedness"] is None
```

Also create empty `tests/test_rag/__init__.py`.

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest tests/test_rag/test_grounding.py -v`

- [ ] **Step 3: Implement**

```python
# src/econsight/rag/grounding.py
from __future__ import annotations

import re
from typing import Any, Protocol

import numpy as np

DEFAULT_THRESHOLD = 0.45  # cosine similarity below this => sentence unsupported

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_CITATION_RE = re.compile(r"\[(\d+)\]")


class Encoder(Protocol):
    def encode(self, texts: list[str]) -> Any: ...


def split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENTENCE_RE.split(text.strip()) if s.strip()]
    return parts


def parse_citations(sentence: str) -> set[int]:
    return {int(m) for m in _CITATION_RE.findall(sentence)}


def _cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-12)
    b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-12)
    return a @ b.T


def build_report(
    answer: str,
    chunks: list[dict[str, str]],
    encoder: Encoder,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    sentences = split_sentences(answer)
    sources = [
        {
            "chunk_id": i + 1,
            "title": c.get("title", "") or f"Source {i + 1}",
            "snippet": (c.get("text", "")[:240]),
        }
        for i, c in enumerate(chunks)
    ]
    if not sentences or not chunks:
        return {"groundedness": None, "sentences": [], "sources": sources}

    chunk_vecs = np.asarray(encoder.encode([c.get("text", "") for c in chunks]), float)
    clean = [_CITATION_RE.sub("", s).strip() for s in sentences]
    sent_vecs = np.asarray(encoder.encode(clean), float)
    sims = _cosine(sent_vecs, chunk_vecs)  # (n_sent, n_chunk)

    out_sentences = []
    supported_count = 0
    for i, sentence in enumerate(sentences):
        best_idx = int(np.argmax(sims[i]))
        best_sim = float(sims[i][best_idx])
        supported = best_sim >= threshold
        supported_count += int(supported)
        out_sentences.append(
            {
                "text": sentence,
                "supported": supported,
                "similarity": round(best_sim, 3),
                "best_source_title": sources[best_idx]["title"],
                "cited_chunk_ids": sorted(parse_citations(sentence)),
            }
        )
    groundedness = supported_count / len(sentences)
    return {
        "groundedness": round(groundedness, 3),
        "sentences": out_sentences,
        "sources": sources,
    }
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest tests/test_rag/test_grounding.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/econsight/rag/grounding.py tests/test_rag/__init__.py tests/test_rag/test_grounding.py
git commit -m "feat: RAG grounding scorer with sentence attribution"
```

---

## Phase 6 — Wire grounding into query engine

### Task 12: Extend `RAGResponse` + attach grounding

**Files:**
- Modify: `src/econsight/api/schemas.py`, `src/econsight/rag/retriever.py`,
  `src/econsight/rag/query_engine.py`
- Test: `tests/test_api/test_rag.py` (existing tests must stay green — verify backward compat)

- [ ] **Step 1: Extend `RAGResponse` (all new fields optional/defaulted)**

```python
class SourceSnippet(BaseModel):
    chunk_id: int
    title: str
    snippet: str


class SentenceAttribution(BaseModel):
    text: str
    supported: bool
    similarity: float
    best_source_title: str
    cited_chunk_ids: list[int] = []


class RAGResponse(BaseModel):
    answer: str
    sources: list[str]
    query_type: Literal["sql", "narrative"]
    groundedness: float | None = None
    grounding: list[SentenceAttribution] | None = None
    source_snippets: list[SourceSnippet] | None = None
    executed_sql: str | None = None
```

- [ ] **Step 2: Expose the shared encoder from the retriever.** In `retriever.py`, add a
public accessor reusing the singleton model:

```python
def get_encoder() -> SentenceTransformer:
    return _get_model()
```

- [ ] **Step 3: Attach grounding in `query_engine._narrative_answer`.** After building
`chunks` and the LLM `response`, compute the report and populate the new fields. Update the
system prompt to number chunks and request `[n]` citations:

```python
    context = "\n\n".join(
        f"[{i + 1}] ({c['title']})\n{c['text']}" for i, c in enumerate(chunks)
    )
    # ... existing LLM call, but system prompt adds:
    #   "Cite the chunk number in square brackets like [1] after each claim it supports."
    answer_text = _text(response)

    from econsight.rag.grounding import build_report
    from econsight.rag.retriever import get_encoder

    report = build_report(answer_text, chunks, encoder=get_encoder())
    return RAGResponse(
        answer=answer_text,
        sources=list({c["title"] for c in chunks if c["title"]}),
        query_type="narrative",
        groundedness=report["groundedness"],
        grounding=[SentenceAttribution(**s) for s in report["sentences"]],
        source_snippets=[SourceSnippet(**s) for s in report["sources"]],
    )
```

(Import `SentenceAttribution`, `SourceSnippet` at top of `query_engine.py`.)

- [ ] **Step 4: Attach `executed_sql` in `_sql_answer`.** Set `executed_sql=sql` on the
successful `RAGResponse`, and leave `groundedness=None` (the answer is the data; the SQL is
the evidence). Keep the safety-reject and error branches unchanged (they may omit the field).

- [ ] **Step 5: Add a grounding-attach test to `tests/test_api/test_rag.py`**

```python
async def test_narrative_answer_includes_grounding(monkeypatch):
    import econsight.rag.query_engine as qe

    async def fake_retrieve(question, top_k=5):
        return [{"title": "Inflation", "text": "Inflation eased over the quarter."}]

    class _FakeEnc:
        def encode(self, texts):
            import numpy as np
            return np.array([[1.0, 0.0] if "inflation" in t.lower() else [0.0, 1.0]
                             for t in texts])

    class _Msg:
        content = "Inflation eased steadily [1]."

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    async def fake_create(*a, **k):
        return _Resp()

    monkeypatch.setattr(qe, "retrieve", fake_retrieve)
    monkeypatch.setattr(qe._client.chat.completions, "create", fake_create)
    monkeypatch.setattr("econsight.rag.retriever.get_encoder", lambda: _FakeEnc())

    resp = await qe._narrative_answer("why did inflation change?")
    assert resp.groundedness is not None
    assert resp.grounding and resp.grounding[0].supported is True
    assert resp.source_snippets[0].chunk_id == 1
```

- [ ] **Step 6: Run — expect PASS (new + existing rag tests)**

Run: `pytest tests/test_api/test_rag.py tests/test_rag -v`

- [ ] **Step 7: Commit**

```bash
git add src/econsight/api/schemas.py src/econsight/rag/retriever.py \
        src/econsight/rag/query_engine.py tests/test_api/test_rag.py
git commit -m "feat: attach grounding evidence + executed SQL to RAG responses"
```

---

## Phase 7 — Frontend

### Task 13: API client types + fetchers

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Extend `RAGResponse` interface** with optional
`groundedness?: number | null`, `grounding?: SentenceAttribution[] | null`,
`source_snippets?: SourceSnippet[] | null`, `executed_sql?: string | null`, and add the two
new interfaces (`SentenceAttribution`, `SourceSnippet`) mirroring the Pydantic models.

- [ ] **Step 2: Add validation types + fetchers**


```typescript
export interface BacktestMetric {
  target: string
  horizon_months: number
  model_type: string
  baseline: string
  n_folds: number
  mae: number | null
  rmse: number | null
  mase: number | null
  skill_score_vs_rw: number | null
  dm_stat: number | null
  dm_pvalue: number | null
  backtest_start: string | null
  backtest_end: string | null
  low_confidence: boolean
}

export interface BacktestPredictionPoint {
  target_date: string
  model_type: string
  y_true: number
  y_pred: number
}
export interface BacktestPredictionSeries {
  target: string
  horizon_months: number
  points: BacktestPredictionPoint[]
}
export interface ValidationSummary {
  total_configs: number
  configs_beating_rw: number
  best_skill_score: number | null
  best_config: string | null
  total_folds: number
  backtest_start: string | null
  backtest_end: string | null
  low_confidence: boolean
}

export const fetchValidationMetrics = () =>
  api.get<BacktestMetric[]>('/api/validation/metrics').then(r => r.data)
export const fetchValidationSummary = () =>
  api.get<ValidationSummary>('/api/validation/summary').then(r => r.data)
export const fetchValidationPredictions = (target: string, horizon: number) =>
  api
    .get<BacktestPredictionSeries>('/api/validation/predictions', {
      params: { target, horizon },
    })
    .then(r => r.data)
```

- [ ] **Step 3: Run typecheck**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: validation + grounding client types and fetchers"
```

### Task 14: Validation page

**Files:**
- Create: `frontend/src/pages/Validation.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Build the page.** Match existing page conventions (TanStack `useQuery`,
CSS variables, shadcn `Card`, Recharts). Sections:
  - **Summary cards** from `fetchValidationSummary`: "Beats random walk on `configs_beating_rw` / `total_configs`", "Best skill `+{best_skill_score*100}%` ({best_config})", "{total_folds} folds, {start}–{end}". If `low_confidence`, show an amber "limited history" note.
  - **Metrics table** from `fetchValidationMetrics`: grouped by target/horizon, columns Model | MAE | RMSE | MASE | Skill vs RW | DM p. Cell coloring rule: green when `mase < 1 && skill_score_vs_rw > 0`, amber otherwise (naive_rw row shown as the baseline, styled neutral). Render `dm_pvalue` as `n/a` when null.
  - **Predicted-vs-actual chart**: target + horizon selector (pills like Forecasts page) → `fetchValidationPredictions`. Pivot `points` by `model_type` into a Recharts `LineChart`: actual (`y_true`, one series) + each model's `y_pred`. Emphasize actual vs random-walk vs best model.
  - **Methodology note**: plain-English paragraph — expanding-window walk-forward, MASE (<1 beats naive), skill score vs random walk, Diebold–Mariano significance, and the honest caveat: "~N monthly observations, ~M folds; DM p-values are indicative, not definitive."

  Follow the exact color-token and layout patterns already in `frontend/src/pages/Forecasts.tsx` (read it first). Keep the page a single focused file; extract a small `MetricCell` helper inside it if it grows.

- [ ] **Step 2: Wire route + nav in `App.tsx`.** Import `Validation`; add
`['/validation', 'Validation']` to `NAV_LINKS` (after Forecasts); add
`<Route path="/validation" element={<Validation />} />`.

- [ ] **Step 3: Run build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: both pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Validation.tsx frontend/src/App.tsx
git commit -m "feat: Validation page — backtest metrics, chart, methodology"
```

### Task 15: Grounding UI in Ask page

**Files:**
- Modify: `frontend/src/pages/Ask.tsx` (read it first to match its answer-panel structure)

- [ ] **Step 1: Render grounding when present.** Below each answer:
  - **Groundedness meter**: if `groundedness != null`, a bar/pill "`{Math.round(groundedness*100)}% grounded — {supportedCount}/{total} claims traceable`", colored green ≥0.8, amber 0.5–0.8, red <0.5.
  - **Sentence attribution**: render `grounding` sentences; unsupported ones get an amber left-border + a small "no strong source found" tag. Show each sentence's `best_source_title` + `similarity` on hover/expand.
  - **Source snippets**: list `source_snippets` as `[n] title — snippet`, so citation numbers in the answer map to sources.
  - **Executed SQL**: if `executed_sql`, a collapsible `<details>` "How this was computed" showing the query in a `<pre>`.
  - All guarded so older/error responses (fields absent) render exactly as today.

- [ ] **Step 2: Run build + lint**

Run: `cd frontend && npm run build && npm run lint`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Ask.tsx
git commit -m "feat: grounding meter, citations, and executed-SQL in Ask page"
```

---

## Phase 8 — Verification & docs

### Task 16: Full backend suite + optional live smoke

**Files:** none (verification)

- [ ] **Step 1: Run the entire backend suite**

Run: `pytest -q`
Expected: all pass (new + existing).

- [ ] **Step 2 (optional, if a live DB + seeded marts are available): real backtest smoke**

Run: `python -m econsight.models.backtest`
Then check row counts via `python -c "import asyncio; ..."` or the `/api/validation/summary`
endpoint. Record the real fold count and whether any model beats random walk — this is the
number that goes in the UI methodology note. **Report the honest result even if XGB/VAR do
NOT beat the random walk** (that is itself a credible finding for macro series).

- [ ] **Step 3: Frontend production build**

Run: `cd frontend && npm run build`
Expected: succeeds.

### Task 17: Docs & session state

**Files:**
- Modify: `tasks/session_state.md`, `tasks/todo.md`; create/append `tasks/lessons.md` if any
  correction arose during execution.

- [ ] **Step 1: Update `tasks/todo.md`** with a Review section summarizing what was built and
the honest backtest outcome (fold count, which configs beat RW, groundedness behavior).

- [ ] **Step 2: Update `tasks/session_state.md`** — add a "Model validation & RAG grounding"
subsection under the current phase with the new endpoints, tables, and page.

- [ ] **Step 3: Commit**

```bash
git add tasks/
git commit -m "docs: record evaluation & grounding work in session state"
```

---

## Definition of Done

- [ ] `pytest -q` green (metrics, engine no-look-ahead, validation API, grounding).
- [ ] `cd frontend && npm run build && npm run lint` green.
- [ ] `/api/validation/{metrics,predictions,summary}` return real data after a seed.
- [ ] Validation page shows the metrics table (honest green/amber), predicted-vs-actual
  chart, and methodology + data-window caveat.
- [ ] Ask page shows groundedness meter, citations, unsupported-claim flags, and executed
  SQL, degrading gracefully when fields are absent.
- [ ] The real backtest result is reported honestly, including cases where a model does not
  beat the random walk.
