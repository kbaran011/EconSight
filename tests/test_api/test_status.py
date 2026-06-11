from __future__ import annotations

from datetime import date, datetime
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient


async def test_get_status() -> None:
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

    mock_cur = AsyncMock()
    mock_cur.fetchone = AsyncMock(side_effect=[
        (36,),
        (date(2025, 1, 1),),
        ("success", 120, datetime(2025, 1, 2, 12, 0, 0)),
    ])
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

    async def override_db():
        yield mock_conn

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/status")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["mart_row_count"] == 36
    assert body["latest_data_date"] == "2025-01-01"
    assert body["seeding_status"] in ("idle", "ready")
