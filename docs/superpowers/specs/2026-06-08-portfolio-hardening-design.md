# EconSight Portfolio Hardening — Design Spec
## v1.0 · 2026-06-08

---

## Context

Phases 1–4 delivered a full-stack Canadian macro intelligence platform. For job-hunt and interview use, the project must:

1. Start with `docker compose up` and show real data without manual steps
2. Tell an honest, defensible technical story
3. Look polished in a 5-minute screen share
4. Pass CI that proves the container stack builds

This spec scopes **portfolio hardening** — not enterprise production (auth, K8s, Airflow, Redis).

---

## Goals

| Goal | Success criteria |
|------|------------------|
| One-command demo | `docker compose up` → Dashboard shows indicators + health score within 5 min |
| Honest positioning | About/README match actual stack (SQL marts, CLI pipeline, GHA cron) |
| Interview-ready docs | README pitch, architecture, "what I'd add at scale" |
| CI credibility | GitHub Actions builds Docker images and smoke-tests `/api/ping` |

## Non-Goals

- JWT auth / user accounts
- Kubernetes / multi-region deploy
- Apache Airflow DAGs
- Redis caching
- Playwright E2E (deferred)
- Alembic migrations (deferred)

---

## Wave 0 — Demo Foundations

### 1. Auto-seed on boot

**Trigger:** `AUTO_SEED=true` (default in Docker Compose).

**Logic** (`src/econsight/db/seed.py`):
1. After `init_db()`, check `SELECT COUNT(*) FROM marts.mart_monthly_macro_indicators`
2. If 0 → run `econsight.pipeline.run()` (live StatCan + BoC fetch)
3. If forecasts table empty → run `econsight.models.forecaster.run_models()`
4. Run in **background task** so `/api/ping` healthcheck passes immediately
5. Expose seeding state via `GET /api/status`

**Env vars:**
- `AUTO_SEED` — enable auto-seed (default `false` locally, `true` in compose)
- `AUTO_SEED_MODELS` — run forecaster after ingest (default `true` when `AUTO_SEED=true`)

### 2. Docker asset bundling

Backend `Dockerfile` copies:
- `notebooks/` — RAG ingestion + full report fallback
- `models/artefacts/` — pre-trained pickles (optional fast path)
- `models/chroma_db/` — pre-built vector store (skip cold embed on boot)

Add `jupyter` + `nbconvert` to runtime deps for PDF report generation.

### 3. Frontend API base URL

- Dev: `VITE_API_BASE_URL=http://localhost:8000` (`.env.development`)
- Docker/prod: empty → relative `/api/` via nginx proxy
- `frontend/Dockerfile` accepts `ARG VITE_API_BASE_URL=`

### 4. Environment cleanup

- `.env.example`: add `GROQ_API_KEY`, `AUTO_SEED`; mark `ANTHROPIC_API_KEY` optional
- `/api/status` reports `groq_configured: bool`
- Startup logs warning if Groq key missing

---

## Wave 1 — Credibility

### 5. Docker CI smoke test

New GHA job `docker`:
- `docker compose build`
- `docker compose up -d` with test env
- Wait for healthy, `curl /api/ping`, tear down

### 6. Scheduled pipeline (GHA cron)

Weekly workflow runs `econsight-run` against CI Postgres — honest scheduling story without Airflow.

### 7. About page honesty

- Phase 4 marked complete
- Replace "dbt / Airflow" claims with "SQL staging views / CLI pipeline + GHA cron"
- Add "Portfolio demo" section with Loom placeholder

---

## Wave 2 — Demo Polish

### 8. All 9 indicators in UI

Add GDP, IPPI, Retail Trade to Dashboard cards and Indicators selector/table.

### 9. Data freshness UX

- `GET /api/status` returns `last_pipeline_run`, `seeding_status`
- Nav/footer shows "Data as of …" from latest mart row or pipeline run
- Refresh button invalidates TanStack Query cache

### 10. Mobile navigation

Hamburger menu for `< md` breakpoints; desktop nav unchanged.

---

## Architecture

```
docker compose up
    │
    ├─ postgres (healthy)
    ├─ backend lifespan
    │     ├─ init_db()
    │     ├─ maybe_ingest_rag()
    │     └─ background: maybe_seed_data()
    └─ frontend (nginx → /api/ proxy → backend)
```

---

## Interview Talking Points

1. **Medallion warehouse** — idempotent upserts, staging views, gold mart
2. **Async ingestion** — concurrent StatCan + BoC with tenacity retry
3. **Modelling layer** — VAR + XGBoost + Monte Carlo, persisted to marts schema
4. **Consulting interface** — FastAPI + React + RAG (Groq) + PDF reports
5. **At scale** — Redis cache, Alembic migrations, Airflow orchestration, read replicas

---

## Phase 3 Complete Checklist (portfolio)

- [ ] `docker compose up` → data appears without manual pipeline run
- [ ] Ask page works with `GROQ_API_KEY` set
- [ ] Report PDF downloads in Docker
- [ ] All 9 indicators visible in UI
- [ ] CI: lint + test + frontend + docker jobs green
- [ ] About page matches implementation
- [ ] README has interview pitch + Loom placeholder
