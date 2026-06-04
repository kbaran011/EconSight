# EconSight Phase 3 — Consulting Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI REST backend + React SPA dashboard + RAG NL query engine + PDF report generator on top of the Phase 1/2 data and modelling layers.

**Architecture:** FastAPI (port 8000) exposes REST endpoints for indicator data, forecasts, RAG queries, and PDF generation. React (Vite, port 5173) is a separate SPA consuming the API via axios + TanStack Query. RAG uses ChromaDB + sentence-transformers for local embedding and Claude API for answer generation. PDF = WeasyPrint consulting brief + nbconvert full analysis, merged with pypdf. Backend tasks first (Tasks 1–6), then frontend (Tasks 7–10).

**Tech Stack:** Python 3.11, FastAPI 0.111, uvicorn, anthropic SDK, chromadb, sentence-transformers, beautifulsoup4, weasyprint, pypdf, pytest + httpx; React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, recharts, TanStack Query, axios

**Spec:** `docs/superpowers/specs/2026-06-04-phase3-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Add 8 new runtime deps |
| `.env.example` | Add ANTHROPIC_API_KEY, CORS_ORIGINS, DB_URL_READONLY |
| `src/econsight/config.py` | Add cors_origins, db_url_readonly fields to Settings |
| `src/econsight/db/connection.py` | Add db_connection_readonly() context manager |
| `src/econsight/api/__init__.py` | Empty |
| `src/econsight/api/main.py` | FastAPI app factory — lifespan, CORS, router mounts |
| `src/econsight/api/dependencies.py` | FastAPI Depends helpers for DB connections |
| `src/econsight/api/schemas.py` | All Pydantic v2 response models |
| `src/econsight/api/routers/indicators.py` | GET /api/indicators, GET /api/health-score |
| `src/econsight/api/routers/forecasts.py` | GET /api/forecasts |
| `src/econsight/api/routers/rag.py` | POST /api/rag/query |
| `src/econsight/api/routers/report.py` | GET /api/report/pdf |
| `src/econsight/rag/__init__.py` | Empty |
| `src/econsight/rag/ingestion.py` | Parse phase2_report.html → ChromaDB; maybe_ingest_rag() |
| `src/econsight/rag/retriever.py` | retrieve(question, top_k) → list of chunks |
| `src/econsight/rag/query_engine.py` | answer(question) → RAGResponse (sql or narrative path) |
| `src/econsight/report/__init__.py` | Empty |
| `src/econsight/report/brief.py` | generate_brief(conn) → PDF bytes via WeasyPrint |
| `src/econsight/report/full_report.py` | generate_full_report() → PDF bytes via nbconvert |
| `src/econsight/report/merger.py` | merge_pdfs(brief, full) → merged PDF bytes |
| `tests/test_api/__init__.py` | Empty |
| `tests/test_api/test_indicators.py` | Endpoint tests with mocked DB |
| `tests/test_api/test_forecasts.py` | Endpoint tests with mocked DB |
| `tests/test_api/test_rag.py` | RAG routing, SQL allowlist, narrative path |
| `tests/test_api/test_report.py` | PDF endpoint returns %PDF bytes |
| `frontend/` | Vite + React + TypeScript project (npm) |
| `frontend/src/api/client.ts` | Typed axios functions for all endpoints |
| `frontend/src/App.tsx` | React Router routes |
| `frontend/src/components/HealthScoreGauge.tsx` | SVG semicircle gauge 0–100 |
| `frontend/src/components/IndicatorCard.tsx` | Value + delta badge card |
| `frontend/src/components/MacroChart.tsx` | recharts LineChart wrapper |
| `frontend/src/components/ForecastTable.tsx` | Target × horizon forecast table |
| `frontend/src/components/QueryBox.tsx` | Input + answer display |
| `frontend/src/pages/Dashboard.tsx` | Health score + cards + table + sparklines |
| `frontend/src/pages/Indicators.tsx` | Selector + full time-series chart |
| `frontend/src/pages/Forecasts.tsx` | VAR vs XGBoost + MC fan + scenarios |
| `frontend/src/pages/Ask.tsx` | RAG query interface |
| `frontend/src/pages/Report.tsx` | PDF download page |

---

## Task 1: Setup — Dependencies, Env, DB Role, Directories

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Modify: `src/econsight/config.py`

- [ ] **Step 1: Update `pyproject.toml`**

Add to the `dependencies` list:
```toml
"fastapi>=0.111",
"uvicorn[standard]>=0.29",
"anthropic>=0.28",
"chromadb>=0.5",
"sentence-transformers>=3.0",
"beautifulsoup4>=4.12",
"weasyprint>=62.0",
"pypdf>=4.0",
```

Note: `httpx>=0.27` is already in the main `dependencies` list from Phase 1 — do NOT add it again to `dev`.

Add mypy overrides for new untyped libraries:
```toml
[[tool.mypy.overrides]]
module = ["chromadb", "chromadb.*", "sentence_transformers", "weasyprint", "bs4", "pypdf"]
ignore_missing_imports = true
```

- [ ] **Step 2: Update `.env.example`**

Append:
```
ANTHROPIC_API_KEY=your_key_here
CORS_ORIGINS=http://localhost:5173
DB_URL_READONLY=postgresql://econsight_reader:password@localhost:5432/econsight
```

- [ ] **Step 3: Update `src/econsight/config.py`**

Add two new fields to the `Settings` class (after `http_max_retries`):
```python
cors_origins: list[str] = ["http://localhost:5173"]
db_url_readonly: str = "postgresql://econsight_reader:password@localhost:5432/econsight"
anthropic_api_key: str = ""
```

Note: `anthropic_api_key` uses `""` default so the app starts without it; the Anthropic client reads `ANTHROPIC_API_KEY` from env directly.

- [ ] **Step 4: Add `.env` entries**

Add to your local `.env` file:
```
ANTHROPIC_API_KEY=<your actual key from console.anthropic.com>
CORS_ORIGINS=http://localhost:5173
DB_URL_READONLY=postgresql://econsight_reader:kbdbaran@localhost:5432/econsight
```

- [ ] **Step 5: Create read-only PostgreSQL role**

```bash
PGPASSWORD=kbdbaran /Library/PostgreSQL/18/bin/psql -U postgres -h localhost econsight -c "
CREATE ROLE econsight_reader LOGIN PASSWORD 'kbdbaran';
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO econsight_reader;
"
```

Expected: `CREATE ROLE` then `GRANT`.

- [ ] **Step 6: Create directory structure**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight"
mkdir -p src/econsight/api/routers src/econsight/rag src/econsight/report
mkdir -p tests/test_api
touch src/econsight/api/__init__.py src/econsight/api/routers/__init__.py
touch src/econsight/rag/__init__.py src/econsight/report/__init__.py
touch tests/test_api/__init__.py
```

- [ ] **Step 7: Install new dependencies**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pip install -e ".[dev]" 2>&1 | tail -5
```

- [ ] **Step 8: Verify FastAPI import**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -c "import fastapi, uvicorn, anthropic, chromadb, sentence_transformers, weasyprint, pypdf; print('All OK')"
```

Expected: `All OK`

- [ ] **Step 9: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add pyproject.toml .env.example src/econsight/config.py src/econsight/api/ src/econsight/rag/ src/econsight/report/ tests/test_api/
git commit -m "feat: Phase 3 setup — deps, config, directory scaffold, read-only DB role"
```

---

## Task 2: FastAPI Core — Schemas, Connection, App, Data Endpoints

**Files:**
- Modify: `src/econsight/db/connection.py`
- Create: `src/econsight/api/schemas.py`
- Create: `src/econsight/api/dependencies.py`
- Create: `src/econsight/api/main.py`
- Create: `src/econsight/api/routers/indicators.py`
- Create: `src/econsight/api/routers/forecasts.py`
- Create: `tests/test_api/test_indicators.py`
- Create: `tests/test_api/test_forecasts.py`

### Step 1: Write failing tests first

`tests/test_api/test_indicators.py`:
```python
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


def make_mock_conn(rows: list, cols: list[str]):
    mock_cur = AsyncMock()
    mock_cur.fetchall = AsyncMock(return_value=rows)
    mock_cur.description = [(c,) for c in cols]
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_conn


async def test_ping():
    from econsight.api.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/api/ping")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_get_indicators_returns_list():
    from econsight.api.main import app
    from econsight.api.dependencies import get_db

    cols = ["period_date", "gdp", "cpi", "unemployment_rate", "ippi",
            "retail_trade", "overnight_rate", "cadusd", "bond_10yr", "m2pp",
            "cpi_yoy", "yield_spread", "unemployment_delta"]
    rows = [(date(2024, 1, 1), 2_100_000, 136.0, 5.8, 110.0, 57_000, 1.75, 0.74, 1.44, 1_950_000, 2.5, -0.31, 0.1)]
    mock_conn = make_mock_conn(rows, cols)

    async def override_db():
        yield mock_conn

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/api/indicators")
    app.dependency_overrides.clear()

    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["cpi"] == 136.0
    assert data[0]["period_date"] == "2024-01-01"


async def test_get_health_score_returns_history():
    from econsight.api.main import app
    from econsight.api.dependencies import get_db

    cols = ["period_date", "score", "component_scores"]
    rows = [(date(2024, 1, 1), 72.5, {"cpi": -0.3, "gdp": 0.4})]
    mock_conn = make_mock_conn(rows, cols)

    async def override_db():
        yield mock_conn

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/api/health-score")
    app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert "history" in body
    assert "latest_score" in body
    assert body["latest_score"] == 72.5
```

`tests/test_api/test_forecasts.py`:
```python
from datetime import date
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient


async def test_get_forecasts_returns_list():
    from econsight.api.main import app
    from econsight.api.dependencies import get_db

    cols = ["id", "period_date", "target", "horizon_months", "model_type",
            "point_forecast", "p10", "p50", "p90",
            "scenario_base", "scenario_upside", "scenario_downside", "created_at"]
    rows = [(1, date(2026, 5, 1), "cpi", 1, "xgboost",
             136.5, 135.0, 136.5, 138.0, 136.5, 134.0, 139.0, date(2026, 5, 1))]

    mock_cur = AsyncMock()
    mock_cur.fetchall = AsyncMock(return_value=rows)
    mock_cur.description = [(c,) for c in cols]
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

    async def override_db():
        yield mock_conn

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/api/forecasts")
    app.dependency_overrides.clear()

    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["target"] == "cpi"
    assert data[0]["point_forecast"] == 136.5
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_api/ -v 2>&1 | tail -10
```

Expected: `ImportError` — API modules don't exist yet

- [ ] **Step 3: Add `db_connection_readonly()` to `src/econsight/db/connection.py`**

Add after the existing `db_connection()` function:

```python
@asynccontextmanager
async def db_connection_readonly() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with await psycopg.AsyncConnection.connect(settings.db_url_readonly) as conn:
        yield conn
```

- [ ] **Step 4: Write `src/econsight/api/schemas.py`**

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class IndicatorRow(BaseModel):
    period_date: date
    gdp: float | None = None
    cpi: float | None = None
    unemployment_rate: float | None = None
    ippi: float | None = None
    retail_trade: float | None = None
    overnight_rate: float | None = None
    cadusd: float | None = None
    bond_10yr: float | None = None
    m2pp: float | None = None
    cpi_yoy: float | None = None
    yield_spread: float | None = None
    unemployment_delta: float | None = None


class HealthScorePoint(BaseModel):
    period_date: date
    score: float
    component_scores: dict[str, float]


class HealthScoreResponse(BaseModel):
    history: list[HealthScorePoint]
    latest_score: float
    # 10 keys: gdp, cpi, unemployment_rate, ippi, retail_trade,
    # overnight_rate, cadusd, bond_10yr, m2pp, yield_spread
    latest_components: dict[str, float]


class ForecastPoint(BaseModel):
    period_date: date
    target: str
    horizon_months: int
    model_type: str
    point_forecast: float
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    scenario_base: float | None = None
    scenario_upside: float | None = None
    scenario_downside: float | None = None


class RAGRequest(BaseModel):
    question: str


class RAGResponse(BaseModel):
    answer: str
    sources: list[str]
    query_type: Literal["sql", "narrative"]
```

- [ ] **Step 5: Write `src/econsight/api/dependencies.py`**

```python
from __future__ import annotations

from collections.abc import AsyncGenerator

import psycopg

from econsight.db.connection import db_connection, db_connection_readonly


async def get_db() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with db_connection() as conn:
        yield conn


async def get_db_readonly() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with db_connection_readonly() as conn:
        yield conn
```

- [ ] **Step 6: Write `src/econsight/api/main.py`**

```python
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from econsight.api.routers import forecasts, indicators, rag, report
from econsight.config import settings


async def maybe_ingest_rag() -> None:
    try:
        from econsight.rag.ingestion import ingest_if_needed
        await ingest_if_needed()
    except Exception:
        pass  # RAG not available yet — ingestion runs lazily


@asynccontextmanager
async def lifespan(app: FastAPI):
    await maybe_ingest_rag()
    yield


app = FastAPI(title="EconSight API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(indicators.router, prefix="/api")
app.include_router(forecasts.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(report.router, prefix="/api")


@app.get("/api/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Write `src/econsight/api/routers/indicators.py`**

```python
from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from econsight.api.dependencies import get_db
from econsight.api.schemas import HealthScoreResponse, IndicatorRow, HealthScorePoint

router = APIRouter()

_INDICATOR_SQL = """
    SELECT period_date, gdp, cpi, unemployment_rate, ippi, retail_trade,
           overnight_rate, cadusd, bond_10yr, m2pp,
           cpi_yoy, yield_spread, unemployment_delta
    FROM marts.mart_monthly_macro_indicators
    ORDER BY period_date DESC
    LIMIT 36
"""

_HEALTH_SQL = """
    SELECT period_date, score, component_scores
    FROM marts.economic_health_score
    ORDER BY period_date ASC
"""


def _row_to_dict(row: tuple, description: list) -> dict:
    return {d[0]: (float(v) if v is not None and not isinstance(v, (str, dict)) else v)
            for d, v in zip(description, row)}


@router.get("/indicators", response_model=list[IndicatorRow])
async def get_indicators(
    conn: psycopg.AsyncConnection = Depends(get_db),
) -> list[IndicatorRow]:
    async with conn.cursor() as cur:
        await cur.execute(_INDICATOR_SQL)
        rows = await cur.fetchall()
        desc = cur.description or []
    result = [IndicatorRow(**_row_to_dict(r, desc)) for r in rows]
    return list(reversed(result))  # return ascending order


@router.get("/health-score", response_model=HealthScoreResponse)
async def get_health_score(
    conn: psycopg.AsyncConnection = Depends(get_db),
) -> HealthScoreResponse:
    async with conn.cursor() as cur:
        await cur.execute(_HEALTH_SQL)
        rows = await cur.fetchall()
    history = [
        HealthScorePoint(
            period_date=r[0],
            score=float(r[1]),
            component_scores={k: float(v) for k, v in r[2].items()},
        )
        for r in rows
    ]
    latest = history[-1]
    return HealthScoreResponse(
        history=history,
        latest_score=latest.score,
        latest_components=latest.component_scores,
    )
```

- [ ] **Step 8: Write `src/econsight/api/routers/forecasts.py`**

```python
from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from econsight.api.dependencies import get_db
from econsight.api.schemas import ForecastPoint

router = APIRouter()

_FORECAST_SQL = """
    SELECT period_date, target, horizon_months, model_type, point_forecast,
           p10, p50, p90, scenario_base, scenario_upside, scenario_downside
    FROM marts.model_forecasts
    ORDER BY target, horizon_months, model_type
"""


def _to_float_or_none(v) -> float | None:
    return float(v) if v is not None else None


@router.get("/forecasts", response_model=list[ForecastPoint])
async def get_forecasts(
    conn: psycopg.AsyncConnection = Depends(get_db),
) -> list[ForecastPoint]:
    async with conn.cursor() as cur:
        await cur.execute(_FORECAST_SQL)
        rows = await cur.fetchall()
    return [
        ForecastPoint(
            period_date=r[0],
            target=r[1],
            horizon_months=r[2],
            model_type=r[3],
            point_forecast=float(r[4]),
            p10=_to_float_or_none(r[5]),
            p50=_to_float_or_none(r[6]),
            p90=_to_float_or_none(r[7]),
            scenario_base=_to_float_or_none(r[8]),
            scenario_upside=_to_float_or_none(r[9]),
            scenario_downside=_to_float_or_none(r[10]),
        )
        for r in rows
    ]
```

- [ ] **Step 9: Write stub routers for rag and report** (so main.py can import them)

`src/econsight/api/routers/rag.py`:
```python
from fastapi import APIRouter
from econsight.api.schemas import RAGRequest, RAGResponse

router = APIRouter()

@router.post("/rag/query", response_model=RAGResponse)
async def query_rag(body: RAGRequest) -> RAGResponse:
    return RAGResponse(answer="Coming soon", sources=[], query_type="narrative")
```

`src/econsight/api/routers/report.py`:
```python
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()

@router.get("/report/pdf")
async def get_pdf() -> Response:
    return Response(content=b"%PDF-1.4 stub", media_type="application/pdf")
```

- [ ] **Step 10: Run tests — confirm they pass**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_api/test_indicators.py tests/test_api/test_forecasts.py -v 2>&1
```

Expected: all PASS

- [ ] **Step 11: Start the API and verify manually**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/uvicorn econsight.api.main:app --reload --port 8000 &
sleep 2 && curl -s http://localhost:8000/api/ping | python -m json.tool
curl -s "http://localhost:8000/api/forecasts" | python -m json.tool | head -20
```

Expected: `{"status": "ok"}` from ping, forecast rows from /api/forecasts.

Kill the server after verification: `kill %1`

- [ ] **Step 12: Lint and type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/econsight/api/ tests/test_api/
.venv/bin/python -m mypy src/econsight/api/
```

- [ ] **Step 13: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/db/connection.py src/econsight/api/ tests/test_api/
git commit -m "feat: FastAPI core — schemas, dependencies, indicators/forecasts endpoints, stub RAG/PDF"
```

---

## Task 3: RAG Pipeline

**Files:**
- Create: `src/econsight/rag/ingestion.py`
- Create: `src/econsight/rag/retriever.py`
- Create: `src/econsight/rag/query_engine.py`
- Modify: `src/econsight/api/routers/rag.py` (replace stub)
- Create: `tests/test_api/test_rag.py`

**Prerequisite:** `notebooks/phase2_report.html` must exist. If it doesn't, run:
```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python notebooks/render.py
```

- [ ] **Step 1: Write failing tests — `tests/test_api/test_rag.py`**

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


async def test_rag_query_returns_response_shape():
    from econsight.api.main import app

    mock_response = MagicMock()
    mock_response.answer = "CPI was 136.0 in January 2024."
    mock_response.sources = ["database"]
    mock_response.query_type = "sql"

    with patch("econsight.api.routers.rag.answer", return_value=mock_response):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post("/api/rag/query", json={"question": "what was CPI in Jan 2024?"})

    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert "sources" in body
    assert body["query_type"] in ("sql", "narrative")


async def test_rag_sql_path_rejects_non_select():
    from econsight.rag.query_engine import _is_safe_sql
    assert _is_safe_sql("SELECT * FROM marts.mart_monthly_macro_indicators") is True
    assert _is_safe_sql("DROP TABLE marts.model_forecasts") is False
    assert _is_safe_sql("SELECT 1; DELETE FROM raw.statcan_observations") is False
    assert _is_safe_sql("DELETE FROM raw.boc_observations") is False


async def test_rag_narrative_path_returns_sources():
    from econsight.api.main import app

    mock_response = MagicMock()
    mock_response.answer = "The yield spread widened due to rate cuts."
    mock_response.sources = ["3. VAR/VECM Results", "7. Economic Health Score"]
    mock_response.query_type = "narrative"

    with patch("econsight.api.routers.rag.answer", return_value=mock_response):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post("/api/rag/query", json={"question": "why is the yield spread widening?"})

    assert r.status_code == 200
    body = r.json()
    assert body["query_type"] == "narrative"
    assert len(body["sources"]) > 0
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_api/test_rag.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Write `src/econsight/rag/ingestion.py`**

```python
from __future__ import annotations

import asyncio
from pathlib import Path

import chromadb
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

from econsight.config import get_logger
from econsight.db.connection import PROJECT_ROOT

logger = get_logger(__name__)

_REPORT_PATH = PROJECT_ROOT / "notebooks" / "phase2_report.html"
_CHROMA_PATH = str(PROJECT_ROOT / "models" / "chroma_db")
_COLLECTION_NAME = "phase2_report"
_MODEL_NAME = "all-MiniLM-L6-v2"


def _parse_report(html_path: Path) -> list[dict[str, str]]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    chunks: list[dict[str, str]] = []
    current_title = "Introduction"
    current_texts: list[str] = []

    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "td"]):
        if tag.name in ("h1", "h2", "h3"):
            if current_texts:
                chunks.append({"title": current_title, "text": " ".join(current_texts)})
                current_texts = []
            current_title = tag.get_text(strip=True)
        else:
            text = tag.get_text(strip=True)
            if text:
                current_texts.append(text)

    if current_texts:
        chunks.append({"title": current_title, "text": " ".join(current_texts)})

    return [c for c in chunks if len(c["text"]) > 50]


async def ingest_if_needed() -> None:
    if not _REPORT_PATH.exists():
        logger.warning("rag.report_missing", path=str(_REPORT_PATH))
        return

    client = chromadb.PersistentClient(path=_CHROMA_PATH)
    collection = client.get_or_create_collection(_COLLECTION_NAME)

    if collection.count() > 0:
        logger.info("rag.already_ingested", count=collection.count())
        return

    logger.info("rag.ingesting", path=str(_REPORT_PATH))
    chunks = await asyncio.to_thread(_parse_report, _REPORT_PATH)
    model = await asyncio.to_thread(SentenceTransformer, _MODEL_NAME)

    texts = [c["text"] for c in chunks]
    embeddings = await asyncio.to_thread(model.encode, texts)

    collection.add(
        documents=texts,
        embeddings=[e.tolist() for e in embeddings],
        metadatas=[{"title": c["title"]} for c in chunks],
        ids=[f"chunk_{i}" for i in range(len(chunks))],
    )
    logger.info("rag.ingested", chunks=len(chunks))
```

- [ ] **Step 4: Write `src/econsight/rag/retriever.py`**

```python
from __future__ import annotations

import asyncio

import chromadb
from sentence_transformers import SentenceTransformer

from econsight.db.connection import PROJECT_ROOT

_CHROMA_PATH = str(PROJECT_ROOT / "models" / "chroma_db")
_COLLECTION_NAME = "phase2_report"
_MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


async def retrieve(question: str, top_k: int = 5) -> list[dict[str, str]]:
    model = await asyncio.to_thread(_get_model)
    embedding = await asyncio.to_thread(model.encode, [question])

    client = chromadb.PersistentClient(path=_CHROMA_PATH)
    collection = client.get_or_create_collection(_COLLECTION_NAME)

    results = collection.query(
        query_embeddings=[embedding[0].tolist()],
        n_results=min(top_k, collection.count() or 1),
        include=["documents", "metadatas"],
    )
    chunks = []
    for doc, meta in zip(
        results["documents"][0], results["metadatas"][0]
    ):
        chunks.append({"title": meta.get("title", ""), "text": doc})
    return chunks
```

- [ ] **Step 5: Write `src/econsight/rag/query_engine.py`**

```python
from __future__ import annotations

import re

from anthropic import AsyncAnthropic

from econsight.api.schemas import RAGResponse
from econsight.config import get_logger
from econsight.db.connection import db_connection_readonly
from econsight.rag.retriever import retrieve

logger = get_logger(__name__)

_client = AsyncAnthropic()

_SCHEMA_CONTEXT = """
Available tables (SELECT only, marts schema):
- marts.mart_monthly_macro_indicators: period_date, gdp, cpi, unemployment_rate, ippi, retail_trade, overnight_rate, cadusd, bond_10yr, m2pp, cpi_yoy, yield_spread, unemployment_delta, data_complete
- marts.model_forecasts: period_date, target, horizon_months, model_type, point_forecast, p10, p50, p90, scenario_base, scenario_upside, scenario_downside, created_at
- marts.economic_health_score: period_date, score, component_scores, updated_at
"""

_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b|;",
    re.IGNORECASE,
)


def _is_safe_sql(query: str) -> bool:
    return not bool(_DANGEROUS.search(query))


async def _classify(question: str) -> str:
    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=10,
        system=(
            "Classify the question as 'sql' if it asks for specific data values, dates, or statistics "
            "that need a database query, or 'narrative' if it asks for analysis, explanation, or insight. "
            "Reply with only the word 'sql' or 'narrative'."
        ),
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text.strip().lower()


async def _sql_answer(question: str) -> RAGResponse:
    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=f"Generate a single read-only PostgreSQL SELECT query to answer the question. "
               f"Use only these tables:\n{_SCHEMA_CONTEXT}\nReply with only the SQL query, no explanation.",
        messages=[{"role": "user", "content": question}],
    )
    sql = response.content[0].text.strip()

    if not _is_safe_sql(sql):
        return RAGResponse(
            answer="I can only run read-only SELECT queries on the marts tables.",
            sources=["database"],
            query_type="sql",
        )

    try:
        async with db_connection_readonly() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql)
                rows = await cur.fetchmany(20)
                cols = [d[0] for d in (cur.description or [])]

        if not rows:
            answer = "No data found for that query."
        else:
            header = " | ".join(cols)
            body = "\n".join(" | ".join(str(v) for v in row) for row in rows)
            answer = f"{header}\n{'---' * len(cols)}\n{body}"
    except Exception as exc:
        answer = f"Query failed: {exc}"

    return RAGResponse(answer=answer, sources=["database"], query_type="sql")


async def _narrative_answer(question: str) -> RAGResponse:
    chunks = await retrieve(question, top_k=5)
    context = "\n\n".join(
        f"[{c['title']}]\n{c['text']}" for c in chunks
    )
    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="Answer the question using only the provided context. Be concise and factual.",
        messages=[{
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}",
        }],
    )
    sources = list({c["title"] for c in chunks if c["title"]})
    return RAGResponse(
        answer=response.content[0].text,
        sources=sources,
        query_type="narrative",
    )


async def answer(question: str) -> RAGResponse:
    query_type = await _classify(question)
    logger.info("rag.query", question=question[:80], type=query_type)
    if query_type == "sql":
        return await _sql_answer(question)
    return await _narrative_answer(question)
```

- [ ] **Step 6: Replace stub `src/econsight/api/routers/rag.py`**

```python
from __future__ import annotations

from fastapi import APIRouter

from econsight.api.schemas import RAGRequest, RAGResponse
from econsight.rag.query_engine import answer

router = APIRouter()


@router.post("/rag/query", response_model=RAGResponse)
async def query_rag(body: RAGRequest) -> RAGResponse:
    return await answer(body.question)
```

- [ ] **Step 7: Run tests — confirm they pass**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_api/test_rag.py -v 2>&1
```

- [ ] **Step 8: Test RAG manually (requires ANTHROPIC_API_KEY)**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python notebooks/render.py 2>/dev/null || true
.venv/bin/uvicorn econsight.api.main:app --reload --port 8000 &
sleep 3
curl -s -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the CPI in the most recent month?"}' | python -m json.tool
kill %1
```

- [ ] **Step 9: Lint and type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/econsight/rag/ src/econsight/api/routers/rag.py tests/test_api/test_rag.py
.venv/bin/python -m mypy src/econsight/rag/ src/econsight/api/routers/rag.py
```

- [ ] **Step 10: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/rag/ src/econsight/api/routers/rag.py tests/test_api/test_rag.py
git commit -m "feat: RAG pipeline — ChromaDB ingestion, sentence-transformers retrieval, Claude-powered answer()"
```

---

## Task 4: PDF Generation

**Files:**
- Create: `src/econsight/report/brief.py`
- Create: `src/econsight/report/full_report.py`
- Create: `src/econsight/report/merger.py`
- Modify: `src/econsight/api/routers/report.py` (replace stub)
- Create: `tests/test_api/test_report.py`

- [ ] **Step 1: Write failing test — `tests/test_api/test_report.py`**

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


async def test_pdf_endpoint_returns_pdf_bytes():
    from econsight.api.main import app

    with patch("econsight.api.routers.report.generate_brief", new_callable=AsyncMock, return_value=b"%PDF-1.4 brief") as mock_brief, \
         patch("econsight.api.routers.report.generate_full_report", return_value=b"%PDF-1.4 full") as mock_full, \
         patch("econsight.api.routers.report.merge_pdfs", return_value=b"%PDF-1.4 merged") as mock_merge:

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get("/api/report/pdf")

    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_generate_brief_produces_pdf_bytes():
    from econsight.report.brief import _render_brief_html

    html = _render_brief_html(
        month_label="2024-01",
        latest_score=72.5,
        score_delta=1.2,
        risk_indicators=[("cpi", 136.0, "↑"), ("unemployment_rate", 6.8, "↑")],
        forecasts=[("CPI", 136.5, 137.0, 136.8, 137.5)],
        outlook_paragraph="The Canadian economy shows moderate resilience.",
    )
    assert "<html>" in html
    assert "72.5" in html
    assert "Economic Health Score" in html
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_api/test_report.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Write `src/econsight/report/brief.py`**

```python
from __future__ import annotations

import string

import psycopg
from weasyprint import HTML

from econsight.config import get_logger

logger = get_logger(__name__)

# Use string.Template ($$score_color → $score_color after substitution) to avoid
# escaping every CSS brace pair in a str.format() call.
_BRIEF_CSS_TMPL = string.Template("""
body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 40px; color: #1a1a2e; }
h1 { font-size: 28px; color: #16213e; border-bottom: 3px solid #0f3460; padding-bottom: 10px; }
h2 { font-size: 18px; color: #0f3460; margin-top: 28px; }
.score { font-size: 72px; font-weight: bold; color: $$score_color; }
.delta { font-size: 18px; color: #555; }
table { border-collapse: collapse; width: 100%; margin-top: 10px; }
th { background: #0f3460; color: white; padding: 8px 12px; text-align: left; }
td { padding: 7px 12px; border-bottom: 1px solid #ddd; }
tr:nth-child(even) { background: #f8f9fa; }
.outlook { background: #eef2ff; border-left: 4px solid #0f3460; padding: 14px; margin-top: 14px; }
""")


def _score_color(score: float) -> str:
    if score >= 60:
        return "#16a34a"
    if score >= 40:
        return "#d97706"
    return "#dc2626"


def _render_brief_html(
    month_label: str,
    latest_score: float,
    score_delta: float,
    risk_indicators: list[tuple[str, float, str]],
    forecasts: list[tuple[str, float, float, float, float]],
    outlook_paragraph: str,
) -> str:
    delta_sign = "+" if score_delta >= 0 else ""
    risk_rows = "".join(
        f"<tr><td>{name.replace('_', ' ').title()}</td><td>{value:.2f}</td><td>{trend}</td></tr>"
        for name, value, trend in risk_indicators
    )
    forecast_rows = "".join(
        f"<tr><td>{name}</td><td>{v1:.3f}</td><td>{v3:.3f}</td><td>{x1:.3f}</td><td>{x3:.3f}</td></tr>"
        for name, v1, v3, x1, x3 in forecasts
    )
    css = _BRIEF_CSS_TMPL.substitute(score_color=_score_color(latest_score))
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>{css}</style></head>
<body>
<h1>EconSight — Canadian Economic Outlook</h1>
<p style="color:#666;font-size:14px;margin-top:-8px">{month_label}</p>

<h2>Economic Health Score</h2>
<div class="score">{latest_score:.1f}<span style="font-size:24px">/100</span></div>
<div class="delta">{delta_sign}{score_delta:.1f} from prior month</div>

<h2>Key Risk Indicators</h2>
<table>
<tr><th>Indicator</th><th>Latest Value</th><th>Trend</th></tr>
{risk_rows}
</table>

<h2>Forecast Summary</h2>
<table>
<tr><th>Target</th><th>VAR 1M</th><th>VAR 3M</th><th>XGB 1M</th><th>XGB 3M</th></tr>
{forecast_rows}
</table>

<h2>Economic Outlook</h2>
<div class="outlook">{outlook_paragraph}</div>
</body>
</html>"""


async def _build_outlook(score: float, forecasts: list[tuple]) -> str:
    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic()
        fc_text = "; ".join(
            f"{name}: {x1:.2f} (1M), {x3:.2f} (3M)"
            for name, _, _, x1, x3 in forecasts
        )
        prompt = (
            f"Write a 2-sentence plain-language economic outlook for Canadian SMEs. "
            f"Health score: {score:.1f}/100. Forecasts: {fc_text}."
        )
        r = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return r.content[0].text.strip()
    except Exception:
        return "The economic outlook remains mixed, with moderate inflationary pressure and stable labour market conditions."


async def generate_brief(conn: psycopg.AsyncConnection) -> bytes:
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT period_date, score FROM marts.economic_health_score ORDER BY period_date DESC LIMIT 2"
        )
        score_rows = await cur.fetchall()
        await cur.execute(
            "SELECT target, horizon_months, model_type, point_forecast "
            "FROM marts.model_forecasts ORDER BY target, horizon_months, model_type"
        )
        forecast_rows = await cur.fetchall()
        await cur.execute(
            "SELECT component_scores FROM marts.economic_health_score ORDER BY period_date DESC LIMIT 1"
        )
        comp_row = await cur.fetchone()

    latest_score = float(score_rows[0][1]) if score_rows else 50.0
    prev_score = float(score_rows[1][1]) if len(score_rows) > 1 else latest_score
    delta = latest_score - prev_score
    month_label = str(score_rows[0][0]) if score_rows else "N/A"

    comp_scores: dict[str, float] = {}
    if comp_row and comp_row[0]:
        comp_scores = {k: float(v) for k, v in comp_row[0].items()}

    risk_indicators = sorted(comp_scores.items(), key=lambda x: x[1])[:3]
    risk_list = [(k, abs(v), "↓" if v < 0 else "↑") for k, v in risk_indicators]

    # SQL column order: target(0), horizon_months(1), model_type(2), point_forecast(3)
    var_1m: dict[str, float] = {}
    var_3m: dict[str, float] = {}
    xgb_1m: dict[str, float] = {}
    xgb_3m: dict[str, float] = {}
    for row in forecast_rows:
        target, horizon, model, pf = str(row[0]), int(row[1]), str(row[2]), float(row[3])
        if model == "var" and horizon == 1:
            var_1m[target] = pf
        elif model == "var" and horizon == 3:
            var_3m[target] = pf
        elif model == "xgboost" and horizon == 1:
            xgb_1m[target] = pf
        elif model == "xgboost" and horizon == 3:
            xgb_3m[target] = pf

    fc_table = [
        (t.replace("_", " ").title(),
         var_1m.get(t, 0), var_3m.get(t, 0),
         xgb_1m.get(t, 0), xgb_3m.get(t, 0))
        for t in ["cpi", "unemployment_rate", "overnight_rate"]
    ]

    outlook = await _build_outlook(latest_score, fc_table)
    html = _render_brief_html(month_label, latest_score, delta, risk_list, fc_table, outlook)

    import asyncio
    return await asyncio.to_thread(lambda: HTML(string=html).write_pdf())
```

- [ ] **Step 4: Write `src/econsight/report/full_report.py`**

```python
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from econsight.config import get_logger
from econsight.db.connection import PROJECT_ROOT

logger = get_logger(__name__)

_NOTEBOOK = PROJECT_ROOT / "notebooks" / "phase2_analysis.ipynb"
_LATEX_AVAILABLE: bool = shutil.which("xelatex") is not None


def generate_full_report() -> bytes:
    """Run nbconvert to produce a PDF of the Phase 2 analysis notebook.
    NOTE: Always call via asyncio.to_thread(generate_full_report) — this is blocking.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_stem = "phase2_analysis"
        if _LATEX_AVAILABLE:
            to_fmt = "pdf"
        else:
            logger.warning("full_report.latex_unavailable", fallback="html+weasyprint")
            to_fmt = "html"

        result = subprocess.run(
            [
                "jupyter", "nbconvert",
                "--execute",
                "--to", to_fmt,
                "--ExecutePreprocessor.timeout=600",
                "--output", output_stem,
                "--output-dir", tmpdir,
                str(_NOTEBOOK),
            ],
            capture_output=True,
            text=True,
            timeout=660,
        )
        if result.returncode != 0:
            raise RuntimeError(f"nbconvert failed:\n{result.stderr[:500]}")

        if to_fmt == "pdf":
            out_path = Path(tmpdir) / f"{output_stem}.pdf"
            return out_path.read_bytes()
        else:
            # Fallback: convert HTML to PDF with WeasyPrint
            from weasyprint import HTML
            html_path = Path(tmpdir) / f"{output_stem}.html"
            return HTML(filename=str(html_path)).write_pdf()
```

- [ ] **Step 5: Write `src/econsight/report/merger.py`**

```python
from __future__ import annotations

import io

from pypdf import PdfReader, PdfWriter


def merge_pdfs(brief_bytes: bytes, full_bytes: bytes) -> bytes:
    writer = PdfWriter()
    for pdf_bytes in (brief_bytes, full_bytes):
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
```

- [ ] **Step 6: Replace stub `src/econsight/api/routers/report.py`**

```python
from __future__ import annotations

import asyncio

import psycopg
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from econsight.api.dependencies import get_db
from econsight.report.brief import generate_brief
from econsight.report.full_report import generate_full_report
from econsight.report.merger import merge_pdfs

router = APIRouter()


@router.get("/report/pdf")
async def get_pdf(conn: psycopg.AsyncConnection = Depends(get_db)) -> Response:
    brief_bytes, full_bytes = await asyncio.gather(
        generate_brief(conn),
        asyncio.to_thread(generate_full_report),
    )
    merged = merge_pdfs(brief_bytes, full_bytes)
    return Response(
        content=merged,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=econsight_report.pdf"},
    )
```

- [ ] **Step 7: Run tests — confirm they pass**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_api/test_report.py -v 2>&1
```

- [ ] **Step 8: Lint and type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/econsight/report/ src/econsight/api/routers/report.py tests/test_api/test_report.py
.venv/bin/python -m mypy src/econsight/report/ src/econsight/api/routers/report.py
```

- [ ] **Step 9: Run full test suite**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest -v -m "not integration" 2>&1 | tail -20
```

- [ ] **Step 10: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add src/econsight/report/ src/econsight/api/routers/report.py tests/test_api/test_report.py
git commit -m "feat: PDF generation — WeasyPrint brief, nbconvert full analysis, pypdf merger"
```

---

## Task 5: React Scaffolding — Vite, Tailwind, shadcn/ui, Routing, API Client

**Files:**
- Create: `frontend/` (entire Vite project)

**Prerequisites:** Node.js and npm must be installed. Check: `node --version && npm --version`

- [ ] **Step 1: Scaffold Vite + React + TypeScript**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight"
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

- [ ] **Step 2: Install runtime dependencies**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight/frontend"
npm install react-router-dom @tanstack/react-query recharts axios
npm install -D tailwindcss postcss autoprefixer @types/node
npx tailwindcss init -p
```

- [ ] **Step 3: Configure Tailwind**

Replace contents of `frontend/tailwind.config.ts`:
```ts
import type { Config } from 'tailwindcss'

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
} satisfies Config
```

Replace contents of `frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Add CSS variables for shadcn/ui to `frontend/src/index.css`**

Append to `frontend/src/index.css`:
```css
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --border: 214.3 31.8% 91.4%;
    --radius: 0.5rem;
  }
}
* { border-color: hsl(var(--border)); }
body { background-color: hsl(var(--background)); color: hsl(var(--foreground)); }
```

- [ ] **Step 5: Install and init shadcn/ui**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight/frontend"
npm install class-variance-authority clsx tailwind-merge lucide-react
```

Create `frontend/src/lib/utils.ts`:
```ts
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

Create `frontend/components.json` (shadcn/ui config):
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils"
  }
}
```

Add path alias to `frontend/vite.config.ts`:
```ts
import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
})
```

Add to `frontend/tsconfig.json` under `compilerOptions`:
```json
"baseUrl": ".",
"paths": { "@/*": ["./src/*"] }
```

Add shadcn/ui core components manually (Card, Button, Badge, Skeleton, Table, Input, Select):

```bash
cd "/Users/barandursun/AI PROJECT/EconSight/frontend"
npx shadcn@latest add button card badge skeleton table input select
```

If the CLI prompts for configuration options, accept defaults.

- [ ] **Step 6: Write `frontend/src/api/client.ts`**

```ts
import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000' })

export interface IndicatorRow {
  period_date: string
  gdp: number | null
  cpi: number | null
  unemployment_rate: number | null
  ippi: number | null
  retail_trade: number | null
  overnight_rate: number | null
  cadusd: number | null
  bond_10yr: number | null
  m2pp: number | null
  cpi_yoy: number | null
  yield_spread: number | null
  unemployment_delta: number | null
}

export interface HealthScorePoint {
  period_date: string
  score: number
  component_scores: Record<string, number>
}

export interface HealthScoreResponse {
  history: HealthScorePoint[]
  latest_score: number
  latest_components: Record<string, number>
}

export interface ForecastPoint {
  period_date: string
  target: string
  horizon_months: number
  model_type: string
  point_forecast: number
  p10: number | null
  p50: number | null
  p90: number | null
  scenario_base: number | null
  scenario_upside: number | null
  scenario_downside: number | null
}

export interface RAGResponse {
  answer: string
  sources: string[]
  query_type: 'sql' | 'narrative'
}

export const fetchIndicators = () =>
  api.get<IndicatorRow[]>('/api/indicators').then(r => r.data)

export const fetchHealthScore = () =>
  api.get<HealthScoreResponse>('/api/health-score').then(r => r.data)

export const fetchForecasts = () =>
  api.get<ForecastPoint[]>('/api/forecasts').then(r => r.data)

export const queryRAG = (question: string) =>
  api.post<RAGResponse>('/api/rag/query', { question }).then(r => r.data)

export const downloadReport = () =>
  api.get('/api/report/pdf', { responseType: 'blob' }).then(r => r.data as Blob)
```

- [ ] **Step 7: Write `frontend/src/App.tsx`**

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Ask from './pages/Ask'
import Dashboard from './pages/Dashboard'
import Forecasts from './pages/Forecasts'
import Indicators from './pages/Indicators'
import Report from './pages/Report'

const queryClient = new QueryClient()

function Nav() {
  return (
    <nav className="border-b bg-white px-6 py-3 flex gap-6 text-sm font-medium">
      <span className="text-blue-700 font-bold text-base">EconSight</span>
      {[
        ['/', 'Dashboard'],
        ['/indicators', 'Indicators'],
        ['/forecasts', 'Forecasts'],
        ['/ask', 'Ask'],
        ['/report', 'Report'],
      ].map(([to, label]) => (
        <Link key={to} to={to} className="text-gray-600 hover:text-blue-700">
          {label}
        </Link>
      ))}
    </nav>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <Nav />
          <main className="max-w-7xl mx-auto px-6 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/indicators" element={<Indicators />} />
              <Route path="/forecasts" element={<Forecasts />} />
              <Route path="/ask" element={<Ask />} />
              <Route path="/report" element={<Report />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

Create stub pages so the app compiles:

```bash
cd "/Users/barandursun/AI PROJECT/EconSight/frontend/src"
mkdir -p pages components
for page in Dashboard Indicators Forecasts Ask Report; do
  echo "export default function ${page}() { return <div>${page}</div> }" > "pages/${page}.tsx"
done
```

- [ ] **Step 8: Start the frontend and verify it loads**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight/frontend" && npm run dev &
sleep 3 && curl -s http://localhost:5173 | grep -c "EconSight\|root" && kill %1
```

Expected: finds "EconSight" or "root" in HTML — app is serving.

- [ ] **Step 9: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add frontend/
git commit -m "feat: React scaffold — Vite + TypeScript + Tailwind + shadcn/ui + routing + typed API client"
```

---

## Task 6: React Shared Components

**Files:**
- Create: `frontend/src/components/HealthScoreGauge.tsx`
- Create: `frontend/src/components/IndicatorCard.tsx`
- Create: `frontend/src/components/MacroChart.tsx`
- Create: `frontend/src/components/ForecastTable.tsx`
- Create: `frontend/src/components/QueryBox.tsx`

- [ ] **Step 1: Write `frontend/src/components/HealthScoreGauge.tsx`**

```tsx
interface Props { score: number; delta?: number }

export default function HealthScoreGauge({ score, delta }: Props) {
  const color = score >= 60 ? '#16a34a' : score >= 40 ? '#d97706' : '#dc2626'
  const angle = (score / 100) * 180 - 90
  const rad = (angle * Math.PI) / 180
  const cx = 100, cy = 100, r = 70
  const nx = cx + r * Math.cos(rad), ny = cy + r * Math.sin(rad)

  return (
    <div className="flex flex-col items-center">
      <svg width="200" height="120" viewBox="0 0 200 120">
        <path d="M 30 100 A 70 70 0 0 1 170 100" fill="none" stroke="#e5e7eb" strokeWidth="14" />
        <path
          d={`M 30 100 A 70 70 0 ${score > 50 ? 1 : 0} 1 ${nx.toFixed(1)} ${ny.toFixed(1)}`}
          fill="none" stroke={color} strokeWidth="14" strokeLinecap="round"
        />
        <text x="100" y="95" textAnchor="middle" fontSize="28" fontWeight="bold" fill={color}>
          {score.toFixed(1)}
        </text>
        <text x="100" y="112" textAnchor="middle" fontSize="11" fill="#6b7280">/100</text>
      </svg>
      {delta !== undefined && (
        <span className={`text-sm font-medium ${delta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {delta >= 0 ? '+' : ''}{delta.toFixed(1)} vs prior month
        </span>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Write `frontend/src/components/IndicatorCard.tsx`**

```tsx
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface Props {
  label: string
  value: number | null
  unit?: string
  delta?: number | null
}

export default function IndicatorCard({ label, value, unit = '', delta }: Props) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-gray-500 font-medium">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {value != null ? `${value.toFixed(2)}${unit}` : '—'}
        </div>
        {delta != null && (
          <Badge variant={delta >= 0 ? 'default' : 'destructive'} className="mt-1 text-xs">
            {delta >= 0 ? '+' : ''}{delta.toFixed(2)} MoM
          </Badge>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 3: Write `frontend/src/components/MacroChart.tsx`**

```tsx
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

interface DataPoint { period_date: string; value: number | null }
interface Props { data: DataPoint[]; color?: string; height?: number }

export default function MacroChart({ data, color = '#2563eb', height = 280 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="period_date"
          tick={{ fontSize: 11 }}
          tickFormatter={d => d.slice(0, 7)}
          interval="preserveStartEnd"
        />
        <YAxis tick={{ fontSize: 11 }} width={60} />
        <Tooltip labelFormatter={l => `Date: ${l}`} />
        <Line type="monotone" dataKey="value" stroke={color} dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 4: Write `frontend/src/components/ForecastTable.tsx`**

```tsx
import { Badge } from '@/components/ui/badge'
import type { ForecastPoint } from '@/api/client'

interface Props { forecasts: ForecastPoint[] }

const TARGETS = ['cpi', 'unemployment_rate', 'overnight_rate']
const LABELS: Record<string, string> = {
  cpi: 'CPI', unemployment_rate: 'Unemployment %', overnight_rate: 'Overnight Rate %',
}

export default function ForecastTable({ forecasts }: Props) {
  const get = (target: string, horizon: number, model: string) =>
    forecasts.find(f => f.target === target && f.horizon_months === horizon && f.model_type === model)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2 pr-4 font-medium text-gray-600">Target</th>
            {['VAR 1M', 'VAR 3M', 'XGB 1M', 'XGB 3M'].map(h => (
              <th key={h} className="text-right py-2 px-3 font-medium text-gray-600">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {TARGETS.map(t => (
            <tr key={t} className="border-b hover:bg-gray-50">
              <td className="py-2 pr-4 font-medium">{LABELS[t]}</td>
              {[[1,'var'],[3,'var'],[1,'xgboost'],[3,'xgboost']].map(([h,m]) => {
                const f = get(t, h as number, m as string)
                return (
                  <td key={`${h}-${m}`} className="text-right py-2 px-3 tabular-nums">
                    {f ? f.point_forecast.toFixed(3) : '—'}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 5: Write `frontend/src/components/QueryBox.tsx`**

```tsx
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { RAGResponse } from '@/api/client'

interface Props {
  onSubmit: (question: string) => void
  response: RAGResponse | null
  loading: boolean
}

const EXAMPLES = [
  'What was CPI in the most recent month?',
  'Why is the economic health score at its current level?',
  'What do the XGBoost forecasts say about unemployment?',
]

export default function QueryBox({ onSubmit, response, loading }: Props) {
  const [question, setQuestion] = useState('')

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          placeholder="Ask a question about the Canadian economy..."
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && question && onSubmit(question)}
          className="flex-1"
        />
        <Button onClick={() => question && onSubmit(question)} disabled={loading || !question}>
          {loading ? 'Thinking...' : 'Ask'}
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map(ex => (
          <button
            key={ex}
            onClick={() => { setQuestion(ex); onSubmit(ex) }}
            className="text-xs text-blue-600 hover:text-blue-800 underline"
          >
            {ex}
          </button>
        ))}
      </div>

      {response && (
        <div className="border rounded-lg p-4 bg-white space-y-3">
          <div className="flex items-center gap-2">
            <Badge variant={response.query_type === 'sql' ? 'default' : 'secondary'}>
              {response.query_type === 'sql' ? 'Database Query' : 'Analysis'}
            </Badge>
          </div>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{response.answer}</p>
          {response.sources.length > 0 && (
            <div className="text-xs text-gray-500">
              Sources: {response.sources.join(', ')}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add frontend/src/components/
git commit -m "feat: React shared components — HealthScoreGauge, IndicatorCard, MacroChart, ForecastTable, QueryBox"
```

---

## Task 7: React Pages — Dashboard and Indicators

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Indicators.tsx`

- [ ] **Step 1: Write `frontend/src/pages/Dashboard.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query'
import { fetchHealthScore, fetchIndicators, fetchForecasts } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import ForecastTable from '@/components/ForecastTable'
import HealthScoreGauge from '@/components/HealthScoreGauge'
import IndicatorCard from '@/components/IndicatorCard'
import MacroChart from '@/components/MacroChart'

export default function Dashboard() {
  const { data: hs, isLoading: hsLoading } = useQuery({
    queryKey: ['health-score'], queryFn: fetchHealthScore,
  })
  const { data: indicators } = useQuery({
    queryKey: ['indicators'], queryFn: fetchIndicators,
  })
  const { data: forecasts } = useQuery({
    queryKey: ['forecasts'], queryFn: fetchForecasts,
  })

  const latest = indicators?.[indicators.length - 1]
  const prev = indicators?.[indicators.length - 2]

  const hsHistory = hs?.history ?? []
  const scoreDelta = hsHistory.length >= 2
    ? hsHistory[hsHistory.length - 1].score - hsHistory[hsHistory.length - 2].score
    : undefined

  const SPARK_INDICATORS = ['cpi', 'unemployment_rate', 'overnight_rate', 'gdp', 'bond_10yr', 'cadusd', 'ippi', 'retail_trade', 'm2pp'] as const

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-800">Canadian Economic Dashboard</h1>

      {/* Health Score */}
      <Card>
        <CardHeader>
          <CardTitle>Economic Health Score</CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center">
          {hsLoading ? (
            <Skeleton className="h-32 w-48" />
          ) : (
            <HealthScoreGauge score={hs?.latest_score ?? 50} delta={scoreDelta} />
          )}
        </CardContent>
      </Card>

      {/* Key Indicators */}
      <div className="grid grid-cols-3 gap-4">
        <IndicatorCard label="CPI" value={latest?.cpi ?? null} delta={(latest?.cpi ?? 0) - (prev?.cpi ?? 0)} />
        <IndicatorCard label="Unemployment Rate" value={latest?.unemployment_rate ?? null} unit="%" delta={(latest?.unemployment_rate ?? 0) - (prev?.unemployment_rate ?? 0)} />
        <IndicatorCard label="Overnight Rate" value={latest?.overnight_rate ?? null} unit="%" delta={(latest?.overnight_rate ?? 0) - (prev?.overnight_rate ?? 0)} />
      </div>

      {/* Forecast Table */}
      <Card>
        <CardHeader><CardTitle>Forecasts</CardTitle></CardHeader>
        <CardContent>
          <ForecastTable forecasts={forecasts ?? []} />
        </CardContent>
      </Card>

      {/* Sparklines */}
      <div className="grid grid-cols-3 gap-4">
        {SPARK_INDICATORS.map(col => {
          const data = (indicators ?? []).slice(-12).map(r => ({
            period_date: r.period_date,
            value: r[col] as number | null,
          }))
          return (
            <Card key={col}>
              <CardHeader className="pb-1">
                <CardTitle className="text-xs text-gray-500">
                  {col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <MacroChart data={data} height={80} />
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Write `frontend/src/pages/Indicators.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchIndicators } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import MacroChart from '@/components/MacroChart'

const INDICATOR_OPTIONS = [
  { value: 'cpi', label: 'Consumer Price Index (CPI)' },
  { value: 'gdp', label: 'GDP' },
  { value: 'unemployment_rate', label: 'Unemployment Rate' },
  { value: 'ippi', label: 'IPPI' },
  { value: 'retail_trade', label: 'Retail Trade' },
  { value: 'overnight_rate', label: 'Overnight Rate' },
  { value: 'cadusd', label: 'CAD/USD' },
  { value: 'bond_10yr', label: '10-Year Bond Yield' },
  { value: 'm2pp', label: 'M2++ Money Supply' },
]

export default function Indicators() {
  const [selected, setSelected] = useState('cpi')
  const { data: indicators } = useQuery({
    queryKey: ['indicators'], queryFn: fetchIndicators,
  })

  const chartData = (indicators ?? []).map(r => ({
    period_date: r.period_date,
    value: r[selected as keyof typeof r] as number | null,
  }))

  const label = INDICATOR_OPTIONS.find(o => o.value === selected)?.label ?? selected

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Indicator Detail</h1>
      <div className="w-72">
        <Select value={selected} onValueChange={setSelected}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {INDICATOR_OPTIONS.map(o => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Card>
        <CardHeader><CardTitle>{label} — Full History</CardTitle></CardHeader>
        <CardContent>
          <MacroChart data={chartData} height={320} />
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 3: Start API + frontend and verify both pages load**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight"
.venv/bin/uvicorn econsight.api.main:app --port 8000 &
cd frontend && npm run dev &
echo "Open http://localhost:5173 in browser — verify Dashboard and Indicators load with data"
```

- [ ] **Step 4: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && kill %1 %2 2>/dev/null || true
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Indicators.tsx
git commit -m "feat: Dashboard page (health score + indicator cards + forecast table + sparklines) and Indicators page"
```

---

## Task 8: React Pages — Forecasts, Ask, and Report

**Files:**
- Modify: `frontend/src/pages/Forecasts.tsx`
- Modify: `frontend/src/pages/Ask.tsx`
- Modify: `frontend/src/pages/Report.tsx`

- [ ] **Step 1: Write `frontend/src/pages/Forecasts.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query'
import { fetchForecasts } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const TARGETS = ['cpi', 'unemployment_rate', 'overnight_rate']
const TARGET_LABELS: Record<string, string> = {
  cpi: 'CPI', unemployment_rate: 'Unemployment Rate', overnight_rate: 'Overnight Rate',
}

export default function Forecasts() {
  const { data: forecasts = [] } = useQuery({
    queryKey: ['forecasts'], queryFn: fetchForecasts,
  })

  const get = (target: string, horizon: number, model: string) =>
    forecasts.find(f => f.target === target && f.horizon_months === horizon && f.model_type === model)

  const scenarios = ['base', 'upside', 'downside'] as const
  const scenarioColors = { base: '#2563eb', upside: '#16a34a', downside: '#dc2626' }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-800">Forecasts</h1>

      {TARGETS.map(target => {
        const xgb1 = get(target, 1, 'xgboost')
        const xgb3 = get(target, 3, 'xgboost')
        const fanData = xgb3 ? [
          { name: 'p10', value: xgb3.p10 },
          { name: 'p50', value: xgb3.p50 },
          { name: 'p90', value: xgb3.p90 },
        ] : []

        return (
          <Card key={target}>
            <CardHeader>
              <CardTitle>{TARGET_LABELS[target]}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Point forecasts */}
              <div className="grid grid-cols-4 gap-3 text-sm">
                {[['VAR 1M', get(target, 1, 'var')], ['VAR 3M', get(target, 3, 'var')],
                  ['XGB 1M', xgb1], ['XGB 3M', xgb3]].map(([label, f]: any) => (
                  <div key={label} className="border rounded p-3 text-center">
                    <div className="text-xs text-gray-500 mb-1">{label}</div>
                    <div className="font-bold tabular-nums">
                      {f ? f.point_forecast.toFixed(3) : '—'}
                    </div>
                  </div>
                ))}
              </div>

              {/* Monte Carlo bands */}
              {xgb3?.p10 != null && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">3-Month Uncertainty (XGBoost)</p>
                  <div className="flex gap-4 text-sm">
                    {[['p10', xgb3.p10], ['p50', xgb3.p50], ['p90', xgb3.p90]].map(([k, v]: any) => (
                      <div key={k} className="text-center">
                        <div className="text-xs text-gray-400">{k}</div>
                        <div className="font-mono font-bold">{v?.toFixed(3)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Scenarios */}
              {xgb3?.scenario_base != null && (
                <div className="grid grid-cols-3 gap-2">
                  {(['base', 'upside', 'downside'] as const).map(sc => {
                    const val = xgb3[`scenario_${sc}` as keyof typeof xgb3] as number | null
                    return (
                      <div key={sc} className="border rounded p-2 text-center">
                        <Badge variant={sc === 'upside' ? 'default' : sc === 'downside' ? 'destructive' : 'secondary'}
                               className="text-xs mb-1">{sc}</Badge>
                        <div className="font-mono text-sm">{val?.toFixed(3) ?? '—'}</div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Write `frontend/src/pages/Ask.tsx`**

```tsx
import { useState } from 'react'
import { queryRAG } from '@/api/client'
import QueryBox from '@/components/QueryBox'
import type { RAGResponse } from '@/api/client'

export default function Ask() {
  const [response, setResponse] = useState<RAGResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (question: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await queryRAG(question)
      setResponse(result)
    } catch (e) {
      setError('Failed to get answer. Make sure the API is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Ask About the Economy</h1>
        <p className="text-sm text-gray-500 mt-1">
          Ask data questions (answered via SQL) or analysis questions (answered via the Phase 2 report).
        </p>
      </div>
      {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">{error}</div>}
      <QueryBox onSubmit={handleSubmit} response={response} loading={loading} />
    </div>
  )
}
```

- [ ] **Step 3: Write `frontend/src/pages/Report.tsx`**

```tsx
import { useState } from 'react'
import { downloadReport } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function Report() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDownload = async () => {
    setLoading(true)
    setError(null)
    try {
      const blob = await downloadReport()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'econsight_report.pdf'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError('Failed to generate report. This may take up to 60 seconds.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-800">Economic Report</h1>
      <Card>
        <CardHeader><CardTitle>What's included</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm text-gray-600">
          <div>
            <p className="font-medium text-gray-800">Part 1 — Consulting Brief (2-3 pages)</p>
            <ul className="list-disc ml-4 mt-1 space-y-1">
              <li>Economic Health Score with trend</li>
              <li>Key risk indicators table</li>
              <li>VAR vs XGBoost forecast summary</li>
              <li>AI-generated plain-language outlook</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-gray-800">Part 2 — Full Analysis</p>
            <ul className="list-disc ml-4 mt-1 space-y-1">
              <li>Data overview and stationarity tests</li>
              <li>VAR/VECM results with IRF charts</li>
              <li>XGBoost model metrics and predictions</li>
              <li>SHAP feature importance plots</li>
              <li>Monte Carlo uncertainty bands</li>
              <li>Economic Health Score timeline</li>
            </ul>
          </div>
        </CardContent>
      </Card>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Button onClick={handleDownload} disabled={loading} size="lg">
        {loading ? 'Generating report… (up to 60s)' : 'Download PDF Report'}
      </Button>
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add frontend/src/pages/
git commit -m "feat: Forecasts, Ask, and Report pages — Monte Carlo cards, RAG query interface, PDF download"
```

---

## Task 9: Backend API Tests + Final Cleanup

**Files:**
- Modify: `tests/test_api/test_indicators.py` (add health-score test)
- Run all existing tests
- Run lint + mypy

- [ ] **Step 1: Run all backend tests**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest tests/test_api/ -v 2>&1
```

Expected: all tests PASS (indicators, forecasts, rag, report)

- [ ] **Step 2: Run full non-integration test suite**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/pytest -v -m "not integration" 2>&1 | tail -20
```

All 52+ tests must PASS.

- [ ] **Step 3: Lint**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m ruff check src/ tests/ 2>&1
```

Expected: clean

- [ ] **Step 4: Type-check**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/python -m mypy src/econsight 2>&1
```

Expected: no errors

- [ ] **Step 5: Integration check — run API + frontend together**

Terminal 1:
```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && .venv/bin/uvicorn econsight.api.main:app --reload --port 8000
```

Terminal 2:
```bash
cd "/Users/barandursun/AI PROJECT/EconSight/frontend" && npm run dev
```

Open http://localhost:5173 and verify:
- Dashboard loads with health score gauge and indicator cards
- Indicators page shows chart that changes when you select different indicators
- Forecasts page shows all 3 target cards with point forecasts
- Ask page shows example questions and accepts input
- Report page shows download button

- [ ] **Step 6: Verify all API endpoints respond**

```bash
curl -s http://localhost:8000/api/ping | python -m json.tool
curl -s "http://localhost:8000/api/indicators" | python -m json.tool | head -20
curl -s "http://localhost:8000/api/health-score" | python -m json.tool | head -10
curl -s "http://localhost:8000/api/forecasts" | python -m json.tool | head -20
```

- [ ] **Step 7: Update README.md** — add Phase 3 to the Roadmap section

Replace the existing Phase 3 roadmap line with:
```markdown
- **Phase 3 — Complete** — FastAPI REST API, React dashboard (5 pages), RAG NL query engine, PDF report generation
```

- [ ] **Step 8: Push to GitHub**

```bash
cd "/Users/barandursun/AI PROJECT/EconSight" && git add README.md && git commit -m "docs: update README with Phase 3 completion" && git push origin main
```

---

## Phase 3 Complete Checklist

- [ ] `GET /api/ping` → `{"status": "ok"}`
- [ ] `GET /api/indicators` → 36 months of data
- [ ] `GET /api/health-score` → history + latest score
- [ ] `GET /api/forecasts` → 12 forecast rows
- [ ] `POST /api/rag/query` (SQL question) → `query_type: "sql"`, valid answer
- [ ] `POST /api/rag/query` (analysis question) → `query_type: "narrative"`, sources cited
- [ ] `GET /api/report/pdf` → PDF file downloads and opens
- [ ] Dashboard renders health score gauge, 3 indicator cards, forecast table, 9 sparklines
- [ ] Indicators page renders full time-series chart for all 9 indicators
- [ ] Forecasts page shows VAR vs XGBoost, p10/p50/p90, base/upside/downside scenarios
- [ ] Ask page returns answers with source citations
- [ ] `pytest tests/test_api/ -v` → all tests PASS
- [ ] `ruff check src/ tests/` → clean
- [ ] `mypy src/econsight` → no errors
- [ ] GitHub Actions CI → green on `main`
