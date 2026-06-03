# EconSight

A production-grade data engineering pipeline that ingests, warehouses, and transforms key Canadian macroeconomic indicators — built to demonstrate end-to-end data engineering across async ingestion, idempotent persistence, and a layered SQL warehouse.

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
| Language | Python 3.11 |
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

---

## Roadmap

- **Phase 2** — Econometric modelling: VAR/VECM, XGBoost + SHAP feature importance, MLflow experiment tracking, Monte Carlo simulation
- **Phase 3** — Consulting interface: FastAPI, React dashboard, RAG natural-language query, PDF report generation
- **Phase 4** — Production deployment: Kubernetes, Airflow DAGs, dbt, CI/CD to cloud
