from datetime import date
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient


async def test_get_forecasts_returns_list():
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

    cols = ["period_date", "target", "horizon_months", "model_type",
            "point_forecast", "p10", "p50", "p90",
            "scenario_base", "scenario_upside", "scenario_downside"]
    rows = [(date(2026, 5, 1), "cpi", 1, "xgboost",
             136.5, 135.0, 136.5, 138.0, 136.5, 134.0, 139.0)]

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
