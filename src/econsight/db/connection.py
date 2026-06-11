import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg

from econsight.config import settings

# In local dev, derive from __file__. In Docker (non-editable install),
# __file__ is in site-packages so we rely on APP_ROOT env var instead.
PROJECT_ROOT = Path(os.environ.get("APP_ROOT", str(Path(__file__).parent.parent.parent.parent)))


@asynccontextmanager
async def db_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with await psycopg.AsyncConnection.connect(settings.db_url) as conn:
        yield conn


@asynccontextmanager
async def db_connection_readonly() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with await psycopg.AsyncConnection.connect(settings.db_url_readonly) as conn:
        yield conn


async def execute_sql_file(conn: psycopg.AsyncConnection, relative_path: str) -> None:
    """Execute a SQL file resolved from the project root."""
    sql = (PROJECT_ROOT / relative_path).read_text()
    await conn.execute(sql)


async def init_db() -> None:
    """Create all schemas, tables, and staging views. Safe to re-run."""
    import asyncio

    schema_sql = (Path(__file__).parent / "schema.sql").read_text()
    stg_statcan = (PROJECT_ROOT / "sql" / "stg_statcan.sql").read_text()
    stg_boc = (PROJECT_ROOT / "sql" / "stg_boc.sql").read_text()

    last_exc: psycopg.OperationalError | None = None
    for attempt in range(5):
        try:
            async with await psycopg.AsyncConnection.connect(
                settings.db_url, autocommit=True
            ) as conn:
                await conn.execute(schema_sql)
                await conn.execute(stg_statcan)
                await conn.execute(stg_boc)
            return
        except psycopg.OperationalError as exc:
            last_exc = exc
            if attempt < 4:
                await asyncio.sleep(2**attempt)

    assert last_exc is not None
    raise last_exc


def init_db_entrypoint() -> None:
    import asyncio
    asyncio.run(init_db())
