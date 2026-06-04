# EconSight Phase 2 — Econometric Modelling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested `econsight.models` Python package that trains VAR/VECM and XGBoost models, computes SHAP explainability, runs Monte Carlo simulations, and produces a composite economic health score — writing forecasts and scores back to PostgreSQL and rendering a Jupyter analysis report to HTML.

**Architecture:** Vertical slice — feature engineering and XGBoost first (most testable), then VAR, Monte Carlo, composite score, and finally the forecaster orchestrator that wires everything together and persists to DB. Notebook is written last, importing exclusively from the models package. All unit tests use synthetic DataFrames; no live DB required.

**Tech Stack:** Python 3.11, statsmodels 0.14, xgboost 2.0, shap 0.44, scikit-learn 1.4, pandas 2.1, matplotlib 3.8, seaborn 0.13, psycopg 3, joblib, pytest, ruff, mypy

**Spec:** `docs/superpowers/specs/2026-06-04-phase2-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Add 7 new runtime deps + 2 dev deps |
| `.gitignore` | Ignore `models/artefacts/`, `notebooks/phase2_report.html`, `.ipynb_checkpoints/` |
| `src/econsight/models/__init__.py` | Empty package marker |
| `src/econsight/models/features.py` | `load_mart()` (async DB read) + `build_feature_matrix()` (pure feature engineering) |
| `src/econsight/models/var_model.py` | `VARModel` — Johansen test → VAR or VECM, predict at horizons 1 and 3 |
| `src/econsight/models/xgb_model.py` | `XGBForecastModel`, `ModelMetrics` dataclass; `TARGETS`/`HORIZONS` constants |
| `src/econsight/models/shap_analysis.py` | `compute_shap_summary()` + `SHAPSummary` dataclass |
| `src/econsight/models/monte_carlo.py` | `simulate()` + `SimulationResult` dataclass — residual bootstrap |
| `src/econsight/models/composite.py` | `CompositeScorer` — z-score + PCA → 0–100 economic health score |
| `src/econsight/models/forecaster.py` | `run_models()` orchestrator + `upsert_forecasts()` + `upsert_health_scores()` |
| `src/econsight/db/schema.sql` | Add DDL for `marts.model_forecasts` + `marts.economic_health_score` |
| `notebooks/phase2_analysis.ipynb` | 7-section analysis report; imports from `econsight.models.*` only |
| `notebooks/render.py` | Execute notebook + export to HTML via nbconvert |
| `tests/test_models/__init__.py` | Empty |
| `tests/test_models/test_features.py` | Lag correctness, no NaN, row-count reduction, load_mart columns |
| `tests/test_models/test_var_model.py` | Interface contract — mocked statsmodels |
| `tests/test_models/test_xgb_model.py` | Fit/predict/SHAP-shape, no leakage, metrics types |
| `tests/test_models/test_monte_carlo.py` | p10≤p50≤p90, scenario keys, band keys, n_sims |
| `tests/test_models/test_composite.py` | Score in [0,100], 10 component keys, fit/score interface |

---

## Shared Test Fixture

The following helper is used across multiple test files. Define it in each test file that needs it (do NOT add a conftest entry — keeps test files self-contained):

```python
import numpy as np
import pandas as pd
from datetime import date


def make_macro_df(n: int = 30) -> pd.DataFrame:
    """Synthetic DataFrame matching load_mart() output — 9 raw indicator columns."""
    rng = np.random.default_rng(42)
    dates = [date(2015 + i // 12, i % 12 + 1, 1) for i in range(n)]
    return pd.DataFrame(
        {
            "gdp":               rng.uniform(2_000_000, 2_600_000, n),
            "cpi":               rng.uniform(120.0, 170.0, n),
            "unemployment_rate": rng.uniform(5.0, 10.0, n),
            "ippi":              rng.uniform(90.0, 130.0, n),
            "retail_trade":      rng.uniform(50_000, 70_000, n),
            "overnight_rate":    rng.uniform(0.25, 5.0, n),
            "cadusd":            rng.uniform(0.70, 0.85, n),
            "bond_10yr":         rng.uniform(0.5, 4.0, n),
            "m2pp":              rng.uniform(1_800_000, 2_500_000, n),
        },
        index=dates,
    )
```

Column naming convention used by `build_feature_matrix()`:
- Lags: `{col}_lag1`, `{col}_lag2`, `{col}_lag3`, `{col}_lag6`, `{col}_lag12`
- Rolling mean: `{col}_roll3`, `{col}_roll6`
- First diff: `{col}_diff`
- YoY: `{col}_yoy`

---

## Task 1: Dependencies and Directory Scaffolding

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `src/econsight/models/__init__.py`
- Create: `tests/test_models/__init__.py`
- Create: `models/artefacts/.gitkeep`
- Create: `notebooks/.gitkeep`

- [ ] **Step 1: Update `pyproject.toml`**

Replace the `dependencies` and `dev` blocks:

```toml
dependencies = [
    "httpx>=0.27",
    "tenacity>=8.3",
    "psycopg[binary]>=3.1",
    "pydantic-settings>=2.3",
    "structlog>=24.1",
    "rich>=13.0",
    "statsmodels>=0.14",
    "xgboost>=2.0",
    "shap>=0.44",
    "scikit-learn>=1.4",
    "pandas>=2.1",
    "matplotlib>=3.8",
    "seaborn>=0.13",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "ruff>=0.4",
    "mypy>=1.10",
    "jupyter>=1.0",
    "nbconvert>=7.0",
]
```

- [ ] **Step 2: Update `.gitignore`**

Add these lines to `.gitignore`:

```
models/artefacts/
notebooks/phase2_report.html
.ipynb_checkpoints/
```

- [ ] **Step 3: Create directories and empty init files**

```bash
mkdir -p "src/econsight/models" "tests/test_models" "models/artefacts" "notebooks"
touch "src/econsight/models/__init__.py"
touch "tests/test_models/__init__.py"
touch "models/artefacts/.gitkeep"
touch "notebooks/.gitkeep"
```

- [ ] **Step 4: Install new dependencies**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pip install -e ".[dev]" 2>&1 | tail -5
```

Expected: `Successfully installed ...` or `already satisfied` for all packages

- [ ] **Step 5: Verify imports work**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -c "
import statsmodels; import xgboost; import shap; import sklearn; import pandas; import matplotlib; import seaborn
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 6: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add pyproject.toml .gitignore src/econsight/models/__init__.py tests/test_models/__init__.py models/artefacts/.gitkeep notebooks/.gitkeep
git commit -m "feat: add Phase 2 dependencies and models/ package scaffold"
```

---

## Task 2: Feature Engineering

**Files:**
- Create: `src/econsight/models/features.py`
- Create: `tests/test_models/test_features.py`

- [ ] **Step 1: Write failing tests — `tests/test_models/test_features.py`**

```python
import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest

from econsight.models.features import build_feature_matrix, load_mart


def make_macro_df(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = [date(2015 + i // 12, i % 12 + 1, 1) for i in range(n)]
    return pd.DataFrame(
        {
            "gdp":               rng.uniform(2_000_000, 2_600_000, n),
            "cpi":               rng.uniform(120.0, 170.0, n),
            "unemployment_rate": rng.uniform(5.0, 10.0, n),
            "ippi":              rng.uniform(90.0, 130.0, n),
            "retail_trade":      rng.uniform(50_000, 70_000, n),
            "overnight_rate":    rng.uniform(0.25, 5.0, n),
            "cadusd":            rng.uniform(0.70, 0.85, n),
            "bond_10yr":         rng.uniform(0.5, 4.0, n),
            "m2pp":              rng.uniform(1_800_000, 2_500_000, n),
        },
        index=dates,
    )


def test_lag_columns_exist() -> None:
    X = build_feature_matrix(make_macro_df(30))
    for col in ["cpi", "overnight_rate"]:
        for lag in [1, 2, 3, 6, 12]:
            assert f"{col}_lag{lag}" in X.columns


def test_rolling_columns_exist() -> None:
    X = build_feature_matrix(make_macro_df(30))
    for col in ["cpi", "gdp"]:
        assert f"{col}_roll3" in X.columns
        assert f"{col}_roll6" in X.columns


def test_diff_and_yoy_columns_exist() -> None:
    X = build_feature_matrix(make_macro_df(30))
    assert "cpi_diff" in X.columns
    assert "cpi_yoy" in X.columns


def test_no_nan_in_output() -> None:
    X = build_feature_matrix(make_macro_df(30))
    assert not X.isnull().any().any(), "Feature matrix must not contain NaN"


def test_rows_dropped_for_lag_window() -> None:
    df = make_macro_df(30)
    X = build_feature_matrix(df)
    # lag-12 is the longest — at least 12 rows must be dropped
    assert len(X) <= len(df) - 12


def test_lag1_value_correct() -> None:
    df = make_macro_df(20)
    X = build_feature_matrix(df)
    # First kept row's lag-1 cpi should equal cpi from the row just before it in df
    first_kept = X.index[0]
    pos_in_df = list(df.index).index(first_kept)
    expected = float(df["cpi"].iloc[pos_in_df - 1])
    assert abs(float(X.loc[first_kept, "cpi_lag1"]) - expected) < 1e-9


def test_diff_value_correct() -> None:
    df = make_macro_df(20)
    X = build_feature_matrix(df)
    first_kept = X.index[0]
    pos = list(df.index).index(first_kept)
    expected = float(df["cpi"].iloc[pos]) - float(df["cpi"].iloc[pos - 1])
    assert abs(float(X.loc[first_kept, "cpi_diff"]) - expected) < 1e-9


async def test_load_mart_returns_correct_columns() -> None:
    """load_mart() returns DataFrame with 9 indicator columns and date index."""
    mock_conn = MagicMock()
    mock_cur = AsyncMock()
    mock_cur.description = [
        (col,) for col in [
            "period_date", "gdp", "cpi", "unemployment_rate", "ippi",
            "retail_trade", "overnight_rate", "cadusd", "bond_10yr", "m2pp",
        ]
    ]
    mock_cur.fetchall = AsyncMock(return_value=[
        (date(2020, 1, 1), 2_100_000.0, 136.0, 5.8, 110.0, 57_000.0, 1.75, 0.74, 1.44, 1_950_000.0),
        (date(2020, 2, 1), 2_110_000.0, 136.5, 5.7, 111.0, 58_000.0, 1.75, 0.75, 1.46, 1_960_000.0),
    ])
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

    df = await load_mart(mock_conn)

    expected_cols = {"gdp", "cpi", "unemployment_rate", "ippi", "retail_trade",
                     "overnight_rate", "cadusd", "bond_10yr", "m2pp"}
    assert set(df.columns) == expected_cols
    assert len(df) == 2
    assert isinstance(df.index[0], date)
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_models/test_features.py -v 2>&1 | tail -10
```

Expected: `ImportError` — `features.py` doesn't exist yet

- [ ] **Step 3: Write `src/econsight/models/features.py`**

```python
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import psycopg

_RAW_COLS = [
    "gdp", "cpi", "unemployment_rate", "ippi", "retail_trade",
    "overnight_rate", "cadusd", "bond_10yr", "m2pp",
]

_SQL = """
    SELECT period_date, gdp, cpi, unemployment_rate, ippi, retail_trade,
           overnight_rate, cadusd, bond_10yr, m2pp
    FROM marts.mart_monthly_macro_indicators
    WHERE data_complete = TRUE
    ORDER BY period_date ASC
"""


async def load_mart(conn: psycopg.AsyncConnection[Any]) -> pd.DataFrame:
    async with conn.cursor() as cur:
        await cur.execute(_SQL)
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]  # type: ignore[union-attr]
    df = pd.DataFrame(rows, columns=cols)
    df["period_date"] = df["period_date"].apply(
        lambda v: v if isinstance(v, date) else v.date()
    )
    df = df.set_index("period_date").sort_index()
    return df[_RAW_COLS]


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build ~90-column feature matrix from 9-column raw indicator DataFrame."""
    frames: list[pd.DataFrame] = [df.copy()]

    for col in _RAW_COLS:
        s = df[col]
        # Lags
        for lag in [1, 2, 3, 6, 12]:
            frames.append(s.shift(lag).rename(f"{col}_lag{lag}").to_frame())
        # Rolling means
        for window in [3, 6]:
            frames.append(
                s.shift(1).rolling(window).mean().rename(f"{col}_roll{window}").to_frame()
            )
        # First difference
        frames.append(s.diff().rename(f"{col}_diff").to_frame())
        # YoY change
        frames.append(
            ((s - s.shift(12)) / s.shift(12).abs() * 100).rename(f"{col}_yoy").to_frame()
        )

    X = pd.concat(frames, axis=1)
    X = X.dropna()
    return X
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_models/test_features.py -v 2>&1
```

Expected: all PASS

- [ ] **Step 5: Lint and type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/econsight/models/features.py tests/test_models/test_features.py
.venv/bin/python -m mypy src/econsight/models/features.py
```

Fix any issues.

- [ ] **Step 6: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/models/features.py tests/test_models/test_features.py
git commit -m "feat: feature engineering — load_mart() and build_feature_matrix()"
```

---

## Task 3: XGBoost Model

**Files:**
- Create: `src/econsight/models/xgb_model.py` (includes `TARGETS`, `HORIZONS`, `ModelMetrics`)
- Create: `tests/test_models/test_xgb_model.py`

Note: `TARGETS` and `HORIZONS` are defined in `xgb_model.py` (not `forecaster.py`) to avoid a circular import — `forecaster.py` imports both `XGBForecastModel` and these constants from `xgb_model.py`.

- [ ] **Step 1: Write failing tests — `tests/test_models/test_xgb_model.py`**

```python
from datetime import date

import numpy as np
import pandas as pd
import pytest

from econsight.models.features import build_feature_matrix
from econsight.models.xgb_model import (
    HORIZONS,
    TARGETS,
    ModelMetrics,
    XGBForecastModel,
)


def make_macro_df(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = [date(2015 + i // 12, i % 12 + 1, 1) for i in range(n)]
    return pd.DataFrame(
        {
            "gdp":               rng.uniform(2_000_000, 2_600_000, n),
            "cpi":               rng.uniform(120.0, 170.0, n),
            "unemployment_rate": rng.uniform(5.0, 10.0, n),
            "ippi":              rng.uniform(90.0, 130.0, n),
            "retail_trade":      rng.uniform(50_000, 70_000, n),
            "overnight_rate":    rng.uniform(0.25, 5.0, n),
            "cadusd":            rng.uniform(0.70, 0.85, n),
            "bond_10yr":         rng.uniform(0.5, 4.0, n),
            "m2pp":              rng.uniform(1_800_000, 2_500_000, n),
        },
        index=dates,
    )


def make_aligned_Xy(target: str = "cpi", horizon: int = 1, n: int = 30) -> tuple[pd.DataFrame, pd.Series]:
    df = make_macro_df(n)
    X = build_feature_matrix(df)
    y = df[target].shift(-horizon).dropna()
    # align: X rows that have a corresponding future y value
    common_idx = X.index.intersection(y.index)
    return X.loc[common_idx], y.loc[common_idx]


def test_targets_and_horizons_constants() -> None:
    assert TARGETS == ["cpi", "unemployment_rate", "overnight_rate"]
    assert HORIZONS == [1, 3]


def test_fit_returns_model_metrics() -> None:
    X, y = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    metrics = model.fit(X, y)
    assert isinstance(metrics, ModelMetrics)
    assert metrics.target == "cpi"
    assert metrics.horizon == 1
    assert np.isfinite(metrics.train_rmse)
    assert np.isfinite(metrics.test_rmse)
    assert metrics.train_rmse >= 0
    assert metrics.test_rmse >= 0


def test_predict_returns_float() -> None:
    X, y = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    model.fit(X, y)
    result = model.predict(X)
    assert isinstance(result, float)
    assert np.isfinite(result)


def test_predict_uses_last_row() -> None:
    """predict() uses X.iloc[-1] internally — calling with a 1-row slice gives same result."""
    X, y = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    model.fit(X, y)
    result_full = model.predict(X)
    result_last = model.predict(X.iloc[[-1]])
    assert result_full == result_last


def test_shap_values_shape() -> None:
    X, y = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    model.fit(X, y)
    shap_vals = model.shap_values(X)
    assert shap_vals.shape == (len(X), X.shape[1])


def test_no_data_leakage_alignment() -> None:
    """X_aligned and y must have equal length — no future data in features."""
    df = make_macro_df(30)
    X = build_feature_matrix(df)
    for h in [1, 3]:
        y = df["cpi"].shift(-h).dropna()
        common = X.index.intersection(y.index)
        assert len(common) == len(y), f"Leakage for horizon {h}"


def test_save_load_roundtrip(tmp_path: object) -> None:
    from pathlib import Path
    X, y = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    model.fit(X, y)
    path = Path(str(tmp_path)) / "xgb_cpi_h1.pkl"
    model.save(path)
    loaded = XGBForecastModel(target="cpi", horizon=1)
    loaded.load(path)
    assert loaded.predict(X) == model.predict(X)


def test_raises_if_predict_before_fit() -> None:
    X, _ = make_aligned_Xy("cpi", 1)
    model = XGBForecastModel(target="cpi", horizon=1)
    with pytest.raises(RuntimeError, match="fit"):
        model.predict(X)
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_models/test_xgb_model.py -v 2>&1 | tail -10
```

Expected: `ImportError` — `xgb_model.py` doesn't exist

- [ ] **Step 3: Write `src/econsight/models/xgb_model.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

TARGETS: list[str] = ["cpi", "unemployment_rate", "overnight_rate"]
HORIZONS: list[int] = [1, 3]


@dataclass
class ModelMetrics:
    target: str
    horizon: int
    train_rmse: float
    test_rmse: float
    train_mae: float
    test_mae: float


class XGBForecastModel:
    def __init__(self, target: str, horizon: int) -> None:
        self.target = target
        self.horizon = horizon
        self._model: XGBRegressor | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ModelMetrics:
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        self._model = XGBRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
            n_jobs=-1,
        )
        self._model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

        train_pred = self._model.predict(X_train)
        test_pred = self._model.predict(X_test)

        return ModelMetrics(
            target=self.target,
            horizon=self.horizon,
            train_rmse=float(np.sqrt(mean_squared_error(y_train, train_pred))),
            test_rmse=float(np.sqrt(mean_squared_error(y_test, test_pred))),
            train_mae=float(mean_absolute_error(y_train, train_pred)),
            test_mae=float(mean_absolute_error(y_test, test_pred)),
        )

    def predict(self, X: pd.DataFrame) -> float:
        if self._model is None:
            raise RuntimeError("Call fit() before predict()")
        return float(self._model.predict(X.iloc[[-1]])[0])

    def shap_values(self, X: pd.DataFrame) -> np.ndarray[Any, Any]:
        if self._model is None:
            raise RuntimeError("Call fit() before shap_values()")
        explainer = shap.TreeExplainer(self._model)
        return np.array(explainer.shap_values(X))

    def save(self, path: Path) -> None:
        joblib.dump(self._model, path)

    def load(self, path: Path) -> None:
        self._model = joblib.load(path)
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_models/test_xgb_model.py -v 2>&1
```

Expected: all PASS

- [ ] **Step 5: Lint and type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/econsight/models/xgb_model.py tests/test_models/test_xgb_model.py
.venv/bin/python -m mypy src/econsight/models/xgb_model.py
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/models/xgb_model.py tests/test_models/test_xgb_model.py
git commit -m "feat: XGBoost forecast model — 6 models (3 targets × 2 horizons), SHAP, save/load"
```

---

## Task 4: SHAP Analysis

**Files:**
- Create: `src/econsight/models/shap_analysis.py`

No separate test file — SHAP is already tested via `test_shap_values_shape` in `test_xgb_model.py`. This task just wraps the raw SHAP array into a structured `SHAPSummary` dataclass for clean notebook consumption.

- [ ] **Step 1: Write `src/econsight/models/shap_analysis.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from econsight.models.xgb_model import XGBForecastModel


@dataclass
class SHAPSummary:
    values: np.ndarray       # shape: (n_samples, n_features)
    mean_abs: dict[str, float]     # feature → mean |SHAP value|
    top_features: list[str]        # top-10 features by mean |SHAP value|


def compute_shap_summary(model: XGBForecastModel, X: pd.DataFrame) -> SHAPSummary:
    raw = model.shap_values(X)
    mean_abs = {
        col: float(np.abs(raw[:, i]).mean())
        for i, col in enumerate(X.columns)
    }
    top_features = sorted(mean_abs, key=lambda k: mean_abs[k], reverse=True)[:10]
    return SHAPSummary(values=raw, mean_abs=mean_abs, top_features=top_features)
```

- [ ] **Step 2: Smoke-test the import**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -c "from econsight.models.shap_analysis import compute_shap_summary, SHAPSummary; print('OK')"
```

- [ ] **Step 3: Lint and type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/econsight/models/shap_analysis.py
.venv/bin/python -m mypy src/econsight/models/shap_analysis.py
```

- [ ] **Step 4: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/models/shap_analysis.py
git commit -m "feat: SHAP summary wrapper — SHAPSummary dataclass and compute_shap_summary()"
```

---

## Task 5: VAR/VECM Model

**Files:**
- Create: `src/econsight/models/var_model.py`
- Create: `tests/test_models/test_var_model.py`

Tests mock statsmodels to avoid degenerate results on synthetic data. They verify the interface contract (output shape/types), not statistical correctness.

- [ ] **Step 1: Write failing tests — `tests/test_models/test_var_model.py`**

```python
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from econsight.models.var_model import VARModel

_TARGET_COLS = ["cpi", "unemployment_rate", "overnight_rate"]


def make_target_df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = [date(2015 + i // 12, i % 12 + 1, 1) for i in range(n)]
    return pd.DataFrame(
        {
            "cpi":               rng.uniform(120.0, 170.0, n),
            "unemployment_rate": rng.uniform(5.0, 10.0, n),
            "overnight_rate":    rng.uniform(0.25, 5.0, n),
        },
        index=dates,
    )


def _patch_statsmodels(mock_forecast: np.ndarray) -> tuple:
    """Return context managers that mock the Johansen test and VAR fitting."""
    johansen_patch = patch("econsight.models.var_model.coint_johansen")
    var_patch = patch("econsight.models.var_model.VAR")

    mock_johansen_result = MagicMock()
    # lr1 below cvt → no cointegration → VAR path
    mock_johansen_result.lr1 = np.array([1.0, 0.5, 0.2])
    mock_johansen_result.cvt = np.array([[10.0] * 3] * 3)

    mock_fit_result = MagicMock()
    mock_fit_result.k_ar = 2
    mock_fit_result.endog = np.zeros((60, 3))
    mock_fit_result.forecast.return_value = mock_forecast

    mock_var_instance = MagicMock()
    mock_var_instance.fit.return_value = mock_fit_result

    return johansen_patch, var_patch, mock_johansen_result, mock_var_instance


def test_predict_returns_correct_structure() -> None:
    """predict() returns {1: {...}, 3: {...}} with all three target keys."""
    df = make_target_df()
    # forecast array: 3 steps × 3 variables
    mock_forecast = np.array([[130.0, 6.5, 2.0], [131.0, 6.6, 2.1], [132.0, 6.7, 2.2]])

    johansen_p, var_p, mock_j, mock_v = _patch_statsmodels(mock_forecast)
    with johansen_p as mj, var_p as mv:
        mj.return_value = mock_j
        mv.return_value = mock_v
        model = VARModel()
        model.fit(df)
        result = model.predict(horizons=[1, 3])

    assert set(result.keys()) == {1, 3}
    for h in [1, 3]:
        assert set(result[h].keys()) == set(_TARGET_COLS)
        for v in result[h].values():
            assert isinstance(v, float)


def test_predict_values_match_forecast_array() -> None:
    """predict() extracts correct rows from the statsmodels forecast array."""
    df = make_target_df()
    mock_forecast = np.array([[130.0, 6.5, 2.0], [131.0, 6.6, 2.1], [132.0, 6.7, 2.2]])

    johansen_p, var_p, mock_j, mock_v = _patch_statsmodels(mock_forecast)
    with johansen_p as mj, var_p as mv:
        mj.return_value = mock_j
        mv.return_value = mock_v
        model = VARModel()
        model.fit(df)
        result = model.predict(horizons=[1, 3])

    # horizon=1 → row index 0 of forecast array
    assert result[1]["cpi"] == pytest.approx(130.0)
    assert result[1]["unemployment_rate"] == pytest.approx(6.5)
    # horizon=3 → row index 2
    assert result[3]["cpi"] == pytest.approx(132.0)


def test_raises_if_predict_before_fit() -> None:
    model = VARModel()
    with pytest.raises(RuntimeError, match="fit"):
        model.predict(horizons=[1])


def test_save_load_roundtrip(tmp_path: Path) -> None:
    df = make_target_df()
    mock_forecast = np.array([[130.0, 6.5, 2.0], [131.0, 6.6, 2.1], [132.0, 6.7, 2.2]])

    johansen_p, var_p, mock_j, mock_v = _patch_statsmodels(mock_forecast)
    with johansen_p as mj, var_p as mv:
        mj.return_value = mock_j
        mv.return_value = mock_v
        model = VARModel()
        model.fit(df)

    path = tmp_path / "var_model.pkl"
    model.save(path)
    loaded = VARModel()
    loaded.load(path)
    assert loaded._fitted_model is not None
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_models/test_var_model.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Write `src/econsight/models/var_model.py`**

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen

_TARGET_COLS = ["cpi", "unemployment_rate", "overnight_rate"]
_MAX_LAG = 6
_SIGNIFICANCE = 0.05  # use 5% critical values (index 1 in cvt)


class VARModel:
    def __init__(self) -> None:
        self._fitted_model: Any = None
        self._model_type: str | None = None  # "var" or "vecm"
        self._col_order: list[str] = _TARGET_COLS

    def fit(self, df: pd.DataFrame) -> None:
        data = df[_TARGET_COLS].dropna()
        johansen = coint_johansen(data.values, det_order=0, k_ar_diff=1)
        # Count cointegrating relations at 5% level
        n_coint = int(
            np.sum(johansen.lr1 > johansen.cvt[:, 1])
        )
        if n_coint > 0:
            self._model_type = "vecm"
            model = VECM(data, k_ar_diff=1, coint_rank=n_coint, deterministic="ci")
            self._fitted_model = model.fit()
        else:
            self._model_type = "var"
            model = VAR(data.diff().dropna())
            lag_order = model.select_order(maxlags=_MAX_LAG).aic
            lag_order = min(max(lag_order, 1), _MAX_LAG)
            self._fitted_model = model.fit(lag_order)

    def predict(self, horizons: list[int]) -> dict[int, dict[str, float]]:
        if self._fitted_model is None:
            raise RuntimeError("Call fit() before predict()")
        max_h = max(horizons)
        if self._model_type == "var":
            # Feed last k_ar observations as the initial condition
            k_ar = self._fitted_model.k_ar
            last_obs = self._fitted_model.endog[-k_ar:]
            raw = self._fitted_model.forecast(last_obs, steps=max_h)
        else:
            raw = self._fitted_model.predict(steps=max_h)

        result: dict[int, dict[str, float]] = {}
        for h in horizons:
            row = raw[h - 1]  # horizon h → row index h-1
            result[h] = {col: float(row[i]) for i, col in enumerate(_TARGET_COLS)}
        return result

    def save(self, path: Path) -> None:
        joblib.dump({"model": self._fitted_model, "type": self._model_type}, path)

    def load(self, path: Path) -> None:
        data = joblib.load(path)
        self._fitted_model = data["model"]
        self._model_type = data["type"]
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_models/test_var_model.py -v 2>&1
```

- [ ] **Step 5: Lint and type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/econsight/models/var_model.py tests/test_models/test_var_model.py
.venv/bin/python -m mypy src/econsight/models/var_model.py
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/models/var_model.py tests/test_models/test_var_model.py
git commit -m "feat: VAR/VECM model — Johansen cointegration test, AIC lag selection, save/load"
```

---

## Task 6: Monte Carlo Simulation

**Files:**
- Create: `src/econsight/models/monte_carlo.py`
- Create: `tests/test_models/test_monte_carlo.py`

- [ ] **Step 1: Write failing tests — `tests/test_models/test_monte_carlo.py`**

```python
from datetime import date

import numpy as np
import pandas as pd
import pytest

from econsight.models.features import build_feature_matrix
from econsight.models.monte_carlo import SimulationResult, simulate
from econsight.models.xgb_model import HORIZONS, TARGETS, XGBForecastModel


def make_macro_df(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = [date(2015 + i // 12, i % 12 + 1, 1) for i in range(n)]
    return pd.DataFrame(
        {
            "gdp":               rng.uniform(2_000_000, 2_600_000, n),
            "cpi":               rng.uniform(120.0, 170.0, n),
            "unemployment_rate": rng.uniform(5.0, 10.0, n),
            "ippi":              rng.uniform(90.0, 130.0, n),
            "retail_trade":      rng.uniform(50_000, 70_000, n),
            "overnight_rate":    rng.uniform(0.25, 5.0, n),
            "cadusd":            rng.uniform(0.70, 0.85, n),
            "bond_10yr":         rng.uniform(0.5, 4.0, n),
            "m2pp":              rng.uniform(1_800_000, 2_500_000, n),
        },
        index=dates,
    )


@pytest.fixture(scope="module")
def fitted_models() -> dict:
    df = make_macro_df(30)
    X = build_feature_matrix(df)
    models = {}
    for target in TARGETS:
        for h in HORIZONS:
            y = df[target].shift(-h).dropna()
            common = X.index.intersection(y.index)
            model = XGBForecastModel(target=target, horizon=h)
            model.fit(X.loc[common], y.loc[common])
            models[(target, h)] = model
    return {"X": X, "models": models}


def test_simulation_result_has_correct_band_keys(fitted_models: dict) -> None:
    sim = simulate(fitted_models["models"], fitted_models["X"], n_sims=50)
    expected_keys = {(t, h) for t in TARGETS for h in HORIZONS}
    assert set(sim.bands.keys()) == expected_keys


def test_percentile_ordering(fitted_models: dict) -> None:
    sim = simulate(fitted_models["models"], fitted_models["X"], n_sims=50)
    for key, band in sim.bands.items():
        assert band["p10"] <= band["p50"] <= band["p90"], (
            f"Percentile ordering violated for {key}"
        )


def test_scenario_keys_present(fitted_models: dict) -> None:
    sim = simulate(fitted_models["models"], fitted_models["X"], n_sims=50)
    assert set(sim.scenarios.keys()) == {"base", "upside", "downside"}


def test_scenario_targets_present(fitted_models: dict) -> None:
    sim = simulate(fitted_models["models"], fitted_models["X"], n_sims=50)
    for scenario in sim.scenarios.values():
        assert set(scenario.keys()) == set(TARGETS)


def test_simulation_result_is_dataclass() -> None:
    from dataclasses import fields
    field_names = {f.name for f in fields(SimulationResult)}
    assert "bands" in field_names
    assert "scenarios" in field_names
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_models/test_monte_carlo.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Write `src/econsight/models/monte_carlo.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from econsight.models.xgb_model import HORIZONS, TARGETS, XGBForecastModel


@dataclass
class SimulationResult:
    # keyed by (target, horizon); each value has p10/p50/p90
    bands: dict[tuple[str, int], dict[str, float]]
    # keyed by "base"/"upside"/"downside"; derived from 3-month horizon
    scenarios: dict[str, dict[str, float]]


def simulate(
    models: dict[tuple[str, int], XGBForecastModel],
    X: pd.DataFrame,
    n_sims: int = 1000,
) -> SimulationResult:
    rng = np.random.default_rng(42)
    bands: dict[tuple[str, int], dict[str, float]] = {}

    for target in TARGETS:
        for h in HORIZONS:
            model = models[(target, h)]
            point = model.predict(X)
            # Compute in-sample residuals using the full X
            in_sample = np.array([
                float(model._model.predict(X.iloc[[i]])[0])  # type: ignore[union-attr]
                for i in range(len(X))
            ])
            residuals = in_sample - in_sample.mean()
            if len(residuals) == 0:
                residuals = np.array([0.0])
            sampled = rng.choice(residuals, size=n_sims, replace=True)
            paths = point + sampled
            bands[(target, h)] = {
                "p10": float(np.percentile(paths, 10)),
                "p50": float(np.percentile(paths, 50)),
                "p90": float(np.percentile(paths, 90)),
            }

    # Named scenarios from 3-month horizon bands
    scenarios: dict[str, dict[str, float]] = {
        "base": {t: bands[(t, 3)]["p50"] for t in TARGETS},
        "upside": {
            "cpi":               bands[("cpi", 3)]["p10"],
            "unemployment_rate": bands[("unemployment_rate", 3)]["p10"],
            "overnight_rate":    bands[("overnight_rate", 3)]["p90"],
        },
        "downside": {
            "cpi":               bands[("cpi", 3)]["p90"],
            "unemployment_rate": bands[("unemployment_rate", 3)]["p90"],
            "overnight_rate":    bands[("overnight_rate", 3)]["p10"],
        },
    }

    return SimulationResult(bands=bands, scenarios=scenarios)
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_models/test_monte_carlo.py -v 2>&1
```

- [ ] **Step 5: Lint and type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/econsight/models/monte_carlo.py tests/test_models/test_monte_carlo.py
.venv/bin/python -m mypy src/econsight/models/monte_carlo.py
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/models/monte_carlo.py tests/test_models/test_monte_carlo.py
git commit -m "feat: Monte Carlo simulation — residual bootstrap, p10/p50/p90 bands, named scenarios"
```

---

## Task 7: Composite Economic Health Score

**Files:**
- Create: `src/econsight/models/composite.py`
- Create: `tests/test_models/test_composite.py`

- [ ] **Step 1: Write failing tests — `tests/test_models/test_composite.py`**

```python
from datetime import date

import numpy as np
import pandas as pd
import pytest

from econsight.models.composite import CompositeScorer

_EXPECTED_COMPONENT_KEYS = {
    "gdp", "cpi", "unemployment_rate", "ippi", "retail_trade",
    "overnight_rate", "cadusd", "bond_10yr", "m2pp", "yield_spread",
}


def make_macro_df(n: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = [date(2015 + i // 12, i % 12 + 1, 1) for i in range(n)]
    return pd.DataFrame(
        {
            "gdp":               rng.uniform(2_000_000, 2_600_000, n),
            "cpi":               rng.uniform(120.0, 170.0, n),
            "unemployment_rate": rng.uniform(5.0, 10.0, n),
            "ippi":              rng.uniform(90.0, 130.0, n),
            "retail_trade":      rng.uniform(50_000, 70_000, n),
            "overnight_rate":    rng.uniform(0.25, 5.0, n),
            "cadusd":            rng.uniform(0.70, 0.85, n),
            "bond_10yr":         rng.uniform(0.5, 4.0, n),
            "m2pp":              rng.uniform(1_800_000, 2_500_000, n),
        },
        index=dates,
    )


def test_score_in_range() -> None:
    df = make_macro_df(20)
    scorer = CompositeScorer()
    scorer.fit(df)
    result = scorer.score(df)
    assert (result["score"] >= 0).all()
    assert (result["score"] <= 100).all()


def test_score_output_has_correct_columns() -> None:
    df = make_macro_df(20)
    scorer = CompositeScorer()
    scorer.fit(df)
    result = scorer.score(df)
    assert "score" in result.columns
    assert "component_scores" in result.columns


def test_component_scores_has_10_keys() -> None:
    df = make_macro_df(20)
    scorer = CompositeScorer()
    scorer.fit(df)
    result = scorer.score(df)
    # Each row's component_scores dict must have all 10 keys
    for cs in result["component_scores"]:
        assert set(cs.keys()) == _EXPECTED_COMPONENT_KEYS


def test_score_output_length_matches_input() -> None:
    df = make_macro_df(20)
    scorer = CompositeScorer()
    scorer.fit(df)
    result = scorer.score(df)
    assert len(result) == len(df)


def test_raises_if_score_before_fit() -> None:
    scorer = CompositeScorer()
    with pytest.raises(RuntimeError, match="fit"):
        scorer.score(make_macro_df(10))


def test_save_load_roundtrip(tmp_path: object) -> None:
    from pathlib import Path
    df = make_macro_df(20)
    scorer = CompositeScorer()
    scorer.fit(df)
    path = Path(str(tmp_path)) / "scorer.pkl"
    scorer.save(path)
    loaded = CompositeScorer()
    loaded.load(path)
    original = scorer.score(df)["score"].values
    restored = loaded.score(df)["score"].values
    np.testing.assert_allclose(original, restored)
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_models/test_composite.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Write `src/econsight/models/composite.py`**

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

_RAW_COLS = [
    "gdp", "cpi", "unemployment_rate", "ippi", "retail_trade",
    "overnight_rate", "cadusd", "bond_10yr", "m2pp",
]
# Higher value = worse outcome → flip sign before PCA
_FLIP_COLS = {"cpi", "unemployment_rate", "ippi", "yield_spread"}


class CompositeScorer:
    def __init__(self) -> None:
        self._scaler: StandardScaler | None = None
        self._pca: PCA | None = None
        self._weights: np.ndarray | None = None
        self._score_min: float | None = None
        self._score_max: float | None = None

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df[_RAW_COLS].copy()
        data["yield_spread"] = data["bond_10yr"] - data["overnight_rate"]
        for col in _FLIP_COLS:
            data[col] = -data[col]
        return data

    def fit(self, df: pd.DataFrame) -> None:
        data = self._prepare(df)
        self._scaler = StandardScaler()
        scaled = self._scaler.fit_transform(data)
        self._pca = PCA(n_components=1, random_state=42)
        scores_raw = self._pca.fit_transform(scaled).ravel()
        self._weights = self._pca.components_[0]
        self._score_min = float(scores_raw.min())
        self._score_max = float(scores_raw.max())

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        if self._scaler is None or self._pca is None:
            raise RuntimeError("Call fit() before score()")
        data = self._prepare(df)
        scaled = self._scaler.transform(data)
        raw_scores = self._pca.transform(scaled).ravel()
        # Rescale to 0–100 using fit-time min/max
        denom = (self._score_max - self._score_min) or 1.0
        scores_100 = (raw_scores - self._score_min) / denom * 100.0
        scores_100 = np.clip(scores_100, 0.0, 100.0)

        col_names = list(data.columns)
        component_scores = [
            {
                col: float(scaled[i, j] * self._weights[j])
                for j, col in enumerate(col_names)
            }
            for i in range(len(df))
        ]
        return pd.DataFrame(
            {"score": scores_100, "component_scores": component_scores},
            index=df.index,
        )

    def save(self, path: Path) -> None:
        joblib.dump(
            {
                "scaler": self._scaler,
                "pca": self._pca,
                "weights": self._weights,
                "score_min": self._score_min,
                "score_max": self._score_max,
            },
            path,
        )

    def load(self, path: Path) -> None:
        data: dict[str, Any] = joblib.load(path)
        self._scaler = data["scaler"]
        self._pca = data["pca"]
        self._weights = data["weights"]
        self._score_min = data["score_min"]
        self._score_max = data["score_max"]
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_models/test_composite.py -v 2>&1
```

- [ ] **Step 5: Lint and type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/econsight/models/composite.py tests/test_models/test_composite.py
.venv/bin/python -m mypy src/econsight/models/composite.py
```

- [ ] **Step 6: Run full test suite — no regressions**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest -v -m "not integration" 2>&1 | tail -20
```

- [ ] **Step 7: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/models/composite.py tests/test_models/test_composite.py
git commit -m "feat: composite economic health score — z-score + PCA → 0–100 with component contributions"
```

---

## Task 8: Database Schema

**Files:**
- Modify: `src/econsight/db/schema.sql`

Add the two new mart tables. `init_db()` already runs `schema.sql` — no code changes needed.

- [ ] **Step 1: Append to `src/econsight/db/schema.sql`**

Add the following at the end of the file:

```sql
-- marts.model_forecasts
CREATE TABLE IF NOT EXISTS marts.model_forecasts (
    id                bigserial   PRIMARY KEY,
    period_date       date        NOT NULL,
    target            text        NOT NULL,
    horizon_months    int         NOT NULL,
    model_type        text        NOT NULL,
    point_forecast    numeric     NOT NULL,
    p10               numeric,
    p50               numeric,
    p90               numeric,
    scenario_base     numeric,
    scenario_upside   numeric,
    scenario_downside numeric,
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (period_date, target, horizon_months, model_type)
);

-- marts.economic_health_score
CREATE TABLE IF NOT EXISTS marts.economic_health_score (
    period_date      date        PRIMARY KEY,
    score            numeric     NOT NULL,
    component_scores jsonb       NOT NULL,
    updated_at       timestamptz NOT NULL DEFAULT now()
);
```

- [ ] **Step 2: Apply schema to local database**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -c "import asyncio; from econsight.db.connection import init_db; asyncio.run(init_db())"
```

- [ ] **Step 3: Verify both tables exist**

```bash
PGPASSWORD=kbdbaran /Library/PostgreSQL/18/bin/psql -U postgres -h localhost econsight -c "\dt marts.*"
```

Expected: 3 tables — `mart_monthly_macro_indicators`, `model_forecasts`, `economic_health_score`

- [ ] **Step 4: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/db/schema.sql
git commit -m "feat: add model_forecasts and economic_health_score tables to schema"
```

---

## Task 9: Forecaster Orchestrator

**Files:**
- Create: `src/econsight/models/forecaster.py`

End-to-end integration — no unit tests (all components already tested). Verified by running against the live DB.

- [ ] **Step 1: Write `src/econsight/models/forecaster.py`**

```python
from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from econsight.db.connection import PROJECT_ROOT, db_connection
from econsight.models.composite import CompositeScorer
from econsight.models.features import build_feature_matrix, load_mart
from econsight.models.monte_carlo import simulate
from econsight.models.var_model import VARModel
from econsight.models.xgb_model import HORIZONS, TARGETS, XGBForecastModel

_ARTEFACTS = PROJECT_ROOT / "models" / "artefacts"

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
    conn: psycopg.AsyncConnection,
    var_forecasts: dict[int, dict[str, float]],
    xgb_models: dict[tuple[str, int], XGBForecastModel],
    X,
    sim,
) -> None:
    forecast_date = _next_month(X.index[-1])
    rows = []
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
    conn: psycopg.AsyncConnection,
    scores,
) -> None:
    rows = [
        (idx, float(row["score"]), Jsonb(row["component_scores"]))
        for idx, row in scores.iterrows()
    ]
    async with conn.cursor() as cur:
        await cur.executemany(_HEALTH_UPSERT, rows)


async def run_models() -> None:
    from econsight.config import configure_logging, get_logger

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

        # XGBoost — 6 models
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
        log.info("composite.done", latest_score=round(float(scores["score"].iloc[-1]), 1))

        # Persist
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
```

- [ ] **Step 2: Run the forecaster end-to-end**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m econsight.models.forecaster 2>&1
```

Expected: logs showing data loaded, features built, VAR done, 6 XGBoost models fitted, Monte Carlo done, composite done, DB persisted, artefacts saved.

- [ ] **Step 3: Verify DB rows**

```bash
PGPASSWORD=kbdbaran /Library/PostgreSQL/18/bin/psql -U postgres -h localhost econsight -c \
  "SELECT target, horizon_months, model_type, point_forecast, p10, p90 FROM marts.model_forecasts ORDER BY model_type, target, horizon_months;"

PGPASSWORD=kbdbaran /Library/PostgreSQL/18/bin/psql -U postgres -h localhost econsight -c \
  "SELECT period_date, score FROM marts.economic_health_score ORDER BY period_date DESC LIMIT 5;"
```

Expected: 12 forecast rows (3 targets × 2 horizons × 2 model types) and health score rows with scores in [0, 100].

- [ ] **Step 4: Lint and type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/econsight/models/forecaster.py
.venv/bin/python -m mypy src/econsight/models/forecaster.py
```

- [ ] **Step 5: Run full test suite — no regressions**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest -v -m "not integration" 2>&1 | tail -25
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/models/forecaster.py
git commit -m "feat: forecaster orchestrator — VAR + XGBoost + Monte Carlo + composite, persists to DB"
```

---

## Task 10: Notebook and Render Script

**Files:**
- Create: `notebooks/phase2_analysis.ipynb`
- Create: `notebooks/render.py`

The notebook imports exclusively from `econsight.models.*`. Each section is a separate cell group.

- [ ] **Step 1: Write `notebooks/render.py`**

```python
"""Execute phase2_analysis.ipynb and export to HTML."""
import subprocess
import sys
from pathlib import Path

NOTEBOOK = Path(__file__).parent / "phase2_analysis.ipynb"
OUTPUT = Path(__file__).parent / "phase2_report.html"


def main() -> None:
    result = subprocess.run(
        [
            sys.executable, "-m", "nbconvert",
            "--to", "html",
            "--execute",
            "--ExecutePreprocessor.timeout=300",
            "--output", str(OUTPUT),
            str(NOTEBOOK),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)
    print(f"Report saved to {OUTPUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `notebooks/phase2_analysis.ipynb`**

Create the notebook with the following cell structure (use `jupyter nbformat` format). Each section header is a Markdown cell; each code block is a Code cell:

**Cell 1 — Markdown:**
```markdown
# EconSight Phase 2 — Canadian Macroeconomic Analysis
A complete analysis of 9 Canadian macro indicators using VAR/VECM econometric models, XGBoost, SHAP explainability, Monte Carlo simulation, and a composite economic health score.
```

**Cell 2 — Code (Setup):**
```python
import asyncio
import warnings
warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import shap

from econsight.db.connection import db_connection
from econsight.models.features import load_mart, build_feature_matrix
from econsight.models.var_model import VARModel
from econsight.models.xgb_model import XGBForecastModel, TARGETS, HORIZONS
from econsight.models.shap_analysis import compute_shap_summary
from econsight.models.monte_carlo import simulate
from econsight.models.composite import CompositeScorer

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["figure.dpi"] = 120

# Load data
async def _load():
    async with db_connection() as conn:
        return await load_mart(conn)

df_raw = asyncio.run(_load())
X = build_feature_matrix(df_raw)
print(f"Loaded {len(df_raw)} months of data ({df_raw.index[0]} → {df_raw.index[-1]})")
print(f"Feature matrix: {X.shape[1]} columns, {len(X)} rows after NaN drop")
```

**Cell 3 — Markdown:**
```markdown
## 1. Data Overview
```

**Cell 4 — Code:**
```python
fig, axes = plt.subplots(3, 3, figsize=(15, 10))
axes = axes.ravel()
for i, col in enumerate(df_raw.columns):
    axes[i].plot(df_raw.index, df_raw[col])
    axes[i].set_title(col.replace("_", " ").title())
    axes[i].tick_params(axis="x", rotation=45)
plt.suptitle("Canadian Macro Indicators — Full History", fontsize=14, y=1.01)
plt.tight_layout()
plt.show()
```

**Cell 5 — Markdown:**
```markdown
## 2. Feature Correlation & Stationarity
```

**Cell 6 — Code:**
```python
from statsmodels.tsa.stattools import adfuller

# ADF stationarity test on raw indicators
print("ADF Stationarity Test (p-value < 0.05 → stationary)")
for col in df_raw.columns:
    result = adfuller(df_raw[col].dropna())
    status = "✓ stationary" if result[1] < 0.05 else "✗ non-stationary"
    print(f"  {col:<22} p={result[1]:.4f}  {status}")

# Correlation heatmap of lag features
lag_cols = [c for c in X.columns if "_lag" in c]
plt.figure(figsize=(14, 6))
sns.heatmap(X[lag_cols[:20]].corr(), cmap="RdBu_r", center=0, annot=False, linewidths=0.3)
plt.title("Lag Feature Correlation (first 20)")
plt.tight_layout()
plt.show()
```

**Cell 7 — Markdown:**
```markdown
## 3. VAR/VECM Results
```

**Cell 8 — Code:**
```python
var = VARModel()
var.fit(df_raw)
var_forecasts = var.predict(horizons=[1, 3])

print("VAR/VECM Point Forecasts")
print(f"{'Target':<22} {'1-month':>12} {'3-month':>12}")
print("-" * 48)
for target in TARGETS:
    print(f"  {target:<20} {var_forecasts[1][target]:>12.3f} {var_forecasts[3][target]:>12.3f}")

# Impulse Response Function
if var._model_type == "var":
    irf = var._fitted_model.irf(periods=12)
    irf.plot(impulse="overnight_rate", response="cpi")
    plt.suptitle("IRF: Overnight Rate shock → CPI response")
    plt.tight_layout()
    plt.show()
```

**Cell 9 — Markdown:**
```markdown
## 4. XGBoost Results
```

**Cell 10 — Code:**
```python
xgb_models = {}
all_metrics = []
for target in TARGETS:
    for h in HORIZONS:
        y = df_raw[target].shift(-h).dropna()
        common = X.index.intersection(y.index)
        model = XGBForecastModel(target=target, horizon=h)
        metrics = model.fit(X.loc[common], y.loc[common])
        xgb_models[(target, h)] = model
        all_metrics.append(metrics)

metrics_df = pd.DataFrame([
    {"target": m.target, "horizon": m.horizon,
     "train_rmse": round(m.train_rmse, 4), "test_rmse": round(m.test_rmse, 4),
     "train_mae": round(m.train_mae, 4), "test_mae": round(m.test_mae, 4)}
    for m in all_metrics
])
print(metrics_df.to_string(index=False))

# Actual vs predicted for CPI h=1
model_cpi = xgb_models[("cpi", 1)]
y_cpi = df_raw["cpi"].shift(-1).dropna()
common = X.index.intersection(y_cpi.index)
split = int(len(common) * 0.8)
test_idx = common[split:]
preds = [model_cpi.predict(X.loc[test_idx[:i+1]]) for i in range(len(test_idx))]
plt.figure(figsize=(12, 4))
plt.plot(test_idx, y_cpi.loc[test_idx].values, label="Actual")
plt.plot(test_idx, preds, label="Predicted", linestyle="--")
plt.title("CPI — Actual vs XGBoost Predicted (test set, h=1)")
plt.legend()
plt.tight_layout()
plt.show()
```

**Cell 11 — Markdown:**
```markdown
## 5. SHAP Analysis
```

**Cell 12 — Code:**
```python
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
for i, target in enumerate(TARGETS):
    model = xgb_models[(target, 1)]
    summary = compute_shap_summary(model, X)
    top = summary.top_features[:10]
    vals = [summary.mean_abs[f] for f in top]
    axes[i].barh(top[::-1], vals[::-1])
    axes[i].set_title(f"SHAP — {target} (h=1)")
    axes[i].set_xlabel("Mean |SHAP value|")
plt.suptitle("Feature Importance by SHAP", fontsize=13)
plt.tight_layout()
plt.show()
```

**Cell 13 — Markdown:**
```markdown
## 6. Monte Carlo Uncertainty
```

**Cell 14 — Code:**
```python
sim = simulate(xgb_models, X, n_sims=1000)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for i, target in enumerate(TARGETS):
    ax = axes[i]
    for h, color in [(1, "steelblue"), (3, "tomato")]:
        band = sim.bands[(target, h)]
        ax.bar([f"h={h}"], [band["p50"]], color=color, alpha=0.7,
               yerr=[[band["p50"]-band["p10"]], [band["p90"]-band["p50"]]],
               capsize=6, label=f"h={h} (p10–p90)")
    ax.set_title(target.replace("_", " ").title())
    ax.legend()
plt.suptitle("Monte Carlo: p10/p50/p90 Forecast Bands", fontsize=13)
plt.tight_layout()
plt.show()

print("\nNamed Scenarios (3-month horizon):")
print(f"{'Scenario':<12} {'CPI':>10} {'Unemployment':>14} {'Overnight':>12}")
print("-" * 50)
for name, vals in sim.scenarios.items():
    print(f"  {name:<10} {vals['cpi']:>10.3f} {vals['unemployment_rate']:>14.3f} {vals['overnight_rate']:>12.3f}")
```

**Cell 15 — Markdown:**
```markdown
## 7. Economic Health Score
```

**Cell 16 — Code:**
```python
scorer = CompositeScorer()
scorer.fit(df_raw)
scores = scorer.score(df_raw)

plt.figure(figsize=(13, 4))
plt.fill_between(scores.index, scores["score"], alpha=0.3, color="seagreen")
plt.plot(scores.index, scores["score"], color="seagreen", linewidth=1.5)
plt.axhline(50, color="gray", linestyle="--", linewidth=0.8, label="Neutral (50)")
plt.title("Economic Health Score — Canada (0=worst, 100=best)")
plt.ylabel("Score")
plt.legend()
plt.tight_layout()
plt.show()

latest = scores.iloc[-1]
print(f"\nLatest month ({scores.index[-1]}): score = {latest['score']:.1f}/100")
print("\nComponent contributions (top 5 positive):")
cs = latest["component_scores"]
for k, v in sorted(cs.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"  {k:<22}: {v:+.4f}")
```

The notebook should be saved as a valid `.ipynb` JSON file. Use `jupyter nbformat` to create it programmatically or write the JSON directly. The simplest approach is to use `nbformat`:

```python
# Run this once in a Python script to generate the notebook JSON:
import nbformat as nbf
# ... build cells as above and save
```

Or just create the file manually as a `.ipynb` — either approach is fine as long as it executes cleanly.

- [ ] **Step 3: Run the render script to verify**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python notebooks/render.py 2>&1
```

Expected: `Report saved to notebooks/phase2_report.html`

Verify: `ls -lh notebooks/phase2_report.html` — file should be > 0 bytes

- [ ] **Step 4: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add notebooks/phase2_analysis.ipynb notebooks/render.py
git commit -m "feat: Phase 2 analysis notebook — 7-section report with SHAP, Monte Carlo, health score"
```

---

## Task 11: CI Update and Final Verification

**Files:**
- No changes needed to `.github/workflows/ci.yml` — the workflow does `pip install -e ".[dev]"` which picks up all new deps automatically

- [ ] **Step 1: Run full lint**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/ tests/ 2>&1
```

Expected: no output (all clean)

- [ ] **Step 2: Run full type check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m mypy src/econsight 2>&1
```

Expected: `Success: no issues found in N source files`

- [ ] **Step 3: Run full test suite**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest -v -m "not integration" 2>&1 | tail -30
```

Expected: all PASS (25 Phase 1 tests + all Phase 2 tests)

- [ ] **Step 4: Run integration tests**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest -v -m integration 2>&1
```

Expected: 4 Phase 1 integration tests PASS

- [ ] **Step 5: Verify DB state**

```bash
PGPASSWORD=kbdbaran /Library/PostgreSQL/18/bin/psql -U postgres -h localhost econsight -c \
  "SELECT model_type, target, horizon_months, round(point_forecast, 3) AS forecast, round(p10, 3) AS p10, round(p90, 3) AS p90 FROM marts.model_forecasts ORDER BY model_type, target, horizon_months;"

PGPASSWORD=kbdbaran /Library/PostgreSQL/18/bin/psql -U postgres -h localhost econsight -c \
  "SELECT COUNT(*) AS total_months, round(MIN(score), 1) AS min_score, round(MAX(score), 1) AS max_score, round(AVG(score), 1) AS avg_score FROM marts.economic_health_score;"
```

- [ ] **Step 6: Push to GitHub**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git push origin main
```

---

## Phase 2 Complete Checklist

- [ ] `pytest -v -m "not integration"` → all unit tests PASS
- [ ] `pytest -v -m integration` → all 4 integration tests PASS
- [ ] `ruff check src/ tests/` → clean
- [ ] `mypy src/econsight` → no errors
- [ ] `python -m econsight.models.forecaster` → runs without error, DB rows written
- [ ] `marts.model_forecasts` → 12 rows (3 targets × 2 horizons × 2 model types)
- [ ] `marts.economic_health_score` → scores in [0, 100] for all months
- [ ] `python notebooks/render.py` → `phase2_report.html` generated
- [ ] GitHub Actions CI → green on `main`
