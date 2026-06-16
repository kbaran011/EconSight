# Power BI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CSV/JSON export endpoints to the FastAPI backend and a committed Power BI Desktop report (.pbix) that connects to those endpoints — no database credentials required to share or demo.

**Architecture:** A new `export` router exposes three endpoints (`/api/export/indicators.csv`, `/api/export/health-score.csv`, `/api/export/forecasts.csv`) using FastAPI `StreamingResponse`. Power BI Desktop connects via its built-in Web connector to these public Railway URLs, eliminating the need to share PostgreSQL credentials. The `.pbix` file is committed to `powerbi/` so interviewers can open it and hit Refresh.

**Tech Stack:** FastAPI `StreamingResponse`, Python `csv.DictWriter`, Power BI Desktop (free), existing Railway deployment. No new Python packages needed.

---

## Why CSV endpoints over direct PostgreSQL

Direct PostgreSQL requires handing out Railway DB credentials to anyone who opens the report. The export API approach:
- Zero credential sharing — the Railway API URL is already public
- Survives DB migrations (the API contract is stable)
- Demonstrates API design thinking (BI tools as first-class consumers)
- Works identically in Power BI, Tableau, Excel, and IBM Cognos

---

## File Map

| File | Change |
|---|---|
| `src/econsight/api/routers/export.py` | **Create** — three streaming CSV endpoints |
| `src/econsight/api/main.py` | **Modify** — register `export` router |
| `tests/test_export.py` | **Create** — integration tests for all three endpoints |
| `powerbi/EconSight.pbix` | **Create manually** — Power BI Desktop report |
| `powerbi/README.md` | **Create** — connection instructions for anyone opening the file |
| `README.md` | **Modify** — add Power BI section with screenshot |

---

## Task 1: CSV Export Router

**Files:**
- Create: `src/econsight/api/routers/export.py`

- [ ] **Step 1: Create `src/econsight/api/routers/export.py`**

```python
from __future__ import annotations

import csv
import io

import psycopg
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from econsight.api.dependencies import get_cursor, get_db_readonly

router = APIRouter()


def _csv_response(headers: list[str], rows: list[tuple[object, ...]]) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment"},
    )


@router.get("/export/indicators.csv", response_class=StreamingResponse)
async def export_indicators(
    conn: psycopg.AsyncConnection = Depends(get_db_readonly),
) -> StreamingResponse:
    """All 36 months of the macro mart as CSV — ready for Power BI Web connector."""
    sql = """
        SELECT period_date, gdp, cpi, unemployment_rate, ippi, retail_trade,
               overnight_rate, cadusd, bond_10yr, m2pp,
               cpi_yoy, yield_spread, unemployment_delta
        FROM marts.mart_monthly_macro_indicators
        ORDER BY period_date ASC
    """
    async with get_cursor(conn) as cur:
        await cur.execute(sql)
        rows = await cur.fetchall()
        headers = [d[0] for d in (cur.description or [])]
    return _csv_response(headers, rows)


@router.get("/export/health-score.csv", response_class=StreamingResponse)
async def export_health_score(
    conn: psycopg.AsyncConnection = Depends(get_db_readonly),
) -> StreamingResponse:
    """Full health score history as CSV."""
    sql = """
        SELECT period_date, score
        FROM marts.economic_health_score
        ORDER BY period_date ASC
    """
    async with get_cursor(conn) as cur:
        await cur.execute(sql)
        rows = await cur.fetchall()
        headers = [d[0] for d in (cur.description or [])]
    return _csv_response(headers, rows)


@router.get("/export/forecasts.csv", response_class=StreamingResponse)
async def export_forecasts(
    conn: psycopg.AsyncConnection = Depends(get_db_readonly),
) -> StreamingResponse:
    """All forecast rows as CSV (all targets, all horizons)."""
    sql = """
        SELECT period_date, target, horizon_months, model_type,
               point_forecast, p10, p50, p90,
               scenario_base, scenario_upside, scenario_downside
        FROM marts.mart_forecasts
        ORDER BY target, period_date ASC
    """
    async with get_cursor(conn) as cur:
        await cur.execute(sql)
        rows = await cur.fetchall()
        headers = [d[0] for d in (cur.description or [])]
    return _csv_response(headers, rows)
```

- [ ] **Step 2: Verify it parses (no import errors)**

```bash
cd /path/to/EconSight
python -c "from econsight.api.routers import export; print('OK')"
```

Expected: `OK`

---

## Task 2: Register the Router

**Files:**
- Modify: `src/econsight/api/main.py`

- [ ] **Step 1: Import and register the export router**

Add one import and one `include_router` call. In `src/econsight/api/main.py`:

```python
# Add to existing imports at top:
from econsight.api.routers import forecasts, indicators, rag, report, status, export

# Add after existing include_router calls:
app.include_router(export.router, prefix="/api")
```

- [ ] **Step 2: Verify the new routes appear in the OpenAPI schema**

```bash
uvicorn econsight.api.main:app --port 8001 &
sleep 2
curl -s http://localhost:8001/openapi.json | python3 -c "
import sys, json
paths = json.load(sys.stdin)['paths']
for p in paths:
    if 'export' in p:
        print(p)
"
kill %1
```

Expected output:
```
/api/export/indicators.csv
/api/export/health-score.csv
/api/export/forecasts.csv
```

- [ ] **Step 3: Commit**

```bash
git add src/econsight/api/routers/export.py src/econsight/api/main.py
git commit -m "feat: add CSV export endpoints for Power BI / BI tool integration"
```

---

## Task 3: Tests

**Files:**
- Create: `tests/test_export.py`

The existing test suite uses `respx` for mocking HTTP and a live `pg_conn` fixture for integration. Export tests need a live DB since they query the mart — mark them `integration`.

- [ ] **Step 1: Write `tests/test_export.py`**

```python
from __future__ import annotations

import csv
import io

import pytest
from httpx import AsyncClient

from econsight.api.main import app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_indicators_returns_csv() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/export/indicators.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    # Must have the 13 mart columns
    assert "period_date" in reader.fieldnames  # type: ignore[operator]
    assert "cpi_yoy" in reader.fieldnames  # type: ignore[operator]
    assert len(rows) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_health_score_returns_csv() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/export/health-score.csv")
    assert r.status_code == 200
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert "score" in reader.fieldnames  # type: ignore[operator]
    assert len(rows) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_forecasts_returns_csv() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/export/forecasts.csv")
    assert r.status_code == 200
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert "point_forecast" in reader.fieldnames  # type: ignore[operator]
```

- [ ] **Step 2: Run integration tests (requires live PostgreSQL)**

```bash
pytest tests/test_export.py -v -m integration
```

Expected: 3 tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_export.py
git commit -m "test: add integration tests for CSV export endpoints"
```

---

## Task 4: Deploy and Smoke-Test Live Endpoints

- [ ] **Step 1: Push to main and wait for Railway deploy**

```bash
git push origin main
# Wait ~4 min for backend build. Watch:
railway status --service EconSight
```

- [ ] **Step 2: Smoke-test each endpoint against production**

```bash
BASE=https://econsight-production.up.railway.app

# indicators — should return CSV with header row
curl -s "$BASE/api/export/indicators.csv" | head -3

# health-score
curl -s "$BASE/api/export/health-score.csv" | head -3

# forecasts
curl -s "$BASE/api/export/forecasts.csv" | head -3
```

Expected: each returns a CSV with column headers on line 1 and data on line 2+.

---

## Task 5: Power BI Desktop Report (Manual)

This task is done in the Power BI Desktop GUI. Download free at [powerbi.microsoft.com/desktop](https://powerbi.microsoft.com/desktop).

- [ ] **Step 1: Connect to indicators data**

  1. Open Power BI Desktop → **Get Data** → **Web**
  2. URL: `https://econsight-production.up.railway.app/api/export/indicators.csv`
  3. Power BI detects CSV format automatically → **Load**
  4. Rename query to `Indicators` in the Query Editor

- [ ] **Step 2: Connect to health score data**

  Repeat for: `https://econsight-production.up.railway.app/api/export/health-score.csv`
  Rename query to `HealthScore`.

- [ ] **Step 3: Connect to forecasts data**

  Repeat for: `https://econsight-production.up.railway.app/api/export/forecasts.csv`
  Rename query to `Forecasts`.

- [ ] **Step 4: Set correct data types in Power Query Editor**

  For the `Indicators` table:
  - `period_date` → **Date**
  - All numeric columns → **Decimal Number**

  For `HealthScore`:
  - `period_date` → **Date**
  - `score` → **Decimal Number**

  For `Forecasts`:
  - `period_date` → **Date**
  - `horizon_months` → **Whole Number**
  - `point_forecast`, `p10`, `p90`, etc. → **Decimal Number**

- [ ] **Step 5: Build Report Page 1 — "Economic Overview"**

  **Visual 1 — Health Score KPI card** (top-left):
  - Visualization: Card
  - Field: `HealthScore[score]` (Last value, formatted to 2 decimal places)
  - Title: "Composite Health Score / 10"

  **Visual 2 — Health Score trend line** (top-right):
  - Visualization: Line chart
  - X-axis: `HealthScore[period_date]`
  - Y-axis: `HealthScore[score]`
  - Y-axis range: 0–10
  - Color: `#1a7a55` (jade)
  - Title: "Health Score — 36 Month Trend"

  **Visual 3 — CPI vs Overnight Rate** (bottom-left):
  - Visualization: Line and Clustered Column Chart
  - X-axis: `Indicators[period_date]`
  - Column: `Indicators[overnight_rate]`
  - Line: `Indicators[cpi_yoy]`
  - Title: "CPI YoY vs Overnight Rate"

  **Visual 4 — Unemployment trend** (bottom-right):
  - Visualization: Line chart with data labels
  - X-axis: `Indicators[period_date]`
  - Y-axis: `Indicators[unemployment_rate]`
  - Color: `#c9483a` (brick red)
  - Title: "Unemployment Rate (%)"

- [ ] **Step 6: Build Report Page 2 — "Forecasts"**

  **Visual 1 — Forecast slicer**:
  - Visualization: Slicer
  - Field: `Forecasts[target]`

  **Visual 2 — Point forecast with P10/P90 band**:
  - Visualization: Line chart
  - X-axis: `Forecasts[period_date]`
  - Values: `Forecasts[point_forecast]`, `Forecasts[p90]`, `Forecasts[p10]`
  - Title: "12-Month Forecast with Confidence Interval"

  **Visual 3 — Scenario comparison**:
  - Visualization: Line chart
  - X-axis: `Forecasts[period_date]`
  - Values: `Forecasts[scenario_base]`, `Forecasts[scenario_upside]`, `Forecasts[scenario_downside]`
  - Title: "Scenario Analysis (Base / Upside / Downside)"

- [ ] **Step 7: Apply editorial theme colours**

  Go to **View** → **Themes** → **Customize current theme**:
  - First color: `#1a7a55` (jade — used for positive/primary)
  - Second color: `#c9483a` (brick red — used for negative/accent)
  - Third color: `#d97706` (amber — warning)
  - Background: `#faf7f2` (parchment)
  - Font family: Segoe UI (closest available to DM Sans in Power BI)

- [ ] **Step 8: Save the report**

  **File** → **Save As** → save to `powerbi/EconSight.pbix`

- [ ] **Step 9: Take a screenshot for the README**

  Save a screenshot of both report pages to:
  - `powerbi/screenshots/overview.png`
  - `powerbi/screenshots/forecasts.png`

---

## Task 6: Documentation

**Files:**
- Create: `powerbi/README.md`
- Modify: `README.md`

- [ ] **Step 1: Create `powerbi/README.md`**

```markdown
# EconSight — Power BI Integration

## Opening the Report

1. Install [Power BI Desktop](https://powerbi.microsoft.com/desktop) (free)
2. Open `EconSight.pbix`
3. Click **Refresh** — the report pulls live data from the Railway API

No database credentials needed. The report connects to the public API endpoints.

## Data Sources

| Query | Endpoint | Refresh |
|---|---|---|
| Indicators | `/api/export/indicators.csv` | On demand |
| HealthScore | `/api/export/health-score.csv` | On demand |
| Forecasts | `/api/export/forecasts.csv` | On demand |

## Live Endpoints

Base URL: `https://econsight-production.up.railway.app`

- `GET /api/export/indicators.csv` — 36 months of 13 macro indicators
- `GET /api/export/health-score.csv` — composite health score history
- `GET /api/export/forecasts.csv` — VAR/XGBoost forecasts with P10/P90 bands

These same endpoints work in **Excel** (Data → From Web), **Tableau** (Web Data Connector),
and **IBM Cognos** (REST data source).
```

- [ ] **Step 2: Add Power BI section to root `README.md`**

  Add before the "What I'd Add at Scale" section:

  ```markdown
  ## Power BI Integration

  The live data is accessible to any BI tool via public CSV endpoints — no database
  credentials required.

  | Tool | Connection |
  |---|---|
  | Power BI Desktop | Get Data → Web → paste endpoint URL |
  | Excel | Data → From Web → paste endpoint URL |
  | IBM Cognos | REST data source → paste endpoint URL |

  **Endpoints:**
  - `GET /api/export/indicators.csv` — full macro mart (13 columns, 36 months)
  - `GET /api/export/health-score.csv` — composite score history
  - `GET /api/export/forecasts.csv` — VAR/XGBoost forecasts with scenario bands

  A pre-built Power BI report (`powerbi/EconSight.pbix`) is included.
  Open it in Power BI Desktop and click **Refresh** to pull live data.

  ![Power BI Overview](powerbi/screenshots/overview.png)
  ```

- [ ] **Step 3: Commit documentation and .pbix**

```bash
git add powerbi/ README.md
git commit -m "feat: Power BI integration — CSV export API + .pbix report + docs"
git push origin main
```

---

## Verification Checklist

After all tasks are done, verify:

- [ ] `curl https://econsight-production.up.railway.app/api/export/indicators.csv | head -2` returns CSV with headers
- [ ] `curl https://econsight-production.up.railway.app/api/export/health-score.csv | head -2` returns CSV
- [ ] `curl https://econsight-production.up.railway.app/api/export/forecasts.csv | head -2` returns CSV
- [ ] Opening `powerbi/EconSight.pbix` in Power BI Desktop and clicking Refresh loads real data
- [ ] CI passes (ruff + mypy + pytest -m integration)
- [ ] README has the Power BI section with screenshot

---

## IBM Cognos Note

IBM Cognos Analytics (enterprise) connects to the same endpoints:

1. Cognos admin panel → **Manage** → **Data server connections** → **New**
2. Type: **REST**
3. URL: `https://econsight-production.up.railway.app/api/export/indicators.csv`
4. Response format: **CSV**
5. Create a **data module** and build a dashboard

If you have Cognos access via McGill's IBM partnership, the identical endpoints work without any code changes.
