from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import psycopg

from econsight.db.connection import db_connection, db_connection_readonly


async def get_db() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with db_connection() as conn:
        yield conn


async def get_db_readonly() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with db_connection_readonly() as conn:
        yield conn


@asynccontextmanager
async def get_cursor(conn: Any) -> AsyncGenerator[psycopg.AsyncCursor[Any], None]:
    """Async context manager for a DB cursor.

    Works with both real psycopg connections (where cursor() is sync) and
    AsyncMock test doubles (where cursor() returns a coroutine).
    """
    result = conn.cursor()
    if inspect.iscoroutine(result):
        result = await result
    async with result as cur:
        yield cur
