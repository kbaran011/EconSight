from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient


async def test_rag_query_returns_response_shape():
    from econsight.api.main import app

    mock_resp = MagicMock()
    mock_resp.answer = "CPI was 136.0 in January 2024."
    mock_resp.sources = ["database"]
    mock_resp.query_type = "sql"

    with patch("econsight.api.routers.rag.answer", new_callable=AsyncMock, return_value=mock_resp):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post("/api/rag/query", json={"question": "what was CPI in Jan 2024?"})

    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert "sources" in body
    assert body["query_type"] in ("sql", "narrative")


async def test_rag_sql_allowlist_rejects_dangerous():
    from econsight.rag.query_engine import _is_safe_sql
    assert _is_safe_sql("SELECT * FROM marts.mart_monthly_macro_indicators") is True
    assert _is_safe_sql("DROP TABLE marts.model_forecasts") is False
    assert _is_safe_sql("SELECT 1; DELETE FROM raw.statcan_observations") is False
    assert _is_safe_sql("delete from raw.boc_observations") is False


async def test_rag_narrative_response_has_sources():
    from econsight.api.main import app

    mock_resp = MagicMock()
    mock_resp.answer = "The yield spread widened due to rate cuts."
    mock_resp.sources = ["3. VAR/VECM Results", "7. Economic Health Score"]
    mock_resp.query_type = "narrative"

    with patch("econsight.api.routers.rag.answer", new_callable=AsyncMock, return_value=mock_resp):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/rag/query",
                json={"question": "why is yield spread widening?"},
            )

    assert r.status_code == 200
    body = r.json()
    assert body["query_type"] == "narrative"
    assert len(body["sources"]) > 0
