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

export interface RAGResponse {
  answer: string
  sources: string[]
  query_type: 'sql' | 'narrative'
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
