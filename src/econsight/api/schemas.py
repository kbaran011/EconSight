from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class IndicatorRow(BaseModel):
    period_date: date
    gdp: float | None = None
    cpi: float | None = None
    unemployment_rate: float | None = None
    ippi: float | None = None
    retail_trade: float | None = None
    overnight_rate: float | None = None
    cadusd: float | None = None
    bond_10yr: float | None = None
    m2pp: float | None = None
    cpi_yoy: float | None = None
    yield_spread: float | None = None
    unemployment_delta: float | None = None


class HealthScorePoint(BaseModel):
    period_date: date
    score: float
    component_scores: dict[str, float]


class HealthScoreResponse(BaseModel):
    history: list[HealthScorePoint]
    latest_score: float
    latest_components: dict[str, float]


class ForecastPoint(BaseModel):
    period_date: date
    target: str
    horizon_months: int
    model_type: str
    point_forecast: float
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    scenario_base: float | None = None
    scenario_upside: float | None = None
    scenario_downside: float | None = None


class RAGRequest(BaseModel):
    question: str


class RAGResponse(BaseModel):
    answer: str
    sources: list[str]
    query_type: Literal["sql", "narrative"]


class StatusResponse(BaseModel):
    seeding_status: str
    seeding_error: str | None = None
    mart_row_count: int
    latest_data_date: date | None = None
    last_pipeline_run_at: datetime | None = None
    last_pipeline_rows: int | None = None
    groq_configured: bool
