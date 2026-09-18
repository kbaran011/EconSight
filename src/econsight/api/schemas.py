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


class SourceSnippet(BaseModel):
    chunk_id: int
    title: str
    snippet: str


class SentenceAttribution(BaseModel):
    text: str
    supported: bool
    similarity: float
    best_source_title: str
    cited_chunk_ids: list[int] = []


class RAGResponse(BaseModel):
    answer: str
    sources: list[str]
    query_type: Literal["sql", "narrative"]
    groundedness: float | None = None
    grounding: list[SentenceAttribution] | None = None
    source_snippets: list[SourceSnippet] | None = None
    executed_sql: str | None = None


class BacktestMetric(BaseModel):
    target: str
    horizon_months: int
    model_type: str
    baseline: str
    n_folds: int
    mae: float | None = None
    rmse: float | None = None
    mase: float | None = None
    skill_score_vs_rw: float | None = None
    dm_stat: float | None = None
    dm_pvalue: float | None = None
    backtest_start: date | None = None
    backtest_end: date | None = None
    low_confidence: bool = False


class BacktestPredictionPoint(BaseModel):
    target_date: date
    model_type: str
    y_true: float
    y_pred: float


class BacktestPredictionSeries(BaseModel):
    target: str
    horizon_months: int
    points: list[BacktestPredictionPoint]


class ValidationSummary(BaseModel):
    total_configs: int
    configs_beating_rw: int
    best_skill_score: float | None = None
    best_config: str | None = None
    total_folds: int
    backtest_start: date | None = None
    backtest_end: date | None = None
    low_confidence: bool = False


class StatusResponse(BaseModel):
    seeding_status: str
    seeding_error: str | None = None
    mart_row_count: int
    latest_data_date: date | None = None
    last_pipeline_run_at: datetime | None = None
    last_pipeline_rows: int | None = None
    groq_configured: bool
    backtest_row_count: int = 0
