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
