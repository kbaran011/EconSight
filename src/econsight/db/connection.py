from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg

from econsight.config import settings

# src/econsight/db/connection.py → 4 parents up → repo root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@asynccontextmanager
async def db_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with await psycopg.AsyncConnection.connect(settings.db_url) as conn:
        yield conn


async def execute_sql_file(conn: psycopg.AsyncConnection, relative_path: str) -> None:
    """Execute a SQL file resolved from the project root."""
    sql = (PROJECT_ROOT / relative_path).read_text()
    await conn.execute(sql)


async def init_db() -> None:
    """Create all schemas, tables, and staging views. Safe to re-run."""
    schema_sql = (Path(__file__).parent / "schema.sql").read_text()
    stg_statcan = (PROJECT_ROOT / "sql" / "stg_statcan.sql").read_text()
    stg_boc = (PROJECT_ROOT / "sql" / "stg_boc.sql").read_text()

    async with await psycopg.AsyncConnection.connect(
        settings.db_url, autocommit=True
    ) as conn:
        await conn.execute(schema_sql)
        await conn.execute(stg_statcan)
        await conn.execute(stg_boc)


def init_db_entrypoint() -> None:
    import asyncio
    asyncio.run(init_db())
