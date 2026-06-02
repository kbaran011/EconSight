# EconSight Phase 1 — Data Engineering Foundation
## Design Spec · v1.1 · 2026-06-01

---

## Context

EconSight is a 4-phase decision intelligence platform for Canadian SMEs, built as an IBM Montreal Strategy & Data Consulting portfolio project. Phase 1 establishes the data engineering foundation: async ingestion from Statistics Canada and Bank of Canada, a PostgreSQL warehouse with Medallion Architecture, SQL transformation layer, and a tested Python pipeline script.

**Scope decisions for this build:**
- Starting from scratch — no existing code
- No Docker Compose initially (added in a later pass alongside Alembic)
- No Airflow initially — pipeline runs as a standalone Python script
- No dbt initially — SQL transforms as plain `.sql` files, migrated to dbt models later
- Tests written alongside code (unit tests first, integration tests tagged separately)
- Build order: vertical slice (one indicator end-to-end first, then generalize)

---

## 1. Project Structure

```
econsight/
├── pyproject.toml
├── .env.example
├── .gitignore
├── src/
│   └── econsight/
│       ├── config.py                 # pydantic-settings config + structlog setup
│       ├── clients/
│       │   ├── base.py               # httpx.AsyncClient + tenacity retry (shared)
│       │   ├── statcan.py            # StatCan WDS client + typed dataclasses
│       │   └── boc.py                # BoC Valet client + typed dataclasses
│       ├── db/
│       │   ├── schema.sql            # DDL for raw.* + meta.* schemas (run once)
│       │   ├── connection.py         # db_connection() context manager
│       │   └── loader.py             # batched idempotent upsert logic
│       └── pipeline.py               # top-level orchestration script
├── sql/
│   ├── stg_statcan.sql               # staging view (future dbt model)
│   ├── stg_boc.sql                   # staging view (future dbt model)
│   └── mart_monthly_macro.sql        # mart table with derived series
└── tests/
    ├── conftest.py                   # fixtures: DB connection, mock HTTP, fixture JSON
    ├── fixtures/
    │   ├── statcan_cpi.json          # captured API response for CPI
    │   └── boc_overnight.json        # captured API response for overnight rate
    ├── test_statcan_client.py
    ├── test_boc_client.py
    └── test_loader.py
```

**Key decisions:**
- `src/` layout prevents accidental imports from the project root and catches packaging issues early
- `schema.sql` (plain DDL) instead of Alembic migrations — Alembic adds real value in a team context; will be layered in with Docker
- `sql/` lives outside the Python package so SQL files migrate cleanly into dbt models without restructuring Python code
- All `sql/*.sql` files must be written as **idempotent DDL**: `CREATE OR REPLACE VIEW` for views, `CREATE TABLE IF NOT EXISTS` for tables. Staging views are executed once during schema init, not on every pipeline run.

---

## 2. Configuration & Logging

`src/econsight/config.py` — single `Settings` class loaded from `.env`:

```python
class Settings(BaseSettings):
    db_url: str = "postgresql://user:pass@localhost/econsight"
    # Note: psycopg 3 uses standard postgresql:// URI (not postgresql+psycopg://)
    log_level: str = "INFO"
    statcan_base_url: str = "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl"
    boc_base_url: str = "https://www.bankofcanada.ca/valet"
    http_timeout: float = 30.0
    http_max_retries: int = 5

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

Logging uses **structlog** with two renderers:
- JSON output in production (`LOG_LEVEL=INFO`)
- Rich pretty-print in local dev

A single `get_logger()` helper is used throughout — no `logging.getLogger(__name__)` scattered across modules.

---

## 3. HTTP Client Design

### `clients/base.py` — shared base

```python
class BaseApiClient:
    def __init__(self, base_url: str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=settings.http_timeout)

    @retry(
        wait=wait_exponential(min=2, max=30),
        stop=stop_after_attempt(settings.http_max_retries),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        # HTTPStatusError covers 4xx/5xx (after raise_for_status())
        # TransportError is the base for TimeoutException + NetworkError
    )
    async def _get(self, path: str, **params) -> dict:
        response = await self._client.get(path, params=params)
        response.raise_for_status()   # raises HTTPStatusError on 4xx/5xx — required for tenacity
        return response.json()

    async def __aenter__(self): ...
    async def __aexit__(self): ...
```

**429 handling:** tenacity's exponential back-off (`wait_exponential`) handles retry timing. Full `Retry-After` header parsing is deferred to a later pass — exponential back-off is sufficient for Phase 1's weekly schedule.

### `clients/statcan.py`

```python
@dataclass
class StatCanObservation:
    indicator_key: str       # e.g. "18-10-0004-01"
    reference_date: date     # monthly: first day of month (e.g. 2024-03-01)
    value: Decimal
    status: str              # "A" (final) or "P" (preliminary)
    ingested_at: datetime

class StatCanClient(BaseApiClient):
    INDICATORS: dict[str, str] = {
        "gdp":          "36-10-0104-01",
        "cpi":          "18-10-0004-01",
        "unemployment": "14-10-0287-01",
        "ippi":         "18-10-0266-01",
        "retail_trade": "20-10-0008-01",
    }

    async def fetch_indicator(self, table_id: str) -> list[StatCanObservation]: ...
    async def fetch_all(self) -> list[StatCanObservation]:
        results = await asyncio.gather(*[
            self.fetch_indicator(tid) for tid in self.INDICATORS.values()
        ])
        return [obs for batch in results for obs in batch]
```

### `clients/boc.py`

```python
@dataclass
class BocObservation:
    series_key: str          # e.g. "V39079"
    reference_date: date     # normalized to first day of month (see note below)
    value: Decimal
    ingested_at: datetime

class BocClient(BaseApiClient):
    SERIES: dict[str, str] = {
        "overnight_rate": "V39079",
        "cadusd":         "FXCADUSD",
        "bond_10yr":      "V122487",
        "m2pp":           "V41552796",
    }

    async def fetch_series(self, series_key: str) -> list[BocObservation]: ...
    async def fetch_all(self) -> list[BocObservation]: ...
```

**Daily → monthly aggregation:** BoC Valet returns daily observations for V39079, FXCADUSD, and V122487. At ingestion time, daily series are aggregated to **month-end value** (last business day of the month) and stored with `reference_date` set to the first day of that month. This normalises all series to monthly grain before writing to `raw.boc_observations`, enabling a clean join with StatCan monthly data in the mart. M2++ (V41552796) is already monthly — no aggregation required.

**Vertical slice entry point:** `StatCanClient.fetch_indicator("18-10-0004-01")` (CPI, monthly, no adjustments — simplest series).

---

## 4. Database Schema

All schema objects are created by running `db/schema.sql` once. Staging views are created at schema init time (not on every pipeline run).

### `raw.statcan_observations`

```sql
CREATE TABLE IF NOT EXISTS raw.statcan_observations (
    id              bigserial   PRIMARY KEY,
    indicator_key   text        NOT NULL,
    reference_date  date        NOT NULL,
    value           numeric     NOT NULL,
    status          char(1)     NOT NULL CHECK (status IN ('A', 'P')),
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    pipeline_run_id uuid,
    UNIQUE (indicator_key, reference_date)
);
```

### `raw.boc_observations`

```sql
CREATE TABLE IF NOT EXISTS raw.boc_observations (
    id              bigserial   PRIMARY KEY,
    series_key      text        NOT NULL,
    reference_date  date        NOT NULL,   -- always first day of month
    value           numeric     NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    pipeline_run_id uuid,
    UNIQUE (series_key, reference_date)
);
```

### `meta.pipeline_runs`

```sql
CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz,
    status       text        CHECK (status IN ('running', 'success', 'failed')),
    rows_loaded  int,
    error_msg    text
);
```

### Staging views (`sql/stg_statcan.sql`, `sql/stg_boc.sql`)

Plain `CREATE OR REPLACE VIEW` (idempotent). Executed once at schema init, not on every pipeline run.

`stg_statcan_observations`:
- All columns from `raw.statcan_observations`
- `period_label text` — `to_char(reference_date, 'YYYY-MM')`
- `is_reliable boolean` — `status IN ('A', 'P')`

`stg_boc_observations`:
- All columns from `raw.boc_observations`
- `period_label text` — `to_char(reference_date, 'YYYY-MM')`
- `is_month_end boolean` — always `true` (enforced at ingestion)

### `sql/mart_monthly_macro.sql` — mart table

The mart materialises one row per calendar month. All series must be present (no partial rows written — see NULL strategy below).

```sql
CREATE TABLE IF NOT EXISTS marts.mart_monthly_macro_indicators (
    period_date         date        NOT NULL,   -- first day of month, e.g. 2024-03-01
    period_label        text        NOT NULL,   -- 'YYYY-MM', primary human-readable key
    -- StatCan series
    gdp                 numeric,
    cpi                 numeric,
    unemployment_rate   numeric,
    ippi                numeric,
    retail_trade        numeric,
    -- BoC series
    overnight_rate      numeric,
    cadusd              numeric,
    bond_10yr           numeric,
    m2pp                numeric,
    -- Derived series
    cpi_yoy             numeric,    -- CPI YoY %: (cpi / lag(cpi, 12) - 1) * 100
    yield_spread        numeric,    -- bond_10yr - overnight_rate (recession indicator)
    unemployment_delta  numeric,    -- unemployment_rate - lag(unemployment_rate, 1)
    -- Metadata
    updated_at          timestamptz NOT NULL DEFAULT now(),
    data_complete       boolean GENERATED ALWAYS AS (
                            cpi IS NOT NULL AND unemployment_rate IS NOT NULL AND
                            overnight_rate IS NOT NULL AND bond_10yr IS NOT NULL AND
                            gdp IS NOT NULL
                        ) STORED,
    UNIQUE (period_date)
);
```

**Materialisation strategy:** On each pipeline run, `pipeline.py` executes:
```sql
INSERT INTO marts.mart_monthly_macro_indicators (...)
SELECT
    date_trunc('month', s.reference_date)::date AS period_date,
    to_char(s.reference_date, 'YYYY-MM')        AS period_label,
    MAX(CASE WHEN s.indicator_key = '18-10-0004-01' THEN s.value END) AS cpi,
    MAX(CASE WHEN s.indicator_key = '36-10-0104-01' THEN s.value END) AS gdp,
    -- ... remaining StatCan pivots
    MAX(CASE WHEN b.series_key = 'V39079'      THEN b.value END) AS overnight_rate,
    -- ... remaining BoC pivots
    -- Derived: window functions computed inline
    (MAX(CASE WHEN s.indicator_key = '18-10-0004-01' THEN s.value END)
     / NULLIF(LAG(MAX(CASE WHEN s.indicator_key = '18-10-0004-01' THEN s.value END), 12)
              OVER (ORDER BY date_trunc('month', s.reference_date)), 0) - 1) * 100 AS cpi_yoy,
    -- yield_spread, unemployment_delta similarly
FROM raw.statcan_observations s
JOIN raw.boc_observations b
  ON date_trunc('month', s.reference_date) = date_trunc('month', b.reference_date)
GROUP BY date_trunc('month', s.reference_date)
ON CONFLICT (period_date)
DO UPDATE SET
    cpi             = EXCLUDED.cpi,
    gdp             = EXCLUDED.gdp,
    overnight_rate  = EXCLUDED.overnight_rate,
    -- ... all columns
    updated_at      = now();
```

**NULL strategy:** Rows with NULL for any core series are written to the mart with NULLs preserved. The `data_complete` generated column (defined in the DDL above) flags rows where all 5 core series (CPI, GDP, unemployment, overnight rate, 10-yr bond) are non-NULL. Phase 2 models filter on `data_complete = true` before running VAR/VECM to avoid silent NaN propagation.

---

## 5. Database Connection & Loader

### `db/connection.py`

```python
from contextlib import asynccontextmanager
from pathlib import Path
import psycopg
from econsight.config import settings

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # src/econsight/db/ → repo root

@asynccontextmanager
async def db_connection():
    # psycopg 3 uses standard postgresql:// URI directly (no SQLAlchemy)
    async with await psycopg.AsyncConnection.connect(settings.db_url) as conn:
        yield conn

async def execute_sql_file(conn: psycopg.AsyncConnection, relative_path: str) -> None:
    """Execute a SQL file at `relative_path` resolved from the project root."""
    sql = (PROJECT_ROOT / relative_path).read_text()
    with conn.cursor() as cur:
        await cur.execute(sql)
```

### `db/loader.py` — batched upsert

Uses psycopg 3's `executemany` (acceptable for Phase 1 weekly schedule; `COPY` mode can be added later for bulk historical loads):

```python
async def upsert_statcan(
    conn: psycopg.AsyncConnection,
    observations: list[StatCanObservation],
    run_id: uuid.UUID,
    batch_size: int = 1000,
) -> int:
    sql = """
        INSERT INTO raw.statcan_observations
            (indicator_key, reference_date, value, status, ingested_at, pipeline_run_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_key, reference_date)
        DO UPDATE SET
            value           = EXCLUDED.value,
            status          = EXCLUDED.status,
            ingested_at     = EXCLUDED.ingested_at,
            pipeline_run_id = EXCLUDED.pipeline_run_id
    """
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(observations), batch_size):
            batch = observations[i : i + batch_size]
            params = [(o.indicator_key, o.reference_date, o.value,
                       o.status, o.ingested_at, run_id) for o in batch]
            await cur.executemany(sql, params)
            total += len(batch)
    return total
```

`upsert_boc` follows the same pattern with `series_key` and without `status`.

### `pipeline.py` — orchestration script

```python
async def run():
    async with db_connection() as conn:
        run_id = await start_run(conn)
        try:
            statcan_data, boc_data = await asyncio.gather(
                StatCanClient().fetch_all(),
                BocClient().fetch_all(),
            )
            rows  = await upsert_statcan(conn, statcan_data, run_id)
            rows += await upsert_boc(conn, boc_data, run_id)
            await execute_sql_file(conn, "sql/mart_monthly_macro.sql")
            await finish_run(conn, run_id, rows)
        except Exception as e:
            await fail_run(conn, run_id, str(e))
            raise
```

Note: staging views are not re-executed here — they are created once at schema init and always reflect current raw data automatically.

### Vertical slice build order

1. `config.py` + logging setup + `pyproject.toml`
2. `db/connection.py` + `db/schema.sql` + database init script
3. `clients/base.py` with tenacity retry
4. `clients/statcan.py` for CPI only + `tests/test_statcan_client.py`
5. `db/loader.py` upsert for StatCan + `tests/test_loader.py`
6. `sql/stg_statcan.sql` staging view
7. Expand to all 5 StatCan indicators
8. `clients/boc.py` for overnight rate only + `tests/test_boc_client.py`
9. Expand to all 4 BoC series
10. `sql/stg_boc.sql` staging view
11. `sql/mart_monthly_macro.sql` with derived series + `data_complete` flag
12. `pipeline.py` wiring everything together
13. GitHub Actions CI (lint + unit tests with Postgres service)

---

## 6. Testing Strategy

### Unit tests (no live DB, no live HTTP)

- **respx** intercepts httpx at transport level — no monkey-patching, fully async compatible
- Fixture JSON files in `tests/fixtures/` captured once from the real API and committed
- Tests never hit the network

```python
# tests/test_statcan_client.py
async def test_fetch_cpi_returns_typed_observations(respx_mock, statcan_cpi_fixture):
    respx_mock.get(...).mock(return_value=Response(200, json=statcan_cpi_fixture))
    obs = await client.fetch_indicator("18-10-0004-01")
    assert all(isinstance(o, StatCanObservation) for o in obs)

async def test_retries_on_500(respx_mock):
    # first response: 500, second response: 200 with valid data
    # verifies tenacity retry fires after raise_for_status() raises HTTPStatusError
    respx_mock.get(...).side_effect = [
        Response(500),
        Response(200, json=statcan_cpi_fixture),
    ]
    obs = await client.fetch_indicator("18-10-0004-01")
    assert len(obs) > 0
```

### Integration tests (`@pytest.mark.integration`)

Run locally against real Postgres, skipped in CI unless a Postgres service is available:

```python
@pytest.mark.integration
async def test_upsert_is_idempotent(pg_conn, sample_observations):
    await upsert_statcan(pg_conn, sample_observations, run_id)
    await upsert_statcan(pg_conn, sample_observations, run_id)  # re-run
    with pg_conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM raw.statcan_observations")
        row = await cur.fetchone()
    assert row[0] == len(sample_observations)  # no duplicates
```

### CI (GitHub Actions)

- Lint: ruff + mypy
- Unit tests with Postgres service container
- No dbt parse step until dbt is added

---

## Future Layers (out of scope for this build)

| Layer | Added when |
|---|---|
| Docker Compose (Postgres + pgAdmin) | After pipeline is working locally |
| Alembic migrations | Alongside Docker |
| `Retry-After` header parsing | Alongside Docker / hardening pass |
| dbt models (staging + marts) | Phase 1 extension pass |
| Apache Airflow DAG | Phase 1 extension pass |
| Phase 2 models | Weeks 4–6 |
