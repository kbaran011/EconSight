import asyncio

from econsight.clients.boc import BocClient
from econsight.clients.statcan import StatCanClient
from econsight.config import configure_logging, get_logger
from econsight.db.connection import db_connection, execute_sql_file
from econsight.db.loader import fail_run, finish_run, start_run, upsert_boc, upsert_statcan

logger = get_logger(__name__)


async def run() -> None:
    configure_logging()
    logger.info("pipeline.start")

    async with db_connection() as conn:
        run_id = None
        run_id = await start_run(conn)
        try:
            async with StatCanClient() as statcan, BocClient() as boc:
                statcan_data, boc_data = await asyncio.gather(
                    statcan.fetch_all(),
                    boc.fetch_all(),
                )

            rows = await upsert_statcan(conn, statcan_data, run_id)
            rows += await upsert_boc(conn, boc_data, run_id)

            await execute_sql_file(conn, "sql/mart_monthly_macro.sql")
            await conn.commit()

            await finish_run(conn, run_id, rows)
            await conn.commit()

            logger.info("pipeline.complete", rows_loaded=rows)

        except Exception as exc:
            logger.error("pipeline.failed", error=str(exc))
            if run_id is not None:
                await fail_run(conn, run_id, str(exc))
                await conn.commit()
            raise


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
