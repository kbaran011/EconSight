# EconSight Phase 2 — Econometric Modelling
## Design Spec · v1.0 · 2026-06-04

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
    ├── features.py            # feature engineering: lags, rolling stats, diffs, YoY
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

## 2. Feature Engineering

**File:** `src/econsight/models/features.py`

Single public function:

```python
def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

Reads from `marts.mart_monthly_macro_indicators` via the existing `db_connection()` context manager. Applies the following transforms to all 9 indicators:

| Transform | Detail |
|-----------|--------|
| Lags | t-1, t-2, t-3, t-6, t-12 for each indicator |
| Rolling mean | 3-month and 6-month windows |
| First differences | Δ(t) = value(t) − value(t−1) — required for VAR stationarity |
| YoY change | (value(t) − value(t−12)) / value(t−12) × 100 |

Rows with NaN introduced by the lag window (first 12 months) are dropped. Returns a typed `pd.DataFrame` with a `period_date` DatetimeIndex. All downstream models receive this same matrix — no feature logic is duplicated in model files.

---

## 3. Models

### 3.1 VAR / VECM (`var_model.py`)

Wraps `statsmodels.tsa.vector_ar` and `statsmodels.tsa.vector_ar.vecm`. On `fit()`:
1. Runs the Johansen cointegration test on the three target series (CPI, unemployment rate, overnight rate)
2. If cointegration is found → fits VECM; otherwise → fits VAR
3. Lag order selected by AIC, capped at 6

Interface:
```python
class VARModel:
    def fit(self, feature_matrix: pd.DataFrame) -> None: ...
    def predict(self, horizons: list[int]) -> dict[int, dict[str, float]]: ...
    # horizons=[1, 3] → {1: {"cpi": ..., "unemployment_rate": ..., "overnight_rate": ...}, 3: {...}}
    def save(self, path: Path) -> None: ...
    def load(self, path: Path) -> None: ...
```

### 3.2 XGBoost (`xgb_model.py`)

6 independent models: 3 targets × 2 horizons. Each is a supervised regressor where:
- **X** = full lag/rolling feature matrix at time t
- **y** = target value at t+h (shifted h steps back)
- Train/test split: 80/20 chronological (never shuffled)
- Evaluation: RMSE and MAE on the held-out test set

SHAP values computed post-fit via `shap.TreeExplainer`.

Interface:
```python
class XGBForecastModel:
    def __init__(self, target: str, horizon: int) -> None: ...
    def fit(self, feature_matrix: pd.DataFrame) -> ModelMetrics: ...
    def predict(self, feature_matrix: pd.DataFrame) -> float: ...
    def shap_values(self, feature_matrix: pd.DataFrame) -> np.ndarray: ...
    def save(self, path: Path) -> None: ...
    def load(self, path: Path) -> None: ...
```

`ModelMetrics` is a dataclass: `{target, horizon, train_rmse, test_rmse, train_mae, test_mae}`.

---

## 4. SHAP Analysis (`shap_analysis.py`)

Thin wrapper around `shap.TreeExplainer`. Exposes:

```python
def compute_shap_summary(model: XGBForecastModel, X: pd.DataFrame) -> SHAPSummary:
    ...
```

`SHAPSummary` dataclass:
- `values`: raw SHAP array (n_samples × n_features)
- `mean_abs`: dict mapping feature name → mean |SHAP value| (for bar plots)
- `top_features`: list of top-10 features by mean absolute SHAP value

The notebook calls `compute_shap_summary()` for each of the 6 XGBoost models and plots using `shap.summary_plot`.

---

## 5. Monte Carlo Simulation (`monte_carlo.py`)

Residual bootstrap — no distributional assumptions:

1. Compute in-sample residuals from fitted XGBoost models
2. Sample residuals with replacement; simulate 1,000 forward paths per target × horizon
3. Return p10/p50/p90 percentiles as uncertainty bands

Three named scenarios derived from the percentile bands:

| Scenario | Definition |
|----------|-----------|
| Base | p50 across all targets |
| Upside | p10 inflation + p10 unemployment + p90 overnight (best-case for SMEs) |
| Downside | p90 inflation + p90 unemployment + p10 overnight (worst-case for SMEs) |

Interface:
```python
@dataclass
class SimulationResult:
    bands: dict[str, dict[str, float]]     # target → {"p10": ..., "p50": ..., "p90": ...}
    scenarios: dict[str, dict[str, float]] # "base"/"upside"/"downside" → target → value

def simulate(
    models: dict[str, XGBForecastModel],
    feature_matrix: pd.DataFrame,
    n_sims: int = 1000,
) -> SimulationResult: ...
```

---

## 6. Composite Economic Health Score (`composite.py`)

Pipeline:
1. Z-score normalise all 9 indicators relative to their full historical mean and std
2. Flip sign on indicators where higher = worse: CPI, unemployment rate, IPPI, yield spread
3. Fit PCA on the normalised matrix; extract first component loadings as indicator weights
4. Compute weighted score; rescale linearly to 0–100 (0 = worst observed month, 100 = best)

Returns a monthly score series and per-indicator component contributions (JSONB-compatible dict).

Interface:
```python
class CompositeScorer:
    def fit(self, feature_matrix: pd.DataFrame) -> None: ...
    def score(self, feature_matrix: pd.DataFrame) -> pd.DataFrame:
        # returns DataFrame with columns: period_date, score, component_scores (dict)
        ...
    def save(self, path: Path) -> None: ...
    def load(self, path: Path) -> None: ...
```

---

## 7. Forecaster Orchestrator (`forecaster.py`)

Ties all components together and writes to the DB:

```python
async def run_models() -> None:
    async with db_connection() as conn:
        df = load_mart(conn)
        X = build_feature_matrix(df)

        # VAR/VECM
        var = VARModel(); var.fit(X)
        var_forecasts = var.predict(horizons=[1, 3])

        # XGBoost + SHAP + Monte Carlo
        xgb_models = {(t, h): XGBForecastModel(t, h).fit(X)
                      for t in TARGETS for h in [1, 3]}
        sim = simulate(xgb_models, X)

        # Composite score
        scorer = CompositeScorer(); scorer.fit(X)
        scores = scorer.score(X)

        # Persist
        await upsert_forecasts(conn, var_forecasts, xgb_models, sim)
        await upsert_health_scores(conn, scores)
        await conn.commit()
```

Model artefacts saved to `models/artefacts/` via joblib after each run.

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
    p10               numeric,
    p50               numeric,
    p90               numeric,
    scenario_base     numeric,
    scenario_upside   numeric,
    scenario_downside numeric,
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

Both use `ON CONFLICT DO UPDATE` upserts — consistent with Phase 1 idempotency pattern.

---

## 9. Notebook Structure

**`notebooks/phase2_analysis.ipynb`** — 7 sections, imports exclusively from `econsight.models.*`:

| Section | Content |
|---------|---------|
| 1. Data Overview | Time series plots for all 9 indicators |
| 2. Feature Correlation | Heatmap of lag-feature correlations; ADF stationarity test results |
| 3. VAR/VECM Results | Cointegration test output; coefficient table; 1-month and 3-month point forecasts |
| 4. XGBoost Results | Train/test RMSE and MAE per model; actual vs predicted plots |
| 5. SHAP Analysis | Summary bar plots per model — feature importance |
| 6. Monte Carlo | Fan charts (p10/p50/p90) + base/upside/downside scenario overlay |
| 7. Economic Health Score | Score time series; component contribution breakdown for latest month |

**`notebooks/render.py`** — calls `nbconvert --execute --to html` to produce `notebooks/phase2_report.html` (gitignored).

---

## 10. Testing Strategy

Unit tests only — synthetic DataFrames (20–30 rows), no live DB required.

| File | Covers |
|------|--------|
| `test_features.py` | Lag columns correctly offset; no NaN leakage; first-diff values correct |
| `test_var_model.py` | `fit()` runs; `predict()` returns correct targets and horizons; output shapes |
| `test_xgb_model.py` | `fit()` + `predict()` run; RMSE is finite; `shap_values()` shape matches feature count |
| `test_monte_carlo.py` | `p10 ≤ p50 ≤ p90`; scenario dict has all three keys; 1000 paths produced |
| `test_composite.py` | Score in [0, 100]; component_scores has all 9 keys; fit/score interface works |

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
- [ ] `SELECT * FROM marts.model_forecasts LIMIT 5;` → forecast rows present
- [ ] `SELECT * FROM marts.economic_health_score ORDER BY period_date DESC LIMIT 3;` → score rows present
- [ ] `python notebooks/render.py` → `phase2_report.html` generated without error
- [ ] GitHub Actions CI → green on `main`
