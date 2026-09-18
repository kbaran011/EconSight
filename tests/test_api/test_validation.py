from datetime import date
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient


def _mock_conn(rows, cols):
    mock_cur = AsyncMock()
    mock_cur.fetchall = AsyncMock(return_value=rows)
    mock_cur.description = [(c,) for c in cols]
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_conn


async def test_metrics_endpoint_returns_rows():
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

    cols = ["target", "horizon_months", "model_type", "baseline", "n_folds",
            "mae", "rmse", "mase", "skill_score_vs_rw", "dm_stat", "dm_pvalue",
            "backtest_start", "backtest_end"]
    rows = [("cpi", 1, "xgboost", "random_walk", 50, 0.4, 0.5, 0.7, 0.25,
             -2.1, 0.03, date(2018, 1, 1), date(2025, 12, 1))]

    async def override_db():
        yield _mock_conn(rows, cols)

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/validation/metrics")
    app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body[0]["model_type"] == "xgboost"
    assert body[0]["mase"] == 0.7
    assert body[0]["low_confidence"] is False   # n_folds 50 >= 12


async def test_metrics_low_confidence_flag():
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

    cols = ["target", "horizon_months", "model_type", "baseline", "n_folds",
            "mae", "rmse", "mase", "skill_score_vs_rw", "dm_stat", "dm_pvalue",
            "backtest_start", "backtest_end"]
    rows = [("cpi", 3, "var", "random_walk", 6, 0.4, 0.5, 1.2, -0.1,
             0.5, 0.6, date(2024, 1, 1), date(2025, 12, 1))]

    async def override_db():
        yield _mock_conn(rows, cols)

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/validation/metrics")
    app.dependency_overrides.clear()
    assert r.json()[0]["low_confidence"] is True   # n_folds 6 < 12


async def test_summary_counts_configs_beating_rw():
    from econsight.api.dependencies import get_db
    from econsight.api.main import app

    cols = ["target", "horizon_months", "model_type", "baseline", "n_folds",
            "mae", "rmse", "mase", "skill_score_vs_rw", "dm_stat", "dm_pvalue",
            "backtest_start", "backtest_end"]
    rows = [
        ("cpi", 1, "xgboost", "random_walk", 50, 0.4, 0.5, 0.7, 0.25, -2.1, 0.03,
         date(2018, 1, 1), date(2025, 12, 1)),
        ("cpi", 1, "naive_rw", "random_walk", 50, 0.5, 0.6, 1.0, 0.0, None, None,
         date(2018, 1, 1), date(2025, 12, 1)),
        ("cpi", 1, "var", "random_walk", 50, 0.7, 0.8, 1.3, -0.3, 1.0, 0.4,
         date(2018, 1, 1), date(2025, 12, 1)),
    ]

    async def override_db():
        yield _mock_conn(rows, cols)

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/validation/summary")
    app.dependency_overrides.clear()
    body = r.json()
    # only xgboost has mase<1 and skill>0 among non-naive models
    assert body["configs_beating_rw"] == 1
    assert body["best_config"] == "cpi h1 xgboost"
