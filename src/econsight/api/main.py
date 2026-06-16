from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from econsight.api.routers import export, forecasts, indicators, rag, report, status
from econsight.config import get_logger, settings

logger = get_logger(__name__)


async def _ingest_rag_background() -> None:
    try:
        from econsight.rag.ingestion import ingest_if_needed
        await ingest_if_needed()
    except Exception:
        pass  # RAG not ready — ingest lazily on first query


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    import asyncio

    from econsight.db.connection import init_db
    from econsight.db.seed import maybe_seed_data

    await init_db()

    if not settings.groq_api_key:
        logger.warning("groq.api_key_missing", hint="Set GROQ_API_KEY for Ask page")

    # Run RAG ingestion and seeding in background so /api/ping responds immediately
    asyncio.get_event_loop().create_task(_ingest_rag_background())
    await maybe_seed_data()
    yield


app = FastAPI(title="EconSight API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(indicators.router, prefix="/api")
app.include_router(forecasts.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/api/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}
