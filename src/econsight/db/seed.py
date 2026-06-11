from __future__ import annotations

import asyncio
from enum import StrEnum

import psycopg

from econsight.config import get_logger, settings

logger = get_logger(__name__)


class SeedStatus(StrEnum):
    IDLE = "idle"
    SEEDING = "seeding"
    READY = "ready"
    ERROR = "error"


_seed_status = SeedStatus.IDLE
_seed_error: str | None = None
_seed_task: asyncio.Task[None] | None = None


def get_seed_status() -> tuple[SeedStatus, str | None]:
    return _seed_status, _seed_error


async def _mart_row_count(conn: psycopg.AsyncConnection) -> int:
    async with conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM marts.mart_monthly_macro_indicators")
        row = await cur.fetchone()
    return int(row[0]) if row else 0


async def _forecast_row_count(conn: psycopg.AsyncConnection) -> int:
    async with conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM marts.model_forecasts")
        row = await cur.fetchone()
    return int(row[0]) if row else 0


async def _run_seed() -> None:
    global _seed_status, _seed_error

    from econsight.db.connection import db_connection

    _seed_status = SeedStatus.SEEDING
    _seed_error = None

    try:
        async with db_connection() as conn:
            mart_count = await _mart_row_count(conn)

        if mart_count == 0:
            logger.info("seed.pipeline_start")
            from econsight.pipeline import run as run_pipeline

            await run_pipeline()
            logger.info("seed.pipeline_done")

        if settings.auto_seed_models:
            async with db_connection() as conn:
                forecast_count = await _forecast_row_count(conn)
            if forecast_count == 0:
                logger.info("seed.models_start")
                from econsight.models.forecaster import run_models

                await run_models()
                logger.info("seed.models_done")

        _seed_status = SeedStatus.READY
        logger.info("seed.complete")
    except Exception as exc:
        _seed_status = SeedStatus.ERROR
        _seed_error = str(exc)
        logger.error("seed.failed", error=str(exc))


async def maybe_seed_data() -> None:
    """Start background seeding when AUTO_SEED is enabled and data is missing."""
    global _seed_task

    if not settings.auto_seed:
        return

    from econsight.db.connection import db_connection

    async with db_connection() as conn:
        mart_count = await _mart_row_count(conn)
        forecast_count = await _forecast_row_count(conn) if settings.auto_seed_models else 1

    if mart_count > 0 and forecast_count > 0:
        global _seed_status
        _seed_status = SeedStatus.READY
        return

    _seed_task = asyncio.create_task(_run_seed())
