# EconSight Phase 2 — Econometric Modelling
## Design Spec · v1.1 · 2026-06-04

---

## Context

Phase 1 delivered a tested async pipeline that ingests 9 Canadian macro indicators from Statistics Canada and the Bank of Canada into a PostgreSQL warehouse with a monthly mart. Phase 2 builds the modelling layer on top: a tested Python package (`src/econsight/models/`) that trains VAR/VECM and XGBoost models, computes SHAP explainability, runs Monte Carlo simulations, and produces a composite economic health score. Forecasts and scores are written back to PostgreSQL. A Jupyter notebook imports from the package to produce a full analysis report rendered to HTML.

**Scope decisions:**
- No MLflow — model artefacts saved to disk with joblib, MLflow added in Phase 4 alongside cloud deployment
- No Airflow integration yet — modelling runs as a standalone script, wired into the pipeline in Phase 4
- Notebook stays thin — all logic lives in the `models/` package; the notebook only connects, calls, and plots
- Unit tests only for Phase 2 — synthetic DataFrames, no live DB required

---

## 1. Project Structure

New additions to the existing codebase:

```
src/econsight/
└── models/
    ├── __init__.py
    ├── features.py            # load_mart() + build_feature_matrix()
    ├── var_model.py           # VAR / VECM wrapper (statsmodels)
    ├── xgb_model.py           # XGBoost — one model per target × horizon
    ├── shap_analysis.py       # SHAP values + summary data structures
    ├── monte_carlo.py         # residual bootstrap → p10/p50/p90 + named scenarios
    ├── composite.py           # economic health score (z-score + PCA → 0–100)
    └── forecaster.py          # orchestrates all models, writes forecasts to DB

sql/
├── mart_model_forecasts.sql        # DDL + upsert for forecast table
└── mart_economic_health_score.sql  # DDL + upsert for health score table

notebooks/
├── phase2_analysis.ipynb      # full analysis report (7 sections)
└── render.py                  # nbconvert → phase2_report.html (gitignored)

models/artefacts/              # joblib-serialised model files (gitignored)
                               # path anchored to PROJECT_ROOT / "models" / "artefacts"
                               # PROJECT_ROOT defined same way as in db/connection.py

tests/
└── test_models/
    ├── __init__.py
    ├── test_features.py
    ├── test_var_model.py
    ├── test_xgb_model.py
    ├── test_monte_carlo.py
    └── test_composite.py
```

---

## 2. Data Loading and Feature Engineering

**File:** `src/econsight/models/features.py`

### 2.1 `load_mart()`

```python
async def load_mart(conn: psycopg.AsyncConnection) -> pd.DataFrame:
    ...
```

Reads from `marts.mart_monthly_macro_indicators` filtering on `data_complete = TRUE` to avoid passing partial months into model training. Returns a `pd.DataFrame` with:
- Index: `period_date` as `datetime.date` (not Timestamp — converted explicitly)
- Columns: all 9 raw indicator columns (`gdp`, `cpi`, `unemployment_rate`, `ippi`, `retail_trade`, `overnight_rate`, `cadusd`, `bond_10yr`, `m2pp`)
- Sorted ascending by `period_date`

### 2.2 `build_feature_matrix()`

```python
def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

Takes the DataFrame returned by `load_mart()`. Applies the following transforms to all 9 raw indicator columns:

| Transform | Detail |
|-----------|--------|
| Lags | t-1, t-2, t-3, t-6, t-12 for each indicator |
| Rolling mean | 3-month and 6-month windows |
| First differences | Δ(t) = value(t) − value(t−1) |
| YoY change | (value(t) − value(t−12)) / value(t−12) × 100 |

Rows with NaN introduced by the lag window (first 12 rows) are dropped. Returns a `pd.DataFrame` with the same `period_date` index. All downstream **XGBoost** models receive this full feature matrix. The **VAR/VECM** model uses the raw 9-column DataFrame from `load_mart()` directly — not the engineered matrix (see Section 3.1).

### 2.3 Call pattern in `forecaster.py`

```python
df_raw = await load_mart(conn)       # 9 raw columns, data_complete=TRUE only
X = build_feature_matrix(df_raw)     # ~90 engineered columns for XGBoost
```

---

## 3. Models

### 3.1 VAR / VECM (`var_model.py`)

**Input:** The raw `df_raw` DataFrame from `load_mart()` — specifically the 3 endogenous target columns: `cpi`, `unemployment_rate`, `overnight_rate`. These are used as levels; first-differencing is applied internally if the Johansen test indicates non-stationarity.

Wraps `statsmodels.tsa.vector_ar` and `statsmodels.tsa.vector_ar.vecm`. On `fit()`:
1. Runs the Johansen cointegration test on the 3 target series
2. If cointegration is found → fits VECM; otherwise → fits VAR on first-differenced series
3. Lag order selected by AIC, capped at 6

Interpretability in the notebook: coefficient tables and impulse response functions (IRF) — not SHAP (which is tree-model only).

Interface:
```python
class VARModel:
    def fit(self, df: pd.DataFrame) -> None:
        # df has columns: cpi, unemployment_rate, overnight_rate
        ...
    def predict(self, horizons: list[int]) -> dict[int, dict[str, float]]:
        # returns {1: {"cpi": ..., "unemployment_rate": ..., "overnight_rate": ...},
        #          3: {"cpi": ..., "unemployment_rate": ..., "overnight_rate": ...}}
        ...
    def save(self, path: Path) -> None: ...
    def load(self, path: Path) -> None: ...
```

### 3.2 XGBoost (`xgb_model.py`)

**Input:** The full engineered feature matrix `X` from `build_feature_matrix()`.

6 independent models: 3 targets × 2 horizons (`TARGETS = ["cpi", "unemployment_rate", "overnight_rate"]`, `HORIZONS = [1, 3]`). `TARGETS` and `HORIZONS` are module-level constants defined in `forecaster.py` and imported by `xgb_model.py`.

**Target construction (no data leakage):** For horizon `h`, the aligned training pair is:
- `X_aligned = X.iloc[:-h]` (drop last h rows — no future target available)
- `y_aligned = df_raw[target].shift(-h).dropna()` aligned to the same index

The 80/20 chronological split is applied **after** this alignment — never shuffled.

Evaluation: RMSE and MAE on the held-out test set. SHAP values computed post-fit via `shap.TreeExplainer`.

Interface:
```python
class XGBForecastModel:
    def __init__(self, target: str, horizon: int) -> None: ...
    def fit(self, X: pd.DataFrame, y_series: pd.Series) -> ModelMetrics: ...
    def predict(self, X: pd.DataFrame) -> float:
        # Callers always pass the full feature matrix;
        # predict() selects X.iloc[[-1]] internally to return the next-period forecast.
        ...
    def shap_values(self, X: pd.DataFrame) -> np.ndarray: ...
    def save(self, path: Path) -> None: ...
    def load(self, path: Path) -> None: ...
```

`ModelMetrics` dataclass: `{target: str, horizon: int, train_rmse: float, test_rmse: float, train_mae: float, test_mae: float}`.

---

## 4. SHAP Analysis (`shap_analysis.py`)

Covers XGBoost models only. VAR interpretability is handled via coefficient tables and IRF in the notebook, not SHAP.

```python
def compute_shap_summary(model: XGBForecastModel, X: pd.DataFrame) -> SHAPSummary:
    ...
```

`SHAPSummary` dataclass:
- `values`: raw SHAP array (n_samples × n_features)
- `mean_abs`: dict mapping feature name → mean |SHAP value|
- `top_features`: list of top-10 features by mean absolute SHAP value

---

## 5. Monte Carlo Simulation (`monte_carlo.py`)

Residual bootstrap over 1,000 paths per target × horizon combination.

**`SimulationResult` includes the horizon dimension:**

```python
@dataclass
class SimulationResult:
    # bands keyed by (target, horizon) tuple
    bands: dict[tuple[str, int], dict[str, float]]
    # e.g. {("cpi", 1): {"p10": ..., "p50": ..., "p90": ...},
    #        ("cpi", 3): {"p10": ..., "p50": ..., "p90": ...}, ...}

    # scenarios derived from the 3-month horizon
    scenarios: dict[str, dict[str, float]]
    # {"base": {"cpi": ..., "unemployment_rate": ..., "overnight_rate": ...},
    #  "upside": {...}, "downside": {...}}
```

Three named scenarios (derived from 3-month horizon bands):

| Scenario | Definition |
|----------|-----------|
| Base | p50 across all targets |
| Upside | p10 CPI + p10 unemployment + p90 overnight (best-case for SMEs) |
| Downside | p90 CPI + p90 unemployment + p10 overnight (worst-case for SMEs) |

Interface:
```python
def simulate(
    models: dict[tuple[str, int], XGBForecastModel],
    X: pd.DataFrame,
    n_sims: int = 1000,
) -> SimulationResult: ...
```

The `models` dict key matches the `(target, horizon)` tuple used in `forecaster.py`.

---

## 6. Composite Economic Health Score (`composite.py`)

**Input:** The 9 raw indicator columns from `df_raw` (the output of `load_mart()`) — not the engineered feature matrix.

Pipeline:
1. Z-score normalise the 9 raw indicator columns relative to their full historical mean and std
2. Compute `yield_spread = df["bond_10yr"] - df["overnight_rate"]` internally; add as a 10th column
3. Flip sign on indicators where higher = worse: `cpi`, `unemployment_rate`, `ippi`, `yield_spread`
4. Fit PCA on the normalised matrix (10 columns); use first-component loadings as weights
5. Compute weighted score; rescale linearly to 0–100 (0 = worst observed month, 100 = best)

`component_scores` in the output dict includes all 10 keys (9 raw indicators + `yield_spread`).

Returns a monthly score series and per-indicator component contributions as a dict.

Interface:
```python
class CompositeScorer:
    def fit(self, df: pd.DataFrame) -> None:
        # df has the 9 raw indicator columns from load_mart()
        ...
    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        # returns DataFrame: period_date | score | component_scores (dict)
        ...
    def save(self, path: Path) -> None: ...
    def load(self, path: Path) -> None: ...
```

---

## 7. Forecaster Orchestrator (`forecaster.py`)

```python
# TARGETS and HORIZONS are defined here in forecaster.py and imported by xgb_model.py
TARGETS: list[str] = ["cpi", "unemployment_rate", "overnight_rate"]
HORIZONS: list[int] = [1, 3]


async def run_models() -> None:
    async with db_connection() as conn:
        df_raw = await load_mart(conn)
        X = build_feature_matrix(df_raw)

        # VAR/VECM (uses raw 3-column series, not engineered matrix)
        var = VARModel()
        var.fit(df_raw)
        var_forecasts = var.predict(horizons=HORIZONS)
        # var_forecasts: {1: {"cpi": ..., ...}, 3: {"cpi": ..., ...}}

        # XGBoost — one model per (target, horizon)
        xgb_models: dict[tuple[str, int], XGBForecastModel] = {}
        for target in TARGETS:
            for h in HORIZONS:
                y = df_raw[target].shift(-h).dropna()
                X_aligned = X.iloc[: len(y)]
                model = XGBForecastModel(target=target, horizon=h)
                model.fit(X_aligned, y)
                xgb_models[(target, h)] = model

        # Monte Carlo
        sim = simulate(xgb_models, X)

        # Composite score
        scorer = CompositeScorer()
        scorer.fit(df_raw)
        scores = scorer.score(df_raw)

        # Persist to DB
        await upsert_forecasts(conn, var_forecasts, xgb_models, X, sim)
        await upsert_health_scores(conn, scores)
        await conn.commit()

        # Save artefacts
        artefacts_dir = PROJECT_ROOT / "models" / "artefacts"
        artefacts_dir.mkdir(parents=True, exist_ok=True)
        var.save(artefacts_dir / "var_model.pkl")
        for (target, h), model in xgb_models.items():
            model.save(artefacts_dir / f"xgb_{target}_h{h}.pkl")
        scorer.save(artefacts_dir / "composite_scorer.pkl")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_models())
```

### `upsert_forecasts()` definition

```python
async def upsert_forecasts(
    conn: psycopg.AsyncConnection,
    var_forecasts: dict[int, dict[str, float]],
    xgb_models: dict[tuple[str, int], XGBForecastModel],
    X: pd.DataFrame,
    sim: SimulationResult,
) -> None:
```

- For each VAR forecast: inserts one row per `(period_date, target, horizon, model_type="var")` with `point_forecast` set; `p10/p50/p90/scenario_*` columns set to NULL
- For each XGBoost model: calls `model.predict(X)` to get `point_forecast`; populates `p10/p50/p90` and `scenario_base/upside/downside` from `sim.bands` and `sim.scenarios`
- `period_date` = the next calendar month after the last observed `period_date` in `X`
- Uses `ON CONFLICT DO UPDATE` (idempotent)

### `upsert_health_scores()` definition

```python
async def upsert_health_scores(
    conn: psycopg.AsyncConnection,
    scores: pd.DataFrame,   # period_date | score | component_scores
) -> None:
```

Inserts all rows from `scores` into `marts.economic_health_score` using `ON CONFLICT (period_date) DO UPDATE`. The `component_scores` dict must be wrapped with `psycopg.types.json.Json(component_scores)` when binding the parameter so psycopg 3 correctly adapts it to PostgreSQL `jsonb`.

---

## 8. Database Schema

**`marts.model_forecasts`**
```sql
CREATE TABLE IF NOT EXISTS marts.model_forecasts (
    id                bigserial   PRIMARY KEY,
    period_date       date        NOT NULL,
    target            text        NOT NULL,   -- 'cpi', 'unemployment_rate', 'overnight_rate'
    horizon_months    int         NOT NULL,   -- 1 or 3
    model_type        text        NOT NULL,   -- 'var', 'xgboost'
    point_forecast    numeric     NOT NULL,
    p10               numeric,               -- NULL for VAR rows
    p50               numeric,               -- NULL for VAR rows
    p90               numeric,               -- NULL for VAR rows
    scenario_base     numeric,               -- NULL for VAR rows
    scenario_upside   numeric,               -- NULL for VAR rows
    scenario_downside numeric,               -- NULL for VAR rows
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (period_date, target, horizon_months, model_type)
);
```

**`marts.economic_health_score`**
```sql
CREATE TABLE IF NOT EXISTS marts.economic_health_score (
    period_date      date        PRIMARY KEY,
    score            numeric     NOT NULL,   -- 0–100
    component_scores jsonb       NOT NULL,   -- {"cpi": -0.4, "unemployment": 0.2, ...}
    updated_at       timestamptz NOT NULL DEFAULT now()
);
```

**Phase 3 access pattern:** Phase 3 (FastAPI) always queries the latest forecast per `(period_date, target, horizon_months, model_type)` using `ORDER BY created_at DESC LIMIT 1` or the unique constraint directly. No run provenance column is needed for Phase 2; a `model_run_id` FK to `meta.pipeline_runs` may be added in Phase 4.

---

## 9. Notebook Structure

**`notebooks/phase2_analysis.ipynb`** — 7 sections, imports exclusively from `econsight.models.*`:

| Section | Content |
|---------|---------|
| 1. Data Overview | Time series plots for all 9 indicators |
| 2. Feature Correlation | Heatmap of lag-feature correlations; ADF stationarity test results |
| 3. VAR/VECM Results | Cointegration test output; coefficient table; IRF plots; 1-month and 3-month point forecasts |
| 4. XGBoost Results | Train/test RMSE and MAE per model; actual vs predicted plots |
| 5. SHAP Analysis | XGBoost only — summary bar plots per model (feature importance) |
| 6. Monte Carlo | Fan charts (p10/p50/p90) + base/upside/downside scenario overlay |
| 7. Economic Health Score | Score time series; component contribution breakdown for latest month |

**`notebooks/render.py`** — calls `nbconvert --execute --to html` to produce `notebooks/phase2_report.html` (gitignored).

---

## 10. Testing Strategy

Unit tests only — no live DB required.

| File | Covers | Min rows |
|------|--------|----------|
| `test_features.py` | Lag columns correctly offset; no NaN leakage; first-diff values correct; `load_mart` returns correct dtypes (mocked) | 20 |
| `test_var_model.py` | `fit()` runs; `predict()` returns correct targets and horizons; output shapes. **Uses mocked statsmodels call** — does not call the real Johansen test on synthetic data to avoid degenerate results on small samples | 50+ |
| `test_xgb_model.py` | `fit()` + `predict()` run; RMSE is finite; `shap_values()` shape matches feature count; no data leakage (X_aligned and y are same length) | 30 |
| `test_monte_carlo.py` | `p10 ≤ p50 ≤ p90` for all (target, horizon) keys; scenario dict has base/upside/downside; bands dict has correct (target, horizon) tuple keys | 30 |
| `test_composite.py` | Score in [0, 100]; component_scores has all 9 indicator keys; fit/score works on raw 9-column DataFrame | 20 |

**Note on VAR tests:** `statsmodels` requires a minimum of `(lag_order + 1) × n_vars + n_vars` observations for the Johansen test. For lag_order=6, n_vars=3, this is 24 rows minimum. Tests for `VARModel` mock the internal `statsmodels` call and test only the interface contract (correct output shape/types), not the statistical computation.

---

## 11. New Dependencies

Added to `pyproject.toml`:

```toml
dependencies = [
    # existing Phase 1 deps ...
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
    # existing dev deps ...
    "jupyter>=1.0",
    "nbconvert>=7.0",
]
```

---

## Phase 2 Complete Checklist

- [ ] `pytest -v -m "not integration"` → all unit tests PASS (including new `test_models/`)
- [ ] `ruff check src/ tests/` → clean
- [ ] `mypy src/econsight` → no errors
- [ ] `python -m econsight.models.forecaster` → runs without error, DB rows written
- [ ] `SELECT * FROM marts.model_forecasts LIMIT 5;` → forecast rows present for both VAR and XGBoost
- [ ] `SELECT * FROM marts.economic_health_score ORDER BY period_date DESC LIMIT 3;` → score rows present, scores in [0, 100]
- [ ] `python notebooks/render.py` → `phase2_report.html` generated without error
- [ ] GitHub Actions CI → green on `main`
