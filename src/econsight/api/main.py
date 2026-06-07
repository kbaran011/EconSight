from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from econsight.api.routers import forecasts, indicators, rag, report
from econsight.config import settings


async def maybe_ingest_rag() -> None:
    try:
        from econsight.rag.ingestion import ingest_if_needed  # type: ignore[import-untyped]
        await ingest_if_needed()
    except Exception:
        pass  # RAG not ready yet — ingest lazily


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from econsight.db.connection import init_db
    await init_db()
    await maybe_ingest_rag()
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


@app.get("/api/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}
