# EconSight

**Canadian macroeconomic decision intelligence** — ingest, model, and consult on 9 key indicators from Statistics Canada and the Bank of Canada.

> *Interview pitch:* EconSight fetches live macro data into a PostgreSQL medallion warehouse, runs VAR/XGBoost forecasts with scenario bands, and serves a consulting-grade React dashboard with RAG Q&A and PDF reports. The full stack runs with `docker compose up`.

[![CI](https://github.com/kbaran011/EconSight/actions/workflows/ci.yml/badge.svg)](https://github.com/kbaran011/EconSight/actions/workflows/ci.yml)

---

## What It Does

EconSight automatically fetches 9 macro indicators from Statistics Canada and the Bank of Canada, loads them into a PostgreSQL warehouse structured as a medallion architecture (Bronze → Silver → Gold), and materialises a monthly analytics mart with derived economic signals.

**Statistics Canada (5 indicators)**
| Indicator | Table |
|-----------|-------|
| Consumer Price Index (CPI) | 18-10-0004-01 |
| Gross Domestic Product (GDP) | 36-10-0104-01 |
| Unemployment Rate | 14-10-0287-01 |
| Industrial Product Price Index (IPPI) | 18-10-0266-01 |
| Retail Trade | 20-10-0008-01 |

**Bank of Canada Valet API (4 series)**
| Series | Key |
|--------|-----|
| Overnight Rate | V39079 |
| CAD/USD Exchange Rate | FXCADUSD |
| 10-Year Government Bond Yield | V122487 |
| M2++ Money Supply | V41552796 |

**Derived signals computed in the mart:**
- CPI Year-over-Year inflation rate
- Yield spread (10-yr bond − overnight rate)
- Unemployment month-over-month delta

---

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐
│  Statistics Canada  │     │  Bank of Canada      │
│  WDS REST API       │     │  Valet API           │
│  (POST, 5 tables)   │     │  (GET, 4 series)     │
└────────┬────────────┘     └──────────┬───────────┘
         │   async concurrent fetch    │
         └──────────────┬──────────────┘
                        ▼
              ┌─────────────────┐
              │   pipeline.py   │  asyncio.gather → fetch all 9
              └────────┬────────┘
                       │  psycopg3 executemany (batches of 1000)
                       ▼
         ┌─────────────────────────────┐
         │  Bronze  raw.*              │
         │  raw.statcan_observations   │  ON CONFLICT DO UPDATE
         │  raw.boc_observations       │  (idempotent upsert)
         └─────────────┬───────────────┘
                       │  CREATE OR REPLACE VIEW
                       ▼
         ┌─────────────────────────────┐
         │  Silver  staging.*          │
         │  stg_statcan_observations   │  + period_label, is_reliable
         │  stg_boc_observations       │  + period_label, is_month_end
         └─────────────┬───────────────┘
                       │  INSERT … ON CONFLICT DO UPDATE
                       ▼
         ┌─────────────────────────────┐
         │  Gold    marts.*            │
         │  mart_monthly_macro_        │  pivot + window functions
         │  indicators                 │  (CPI YoY, yield spread, …)
         └─────────────────────────────┘
                       │
         ┌─────────────┴───────────────┐
         │  Observability  meta.*      │
         │  pipeline_runs              │  audit trail per run
         └─────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| HTTP client | httpx (async) + tenacity (exponential back-off retry) |
| Database | PostgreSQL 16+ |
| DB driver | psycopg 3 (async) |
| Config | pydantic-settings (`.env` + env vars) |
| Logging | structlog (JSON in prod, console in debug) |
| Testing | pytest + pytest-asyncio + respx |
| Linting | ruff |
| Type checking | mypy (strict mode) |
| CI | GitHub Actions |

---

## Project Structure

```
econsight/
├── src/econsight/
│   ├── clients/
│   │   ├── base.py          # BaseApiClient — httpx + tenacity retry
│   │   ├── statcan.py       # StatCan WDS REST client (POST API)
│   │   └── boc.py           # BoC Valet client (daily → monthly agg)
│   ├── db/
│   │   ├── schema.sql        # DDL for all 4 schemas and tables
│   │   ├── connection.py     # async context manager + init_db()
│   │   └── loader.py         # idempotent upsert + pipeline audit
│   ├── config.py             # Settings, configure_logging, get_logger
│   └── pipeline.py           # Orchestration entry point
├── sql/
│   ├── stg_statcan.sql       # Silver view — StatCan
│   ├── stg_boc.sql           # Silver view — BoC
│   └── mart_monthly_macro.sql # Gold mart — pivot + derived signals
├── tests/
│   ├── fixtures/             # Captured API responses (respx mocks)
│   ├── conftest.py           # pg_conn integration fixture
│   ├── test_base_client.py
│   ├── test_statcan_client.py
│   ├── test_boc_client.py
│   └── test_loader.py
└── .github/workflows/ci.yml  # Lint + test with Postgres service
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 16+

### Setup

```bash
git clone https://github.com/kbaran011/EconSight.git
cd EconSight

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env — set DB_URL to your local PostgreSQL connection string
```

### Initialise the database

```bash
createdb econsight
python -c "import asyncio; from econsight.db.connection import init_db; asyncio.run(init_db())"
```

### Run the pipeline

```bash
econsight-run
# or
python -m econsight.pipeline
```

The pipeline fetches all 9 indicators concurrently, upserts into the raw layer, materialises the mart, and records the run in `meta.pipeline_runs`. Re-running is safe — all writes are idempotent.

### Verify results

```sql
-- Pipeline audit trail
SELECT id, status, rows_loaded, started_at
FROM meta.pipeline_runs
ORDER BY started_at DESC
LIMIT 5;

-- Complete mart rows (all 5 core series present)
SELECT period_label, cpi, overnight_rate, yield_spread, cpi_yoy, data_complete
FROM marts.mart_monthly_macro_indicators
ORDER BY period_date DESC
LIMIT 12;
```

---

## Running Tests

```bash
# Unit tests only (no database required)
pytest -v -m "not integration"

# All tests including integration (requires live PostgreSQL)
pytest -v

# Lint + type check
ruff check src/ tests/
mypy src/econsight
```

---

## Quick Start (Docker) — Recommended for Demo

> Requires Docker Desktop installed and running.

```bash
cp .env.docker.example .env.docker
# Fill in POSTGRES_PASSWORD and GROQ_API_KEY in .env.docker
docker compose --env-file .env.docker up --build
```

Open **http://localhost** — PostgreSQL, FastAPI backend, and React frontend start automatically.

**First boot** fetches live data from StatCan + BoC and trains forecast models in the background (~3–8 min). Watch the nav bar for "Seeding data…" → "Data through YYYY-MM". Set `AUTO_SEED=false` to skip and run `econsight-run` manually inside the backend container.

## Environment Variables

Copy `.env.docker.example` to `.env.docker` and fill in:

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | Password for the PostgreSQL `postgres` user |
| `GROQ_API_KEY` | Free API key from [console.groq.com](https://console.groq.com) — powers the Ask page |
| `AUTO_SEED` | `true` (default in Docker) — fetch data + train models on first boot if DB is empty |
| `AUTO_SEED_MODELS` | `true` — run forecaster after ingest when forecasts table is empty |

Never commit `.env.docker` — it is gitignored.

### Local development (without Docker)

```bash
# Terminal 1 — backend
uvicorn econsight.api.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open **http://localhost:5173**. Frontend uses `frontend/.env.development` to reach the API at `:8000`.

## Demo

<!-- Add Loom demo URL here after recording -->

## Deploy to Railway (Live Demo)

Railway runs the full stack in the cloud with a single public URL. Requires a free Railway account.

### One-time setup

1. Push this repo to GitHub.
2. Open [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → select this repo.
3. Railway auto-detects `railway.toml` and creates the **backend** service.
4. Click **New** → **Database** → **Add PostgreSQL** — Railway provisions a database and injects `DATABASE_URL` into the backend automatically.
5. In the backend service **Variables** tab, set:

| Variable | Value |
|----------|-------|
| `GROQ_API_KEY` | Your key from [console.groq.com](https://console.groq.com) |
| `AUTO_SEED` | `true` |
| `AUTO_SEED_MODELS` | `true` |

6. Click **New** → **GitHub Repo** again → same repo → set **Root Directory** to `frontend` → Railway detects `frontend/railway.toml` and creates the **frontend** service.
7. In the frontend service **Variables** tab, set:

| Variable | Value |
|----------|-------|
| `BACKEND_URL` | `backend.railway.internal:8000` |

8. Note the public domain Railway assigns to the frontend service (e.g. `econsight-frontend-xxxx.railway.app`). In the backend **Variables** tab, add:

| Variable | Value |
|----------|-------|
| `CORS_ORIGINS` | `https://econsight-frontend-xxxx.railway.app` |

9. **Deploy all** — Railway builds and starts all three services.

First boot fetches live data and trains models (~3–8 min). Watch the nav bar for **"Seeding data…"** → **"Data through YYYY-MM"**.

> **Cost:** Railway's free tier includes $5/month credit — enough for a low-traffic demo. Upgrade to the $20/month Hobby plan for always-on uptime.

---

## Design Decisions

**Idempotent upserts over truncate-reload** — every write uses `ON CONFLICT DO UPDATE`, so the pipeline can be re-run at any time without data loss or duplication. Preliminary (`P`) observations get overwritten when Statistics Canada publishes final (`A`) values.

**Async concurrent ingestion** — all 9 API calls are dispatched in parallel via `asyncio.gather`, cutting wall-clock fetch time by ~8×.

**Medallion architecture in PostgreSQL** — staging layers are views (zero storage cost, always current), the mart is a materialised table (fast analytical queries). A single `dbt profile` change swaps the warehouse to any cloud DW.

**Retry with exponential back-off** — `tenacity` retries on `HTTPStatusError` and `TransportError` with jittered delays (2s → 30s), making the pipeline resilient to transient API failures.

**Full audit trail** — every pipeline run is recorded in `meta.pipeline_runs` with status, row count, timestamps, and error messages. The `data_complete` generated column on the mart flags months where all 5 core series are present.

---

## CI/CD

GitHub Actions runs on every push and pull request:
- **lint**: `ruff check` + `mypy --strict`
- **test**: full pytest suite against a live `postgres:16` service container
- **frontend**: TypeScript check, ESLint, Vite build
- **docker**: build Compose stack + smoke test `/api/ping` and `/api/status`
- **pipeline-cron** (weekly): live ingestion against CI Postgres

---

## What I'd Add at Scale

- **Redis** — cache hot API endpoints; invalidate on pipeline run
- **Alembic** — versioned schema migrations instead of idempotent `schema.sql`
- **Airflow** — orchestrate ingestion, dbt, and model training with SLA monitoring
- **Read replicas** — route analytics queries to `econsight_reader` role
- **Playwright E2E** — automated UI smoke tests in CI

---

## Project Phases (Complete)

| Phase | Deliverable |
|-------|-------------|
| 1 | Async ingestion, PostgreSQL medallion, SQL marts, CI |
| 2 | VAR/VECM, XGBoost, SHAP, Monte Carlo, health score |
| 3 | FastAPI + React + RAG + PDF reports |
| 4 | Docker Compose, auto-seed, portfolio polish |
