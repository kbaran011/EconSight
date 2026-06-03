import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from econsight.clients.statcan import StatCanObservation
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
