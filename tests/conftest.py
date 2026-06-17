from collections.abc import AsyncGenerator
from typing import Any

import psycopg
import pytest

from econsight.config import settings


@pytest.fixture
async def pg_conn() -> AsyncGenerator[psycopg.AsyncConnection[Any], None]:
    """Integration test fixture — requires live PostgreSQL."""
    async with await psycopg.AsyncConnection.connect(settings.db_url) as conn:
        yield conn
        await conn.rollback()  # clean up after each test


@pytest.fixture
async def seeded_marts() -> AsyncGenerator[None, None]:
    """Insert one committed row per mart table so export endpoints have data."""
    async with await psycopg.AsyncConnection.connect(
        settings.db_url, autocommit=True
    ) as conn:
        await conn.execute("""
            INSERT INTO marts.mart_monthly_macro_indicators
                (period_date, period_label, gdp, cpi, unemployment_rate, ippi,
                 retail_trade, overnight_rate, cadusd, bond_10yr,
                 m2pp, cpi_yoy, yield_spread, unemployment_delta)
            VALUES ('1990-01-01', '1990-01', 100, 160, 6.0, 110,
                    50000, 5.0, 0.73, 3.5, 2200000, 3.1, -1.5, 0.1)
            ON CONFLICT DO NOTHING
        """)
        await conn.execute("""
            INSERT INTO marts.economic_health_score (period_date, score, component_scores)
            VALUES ('1990-01-01', 6.5, '{}')
            ON CONFLICT DO NOTHING
        """)
        await conn.execute("""
            INSERT INTO marts.model_forecasts
                (period_date, target, horizon_months, model_type,
                 point_forecast, p10, p50, p90,
                 scenario_base, scenario_upside, scenario_downside)
            VALUES ('1990-02-01', 'cpi', 1, 'xgb',
                    161.0, 158.0, 161.0, 164.0, 161.0, 163.0, 159.0)
            ON CONFLICT DO NOTHING
        """)
        yield
        await conn.execute(
            "DELETE FROM marts.mart_monthly_macro_indicators WHERE period_date = '1990-01-01'"
        )
        await conn.execute(
            "DELETE FROM marts.economic_health_score WHERE period_date = '1990-01-01'"
        )
        await conn.execute(
            "DELETE FROM marts.model_forecasts WHERE period_date = '1990-02-01' AND target = 'cpi'"
        )
