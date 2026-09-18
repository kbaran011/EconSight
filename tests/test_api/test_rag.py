from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from econsight.api.schemas import RAGResponse


async def test_rag_query_returns_response_shape():
    from econsight.api.main import app

    mock_resp = RAGResponse(
        answer="CPI was 136.0 in January 2024.",
        sources=["database"],
        query_type="sql",
    )

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

    mock_resp = RAGResponse(
        answer="The yield spread widened due to rate cuts.",
        sources=["3. VAR/VECM Results", "7. Economic Health Score"],
        query_type="narrative",
    )

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


async def test_narrative_answer_includes_grounding(monkeypatch):
    import econsight.rag.query_engine as qe

    async def fake_retrieve(question, top_k=5):
        return [{"title": "Inflation", "text": "Inflation eased over the quarter."}]

    class _FakeEnc:
        def encode(self, texts):
            import numpy as np
            return np.array([[1.0, 0.0] if "inflation" in t.lower() else [0.0, 1.0]
                             for t in texts])

    class _Msg:
        content = "Inflation eased steadily [1]."

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    async def fake_create(*a, **k):
        return _Resp()

    monkeypatch.setattr(qe, "retrieve", fake_retrieve)
    monkeypatch.setattr(qe._client.chat.completions, "create", fake_create)
    monkeypatch.setattr("econsight.rag.retriever.get_encoder", lambda: _FakeEnc())

    resp = await qe._narrative_answer("why did inflation change?")
    assert resp.groundedness is not None
    assert resp.grounding and resp.grounding[0].supported is True
    assert resp.source_snippets[0].chunk_id == 1
