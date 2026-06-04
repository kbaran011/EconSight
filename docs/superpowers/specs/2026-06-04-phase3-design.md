# EconSight Phase 3 — Consulting Interface
## Design Spec · v1.1 · 2026-06-04

---

## Context

Phases 1 and 2 delivered a tested async ingestion pipeline and an econometric modelling layer. Phase 3 builds the consulting interface on top: a FastAPI REST backend, a React SPA dashboard, a RAG natural-language query engine, and a PDF report generator. The system serves two audiences — an executive scorecard view and an analyst drill-down view — from a single dashboard.

**Scope decisions:**
- Full Phase 3 in one pass: API + React + RAG + PDF
- FastAPI (port 8000) and React (port 5173) run as separate processes with CORS — mirrors Phase 4 production topology
- RAG uses ChromaDB + sentence-transformers (local, no API cost for embedding) + Claude API for answer generation
- PDF = WeasyPrint consulting brief + nbconvert full analysis, merged with pypdf
- No caching in Phase 3 — Phase 4 adds Redis
- No automated frontend tests in Phase 3 — Phase 4 adds Playwright E2E

---

## 1. Project Structure

```
src/econsight/
├── api/
│   ├── __init__.py
│   ├── main.py             # app factory, CORS, router mounts, /api/ping
│   ├── routers/
│   │   ├── indicators.py   # GET /api/indicators, GET /api/health-score
│   │   ├── forecasts.py    # GET /api/forecasts
│   │   ├── rag.py          # POST /api/rag/query
│   │   └── report.py       # GET /api/report/pdf
│   └── schemas.py          # Pydantic response models for all endpoints
├── rag/
│   ├── __init__.py
│   ├── ingestion.py        # parse phase2_report.html → chunks → ChromaDB
│   ├── retriever.py        # embed query → ChromaDB top-k → chunks + titles
│   └── query_engine.py     # route sql|narrative, execute, return answer
└── report/
    ├── __init__.py
    ├── brief.py            # WeasyPrint consulting brief HTML template → PDF bytes
    ├── full_report.py      # nbconvert notebook → PDF bytes
    └── merger.py           # pypdf concatenate brief + full analysis

frontend/
├── src/
│   ├── pages/
│   │   ├── Dashboard.tsx   # health score gauge + indicator cards + forecast table
│   │   ├── Indicators.tsx  # selectable indicator time-series chart
│   │   ├── Forecasts.tsx   # VAR vs XGBoost + Monte Carlo fan charts + scenarios
│   │   ├── Ask.tsx         # NL query input + answer + source citations
│   │   └── Report.tsx      # PDF download page
│   ├── components/
│   │   ├── HealthScoreGauge.tsx
│   │   ├── IndicatorCard.tsx
│   │   ├── MacroChart.tsx  # recharts wrapper
│   │   ├── ForecastTable.tsx
│   │   └── QueryBox.tsx
│   ├── api/
│   │   └── client.ts       # axios instance + typed fetch functions
│   ├── App.tsx             # React Router routes
│   └── main.tsx
├── package.json
├── vite.config.ts
└── tailwind.config.ts

tests/
├── test_api/
│   ├── __init__.py
│   ├── test_indicators.py
│   ├── test_forecasts.py
│   ├── test_rag.py
│   └── test_report.py
```

---

## 2. FastAPI Backend

### `src/econsight/api/main.py`

Creates the FastAPI app using the `lifespan` async context manager pattern (not the deprecated `@app.on_event("startup")`):

```python
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    await maybe_ingest_rag()   # runs ChromaDB ingestion if collection absent
    yield
app = FastAPI(lifespan=lifespan)
```

CORS is configured from `settings.cors_origins` (a `list[str]` read from the `CORS_ORIGINS` env var, defaulting to `["http://localhost:5173"]`). Mounts all routers under `/api`. Exposes `GET /api/ping → {"status": "ok"}`. Entry point: `uvicorn econsight.api.main:app --reload --port 8000`.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/ping` | Health check |
| `GET` | `/api/indicators` | Last 36 months of all 9 indicators + derived signals from `marts.mart_monthly_macro_indicators`, sorted ascending by date |
| `GET` | `/api/health-score` | Full `marts.economic_health_score` time series, latest score, and latest `component_scores` dict |
| `GET` | `/api/forecasts` | Flat `list[ForecastPoint]` — all 12 rows from `marts.model_forecasts` (3 targets × 2 horizons × 2 model types); includes VAR and XGBoost point forecasts and p10/p50/p90 bands |
| `POST` | `/api/rag/query` | Body: `{"question": str}` → `{"answer": str, "sources": list[str], "query_type": "sql" \| "narrative"}` |
| `GET` | `/api/report/pdf` | Streams merged PDF (`application/pdf`, `Content-Disposition: attachment`) |

### `src/econsight/api/schemas.py`

Pydantic v2 models for all response shapes. Key models:

```python
class IndicatorRow(BaseModel):
    period_date: date
    gdp: float | None
    cpi: float | None
    unemployment_rate: float | None
    ippi: float | None
    retail_trade: float | None
    overnight_rate: float | None
    cadusd: float | None
    bond_10yr: float | None
    m2pp: float | None
    cpi_yoy: float | None
    yield_spread: float | None
    unemployment_delta: float | None

class HealthScorePoint(BaseModel):
    period_date: date
    score: float
    component_scores: dict[str, float]

class HealthScoreResponse(BaseModel):
    history: list[HealthScorePoint]
    latest_score: float
    latest_components: dict[str, float]
    # latest_components always has exactly 10 keys:
    # "gdp", "cpi", "unemployment_rate", "ippi", "retail_trade",
    # "overnight_rate", "cadusd", "bond_10yr", "m2pp", "yield_spread"
    # (9 raw indicators + computed yield_spread from CompositeScorer._prepare)

class ForecastPoint(BaseModel):
    period_date: date
    target: str
    horizon_months: int
    model_type: str
    point_forecast: float
    p10: float | None
    p50: float | None
    p90: float | None
    scenario_base: float | None
    scenario_upside: float | None
    scenario_downside: float | None

class RAGRequest(BaseModel):
    question: str

class RAGResponse(BaseModel):
    answer: str
    sources: list[str]
    query_type: Literal["sql", "narrative"]
```

All DB access uses the existing `db_connection()` async context manager.

---

## 3. React Frontend

**Setup:** Vite + React + TypeScript, Tailwind CSS, shadcn/ui, React Router v6, TanStack Query v5, recharts, axios.

### Pages

**`Dashboard` (`/`):**
- Large `HealthScoreGauge` component showing the latest 0–100 score with colour coding (red <40, amber 40–60, green >60)
- Row of 3 `IndicatorCard` components: latest CPI, unemployment rate, overnight rate with month-over-month delta badge
- `ForecastTable` showing 1-month and 3-month XGBoost forecasts for all 3 targets
- Mini sparkline (last 12 months) for each of the 9 indicators

**`Indicators` (`/indicators`):**
- Dropdown to select any of the 9 indicators
- Full `MacroChart` (recharts LineChart) showing the full history
- Date range slider to zoom in/out

**`Forecasts` (`/forecasts`):**
- For each of the 3 targets: a card with VAR and XGBoost point forecasts side by side
- Monte Carlo fan chart: area bands for p10–p90, line for p50
- Three scenario cards (base / upside / downside) with colour coding

**`Ask` (`/ask`):**
- `QueryBox`: text input + submit button
- Response area showing `answer` text and `sources` list as citation chips
- `query_type` badge showing whether SQL or narrative RAG was used
- Example questions shown as clickable chips on load

**`Report` (`/report`):**
- Description of report contents (consulting brief + full analysis)
- "Download PDF Report" button calling `GET /api/report/pdf`
- Loading spinner while PDF is generating (can take 30–60s)

### `frontend/src/api/client.ts`

Axios instance with `baseURL: "http://localhost:8000"`. Typed functions:
- `fetchIndicators(): Promise<IndicatorRow[]>`
- `fetchHealthScore(): Promise<HealthScoreResponse>`
- `fetchForecasts(): Promise<ForecastPoint[]>`
- `queryRAG(question: string): Promise<RAGResponse>`
- `downloadReport(): Promise<Blob>`

---

## 4. RAG System

### `src/econsight/rag/ingestion.py`

Parses `notebooks/phase2_report.html` using BeautifulSoup. Splits on `<h2>` and `<h3>` tags to produce ~50 sections, each with a `title` and `text` (stripped of HTML tags). Embeds each section with `sentence-transformers` model `all-MiniLM-L6-v2` (local, ~80MB). Stores embeddings in a persistent ChromaDB collection at `models/chroma_db/`. Ingestion is triggered by `maybe_ingest_rag()`, a plain async function called from the `lifespan` context manager in `main.py`. The function checks whether the ChromaDB collection already exists and is a no-op on subsequent startups.

### `src/econsight/rag/retriever.py`

```python
def retrieve(question: str, top_k: int = 5) -> list[dict[str, str]]:
    # returns list of {"title": ..., "text": ...}
```

Embeds the question with the same sentence-transformers model, queries ChromaDB, returns the top-k chunks by cosine similarity.

### `src/econsight/rag/query_engine.py`

**Public interface** (called by `src/econsight/api/routers/rag.py`):

```python
async def answer(question: str) -> RAGResponse:
    # returns RAGResponse(answer=..., sources=[...], query_type="sql"|"narrative")
```

**Step 1 — Classify:** Send question to Claude (`claude-sonnet-4-6`) with system prompt:
> "Classify the following question as 'sql' if it asks for specific data values, dates, or statistics that can be answered by querying a database, or 'narrative' if it asks for analysis, explanation, interpretation, or insight. Reply with only 'sql' or 'narrative'."

**Step 2a — SQL path:**
- Send question to Claude with the DB schema string (table/column names only, no data) — schema exposes only the `marts.*` tables (`mart_monthly_macro_indicators`, `model_forecasts`, `economic_health_score`); raw and meta tables are omitted from the schema string to prevent exfiltration
- Claude generates a `SELECT` statement
- Secondary defence: keyword allowlist check — reject if the normalised query (`query.upper()`) contains `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `TRUNCATE`, or `;` (blocks multi-statement)
- Primary defence: execute using a dedicated read-only PostgreSQL role `econsight_reader` that has `SELECT` granted only on `marts.*` tables. Connection uses `settings.db_url_readonly` (e.g. `postgresql://econsight_reader:password@localhost:5432/econsight`). `db_connection_readonly()` is a second async context manager in `db/connection.py` that connects as this role.
- Format result rows as a markdown table, return as answer + `sources: ["database"]`

**Step 2b — Narrative path:**
- Call `retriever.retrieve(question, top_k=5)`
- Send retrieved chunks + question to Claude:
  > "Answer the question using only the provided context. Cite the section titles you used."
- Return answer + `sources: [list of section titles used]`

**Claude model:** `claude-sonnet-4-6` for all calls. Uses `anthropic` Python SDK with the `ANTHROPIC_API_KEY` env var (added to `.env.example`).

---

## 5. PDF Generation

### `src/econsight/report/brief.py`

Generates a 2-3 page consulting brief as PDF bytes using WeasyPrint from an inline HTML/CSS template. Contents:

1. **Cover:** "EconSight — Canadian Economic Outlook" with current month/year and a subtitle line
2. **Economic Health Score:** Latest score (large number, colour-coded), month-over-month change, brief description of what the score means
3. **Key Risk Indicators:** Table of the 3 indicators with the most negative `component_scores` values, showing latest value and trend direction
4. **Forecast Summary:** Table with rows = targets (CPI, unemployment, overnight rate), columns = VAR 1M, VAR 3M, XGBoost 1M, XGBoost 3M
5. **Outlook:** 2-3 sentence paragraph generated by Claude API summarising the economic picture in plain language, based on latest health score, forecast direction, and top risk indicators

Function signature:
```python
async def generate_brief(conn: psycopg.AsyncConnection) -> bytes:
```

### `src/econsight/report/full_report.py`

Runs nbconvert to execute and export `notebooks/phase2_analysis.ipynb` to PDF via LaTeX. Because `subprocess` is blocking and PDF generation takes 30–60 seconds, the function is wrapped in `asyncio.to_thread` by the caller:

```python
def generate_full_report() -> bytes:
    # subprocess: jupyter nbconvert --execute --to pdf notebooks/phase2_analysis.ipynb
    # reads output PDF bytes and returns them
    # NOTE: always call as: await asyncio.to_thread(generate_full_report)
```

**LaTeX availability** is checked once at module import time via `shutil.which("xelatex")` and stored as `_LATEX_AVAILABLE: bool`. If `False`, `generate_full_report` uses `nbconvert --to html` then WeasyPrint to produce the PDF, and logs a `structlog` warning so the fallback is always visible in logs. The `/api/report/pdf` endpoint likewise calls `generate_brief` (async) and `asyncio.to_thread(generate_full_report)` concurrently via `asyncio.gather` to minimise wall-clock latency.

### `src/econsight/report/merger.py`

```python
def merge_pdfs(brief_bytes: bytes, full_bytes: bytes) -> bytes:
    # pypdf: concatenate brief + full analysis
    # returns merged PDF bytes
```

The `GET /api/report/pdf` endpoint awaits `generate_brief` and `asyncio.to_thread(generate_full_report)` concurrently via `asyncio.gather`; once both complete their results are passed to `merge_pdfs`, and the merged PDF bytes are streamed back.

---

## 6. Testing Strategy

### Backend Tests (`tests/test_api/`)

Uses `pytest` + `httpx.AsyncClient` with FastAPI's `TestClient`. All DB calls are mocked using `unittest.mock.AsyncMock` with fixture data.

| File | Tests |
|------|-------|
| `test_indicators.py` | Status 200, response is a list of `IndicatorRow`, date field is a date string |
| `test_forecasts.py` | Status 200, all 12 expected rows present (3 targets × 2 horizons × 2 model types) |
| `test_rag.py` | SQL path returns `query_type="sql"`; narrative path returns `query_type="narrative"`; non-SELECT SQL is rejected with 400 |
| `test_report.py` | PDF endpoint returns `Content-Type: application/pdf`; response body starts with `%PDF` |

### PDF Tests

`test_report.py` calls `generate_brief()` with mocked DB data and asserts the result is bytes starting with `%PDF-`.

### Frontend

No automated tests — manually verify all 5 pages load, charts render, RAG query returns an answer, PDF download works.

---

## 7. New Dependencies

### Python (`pyproject.toml`)

```toml
dependencies = [
    # existing ...
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "anthropic>=0.28",
    "chromadb>=0.5",
    "sentence-transformers>=3.0",
    "beautifulsoup4>=4.12",
    "weasyprint>=62.0",
    "pypdf>=4.0",
]

[project.optional-dependencies]
dev = [
    # existing dev deps ...
    "httpx>=0.27",   # required by FastAPI TestClient
]
```

### Frontend (`frontend/package.json`)

```json
{
  "dependencies": {
    "react": "^18.3",
    "react-dom": "^18.3",
    "react-router-dom": "^6.24",
    "@tanstack/react-query": "^5.48",
    "recharts": "^2.12",
    "axios": "^1.7"
  },
  "devDependencies": {
    "vite": "^5.3",
    "@vitejs/plugin-react": "^4.3",
    "tailwindcss": "^3.4",
    "typescript": "^5.5"
  }
}
```

shadcn/ui components added via CLI: `card`, `button`, `table`, `input`, `badge`, `skeleton`, `select`.

### Environment

Add to `.env.example`:
```
ANTHROPIC_API_KEY=your_key_here
CORS_ORIGINS=http://localhost:5173
DB_URL_READONLY=postgresql://econsight_reader:password@localhost:5432/econsight
```

`settings` in `src/econsight/config.py` gains two new fields:
```python
cors_origins: list[str] = ["http://localhost:5173"]
db_url_readonly: str = "postgresql://econsight_reader:password@localhost:5432/econsight"
```

The `econsight_reader` PostgreSQL role must be created before running Phase 3:
```sql
CREATE ROLE econsight_reader LOGIN PASSWORD 'password';
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO econsight_reader;
```

---

## Phase 3 Complete Checklist

- [ ] `GET /api/ping` returns `{"status": "ok"}`
- [ ] `GET /api/indicators` returns 36 months of data
- [ ] `GET /api/health-score` returns history + latest score
- [ ] `GET /api/forecasts` returns 12 forecast rows
- [ ] `POST /api/rag/query` with a data question → `query_type: "sql"`, valid answer
- [ ] `POST /api/rag/query` with an analysis question → `query_type: "narrative"`, cited sources
- [ ] `GET /api/report/pdf` → PDF file downloads, opens correctly
- [ ] Dashboard loads with health score gauge + indicator cards + forecast table
- [ ] Indicators page renders time-series chart for each of the 9 indicators
- [ ] Forecasts page shows VAR vs XGBoost + Monte Carlo fan charts
- [ ] Ask page returns answers with source citations
- [ ] `pytest tests/test_api/ -v` → all API tests PASS
- [ ] `ruff check src/ tests/` → clean
- [ ] `mypy src/econsight` → no errors
- [ ] GitHub Actions CI → green on `main`
