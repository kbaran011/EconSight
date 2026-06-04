from datetime import date
from unittest.mock import AsyncMock

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
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

    cols = ["period_date", "gdp", "cpi", "unemployment_rate", "ippi",
            "retail_trade", "overnight_rate", "cadusd", "bond_10yr", "m2pp",
            "cpi_yoy", "yield_spread", "unemployment_delta"]
    rows = [
        (
            date(2024, 1, 1), 2_100_000, 136.0, 5.8, 110.0, 57_000,
            1.75, 0.74, 1.44, 1_950_000, 2.5, -0.31, 0.1,
        )
    ]
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
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

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
