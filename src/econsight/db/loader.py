import uuid

import psycopg

from econsight.clients.boc import BocObservation
from econsight.clients.statcan import StatCanObservation
from econsight.config import get_logger

logger = get_logger(__name__)

_STATCAN_UPSERT = """
    INSERT INTO raw.statcan_observations
        (indicator_key, reference_date, value, status, ingested_at, pipeline_run_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (indicator_key, reference_date) DO UPDATE SET
        value           = EXCLUDED.value,
        status          = EXCLUDED.status,
        ingested_at     = EXCLUDED.ingested_at,
        pipeline_run_id = EXCLUDED.pipeline_run_id
"""

_BOC_UPSERT = """
    INSERT INTO raw.boc_observations
        (series_key, reference_date, value, ingested_at, pipeline_run_id)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (series_key, reference_date) DO UPDATE SET
        value           = EXCLUDED.value,
        ingested_at     = EXCLUDED.ingested_at,
        pipeline_run_id = EXCLUDED.pipeline_run_id
"""


async def upsert_statcan(
    conn: psycopg.AsyncConnection[object],
    observations: list[StatCanObservation],
    run_id: uuid.UUID,
    batch_size: int = 1000,
) -> int:
    total = 0
    async with conn.cursor() as cur:
        for i in range(0, len(observations), batch_size):
            batch = observations[i : i + batch_size]
            params = [
                (o.indicator_key, o.reference_date, o.value,
                 o.status, o.ingested_at, run_id)
                for o in batch
            ]
            await cur.executemany(_STATCAN_UPSERT, params)
            total += len(batch)
    logger.info("loader.statcan.upserted", count=total)
    return total


async def upsert_boc(
    conn: psycopg.AsyncConnection[object],
    observations: list[BocObservation],
    run_id: uuid.UUID,
    batch_size: int = 1000,
) -> int:
    total = 0
    async with conn.cursor() as cur:
        for i in range(0, len(observations), batch_size):
            batch = observations[i : i + batch_size]
            params = [
                (o.series_key, o.reference_date, o.value, o.ingested_at, run_id)
                for o in batch
            ]
            await cur.executemany(_BOC_UPSERT, params)
            total += len(batch)
    logger.info("loader.boc.upserted", count=total)
    return total


async def start_run(conn: psycopg.AsyncConnection[object]) -> uuid.UUID:
    run_id = uuid.uuid4()
    async with conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO meta.pipeline_runs (id, status) VALUES (%s, 'running')",
            (run_id,),
        )
    return run_id


async def finish_run(
    conn: psycopg.AsyncConnection[object], run_id: uuid.UUID, rows_loaded: int
) -> None:
    async with conn.cursor() as cur:
        await cur.execute(
            "UPDATE meta.pipeline_runs SET status='success', rows_loaded=%s, "
            "finished_at=now() WHERE id=%s",
            (rows_loaded, run_id),
        )


async def fail_run(
    conn: psycopg.AsyncConnection[object], run_id: uuid.UUID, error_msg: str
) -> None:
    async with conn.cursor() as cur:
        await cur.execute(
            "UPDATE meta.pipeline_runs SET status='failed', error_msg=%s, "
            "finished_at=now() WHERE id=%s",
            (error_msg[:500], run_id),
        )
