# Todo — Forecast Evaluation, Validation & RAG Grounding

Spec: `docs/superpowers/specs/2026-09-18-evaluation-and-grounding-design.md`
Plan: `docs/superpowers/plans/2026-09-18-evaluation-and-grounding.md`
Branch: `feat/evaluation-and-grounding`

## Tasks
- [x] Phase 1 — MAE/RMSE/MASE/skill-score + Diebold–Mariano metrics
- [x] Phase 2 — walk-forward engine (leakage-free t−h cutoff), naive/seasonal/VAR/XGB adapters, VAR level reconstruction, aggregation
- [x] Phase 3 — schema tables, `run_backtest()` runner, seed hook
- [x] Phase 4 — `/api/validation/{metrics,predictions,summary}` + `backtest_row_count` in status
- [x] Phase 5 — RAG grounding scorer (sentence attribution, groundedness)
- [x] Phase 6 — wire grounding + executed-SQL into query engine (backward-compatible)
- [x] Phase 7 — client types, Validation page, Ask grounding UI
- [x] Phase 8 — verification + docs
- [x] Lint/type hardening — ruff + mypy strict clean across src/ and tests/

## Review

**What was built.** A rigorous, honest answer to the critique "show me evaluation against a
baseline, a validation method, and evidence the answers are grounded":

- **Validation (forecasts).** `models/backtest.py` runs an expanding-window, rolling-origin
  backtest that is leakage-free (training restricted to pairs with `target_date ≤ origin`,
  the `t−h` cutoff). Four contenders — random walk, seasonal naive, VAR, XGBoost — are scored
  with MAE, RMSE, **MASE** (scaled by in-sample naive MAE; <1 beats naive), **skill score vs
  random walk**, and a **Diebold–Mariano** test (HLN small-sample correction; HAC variance
  with autocovariances to lag h−1 for the overlapping h=3 forecasts). VAR is compared in
  level space via a new `VARModel.predict_levels()` so the differenced branch isn't unfairly
  penalised. Results persist to `marts.model_backtests` + `marts.backtest_predictions`,
  surfaced at `/api/validation/*` and on a new **Validation** page (honest green/amber table,
  predicted-vs-actual chart, methodology + data-window caveat).

- **Grounding (RAG).** `rag/grounding.py` independently verifies each answer sentence by
  re-embedding it and measuring cosine similarity to the retrieved chunks → a **groundedness
  score**, per-sentence best source, and unsupported-claim flagging. SQL answers carry the
  **executed query** as evidence. Surfaced in the Ask page (meter, citations, amber flags,
  collapsible SQL). All new `RAGResponse` fields are optional/backward-compatible.

**Verification.**
- Backend: `89 passed` (non-integration) with `KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1`.
- `ruff check src/ tests/` clean; `mypy src/econsight` strict clean.
- Frontend: `npm run build` + `npm run lint` clean.
- End-to-end engine smoke on synthetic 80-month data: all 4 models ran across 31 folds; VAR
  beat random walk (MASE ~0.73), XGBoost did not (MASE ~1.23), seasonal-naive worst on a
  trend series — realistic, differentiated output, no units bug.

**Honest limitations.**
- No live Postgres was available in this session, so the **real** headline numbers (which
  models beat random walk on actual StatCan/BoC data, and by how much) still need a seed run
  (`docker compose up` with `AUTO_SEED`, or `python -m econsight.models.backtest` against a
  seeded DB). The pipeline is wired and verified on synthetic data; the numbers themselves
  must be generated and reported honestly, including the likely case that the ML/econometric
  models do NOT beat a random walk on some series — that is itself a credible finding.
- Data window is ~8–10 years monthly (~50 folds); DM p-values are reported as indicative,
  not definitive, in the UI copy.

## Next (user-driven)
- [ ] Run a seed against a live DB and record the real backtest numbers in the Validation
      methodology note / README.
- [ ] Review the branch and merge (`feat/evaluation-and-grounding`).
- [ ] Optional: decide whether to amend the 4 earlier doc commits that carried a
      `Co-Authored-By` trailer (contradicts sole-author commit style).
