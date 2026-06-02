# EconSight Phase 1 — Data Engineering Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested async Python pipeline that ingests 9 Canadian macro indicators from Statistics Canada and Bank of Canada into a PostgreSQL warehouse with staging views and a monthly mart table.

**Architecture:** Vertical slice — CPI end-to-end first, then generalise to all 9 indicators. `src/` layout Python package. Async httpx + tenacity retry. psycopg 3 idempotent upsert. SQL staging views + monthly mart. `pipeline.py` entry point (Airflow/dbt added later).

**Tech Stack:** Python 3.11, PostgreSQL 16, psycopg 3, httpx 0.27, tenacity 8.3, pydantic-settings 2.3, structlog 24.1, pytest 8 + pytest-asyncio 0.23 + respx 0.21, ruff + mypy

**Spec:** `docs/superpowers/specs/2026-06-01-phase1-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package, deps, ruff/mypy/pytest config |
| `.env.example` | Example env vars |
| `.gitignore` | Standard Python ignores |
| `src/econsight/__init__.py` | Package root (empty) |
| `src/econsight/config.py` | `Settings` (pydantic-settings), `get_logger()`, `configure_logging()` |
| `src/econsight/clients/__init__.py` | Empty |
| `src/econsight/clients/base.py` | `BaseApiClient`: httpx async + tenacity retry |
| `src/econsight/clients/statcan.py` | `StatCanObservation` dataclass + `StatCanClient` |
| `src/econsight/clients/boc.py` | `BocObservation` dataclass + `BocClient` (daily→monthly agg) |
| `src/econsight/db/__init__.py` | Empty |
| `src/econsight/db/schema.sql` | DDL: schemas + `raw.*` + `meta.*` + `marts.*` tables |
| `src/econsight/db/connection.py` | `db_connection()`, `execute_sql_file()`, `init_db()` |
| `src/econsight/db/loader.py` | `upsert_statcan()`, `upsert_boc()`, `start_run()`, `finish_run()`, `fail_run()` |
| `src/econsight/pipeline.py` | `run()` + `main()` CLI entry point |
| `sql/stg_statcan.sql` | `CREATE OR REPLACE VIEW staging.stg_statcan_observations` |
| `sql/stg_boc.sql` | `CREATE OR REPLACE VIEW staging.stg_boc_observations` |
| `sql/mart_monthly_macro.sql` | `INSERT INTO marts.mart_monthly_macro_indicators … ON CONFLICT` |
| `tests/__init__.py` | Empty |
| `tests/conftest.py` | Shared fixtures: `pg_conn`, JSON fixture loaders |
| `tests/fixtures/statcan_cpi.json` | Captured StatCan CPI response (18-10-0004-01) |
| `tests/fixtures/statcan_gdp.json` | Captured GDP response (36-10-0104-01) |
| `tests/fixtures/statcan_unemployment.json` | Captured unemployment response |
| `tests/fixtures/statcan_ippi.json` | Captured IPPI response |
| `tests/fixtures/statcan_retail.json` | Captured retail trade response |
| `tests/fixtures/boc_overnight.json` | Captured overnight rate response (V39079) |
| `tests/fixtures/boc_cadusd.json` | Captured CAD/USD response (FXCADUSD) |
| `tests/fixtures/boc_bond10yr.json` | Captured 10-yr bond response (V122487) |
| `tests/fixtures/boc_m2pp.json` | Captured M2++ response (V41552796) |
| `tests/test_base_client.py` | Retry behaviour tests |
| `tests/test_statcan_client.py` | StatCan client unit tests |
| `tests/test_boc_client.py` | BoC client unit tests |
| `tests/test_loader.py` | Loader integration tests (`@pytest.mark.integration`) |
| `.github/workflows/ci.yml` | Lint (ruff + mypy) + unit tests on push/PR |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/econsight/__init__.py`, `src/econsight/clients/__init__.py`, `src/econsight/db/__init__.py`
- Create: `tests/__init__.py`, `tests/fixtures/` (empty dir)
- Create: `sql/` (empty dir)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p src/econsight/clients src/econsight/db tests/fixtures sql docs/superpowers/plans
touch src/econsight/__init__.py src/econsight/clients/__init__.py src/econsight/db/__init__.py
touch tests/__init__.py
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "econsight"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "tenacity>=8.3",
    "psycopg[binary]>=3.1",
    "pydantic-settings>=2.3",
    "structlog>=24.1",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "ruff>=0.4",
    "mypy>=1.10",
]

[project.scripts]
econsight-run = "econsight.pipeline:main"

[tool.hatch.build.targets.wheel]
packages = ["src/econsight"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "integration: requires live PostgreSQL (skip with '-m not integration')",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
dist/
.env
*.egg-info/
.mypy_cache/
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 4: Write `.env.example`**

```
DB_URL=postgresql://postgres:password@localhost:5432/econsight
LOG_LEVEL=DEBUG
HTTP_TIMEOUT=30.0
HTTP_MAX_RETRIES=5
```

- [ ] **Step 5: Create a `.env` from the example (do not commit)**

```bash
cp .env.example .env
# Edit DB_URL to match your local Postgres credentials
```

- [ ] **Step 6: Install in editable mode with dev deps**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

- [ ] **Step 7: Verify tooling**

```bash
ruff check src/ tests/
```
Expected: no output (nothing to lint yet)

- [ ] **Step 8: Commit**

```bash
git init
git add pyproject.toml .gitignore .env.example src/ tests/ sql/ docs/
git commit -m "feat: project scaffolding — src layout, pyproject.toml, tooling config"
```

---

## Task 2: Configuration and Logging

**Files:**
- Create: `src/econsight/config.py`

- [ ] **Step 1: Write `src/econsight/config.py`**

```python
import logging
import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_url: str = "postgresql://postgres:password@localhost:5432/econsight"
    log_level: str = "INFO"
    # Trailing slash required for correct httpx base_url path merging
    statcan_base_url: str = "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/"
    boc_base_url: str = "https://www.bankofcanada.ca/valet/"
    http_timeout: float = 30.0
    http_max_retries: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if settings.log_level.upper() == "DEBUG":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return structlog.get_logger(name)
```

- [ ] **Step 2: Write a quick smoke test**

```bash
python -c "from econsight.config import settings, configure_logging; configure_logging(); print(settings.model_dump())"
```
Expected: prints all settings without error

- [ ] **Step 3: Run linter and type-checker**

```bash
ruff check src/econsight/config.py
mypy src/econsight/config.py
```
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add src/econsight/config.py
git commit -m "feat: add pydantic-settings config and structlog setup"
```

---

## Task 3: Database Schema and Connection

**Files:**
- Create: `src/econsight/db/schema.sql`
- Create: `src/econsight/db/connection.py`

- [ ] **Step 1: Create a local Postgres database**

```bash
createdb econsight
# Or via psql: CREATE DATABASE econsight;
```

- [ ] **Step 2: Write `src/econsight/db/schema.sql`**

```sql
-- Schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS meta;

-- raw.statcan_observations
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

-- raw.boc_observations
CREATE TABLE IF NOT EXISTS raw.boc_observations (
    id              bigserial   PRIMARY KEY,
    series_key      text        NOT NULL,
    reference_date  date        NOT NULL,   -- always first day of month
    value           numeric     NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    pipeline_run_id uuid,
    UNIQUE (series_key, reference_date)
);

-- meta.pipeline_runs
CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz,
    status       text        CHECK (status IN ('running', 'success', 'failed')),
    rows_loaded  int,
    error_msg    text
);

-- marts.mart_monthly_macro_indicators
CREATE TABLE IF NOT EXISTS marts.mart_monthly_macro_indicators (
    period_date         date        NOT NULL,
    period_label        text        NOT NULL,
    gdp                 numeric,
    cpi                 numeric,
    unemployment_rate   numeric,
    ippi                numeric,
    retail_trade        numeric,
    overnight_rate      numeric,
    cadusd              numeric,
    bond_10yr           numeric,
    m2pp                numeric,
    cpi_yoy             numeric,
    yield_spread        numeric,
    unemployment_delta  numeric,
    updated_at          timestamptz NOT NULL DEFAULT now(),
    data_complete       boolean GENERATED ALWAYS AS (
                            cpi IS NOT NULL AND unemployment_rate IS NOT NULL
                            AND overnight_rate IS NOT NULL AND bond_10yr IS NOT NULL
                            AND gdp IS NOT NULL
                        ) STORED,
    UNIQUE (period_date)
);
```

- [ ] **Step 3: Write `src/econsight/db/connection.py`**

```python
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import psycopg

from econsight.config import settings

# src/econsight/db/connection.py → 4 parents up → repo root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@asynccontextmanager
async def db_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with await psycopg.AsyncConnection.connect(settings.db_url) as conn:
        yield conn


async def execute_sql_file(conn: psycopg.AsyncConnection, relative_path: str) -> None:
    """Execute a SQL file resolved from the project root."""
    sql = (PROJECT_ROOT / relative_path).read_text()
    await conn.execute(sql)


async def init_db() -> None:
    """Create all schemas, tables, and staging views. Safe to re-run."""
    schema_sql = (Path(__file__).parent / "schema.sql").read_text()
    stg_statcan = (PROJECT_ROOT / "sql" / "stg_statcan.sql").read_text()
    stg_boc = (PROJECT_ROOT / "sql" / "stg_boc.sql").read_text()

    async with await psycopg.AsyncConnection.connect(
        settings.db_url, autocommit=True
    ) as conn:
        await conn.execute(schema_sql)
        await conn.execute(stg_statcan)
        await conn.execute(stg_boc)


def init_db_entrypoint() -> None:
    import asyncio
    asyncio.run(init_db())
```

- [ ] **Step 4: Write stub SQL files so `init_db` doesn't fail**

`sql/stg_statcan.sql` (placeholder — replaced in Task 10):
```sql
CREATE OR REPLACE VIEW staging.stg_statcan_observations AS
SELECT * FROM raw.statcan_observations WHERE false;
```

`sql/stg_boc.sql` (placeholder — replaced in Task 10):
```sql
CREATE OR REPLACE VIEW staging.stg_boc_observations AS
SELECT * FROM raw.boc_observations WHERE false;
```

- [ ] **Step 5: Run `init_db` to verify the schema applies cleanly**

```bash
python -c "import asyncio; from econsight.db.connection import init_db; asyncio.run(init_db())"
```
Expected: no errors. Verify in psql:
```bash
psql econsight -c "\dn"          # should show raw, staging, marts, meta
psql econsight -c "\dt raw.*"    # should show statcan_observations, boc_observations
psql econsight -c "\dt meta.*"   # should show pipeline_runs
psql econsight -c "\dt marts.*"  # should show mart_monthly_macro_indicators
```

- [ ] **Step 6: Commit**

```bash
git add src/econsight/db/schema.sql src/econsight/db/connection.py sql/stg_statcan.sql sql/stg_boc.sql
git commit -m "feat: add DB schema DDL and psycopg3 connection helpers"
```

---

## Task 4: Base HTTP Client with Retry

**Files:**
- Create: `src/econsight/clients/base.py`
- Create: `tests/test_base_client.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_base_client.py`:
```python
import httpx
import pytest
import respx
import tenacity

from econsight.clients.base import BaseApiClient


@pytest.fixture
def client() -> BaseApiClient:
    return BaseApiClient(base_url="https://test.example.com/")


async def test_get_returns_json_on_200(client: BaseApiClient) -> None:
    with respx.mock:
        respx.get("https://test.example.com/data").mock(
            return_value=httpx.Response(200, json={"key": "value"})
        )
        result = await client._get("data")
    assert result == {"key": "value"}


async def test_get_retries_on_server_error(
    client: BaseApiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def instant_sleep(_: float) -> None:
        pass
    # Patch AsyncRetrying.sleep directly — tenacity captures the reference at class
    # definition time so patching asyncio.sleep globally has no effect.
    monkeypatch.setattr(tenacity.AsyncRetrying, "sleep", staticmethod(instant_sleep))

    with respx.mock:
        route = respx.get("https://test.example.com/data")
        route.side_effect = [
            httpx.Response(500),
            httpx.Response(200, json={"ok": True}),
        ]
        result = await client._get("data")

    assert result == {"ok": True}
    assert route.call_count == 2


async def test_get_raises_after_max_retries(
    client: BaseApiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def instant_sleep(_: float) -> None:
        pass
    monkeypatch.setattr(tenacity.AsyncRetrying, "sleep", staticmethod(instant_sleep))

    with respx.mock:
        respx.get("https://test.example.com/data").mock(
            return_value=httpx.Response(503)
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client._get("data")


async def test_context_manager_closes_client() -> None:
    async with BaseApiClient(base_url="https://test.example.com/") as c:
        assert not c._client.is_closed
    assert c._client.is_closed
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_base_client.py -v
```
Expected: `ImportError` or `ModuleNotFoundError` — `base.py` doesn't exist yet

- [ ] **Step 3: Write `src/econsight/clients/base.py`**

```python
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from econsight.config import get_logger, settings

logger = get_logger(__name__)


class BaseApiClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=settings.http_timeout,
        )

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(settings.http_max_retries),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        reraise=True,
    )
    async def _get(self, path: str, **params: str) -> Any:
        logger.debug("http.get", path=path, params=params)
        response = await self._client.get(path, params=params)
        response.raise_for_status()   # raises HTTPStatusError on 4xx/5xx
        return response.json()

    async def __aenter__(self) -> "BaseApiClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.aclose()
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
pytest tests/test_base_client.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/econsight/clients/base.py tests/test_base_client.py
git commit -m "feat: base HTTP client with tenacity exponential back-off retry"
```

---

## Task 5: StatCan CPI Client — Vertical Slice Start

**Files:**
- Create: `tests/fixtures/statcan_cpi.json` (captured from real API)
- Create: `src/econsight/clients/statcan.py` (CPI only)
- Create: `tests/test_statcan_client.py`

### About the StatCan WDS API

Endpoint: `GET {statcan_base_url}getDataFromCubePidCoordAndLatestNPeriods/{pid}/{coord}/{n}`

- PID: strip hyphens from table ID → `18-10-0004-01` → `1810000401`
- Coordinate `1.1` selects the Canada-level all-items total for CPI
- `120` fetches 10 years of monthly data

Response structure (array, one element per coordinate):
```json
[
  {
    "responseStatusCode": 0,
    "vectorDataPoint": [
      {
        "refPer": "2024-03",
        "value": 160.8,
        "statusCode": 1
      }
    ]
  }
]
```

`statusCode`: `1` = final ("A"), `2` = preliminary ("P"), others map to "P" by convention.

- [ ] **Step 1: Capture the real CPI fixture**

```bash
curl -s "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/getDataFromCubePidCoordAndLatestNPeriods/1810000401/1.1/120" \
  | python -m json.tool > tests/fixtures/statcan_cpi.json
```

Verify the file is non-empty and contains `vectorDataPoint`. If coordinate `1.1` returns an empty array, inspect the API response for available coordinates:
```bash
curl -s "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/getSeriesInfoFromCubePid/1810000401" \
  | python -m json.tool | head -60
```
Adjust the coordinate in the fixture capture command if needed.

- [ ] **Step 2: Write the failing tests**

`tests/test_statcan_client.py`:
```python
import json
from dataclasses import fields
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

from econsight.clients.statcan import StatCanClient, StatCanObservation

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def cpi_fixture() -> dict:
    return json.loads((FIXTURES / "statcan_cpi.json").read_text())


@pytest.fixture
def client() -> StatCanClient:
    return StatCanClient()


async def test_fetch_cpi_returns_observations(
    client: StatCanClient, cpi_fixture: dict, respx_mock: respx.MockRouter
) -> None:
    pid = "1810000401"
    respx_mock.get(
        url__regex=rf".*{pid}.*"
    ).mock(return_value=httpx.Response(200, json=cpi_fixture))

    obs = await client.fetch_indicator("18-10-0004-01")

    assert len(obs) > 0
    assert all(isinstance(o, StatCanObservation) for o in obs)


async def test_observation_fields_are_typed(
    client: StatCanClient, cpi_fixture: dict, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(url__regex=r".*1810000401.*").mock(
        return_value=httpx.Response(200, json=cpi_fixture)
    )
    obs = await client.fetch_indicator("18-10-0004-01")
    first = obs[0]

    assert isinstance(first.indicator_key, str)
    assert isinstance(first.reference_date, date)
    assert isinstance(first.value, Decimal)
    assert first.status in ("A", "P")


async def test_fetch_skips_null_values(
    client: StatCanClient, respx_mock: respx.MockRouter
) -> None:
    payload = [{"responseStatusCode": 0, "vectorDataPoint": [
        {"refPer": "2024-01", "value": None, "statusCode": 1},
        {"refPer": "2024-02", "value": 161.0, "statusCode": 1},
    ]}]
    respx_mock.get(url__regex=r".*1810000401.*").mock(
        return_value=httpx.Response(200, json=payload)
    )
    obs = await client.fetch_indicator("18-10-0004-01")
    assert len(obs) == 1
    assert obs[0].reference_date == date(2024, 2, 1)
```

- [ ] **Step 3: Run tests — confirm they fail**

```bash
pytest tests/test_statcan_client.py -v
```
Expected: `ImportError` — `statcan.py` doesn't exist yet

- [ ] **Step 4: Write `src/econsight/clients/statcan.py` (CPI only)**

```python
import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from econsight.clients.base import BaseApiClient
from econsight.config import get_logger, settings

logger = get_logger(__name__)


@dataclass
class StatCanObservation:
    indicator_key: str
    reference_date: date
    value: Decimal
    status: str        # "A" (final) or "P" (preliminary)
    ingested_at: datetime


class StatCanClient(BaseApiClient):
    # Maps friendly name → (table_id, coordinate)
    # Coordinate "1.1" = Canada-level total for single-dimension tables.
    # Verify coordinates by inspecting: getSeriesInfoFromCubePid/{pid}
    INDICATORS: dict[str, tuple[str, str]] = {
        "cpi": ("18-10-0004-01", "1.1"),
    }

    def __init__(self) -> None:
        super().__init__(base_url=settings.statcan_base_url)

    async def fetch_indicator(self, table_id: str) -> list[StatCanObservation]:
        pid = table_id.replace("-", "")
        # Find the coordinate for this table_id
        coord = next(
            (c for _, (tid, c) in self.INDICATORS.items() if tid == table_id),
            "1.1",
        )
        path = f"getDataFromCubePidCoordAndLatestNPeriods/{pid}/{coord}/120"
        raw: list[dict] = await self._get(path)
        return self._parse(raw, table_id)

    def _parse(self, raw: list[dict], indicator_key: str) -> list[StatCanObservation]:
        if not raw or raw[0].get("responseStatusCode") != 0:
            raise ValueError(f"Unexpected response for {indicator_key}: {str(raw)[:200]}")
        points = raw[0].get("vectorDataPoint", [])
        now = datetime.now(tz=timezone.utc)
        result = []
        for pt in points:
            if pt.get("value") is None:
                continue
            ref = pt["refPer"]  # "YYYY-MM" or "YYYY-MM-DD"
            if len(ref) == 7:
                ref_date = date.fromisoformat(ref + "-01")
            else:
                ref_date = date.fromisoformat(ref[:10])
            status = "A" if pt.get("statusCode") == 1 else "P"
            result.append(StatCanObservation(
                indicator_key=indicator_key,
                reference_date=ref_date,
                value=Decimal(str(pt["value"])),
                status=status,
                ingested_at=now,
            ))
        return result

    async def fetch_all(self) -> list[StatCanObservation]:
        batches = await asyncio.gather(*[
            self.fetch_indicator(tid)
            for _, (tid, _) in self.INDICATORS.items()
        ])
        return [obs for batch in batches for obs in batch]
```

- [ ] **Step 5: Run tests — confirm they pass**

```bash
pytest tests/test_statcan_client.py -v
```
Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/statcan_cpi.json src/econsight/clients/statcan.py tests/test_statcan_client.py
git commit -m "feat: StatCan CPI client with typed observations (vertical slice)"
```

---

## Task 6: StatCan Upsert Loader

**Files:**
- Create: `src/econsight/db/loader.py`
- Create: `tests/test_loader.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
import pytest
import psycopg
from econsight.config import settings


@pytest.fixture
async def pg_conn():
    """Integration test fixture — requires live PostgreSQL."""
    async with await psycopg.AsyncConnection.connect(settings.db_url) as conn:
        yield conn
        await conn.rollback()  # clean up after each test
```

- [ ] **Step 2: Write the failing integration test**

`tests/test_loader.py`:
```python
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from econsight.clients.statcan import StatCanObservation
from econsight.db.loader import upsert_statcan


@pytest.mark.integration
async def test_upsert_statcan_inserts_rows(pg_conn) -> None:
    run_id = uuid.uuid4()
    obs = [StatCanObservation(
        indicator_key="18-10-0004-01",
        reference_date=date(2024, 1, 1),
        value=Decimal("160.8"),
        status="A",
        ingested_at=datetime.now(tz=timezone.utc),
    )]
    count = await upsert_statcan(pg_conn, obs, run_id)
    assert count == 1


@pytest.mark.integration
async def test_upsert_statcan_is_idempotent(pg_conn) -> None:
    run_id = uuid.uuid4()
    obs = [StatCanObservation(
        indicator_key="18-10-0004-01",
        reference_date=date(2024, 2, 1),
        value=Decimal("161.2"),
        status="A",
        ingested_at=datetime.now(tz=timezone.utc),
    )]
    await upsert_statcan(pg_conn, obs, run_id)
    await upsert_statcan(pg_conn, obs, run_id)  # re-run same data

    async with pg_conn.cursor() as cur:
        await cur.execute(
            "SELECT COUNT(*) FROM raw.statcan_observations "
            "WHERE indicator_key = %s AND reference_date = %s",
            ("18-10-0004-01", date(2024, 2, 1)),
        )
        row = await cur.fetchone()
    assert row is not None and row[0] == 1  # no duplicates


@pytest.mark.integration
async def test_upsert_statcan_updates_value_on_conflict(pg_conn) -> None:
    run_id = uuid.uuid4()
    base = StatCanObservation(
        indicator_key="18-10-0004-01",
        reference_date=date(2024, 3, 1),
        value=Decimal("160.0"),
        status="P",
        ingested_at=datetime.now(tz=timezone.utc),
    )
    await upsert_statcan(pg_conn, [base], run_id)

    revised = StatCanObservation(
        indicator_key="18-10-0004-01",
        reference_date=date(2024, 3, 1),
        value=Decimal("160.5"),   # revised value
        status="A",               # now final
        ingested_at=datetime.now(tz=timezone.utc),
    )
    await upsert_statcan(pg_conn, [revised], run_id)

    async with pg_conn.cursor() as cur:
        await cur.execute(
            "SELECT value, status FROM raw.statcan_observations "
            "WHERE indicator_key = %s AND reference_date = %s",
            ("18-10-0004-01", date(2024, 3, 1)),
        )
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == Decimal("160.5")
    assert row[1] == "A"
```

- [ ] **Step 3: Stub out `src/econsight/clients/boc.py`**

`loader.py` imports `BocObservation`, but `boc.py` is not written until Task 8. Create a minimal stub now so the import resolves:

```python
# src/econsight/clients/boc.py — STUB, replaced in Task 8
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class BocObservation:
    series_key: str
    reference_date: date
    value: Decimal
    ingested_at: datetime
```

- [ ] **Step 4: Run integration tests — confirm they fail**

```bash
pytest tests/test_loader.py -v -m integration
```
Expected: `ImportError` — `loader.py` doesn't exist yet

- [ ] **Step 5: Write `src/econsight/db/loader.py`**

```python
import uuid
from datetime import datetime, timezone

import psycopg

from econsight.clients.boc import BocObservation
from econsight.clients.statcan import StatCanObservation
from econsight.config import get_logger

logger = get_logger(__name__)

_STATCAN_UPSERT = """
    INSERT INTO raw.statcan_observations
        (indicator_key, reference_date, value, status, ingested_at, pipeline_run_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (indicator_key, reference_date) DO UPDATE SET
        value           = EXCLUDED.value,
        status          = EXCLUDED.status,
        ingested_at     = EXCLUDED.ingested_at,
        pipeline_run_id = EXCLUDED.pipeline_run_id
"""

_BOC_UPSERT = """
    INSERT INTO raw.boc_observations
        (series_key, reference_date, value, ingested_at, pipeline_run_id)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (series_key, reference_date) DO UPDATE SET
        value           = EXCLUDED.value,
        ingested_at     = EXCLUDED.ingested_at,
        pipeline_run_id = EXCLUDED.pipeline_run_id
"""


async def upsert_statcan(
    conn: psycopg.AsyncConnection,
    observations: list[StatCanObservation],
    run_id: uuid.UUID,
    batch_size: int = 1000,
) -> int:
    total = 0
    async with conn.cursor() as cur:
        for i in range(0, len(observations), batch_size):
            batch = observations[i : i + batch_size]
            params = [
                (o.indicator_key, o.reference_date, o.value,
                 o.status, o.ingested_at, run_id)
                for o in batch
            ]
            await cur.executemany(_STATCAN_UPSERT, params)
            total += len(batch)
    logger.info("loader.statcan.upserted", count=total)
    return total


async def upsert_boc(
    conn: psycopg.AsyncConnection,
    observations: list[BocObservation],
    run_id: uuid.UUID,
    batch_size: int = 1000,
) -> int:
    total = 0
    async with conn.cursor() as cur:
        for i in range(0, len(observations), batch_size):
            batch = observations[i : i + batch_size]
            params = [
                (o.series_key, o.reference_date, o.value, o.ingested_at, run_id)
                for o in batch
            ]
            await cur.executemany(_BOC_UPSERT, params)
            total += len(batch)
    logger.info("loader.boc.upserted", count=total)
    return total


async def start_run(conn: psycopg.AsyncConnection) -> uuid.UUID:
    run_id = uuid.uuid4()
    async with conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO meta.pipeline_runs (id, status) VALUES (%s, 'running')",
            (run_id,),
        )
    return run_id


async def finish_run(
    conn: psycopg.AsyncConnection, run_id: uuid.UUID, rows_loaded: int
) -> None:
    async with conn.cursor() as cur:
        await cur.execute(
            "UPDATE meta.pipeline_runs SET status='success', rows_loaded=%s, "
            "finished_at=now() WHERE id=%s",
            (rows_loaded, run_id),
        )


async def fail_run(
    conn: psycopg.AsyncConnection, run_id: uuid.UUID, error_msg: str
) -> None:
    async with conn.cursor() as cur:
        await cur.execute(
            "UPDATE meta.pipeline_runs SET status='failed', error_msg=%s, "
            "finished_at=now() WHERE id=%s",
            (error_msg[:500], run_id),
        )
```

- [ ] **Step 6: Run integration tests — confirm they pass**

```bash
pytest tests/test_loader.py -v -m integration
```
Expected: 3 PASSED

- [ ] **Step 7: Run all tests to check for regressions**

```bash
pytest -v -m "not integration"
```
Expected: all existing unit tests still PASS

- [ ] **Step 8: Commit**

```bash
git add src/econsight/clients/boc.py src/econsight/db/loader.py tests/test_loader.py tests/conftest.py
git commit -m "feat: idempotent upsert loader for StatCan + pipeline_runs audit table"
```

---

## Task 7: Expand StatCan to All 5 Indicators

**Files:**
- Modify: `src/econsight/clients/statcan.py` (add 4 indicators)
- Create: `tests/fixtures/statcan_gdp.json`
- Create: `tests/fixtures/statcan_unemployment.json`
- Create: `tests/fixtures/statcan_ippi.json`
- Create: `tests/fixtures/statcan_retail.json`
- Modify: `tests/test_statcan_client.py` (add coverage)

- [ ] **Step 1: Capture the 4 remaining fixtures**

```bash
# GDP (36-10-0104-01) — quarterly, coordinate may vary; try 1.1
curl -s "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/getDataFromCubePidCoordAndLatestNPeriods/3610010401/1.1/60" \
  | python -m json.tool > tests/fixtures/statcan_gdp.json

# Unemployment (14-10-0287-01) — both sexes, 15+, Canada = try coord 1.1.1
curl -s "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/getDataFromCubePidCoordAndLatestNPeriods/1410028701/1.1.1/120" \
  | python -m json.tool > tests/fixtures/statcan_unemployment.json

# IPPI (18-10-0266-01) — total = try 1.1
curl -s "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/getDataFromCubePidCoordAndLatestNPeriods/1810026601/1.1/120" \
  | python -m json.tool > tests/fixtures/statcan_ippi.json

# Retail trade (20-10-0008-01) — seasonally adj total = try 1.1
curl -s "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/getDataFromCubePidCoordAndLatestNPeriods/2010000801/1.1/120" \
  | python -m json.tool > tests/fixtures/statcan_retail.json
```

For each fixture, verify `vectorDataPoint` is non-empty. If a coordinate is wrong (empty array), inspect `getSeriesInfoFromCubePid/{pid}` to find the correct coordinate and re-capture.

- [ ] **Step 2: Expand `INDICATORS` dict in `statcan.py`**

Replace the `INDICATORS` dict:
```python
INDICATORS: dict[str, tuple[str, str]] = {
    "cpi":          ("18-10-0004-01", "1.1"),
    "gdp":          ("36-10-0104-01", "1.1"),
    "unemployment": ("14-10-0287-01", "1.1.1"),
    "ippi":         ("18-10-0266-01", "1.1"),
    "retail_trade": ("20-10-0008-01", "1.1"),
}
```

Update `INDICATORS` to match whichever coordinates produced non-empty fixtures in Step 1.

- [ ] **Step 3: Add parametrised test for all 5 indicators**

Add to `tests/test_statcan_client.py`:
```python
@pytest.mark.parametrize("name,table_id,fixture_file", [
    ("cpi",          "18-10-0004-01", "statcan_cpi.json"),
    ("gdp",          "36-10-0104-01", "statcan_gdp.json"),
    ("unemployment", "14-10-0287-01", "statcan_unemployment.json"),
    ("ippi",         "18-10-0266-01", "statcan_ippi.json"),
    ("retail_trade", "20-10-0008-01", "statcan_retail.json"),
])
async def test_fetch_indicator_returns_observations(
    client: StatCanClient,
    respx_mock: respx.MockRouter,
    name: str,
    table_id: str,
    fixture_file: str,
) -> None:
    fixture = json.loads((FIXTURES / fixture_file).read_text())
    pid = table_id.replace("-", "")
    respx_mock.get(url__regex=rf".*{pid}.*").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    obs = await client.fetch_indicator(table_id)
    assert len(obs) > 0, f"No observations parsed for {name}"
    assert all(o.indicator_key == table_id for o in obs)


async def test_fetch_all_returns_all_5_indicators(
    client: StatCanClient, respx_mock: respx.MockRouter
) -> None:
    for name, (table_id, _) in StatCanClient.INDICATORS.items():
        fixture_file = f"statcan_{name}.json"
        fixture = json.loads((FIXTURES / fixture_file).read_text())
        pid = table_id.replace("-", "")
        respx_mock.get(url__regex=rf".*{pid}.*").mock(
            return_value=httpx.Response(200, json=fixture)
        )
    obs = await client.fetch_all()
    keys = {o.indicator_key for o in obs}
    assert keys == {tid for _, (tid, _) in StatCanClient.INDICATORS.items()}
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_statcan_client.py -v
```
Expected: all PASS (5 parametrised + existing tests)

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/statcan_*.json src/econsight/clients/statcan.py tests/test_statcan_client.py
git commit -m "feat: expand StatCan client to all 5 macro indicators"
```

---

## Task 8: Bank of Canada Overnight Rate Client — Vertical Slice

**Files:**
- Create: `tests/fixtures/boc_overnight.json` (captured)
- Create: `src/econsight/clients/boc.py` (overnight rate only)
- Create: `tests/test_boc_client.py`

### About the BoC Valet API

Endpoint: `GET {boc_base_url}observations/{seriesKey}/json?start_date=2010-01-01`

Response:
```json
{
  "terms": {"url": "..."},
  "seriesDetail": {
    "V39079": {"label": "Target for the Overnight Rate", ...}
  },
  "observations": [
    {"d": "2024-01-03", "V39079": {"v": "5.00"}},
    {"d": "2024-01-04", "V39079": {"v": "5.00"}},
    ...
  ]
}
```

Daily series are aggregated to **month-end value** (last observation per calendar month), stored with `reference_date` = first day of that month. M2++ is already monthly — no aggregation needed.

- [ ] **Step 1: Capture the overnight rate fixture**

```bash
curl -s "https://www.bankofcanada.ca/valet/observations/V39079/json?start_date=2010-01-01" \
  | python -m json.tool > tests/fixtures/boc_overnight.json
```

Verify `observations` array is non-empty.

- [ ] **Step 2: Write the failing tests**

`tests/test_boc_client.py`:
```python
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

from econsight.clients.boc import BocClient, BocObservation

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def overnight_fixture() -> dict:
    return json.loads((FIXTURES / "boc_overnight.json").read_text())


@pytest.fixture
def client() -> BocClient:
    return BocClient()


async def test_fetch_overnight_returns_observations(
    client: BocClient, overnight_fixture: dict, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(url__regex=r".*V39079.*").mock(
        return_value=httpx.Response(200, json=overnight_fixture)
    )
    obs = await client.fetch_series("V39079")
    assert len(obs) > 0
    assert all(isinstance(o, BocObservation) for o in obs)


async def test_daily_aggregates_to_month_end(
    client: BocClient, respx_mock: respx.MockRouter
) -> None:
    # Three observations in Jan 2024: first, middle, last business day
    payload = {"observations": [
        {"d": "2024-01-03", "V39079": {"v": "5.00"}},
        {"d": "2024-01-17", "V39079": {"v": "5.00"}},
        {"d": "2024-01-31", "V39079": {"v": "5.25"}},  # month-end
    ]}
    respx_mock.get(url__regex=r".*V39079.*").mock(
        return_value=httpx.Response(200, json=payload)
    )
    obs = await client.fetch_series("V39079")
    assert len(obs) == 1
    assert obs[0].reference_date == date(2024, 1, 1)
    assert obs[0].value == Decimal("5.25")  # last value wins


async def test_skips_missing_values(
    client: BocClient, respx_mock: respx.MockRouter
) -> None:
    payload = {"observations": [
        {"d": "2024-02-01", "V39079": {"v": ""}},
        {"d": "2024-02-28", "V39079": {"v": "5.00"}},
    ]}
    respx_mock.get(url__regex=r".*V39079.*").mock(
        return_value=httpx.Response(200, json=payload)
    )
    obs = await client.fetch_series("V39079")
    assert len(obs) == 1
    assert obs[0].value == Decimal("5.00")
```

- [ ] **Step 3: Run tests — confirm they fail**

```bash
pytest tests/test_boc_client.py -v
```
Expected: `ImportError: cannot import name 'BocClient' from 'econsight.clients.boc'` — the stub has no `BocClient` yet

- [ ] **Step 4: Write `src/econsight/clients/boc.py` (overnight rate only)**

```python
import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from econsight.clients.base import BaseApiClient
from econsight.config import get_logger, settings

logger = get_logger(__name__)


@dataclass
class BocObservation:
    series_key: str
    reference_date: date      # first day of month
    value: Decimal
    ingested_at: datetime


class BocClient(BaseApiClient):
    # Maps friendly name → series key
    SERIES: dict[str, str] = {
        "overnight_rate": "V39079",
    }

    def __init__(self) -> None:
        super().__init__(base_url=settings.boc_base_url)

    async def fetch_series(self, series_key: str) -> list[BocObservation]:
        path = f"observations/{series_key}/json"
        raw: dict = await self._get(path, start_date="2010-01-01")
        return self._parse(raw, series_key)

    def _parse(self, raw: dict, series_key: str) -> list[BocObservation]:
        observations_raw = raw.get("observations", [])
        now = datetime.now(tz=timezone.utc)
        # Group by (year, month) — keep last non-empty value (month-end)
        monthly: dict[tuple[int, int], BocObservation] = {}
        for obs in observations_raw:
            value_str = (obs.get(series_key) or {}).get("v", "")
            if not value_str:
                continue
            obs_date = date.fromisoformat(obs["d"])
            key = (obs_date.year, obs_date.month)
            monthly[key] = BocObservation(
                series_key=series_key,
                reference_date=date(obs_date.year, obs_date.month, 1),
                value=Decimal(value_str),
                ingested_at=now,
            )
        return list(monthly.values())

    async def fetch_all(self) -> list[BocObservation]:
        batches = await asyncio.gather(*[
            self.fetch_series(sk) for sk in self.SERIES.values()
        ])
        return [obs for batch in batches for obs in batch]
```

- [ ] **Step 5: Run tests — confirm they pass**

```bash
pytest tests/test_boc_client.py -v
```
Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/boc_overnight.json src/econsight/clients/boc.py tests/test_boc_client.py
git commit -m "feat: BoC Valet client — overnight rate with daily-to-monthly aggregation"
```

---

## Task 9: Expand BoC to All 4 Series

**Files:**
- Modify: `src/econsight/clients/boc.py` (add 3 series)
- Create: `tests/fixtures/boc_cadusd.json`
- Create: `tests/fixtures/boc_bond10yr.json`
- Create: `tests/fixtures/boc_m2pp.json`
- Modify: `tests/test_boc_client.py`

- [ ] **Step 1: Capture the 3 remaining fixtures**

```bash
curl -s "https://www.bankofcanada.ca/valet/observations/FXCADUSD/json?start_date=2010-01-01" \
  | python -m json.tool > tests/fixtures/boc_cadusd.json

curl -s "https://www.bankofcanada.ca/valet/observations/V122487/json?start_date=2010-01-01" \
  | python -m json.tool > tests/fixtures/boc_bond10yr.json

curl -s "https://www.bankofcanada.ca/valet/observations/V41552796/json?start_date=2010-01-01" \
  | python -m json.tool > tests/fixtures/boc_m2pp.json
```

- [ ] **Step 2: Expand `SERIES` dict in `boc.py`**

```python
SERIES: dict[str, str] = {
    "overnight_rate": "V39079",
    "cadusd":         "FXCADUSD",
    "bond_10yr":      "V122487",
    "m2pp":           "V41552796",
}
```

Note: M2++ (V41552796) is already monthly — the `_parse` method handles it correctly since each observation will be the only one in its (year, month) bucket.

- [ ] **Step 3: Add parametrised test for all 4 series**

Add to `tests/test_boc_client.py`:
```python
@pytest.mark.parametrize("name,series_key,fixture_file", [
    ("overnight_rate", "V39079",    "boc_overnight.json"),
    ("cadusd",         "FXCADUSD",  "boc_cadusd.json"),
    ("bond_10yr",      "V122487",   "boc_bond10yr.json"),
    ("m2pp",           "V41552796", "boc_m2pp.json"),
])
async def test_fetch_series_returns_observations(
    client: BocClient,
    respx_mock: respx.MockRouter,
    name: str,
    series_key: str,
    fixture_file: str,
) -> None:
    fixture = json.loads((FIXTURES / fixture_file).read_text())
    respx_mock.get(url__regex=rf".*{series_key}.*").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    obs = await client.fetch_series(series_key)
    assert len(obs) > 0, f"No observations for {name}"
    assert all(o.series_key == series_key for o in obs)
    assert all(o.reference_date.day == 1 for o in obs)  # always first of month


async def test_fetch_all_returns_all_4_series(
    client: BocClient, respx_mock: respx.MockRouter
) -> None:
    fixture_map = {
        "V39079":    "boc_overnight.json",
        "FXCADUSD":  "boc_cadusd.json",
        "V122487":   "boc_bond10yr.json",
        "V41552796": "boc_m2pp.json",
    }
    for sk, fname in fixture_map.items():
        fixture = json.loads((FIXTURES / fname).read_text())
        respx_mock.get(url__regex=rf".*{sk}.*").mock(
            return_value=httpx.Response(200, json=fixture)
        )
    obs = await client.fetch_all()
    keys = {o.series_key for o in obs}
    assert keys == set(BocClient.SERIES.values())
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_boc_client.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/boc_*.json src/econsight/clients/boc.py tests/test_boc_client.py
git commit -m "feat: expand BoC client to all 4 series (cadusd, bond10yr, m2pp)"
```

---

## Task 10: Staging SQL Views

**Files:**
- Modify: `sql/stg_statcan.sql` (replace placeholder with real view)
- Modify: `sql/stg_boc.sql` (replace placeholder with real view)

- [ ] **Step 1: Write `sql/stg_statcan.sql`**

```sql
CREATE OR REPLACE VIEW staging.stg_statcan_observations AS
SELECT
    id,
    indicator_key,
    reference_date,
    value,
    status,
    ingested_at,
    pipeline_run_id,
    to_char(reference_date, 'YYYY-MM')          AS period_label,
    status IN ('A', 'P')                         AS is_reliable
FROM raw.statcan_observations;
```

- [ ] **Step 2: Write `sql/stg_boc.sql`**

```sql
CREATE OR REPLACE VIEW staging.stg_boc_observations AS
SELECT
    id,
    series_key,
    reference_date,
    value,
    ingested_at,
    pipeline_run_id,
    to_char(reference_date, 'YYYY-MM')          AS period_label,
    true                                         AS is_month_end
FROM raw.boc_observations;
```

- [ ] **Step 3: Apply views to the local database**

```bash
python -c "import asyncio; from econsight.db.connection import init_db; asyncio.run(init_db())"
```

- [ ] **Step 4: Verify views in psql**

```bash
psql econsight -c "\dv staging.*"
psql econsight -c "SELECT * FROM staging.stg_statcan_observations LIMIT 3;"
psql econsight -c "SELECT * FROM staging.stg_boc_observations LIMIT 3;"
```
Expected: views exist; if raw tables have data from integration tests, rows are returned with `period_label`.

- [ ] **Step 5: Commit**

```bash
git add sql/stg_statcan.sql sql/stg_boc.sql
git commit -m "feat: staging views for StatCan and BoC with period_label and reliability flags"
```

---

## Task 11: Mart SQL — Monthly Macro Indicators

**Files:**
- Modify: `sql/mart_monthly_macro.sql` (replace placeholder with real upsert)
- Modify: `tests/test_loader.py` (add mart integration test)

- [ ] **Step 1: Write the failing mart integration test**

Add to `tests/test_loader.py`:
```python
from econsight.db.connection import execute_sql_file


@pytest.mark.integration
async def test_mart_materialises_after_upsert(pg_conn) -> None:
    import uuid
    from datetime import datetime, timezone
    from decimal import Decimal
    from econsight.clients.boc import BocObservation
    from econsight.db.loader import upsert_boc

    run_id = uuid.uuid4()
    # Insert one StatCan row
    statcan_obs = [StatCanObservation(
        indicator_key="18-10-0004-01",
        reference_date=date(2020, 6, 1),
        value=Decimal("136.0"),
        status="A",
        ingested_at=datetime.now(tz=timezone.utc),
    )]
    await upsert_statcan(pg_conn, statcan_obs, run_id)

    # Insert matching BoC rows
    boc_obs = [
        BocObservation("V39079",    date(2020, 6, 1), Decimal("0.25"), datetime.now(tz=timezone.utc)),
        BocObservation("V122487",   date(2020, 6, 1), Decimal("0.55"), datetime.now(tz=timezone.utc)),
        BocObservation("FXCADUSD",  date(2020, 6, 1), Decimal("0.74"), datetime.now(tz=timezone.utc)),
        BocObservation("V41552796", date(2020, 6, 1), Decimal("2200000"), datetime.now(tz=timezone.utc)),
    ]
    await upsert_boc(pg_conn, boc_obs, run_id)

    # Materialise the mart
    await execute_sql_file(pg_conn, "sql/mart_monthly_macro.sql")

    async with pg_conn.cursor() as cur:
        await cur.execute(
            "SELECT cpi, overnight_rate, yield_spread FROM marts.mart_monthly_macro_indicators "
            "WHERE period_date = %s",
            (date(2020, 6, 1),),
        )
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == Decimal("136.0")   # cpi
    assert row[1] == Decimal("0.25")    # overnight_rate
    assert row[2].normalize() == (Decimal("0.55") - Decimal("0.25")).normalize()  # yield_spread
```

- [ ] **Step 2: Run the failing test to confirm it fails**

```bash
pytest tests/test_loader.py::test_mart_materialises_after_upsert -v -m integration
```
Expected: FAIL — `sql/mart_monthly_macro.sql` is still a placeholder

- [ ] **Step 3: Write `sql/mart_monthly_macro.sql`**

```sql
INSERT INTO marts.mart_monthly_macro_indicators (
    period_date, period_label,
    gdp, cpi, unemployment_rate, ippi, retail_trade,
    overnight_rate, cadusd, bond_10yr, m2pp,
    cpi_yoy, yield_spread, unemployment_delta,
    updated_at
)
WITH monthly_statcan AS (
    SELECT
        date_trunc('month', reference_date)::date                                AS period_date,
        MAX(CASE WHEN indicator_key = '36-10-0104-01' THEN value END)            AS gdp,
        MAX(CASE WHEN indicator_key = '18-10-0004-01' THEN value END)            AS cpi,
        MAX(CASE WHEN indicator_key = '14-10-0287-01' THEN value END)            AS unemployment_rate,
        MAX(CASE WHEN indicator_key = '18-10-0266-01' THEN value END)            AS ippi,
        MAX(CASE WHEN indicator_key = '20-10-0008-01' THEN value END)            AS retail_trade
    FROM raw.statcan_observations
    GROUP BY 1
),
monthly_boc AS (
    SELECT
        date_trunc('month', reference_date)::date                                AS period_date,
        MAX(CASE WHEN series_key = 'V39079'    THEN value END)                   AS overnight_rate,
        MAX(CASE WHEN series_key = 'FXCADUSD'  THEN value END)                   AS cadusd,
        MAX(CASE WHEN series_key = 'V122487'   THEN value END)                   AS bond_10yr,
        MAX(CASE WHEN series_key = 'V41552796' THEN value END)                   AS m2pp
    FROM raw.boc_observations
    GROUP BY 1
),
combined AS (
    SELECT
        s.period_date,
        to_char(s.period_date, 'YYYY-MM')                                        AS period_label,
        s.gdp, s.cpi, s.unemployment_rate, s.ippi, s.retail_trade,
        b.overnight_rate, b.cadusd, b.bond_10yr, b.m2pp,
        ROUND(
            (s.cpi
             / NULLIF(LAG(s.cpi, 12) OVER (ORDER BY s.period_date), 0) - 1
            ) * 100, 2
        )                                                                         AS cpi_yoy,
        ROUND(b.bond_10yr - b.overnight_rate, 4)                                  AS yield_spread,
        ROUND(
            s.unemployment_rate
            - LAG(s.unemployment_rate, 1) OVER (ORDER BY s.period_date), 2
        )                                                                         AS unemployment_delta
    FROM monthly_statcan s
    LEFT JOIN monthly_boc b ON s.period_date = b.period_date
)
SELECT
    period_date, period_label,
    gdp, cpi, unemployment_rate, ippi, retail_trade,
    overnight_rate, cadusd, bond_10yr, m2pp,
    cpi_yoy, yield_spread, unemployment_delta,
    now() AS updated_at
FROM combined
ON CONFLICT (period_date) DO UPDATE SET
    gdp                = EXCLUDED.gdp,
    cpi                = EXCLUDED.cpi,
    unemployment_rate  = EXCLUDED.unemployment_rate,
    ippi               = EXCLUDED.ippi,
    retail_trade       = EXCLUDED.retail_trade,
    overnight_rate     = EXCLUDED.overnight_rate,
    cadusd             = EXCLUDED.cadusd,
    bond_10yr          = EXCLUDED.bond_10yr,
    m2pp               = EXCLUDED.m2pp,
    cpi_yoy            = EXCLUDED.cpi_yoy,
    yield_spread       = EXCLUDED.yield_spread,
    unemployment_delta = EXCLUDED.unemployment_delta,
    updated_at         = EXCLUDED.updated_at;
```

- [ ] **Step 4: Run the mart integration test — confirm it passes**

```bash
pytest tests/test_loader.py::test_mart_materialises_after_upsert -v -m integration
```
Expected: PASS

- [ ] **Step 5: Verify SQL manually with full pipeline data**

```bash
psql econsight -f sql/mart_monthly_macro.sql
psql econsight -c "SELECT period_label, cpi, overnight_rate, yield_spread, data_complete FROM marts.mart_monthly_macro_indicators ORDER BY period_date DESC LIMIT 5;"
```
Expected: rows returned; `data_complete = true` for months where all 5 core series are present.

- [ ] **Step 6: Commit**

```bash
git add sql/mart_monthly_macro.sql tests/test_loader.py
git commit -m "feat: mart SQL — monthly macro indicators with derived series and data_complete flag"
```

---

## Task 12: Pipeline Orchestration Script

**Files:**
- Create: `src/econsight/pipeline.py`

- [ ] **Step 1: Write `src/econsight/pipeline.py`**

```python
import asyncio

from econsight.clients.boc import BocClient
from econsight.clients.statcan import StatCanClient
from econsight.config import configure_logging, get_logger
from econsight.db.connection import db_connection, execute_sql_file
from econsight.db.loader import fail_run, finish_run, start_run, upsert_boc, upsert_statcan

logger = get_logger(__name__)


async def run() -> None:
    configure_logging()
    logger.info("pipeline.start")

    async with db_connection() as conn:
        run_id = None   # guard: start_run may raise before run_id is assigned
        run_id = await start_run(conn)
        try:
            async with StatCanClient() as statcan, BocClient() as boc:
                statcan_data, boc_data = await asyncio.gather(
                    statcan.fetch_all(),
                    boc.fetch_all(),
                )

            rows = await upsert_statcan(conn, statcan_data, run_id)
            rows += await upsert_boc(conn, boc_data, run_id)

            await execute_sql_file(conn, "sql/mart_monthly_macro.sql")
            await conn.commit()

            await finish_run(conn, run_id, rows)
            await conn.commit()

            logger.info("pipeline.complete", rows_loaded=rows)

        except Exception as exc:
            logger.error("pipeline.failed", error=str(exc))
            if run_id is not None:
                await fail_run(conn, run_id, str(exc))
                await conn.commit()
            raise


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the pipeline end-to-end**

```bash
python -m econsight.pipeline
```
Expected:
- Logs showing fetch + upsert for all 9 indicators
- No errors
- `meta.pipeline_runs` shows a new row with `status = 'success'`

Verify in psql:
```bash
psql econsight -c "SELECT id, status, rows_loaded, started_at FROM meta.pipeline_runs ORDER BY started_at DESC LIMIT 3;"
psql econsight -c "SELECT COUNT(*) FROM marts.mart_monthly_macro_indicators WHERE data_complete = true;"
```

- [ ] **Step 3: Run the pipeline a second time (idempotency check)**

```bash
python -m econsight.pipeline
psql econsight -c "SELECT COUNT(*) FROM raw.statcan_observations;"
```
Expected: row count is the same as after the first run (upserts, no duplicates).

- [ ] **Step 4: Run all tests to confirm no regressions**

```bash
pytest -v -m "not integration"
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/econsight/pipeline.py
git commit -m "feat: pipeline.py — async fetch + upsert + mart materialisation, full audit trail"
```

---

## Task 13: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/` directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: ["main"]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"   # install project + stubs so mypy can resolve imports
      - run: ruff check src/ tests/
      - run: mypy src/econsight

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: econsight
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - name: Init database schema
        env:
          DB_URL: postgresql://postgres:password@localhost:5432/econsight
        run: python -c "import asyncio; from econsight.db.connection import init_db; asyncio.run(init_db())"
      - name: Run unit + integration tests
        env:
          DB_URL: postgresql://postgres:password@localhost:5432/econsight
        run: pytest -v --tb=short
```

- [ ] **Step 3: Verify the workflow file is valid YAML**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "Valid YAML"
```
Expected: `Valid YAML`

- [ ] **Step 4: Commit and push**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions — lint (ruff + mypy) + tests with Postgres service"
git remote add origin https://github.com/<your-username>/econsight.git
git push -u origin main
```

- [ ] **Step 5: Verify CI passes on GitHub**

Open the Actions tab on GitHub. Both `lint` and `test` jobs should go green. Fix any failures before declaring Phase 1 complete.

---

## Phase 1 Complete — Checklist

- [ ] `pytest -v -m "not integration"` → all unit tests PASS
- [ ] `pytest -v -m integration` → all integration tests PASS (requires local Postgres)
- [ ] `python -m econsight.pipeline` → runs without error, `pipeline_runs.status = 'success'`
- [ ] `SELECT COUNT(*) FROM marts.mart_monthly_macro_indicators WHERE data_complete = true;` → non-zero
- [ ] GitHub Actions CI → green on `main`
- [ ] `ruff check src/ tests/` → clean
- [ ] `mypy src/econsight` → no errors
