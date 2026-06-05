from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient


async def test_pdf_endpoint_returns_pdf_content_type():
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

    mock_conn = AsyncMock()

    async def override_db():
        yield mock_conn

    app.dependency_overrides[get_db] = override_db

    with (
        patch(
            "econsight.api.routers.report.generate_brief",
            new_callable=AsyncMock,
            return_value=b"%PDF-1.4 brief",
        ),
        patch(
            "econsight.api.routers.report.generate_full_report",
            return_value=b"%PDF-1.4 full",
        ),
        patch(
            "econsight.api.routers.report.merge_pdfs",
            return_value=b"%PDF-1.4 merged",
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get("/api/report/pdf")

    app.dependency_overrides.clear()
    assert r.status_code == 200
    assert "application/pdf" in r.headers["content-type"]
    assert r.content.startswith(b"%PDF")


def test_render_brief_html_contains_score():
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
    assert "The Canadian economy" in html
