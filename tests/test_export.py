from __future__ import annotations

import csv
import io

import pytest
from httpx import ASGITransport, AsyncClient

from econsight.api.main import app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_indicators_returns_csv(seeded_marts: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/export/indicators.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert reader.fieldnames is not None
    assert "period_date" in reader.fieldnames
    assert "cpi_yoy" in reader.fieldnames
    assert len(rows) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_health_score_returns_csv(seeded_marts: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/export/health-score.csv")
    assert r.status_code == 200
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert reader.fieldnames is not None
    assert "score" in reader.fieldnames
    assert len(rows) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_forecasts_returns_csv(seeded_marts: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/export/forecasts.csv")
    assert r.status_code == 200
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert reader.fieldnames is not None
    assert "point_forecast" in reader.fieldnames
    assert len(rows) > 0
