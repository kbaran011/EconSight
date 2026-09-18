# Design: Forecast Evaluation, Validation & RAG Grounding

**Date:** 2026-09-18
**Status:** Approved (design), pending spec review
**Author:** EconSight

## Motivation

A reviewer's critique: *"Forecasting plus an LLM dashboard is easy to describe. What
would impress me is a forecast evaluation against a baseline, a clear validation
method, or evidence that the answers are grounded accurately."*

The current system produces forecasts (VAR/VECM, XGBoost) and RAG answers, but:

- **No baseline comparison.** `xgb_model.py` reports a single 80/20 chronological
  train/test RMSE. It is never compared against a naive forecast, so we cannot claim
  the models add value. For macro series, a random walk is famously hard to beat — an
  honest evaluation is the whole point.
- **Weak validation.** One static chronological split, no walk-forward backtesting.
- **No grounding evidence.** `query_engine._narrative_answer` stuffs 5 retrieved chunks
  into the prompt and trusts the LLM. There are no citations, no faithfulness score, and
  no way to see whether a given sentence is actually supported by a source.

This design adds all three, coherently, with honest reporting of limitations.

## Data reality (honest baseline)

- StatCan client pulls `latestN: 120` → 10 years monthly per indicator.
- BoC client pulls from `2010-01-01` → ~16 years.
- The `data_complete` mart filter requires GDP + CPI + unemployment + overnight rate +
  10yr bond all non-null. Realistic intersection: **~100–120 monthly rows, ~8–10 years.**
- This supports a rolling-origin backtest with **~50+ folds** at horizons 1 and 3. It is
  **not** enough for strong statistical claims. The UI and methodology copy state this
  explicitly; the Diebold–Mariano test is reported as *indicative*, not definitive.
- Implementation must verify the live mart row count / date range before trusting the
  fold count, and degrade gracefully (fewer folds, clear message) if the window is thin.

## Scope

Three parts, one theme — *evidence*:

- **A. Forecast evaluation & validation** — walk-forward backtest vs. naive baselines,
  with MASE, skill score, and Diebold–Mariano significance.
- **B. RAG grounding** — sentence-level attribution, groundedness score, unsupported-claim
  flagging, and executed-SQL evidence.
- **C. Surfacing** — API endpoints, a new Validation page, grounding UI in Ask, tests,
  and seed/Docker integration.

Out of scope: retraining production forecast models, new data sources, changing the
existing forecast/health-score endpoints, auth.

---

## Part A — Forecast evaluation & validation

### A.1 New module `src/econsight/models/backtest.py`

**Method: rolling-origin (expanding-window) walk-forward.**

For each `target ∈ {cpi, unemployment_rate, overnight_rate}` and `horizon ∈ {1, 3}`:

- Build the aligned data once: raw level series (for naive baselines and VAR) and the
  `build_feature_matrix` output (for XGBoost). Reuse existing `features.py` — no
  re-implementation of feature logic.
- Choose an initial training window `min_train` (default 48 months, clamped so at least
  ~20 folds remain; if data is too short, reduce and record the actual fold count).
- For each origin `t` from `min_train` to `T - h`:
  - Train each model only on forecast pairs whose **target date is ≤ `t`** — i.e. origins up
    to `t - h`. This is the critical detail and the invariant under test: because the XGB/VAR
    target is `y = series.shift(-h)` (a value at `t + h` indexed at origin `t`), naively
    slicing `y.loc[:t]` would admit training pairs whose realized targets run up to `t + h`,
    i.e. future information relative to the origin being forecast. The leakage-free slice is
    `X.loc[:t-h]` / `y.loc[:t-h]` (equivalently: keep only pairs with `target_date ≤ t`).
  - Then forecast the value at period `t + h` and record
    `(origin_date, target_date, y_true, y_pred)`.
  - **No look-ahead**: features at origin `t` use only information available at `t`
    (contemporaneous raw levels and lag/rolling/diff transforms — *not* exclusively
    `shift(1)+` transforms), and the `t - h` target cutoff above guarantees no training
    pair's `target_date` exceeds `t`. The naive baselines are closed-form and use only
    `y_t` / `y_{t+h-12}`, both known at `t`.

**Registered forecasters (model-agnostic via a small protocol):**

- `naive_rw` — random walk: `ŷ_{t+h} = y_t` (last observed level). Primary baseline.
- `seasonal_naive` — `ŷ_{t+h} = y_{t+h-12}` (value 12 months before the target period,
  known at origin `t` for `h ≤ 12`). Secondary baseline.
- `var` — reuse `VARModel.fit/predict`, refit per origin.
- `xgboost` — reuse `XGBForecastModel.fit/predict`, refit per origin.

A `Forecaster` protocol (`fit(train_df) -> None`, `predict_h(h) -> float`) lets each
model plug in; the loop is written once. Naive baselines are trivial closed-form
implementations of the same protocol.

Refit strategy: **full re-fit at every origin** (chosen approach A). ~100 rows × ~50
origins × 4 models × 2 horizons is a couple of minutes offline — acceptable for an
offline/seed-time job and the only leakage-free option for the ML model.

### A.2 Metrics

Computed per `(target, horizon, model)` over the collected folds:

- **MAE**, **RMSE** — standard.
- **MASE** (Hyndman & Koehler): `MASE = MAE_model / MAE_naive_insample`, where the scale
  is the MAE of the one-step naive forecast on the **training** series
  (`mean(|y_i − y_{i-1}|)`). MASE < 1 ⇒ beats the naive benchmark. Scale-free, comparable
  across the three targets.
- **Skill score vs random walk**: `1 − RMSE_model / RMSE_rw`. Positive ⇒ better than RW.
  Reported per model (RW's own skill score is 0 by construction).
- **Diebold–Mariano test** vs random walk: on the per-fold squared-error loss
  differentials, with the Harvey–Leybourne–Newbold small-sample correction and a
  Student-t reference distribution. For multi-step horizons (`h > 1`) the forecasts overlap,
  so the loss differentials are serially correlated; the statistic therefore uses a long-run
  (HAC) variance that includes autocovariances up to lag `h − 1`, not the naive i.i.d.
  variance (for `h = 1` this reduces to the plain variance). Returns `dm_stat`, `dm_pvalue`.
  Implemented directly (small, well-specified function) since statsmodels lacks a clean DM.
  Guards for degenerate cases (identical losses, `n < 8`) → `dm_pvalue = None`.

### A.3 Persistence — new tables (added to `db/schema.sql`, idempotent)

```
marts.model_backtests(
  id bigserial PK,
  target text, horizon_months int, model_type text,
  baseline text,                      -- e.g. 'random_walk'
  n_folds int,
  mae numeric, rmse numeric, mase numeric,
  skill_score_vs_rw numeric,
  dm_stat numeric, dm_pvalue numeric,
  backtest_start date, backtest_end date,
  created_at timestamptz default now(),
  UNIQUE(target, horizon_months, model_type)
)

marts.backtest_predictions(
  id bigserial PK,
  target text, horizon_months int, model_type text,
  origin_date date, target_date date,
  y_true numeric, y_pred numeric,
  created_at timestamptz default now(),
  UNIQUE(target, horizon_months, model_type, target_date)
)
```

Both get `GRANT SELECT ... TO econsight_reader` and the default-privileges grant, matching
the existing pattern. Upserts follow the existing `ON CONFLICT ... DO UPDATE` idiom.

### A.4 Runner & seed integration

- `backtest.py` exposes `async def run_backtest()` mirroring `forecaster.run_models()`:
  load mart → run walk-forward → upsert metrics + predictions → commit.
- Invoked after `run_models()` in the seed path (`db/seed.py`) so a Docker boot with
  `AUTO_SEED` populates validation data. Gated on empty-table check to stay idempotent.
- Also runnable standalone via `python -m econsight.models.backtest`.

### A.5 API — new router `src/econsight/api/routers/validation.py`

- `GET /api/validation/metrics` → `list[BacktestMetric]` (all target×horizon×model rows).
- `GET /api/validation/predictions?target=&horizon=` → per-fold actual-vs-predicted for
  every model at that target/horizon (for charting).
- `GET /api/validation/summary` → headline object: number of configs where the best model
  beats random walk (MASE < 1 and skill > 0), best skill score + its config, total folds,
  backtest window. Powers the page headline honestly.

New Pydantic schemas: `BacktestMetric`, `BacktestPredictionSeries`, `ValidationSummary`.
Router registered in `api/main.py` alongside the others.

### A.6 Frontend — new `Validation.tsx` (route `/validation`, nav link)

- **Headline cards**: "Beats random walk on N / 6 configs", "Best skill +X% (target, h)",
  "M folds over YYYY–YYYY". Honest — if a model loses to RW, the card says so.
- **Metrics table**: rows = target × horizon × model; columns MAE, RMSE, MASE, skill vs RW,
  DM p-value. Cell coloring: green where model beats baseline (MASE < 1 / skill > 0),
  amber where it does not. No cherry-picking.
- **Predicted-vs-actual chart** (recharts): actual line + selected model line + random-walk
  line over the backtest window, with a target/horizon selector.
- **Methodology note**: plain-English walk-forward + MASE + DM explanation and the
  data-window caveat (~10y monthly, ~50 folds, DM indicative).

### A.7 Tests

- `tests/test_models/test_backtest.py`: MASE on a known series (hand-computed),
  DM statistic on synthetic loss series (sign + rough magnitude), skill-score arithmetic,
  and a **no-look-ahead integrity** test that asserts, for every training pair used at
  origin `t`, that its `target_date ≤ t` (equivalently `origin + h ≤ t`) — checking the
  *target* dates, not just `X`'s index, since a `shift(-h)` leak lives in `y`'s values and
  would otherwise slip past an index-only check — and that a deterministic naive forecast
  equals `y_t`.
- `tests/test_api/test_validation.py`: endpoints return fixture-seeded rows with correct
  shape and filtering.

---

## Part B — RAG grounding

### B.1 New module `src/econsight/rag/grounding.py`

Given an answer string and the retrieved chunks (with their embeddings), produce grounding
evidence **independently of the LLM that wrote the answer**:

- **Sentence split**: lightweight regex/`re` splitter (no heavy NLP dep) into sentences.
- **Per-sentence verification**: embed each sentence with the same `all-MiniLM-L6-v2`
  model already loaded in `retriever.py`; compute max cosine similarity to the retrieved
  chunk embeddings. Attach `best_source_title`, `similarity`, and `supported = similarity
  ≥ THRESHOLD` (default 0.45, a config constant with a documented rationale).
- **Citations**: the generation prompt is updated to number the context chunks and ask the
  LLM to append `[n]` markers. `grounding.py` parses `[n]` → `cited_chunk_ids`. A `chunk_id`
  is the **1-based positional index into the numbered context** (chunk 1..k as presented to
  the LLM), matching the `[n]` markers; the retriever does not need to surface stable ids,
  and `SourceSnippet.chunk_id` is that same position. Citations and the independent
  similarity check are both reported; the similarity check is the trustworthy signal (LLM
  citations can be wrong).
- **Groundedness score**: fraction of sentences with `supported = True` (0–100%). Also
  expose mean similarity for nuance.

Returns a `GroundingReport`: `groundedness: float`, `sentences: list[SentenceAttribution]`,
`sources: list[SourceSnippet]` (title + short snippet + chunk id).

The retriever is extended to optionally return chunk embeddings (it already encodes the
query; returning `include=["documents","metadatas","embeddings"]` or re-encoding docs).
Re-encoding the ~5 retrieved docs is cheap and avoids relying on Chroma storing embeddings.

### B.2 `query_engine.py` changes

- `_narrative_answer`: after generating the answer, call `grounding.build_report(...)` and
  attach it to the response. Prompt updated to request `[n]` citations.
- `_sql_answer`: attach `executed_sql` (the safe query actually run) and set groundedness to
  a direct-query sentinel (the answer *is* the data). No sentence attribution needed;
  the SQL is the evidence.
- Backward compatibility: all new fields are optional on `RAGResponse`.

### B.3 Schema changes (`api/schemas.py`)

```
class SourceSnippet:        title, snippet, chunk_id
class SentenceAttribution:  text, supported, similarity, best_source_title, cited_chunk_ids
class RAGResponse (extended, all new fields Optional/defaulted):
  answer, sources, query_type,
  groundedness: float | None,
  grounding: list[SentenceAttribution] | None,
  source_snippets: list[SourceSnippet] | None,
  executed_sql: str | None
```

### B.4 Frontend — `Ask.tsx` grounding UI

- **Groundedness meter**: e.g. "92% grounded — 11 / 12 claims traceable to sources", color
  scaled (green/amber/red).
- **Inline citation chips** after sentences; clicking a chip reveals the matched source
  snippet. Unsupported sentences get an amber underline + "no strong source found" note —
  honest about hallucination risk rather than hiding it.
- **SQL answers**: collapsible "How this was computed" showing the executed query.
- Graceful when grounding fields are absent (older responses / errors).

### B.5 Tests

- `tests/test_rag/test_grounding.py`: synthetic sentences vs. synthetic chunk embeddings →
  assert supported/unsupported classification at the threshold, groundedness arithmetic,
  citation parsing (`[1][3]` → `{1,3}`), and the SQL-path direct-groundedness sentinel.
  Embedding model calls are stubbed/monkeypatched to keep the test fast and offline.

---

## Part C — Cross-cutting

- **Schema migrations**: two new tables + grants appended to `db/schema.sql`, idempotent,
  applied by the existing `init_db()` lifespan hook.
- **Seed/Docker**: `run_backtest()` wired into the seed path behind an empty-table guard.
- **Status endpoint** (optional, low cost): add `backtest_row_count` to `/api/status` so
  the frontend can show whether validation data is ready.
- **Honest copy**: Validation page + About page state the data window and that DM tests on
  ~50 folds are indicative, not definitive.
- **Docs**: update `tasks/session_state.md`, `tasks/todo.md`; capture any corrections in
  `tasks/lessons.md`.

## Error handling & edge cases

- Thin data: if folds < a floor (e.g. 12), still compute but flag results `low_confidence`
  and the UI shows a warning; never crash. No extra table column is needed — `low_confidence`
  is derived from the persisted `n_folds` (the API/`ValidationSummary` computes and exposes
  the flag from `n_folds < floor`).
- Degenerate DM (identical losses, tiny n): `dm_pvalue = None`, UI shows "n/a".
- VAR fit failure at an origin (singular matrix): skip that fold for VAR only, count it,
  and record the reduced fold count rather than aborting the whole backtest.
- Empty Chroma collection / RAG grounding when no chunks: groundedness `None`, answer still
  returned with a "not indexed" note (existing behavior preserved).
- All new API endpoints return empty lists (200) when tables are unseeded, so the frontend
  degrades to an informative empty state.

## Testing strategy summary

Unit tests for the pure metric/grounding math (deterministic, offline, stubbed embeddings),
integrity test for no-look-ahead, and API tests against fixture-seeded tables. Existing
test suite must stay green; new tables are additive.

## Module boundaries (isolation check)

- `models/backtest.py` — *what*: run walk-forward, compute metrics; *depends on*:
  `features.py`, `var_model.py`, `xgb_model.py`, db connection. Pure functions for metrics
  are separable and unit-tested without a DB.
- `rag/grounding.py` — *what*: score an answer against chunks; *depends on*: the embedding
  model only. No DB, no LLM. Independently testable.
- Routers/pages are thin adapters over these, matching existing patterns.
