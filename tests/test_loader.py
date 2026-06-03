import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from econsight.clients.statcan import StatCanObservation
from econsight.db.connection import execute_sql_file
from econsight.db.loader import upsert_statcan


@pytest.mark.integration
async def test_upsert_statcan_inserts_rows(pg_conn) -> None:
    run_id = uuid.uuid4()
    obs = [StatCanObservation(
        indicator_key="18-10-0004-01",
        reference_date=date(2024, 1, 1),
        value=Decimal("160.8"),
        status="A",
        ingested_at=datetime.now(tz=UTC),
    )]
    count = await upsert_statcan(pg_conn, obs, run_id)
    assert count == 1


@pytest.mark.integration
async def test_upsert_statcan_is_idempotent(pg_conn) -> None:
    run_id = uuid.uuid4()
    obs = [StatCanObservation(
        indicator_key="18-10-0004-01",
        reference_date=date(2024, 2, 1),
        value=Decimal("161.2"),
        status="A",
        ingested_at=datetime.now(tz=UTC),
    )]
    await upsert_statcan(pg_conn, obs, run_id)
    await upsert_statcan(pg_conn, obs, run_id)  # re-run same data

    async with pg_conn.cursor() as cur:
        await cur.execute(
            "SELECT COUNT(*) FROM raw.statcan_observations "
            "WHERE indicator_key = %s AND reference_date = %s",
            ("18-10-0004-01", date(2024, 2, 1)),
        )
        row = await cur.fetchone()
    assert row is not None and row[0] == 1  # no duplicates


@pytest.mark.integration
async def test_upsert_statcan_updates_value_on_conflict(pg_conn) -> None:
    run_id = uuid.uuid4()
    base = StatCanObservation(
        indicator_key="18-10-0004-01",
        reference_date=date(2024, 3, 1),
        value=Decimal("160.0"),
        status="P",
        ingested_at=datetime.now(tz=UTC),
    )
    await upsert_statcan(pg_conn, [base], run_id)

    revised = StatCanObservation(
        indicator_key="18-10-0004-01",
        reference_date=date(2024, 3, 1),
        value=Decimal("160.5"),
        status="A",
        ingested_at=datetime.now(tz=UTC),
    )
    await upsert_statcan(pg_conn, [revised], run_id)

    async with pg_conn.cursor() as cur:
        await cur.execute(
            "SELECT value, status FROM raw.statcan_observations "
            "WHERE indicator_key = %s AND reference_date = %s",
            ("18-10-0004-01", date(2024, 3, 1)),
        )
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == Decimal("160.5")
    assert row[1] == "A"


@pytest.mark.integration
async def test_mart_materialises_after_upsert(pg_conn) -> None:
    import uuid as _uuid
    from econsight.clients.boc import BocObservation
    from econsight.db.loader import upsert_boc

    run_id = _uuid.uuid4()
    statcan_obs = [StatCanObservation(
        indicator_key="18-10-0004-01",
        reference_date=date(2020, 6, 1),
        value=Decimal("136.0"),
        status="A",
        ingested_at=datetime.now(tz=UTC),
    )]
    await upsert_statcan(pg_conn, statcan_obs, run_id)

    boc_obs = [
        BocObservation("V39079",    date(2020, 6, 1), Decimal("0.25"), datetime.now(tz=UTC)),
        BocObservation("V122487",   date(2020, 6, 1), Decimal("0.55"), datetime.now(tz=UTC)),
        BocObservation("FXCADUSD",  date(2020, 6, 1), Decimal("0.74"), datetime.now(tz=UTC)),
        BocObservation("V41552796", date(2020, 6, 1), Decimal("2200000"), datetime.now(tz=UTC)),
    ]
    await upsert_boc(pg_conn, boc_obs, run_id)

    await execute_sql_file(pg_conn, "sql/mart_monthly_macro.sql")

    async with pg_conn.cursor() as cur:
        await cur.execute(
            "SELECT cpi, overnight_rate, yield_spread FROM marts.mart_monthly_macro_indicators "
            "WHERE period_date = %s",
            (date(2020, 6, 1),),
        )
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == Decimal("136.0")   # cpi
    assert row[1] == Decimal("0.25")    # overnight_rate
    assert row[2].normalize() == (Decimal("0.55") - Decimal("0.25")).normalize()  # yield_spread
