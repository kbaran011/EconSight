import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? ''

const api = axios.create({ baseURL })

export interface IndicatorRow {
  period_date: string
  gdp: number | null
  cpi: number | null
  unemployment_rate: number | null
  ippi: number | null
  retail_trade: number | null
  overnight_rate: number | null
  cadusd: number | null
  bond_10yr: number | null
  m2pp: number | null
  cpi_yoy: number | null
  yield_spread: number | null
  unemployment_delta: number | null
}

export interface HealthScorePoint {
  period_date: string
  score: number
  component_scores: Record<string, number>
}

export interface HealthScoreResponse {
  history: HealthScorePoint[]
  latest_score: number
  latest_components: Record<string, number>
}

export interface ForecastPoint {
  period_date: string
  target: string
  horizon_months: number
  model_type: string
  point_forecast: number
  p10: number | null
  p50: number | null
  p90: number | null
  scenario_base: number | null
  scenario_upside: number | null
  scenario_downside: number | null
}

export interface SentenceAttribution {
  text: string
  supported: boolean
  similarity: number
  best_source_title: string
  cited_chunk_ids: number[]
}

export interface SourceSnippet {
  chunk_id: number
  title: string
  snippet: string
}

export interface RAGResponse {
  answer: string
  sources: string[]
  query_type: 'sql' | 'narrative'
  groundedness?: number | null
  grounding?: SentenceAttribution[] | null
  source_snippets?: SourceSnippet[] | null
  executed_sql?: string | null
}

export const fetchIndicators = () =>
  api.get<IndicatorRow[]>('/api/indicators').then(r => r.data)

export const fetchHealthScore = () =>
  api.get<HealthScoreResponse>('/api/health-score').then(r => r.data)

export const fetchForecasts = () =>
  api.get<ForecastPoint[]>('/api/forecasts').then(r => r.data)

export const queryRAG = (question: string) =>
  api.post<RAGResponse>('/api/rag/query', { question }).then(r => r.data)

export const downloadReport = () =>
  api.get('/api/report/pdf', { responseType: 'blob' }).then(r => r.data as Blob)

export interface StatusResponse {
  seeding_status: 'idle' | 'seeding' | 'ready' | 'error'
  seeding_error: string | null
  mart_row_count: number
  latest_data_date: string | null
  last_pipeline_run_at: string | null
  last_pipeline_rows: number | null
  groq_configured: boolean
}

export const fetchStatus = () =>
  api.get<StatusResponse>('/api/status').then(r => r.data)

export interface BacktestMetric {
  target: string
  horizon_months: number
  model_type: string
  baseline: string
  n_folds: number
  mae: number | null
  rmse: number | null
  mase: number | null
  skill_score_vs_rw: number | null
  dm_stat: number | null
  dm_pvalue: number | null
  backtest_start: string | null
  backtest_end: string | null
  low_confidence: boolean
}

export interface BacktestPredictionPoint {
  target_date: string
  model_type: string
  y_true: number
  y_pred: number
}

export interface BacktestPredictionSeries {
  target: string
  horizon_months: number
  points: BacktestPredictionPoint[]
}

export interface ValidationSummary {
  total_configs: number
  configs_beating_rw: number
  best_skill_score: number | null
  best_config: string | null
  total_folds: number
  backtest_start: string | null
  backtest_end: string | null
  low_confidence: boolean
}

export const fetchValidationMetrics = () =>
  api.get<BacktestMetric[]>('/api/validation/metrics').then(r => r.data)

export const fetchValidationSummary = () =>
  api.get<ValidationSummary>('/api/validation/summary').then(r => r.data)

export const fetchValidationPredictions = (target: string, horizon: number) =>
  api
    .get<BacktestPredictionSeries>('/api/validation/predictions', {
      params: { target, horizon },
    })
    .then(r => r.data)
