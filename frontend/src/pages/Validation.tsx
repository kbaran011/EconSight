import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchValidationMetrics,
  fetchValidationSummary,
  fetchValidationPredictions,
} from '../api/client'
import type { BacktestMetric } from '../api/client'
import { Skeleton } from '../components/ui/skeleton'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Legend,
} from 'recharts'

const MODEL_LABEL: Record<string, string> = {
  naive_rw:       'Random Walk',
  seasonal_naive: 'Seasonal Naive',
  var:            'VAR',
  xgboost:        'XGBoost',
}

// Preferred display order — baseline first, then challengers.
const MODEL_ORDER = ['naive_rw', 'seasonal_naive', 'var', 'xgboost']

// Line colours for the predicted-vs-actual chart (existing token palette).
const SERIES_COLOR: Record<string, string> = {
  Actual:            '#1a2a1a', // --text-primary — the ground truth
  'Random Walk':     '#b0a090', // --text-xmuted — neutral baseline
  'Seasonal Naive':  '#8a7a60', // --text-muted
  VAR:               '#c9483a', // --accent
  XGBoost:           '#1a7a55', // --primary — best challenger
}

const modelLabel = (m: string) => MODEL_LABEL[m] ?? m
const beatsBaseline = (m: BacktestMetric) =>
  m.mase != null && m.mase < 1 && m.skill_score_vs_rw != null && m.skill_score_vs_rw > 0

const fmt = (v: number | null | undefined, digits = 3) =>
  v == null ? '—' : v.toFixed(digits)

interface TooltipEntry { name: string; value: number | null; color: string }
interface TooltipProps { active?: boolean; payload?: TooltipEntry[]; label?: string }
const ChartTooltip = ({ active, payload, label }: TooltipProps) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-[var(--border)] rounded-lg shadow-sm px-3 py-2 text-left min-w-[150px]">
      <p className="text-[11px] text-[var(--text-muted)] mb-2">{label}</p>
      {payload.map((p) => p.value != null && (
        <div key={p.name} className="flex justify-between gap-4 text-[12px]">
          <span className="text-[var(--text-muted)]" style={{ color: p.color }}>{p.name}</span>
          <span className="font-serif font-bold text-[var(--text-primary)]">{p.value.toFixed(3)}</span>
        </div>
      ))}
    </div>
  )
}

/* A single numeric metric cell, coloured only when a model genuinely beats the baseline. */
function MetricCell({ value, digits = 3, good, muted }: {
  value: number | null | undefined
  digits?: number
  good?: boolean
  muted?: boolean
}) {
  const color = muted
    ? 'text-[var(--text-xmuted)]'
    : good === undefined
      ? 'text-[var(--text-secondary)]'
      : good
        ? 'text-[var(--positive)] font-semibold'
        : 'text-amber-600'
  return <td className={`table-td font-mono ${color}`}>{fmt(value, digits)}</td>
}

function GroupTable({ target, horizon, rows }: {
  target: string
  horizon: number
  rows: BacktestMetric[]
}) {
  const ordered = [...rows].sort(
    (a, b) => MODEL_ORDER.indexOf(a.model_type) - MODEL_ORDER.indexOf(b.model_type)
  )
  return (
    <div className="ed-card overflow-hidden">
      <div className="px-6 py-4 border-b border-[var(--border)] flex items-baseline justify-between gap-3">
        <p className="section-label mb-0">{target} — {horizon}-Month Horizon</p>
        <span className="text-[11px] text-[var(--text-muted)] font-mono">vs random walk</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-[var(--surface-2)]">
            <tr>
              {['Model', 'Folds', 'MAE', 'RMSE', 'MASE', 'Skill vs RW', 'DM p'].map(h => (
                <th key={h} className="table-th">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ordered.map((m) => {
              const isBaseline = m.model_type === 'naive_rw'
              const good = isBaseline ? undefined : beatsBaseline(m)
              const significant = m.dm_pvalue != null && m.dm_pvalue < 0.05
              return (
                <tr
                  key={m.model_type}
                  className={`border-b border-[var(--border)] last:border-0 ${
                    isBaseline ? 'bg-[var(--surface-2)]/50' : 'hover:bg-[var(--surface-2)] transition-colors'
                  }`}
                >
                  <td className="table-td font-medium text-[var(--text-primary)]">
                    {modelLabel(m.model_type)}
                    {isBaseline && (
                      <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-[var(--text-xmuted)]">baseline</span>
                    )}
                    {m.low_confidence && (
                      <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-amber-600">low n</span>
                    )}
                  </td>
                  <td className="table-td font-mono text-[var(--text-muted)]">{m.n_folds}</td>
                  <MetricCell value={m.mae} muted={isBaseline} />
                  <MetricCell value={m.rmse} muted={isBaseline} />
                  <MetricCell value={m.mase} digits={2} good={good} muted={isBaseline} />
                  <td className={`table-td font-mono ${
                    isBaseline
                      ? 'text-[var(--text-xmuted)]'
                      : good ? 'text-[var(--positive)] font-semibold' : 'text-amber-600'
                  }`}>
                    {m.skill_score_vs_rw == null ? '—'
                      : `${m.skill_score_vs_rw >= 0 ? '+' : ''}${(m.skill_score_vs_rw * 100).toFixed(1)}%`}
                  </td>
                  <td className={`table-td font-mono ${
                    m.dm_pvalue == null ? 'text-[var(--text-xmuted)]'
                      : significant ? 'text-[var(--text-primary)] font-semibold' : 'text-[var(--text-secondary)]'
                  }`}>
                    {m.dm_pvalue == null ? 'n/a' : m.dm_pvalue.toFixed(3)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function Validation() {
  const summaryQ = useQuery({ queryKey: ['validation-summary'], queryFn: fetchValidationSummary })
  const metricsQ = useQuery({ queryKey: ['validation-metrics'], queryFn: fetchValidationMetrics })

  const metrics = useMemo(() => metricsQ.data ?? [], [metricsQ.data])

  // Distinct target/horizon groups, ordered by target then horizon.
  const groups = useMemo(() => {
    const map = new Map<string, { target: string; horizon: number; rows: BacktestMetric[] }>()
    for (const m of metrics) {
      const key = `${m.target}|${m.horizon_months}`
      if (!map.has(key)) map.set(key, { target: m.target, horizon: m.horizon_months, rows: [] })
      map.get(key)!.rows.push(m)
    }
    return [...map.values()].sort(
      (a, b) => a.target.localeCompare(b.target) || a.horizon - b.horizon
    )
  }, [metrics])

  const targets = useMemo(() => [...new Set(metrics.map(m => m.target))], [metrics])
  const [target, setTarget] = useState('')
  const activeTarget = target || targets[0] || ''

  const horizons = useMemo(
    () => [...new Set(metrics.filter(m => m.target === activeTarget).map(m => m.horizon_months))]
      .sort((a, b) => a - b),
    [metrics, activeTarget]
  )
  const [horizon, setHorizon] = useState<number | null>(null)
  const activeHorizon = horizon ?? horizons[0] ?? null

  const predQ = useQuery({
    queryKey: ['validation-predictions', activeTarget, activeHorizon],
    queryFn: () => fetchValidationPredictions(activeTarget, activeHorizon as number),
    enabled: !!activeTarget && activeHorizon != null,
  })

  // Pivot prediction points into { date, Actual, <ModelLabel>: y_pred } rows.
  const { chartData, seriesNames } = useMemo(() => {
    const points = predQ.data?.points ?? []
    const byDate = new Map<string, Record<string, number>>()
    const models = new Set<string>()
    for (const p of points) {
      const date = p.target_date.slice(0, 7)
      if (!byDate.has(date)) byDate.set(date, { Actual: p.y_true })
      byDate.get(date)![modelLabel(p.model_type)] = p.y_pred
      models.add(modelLabel(p.model_type))
    }
    const rows = [...byDate.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, vals]) => ({ date, ...vals }))
    return { chartData: rows, seriesNames: [...models] }
  }, [predQ.data])

  const summary = summaryQ.data
  const beatPct = summary && summary.total_configs > 0
    ? Math.round((summary.configs_beating_rw / summary.total_configs) * 100)
    : 0

  return (
    <div className="space-y-6">
      <div>
        <p className="section-label">Out-of-Sample Evaluation</p>
        <h1 className="font-serif font-bold text-[28px] tracking-tight text-[var(--text-primary)]">Model Validation</h1>
        <p className="text-sm text-[var(--text-muted)] mt-0.5">
          Expanding-window walk-forward backtest against naive baselines — MASE, skill score, and Diebold–Mariano significance
        </p>
      </div>

      {/* Limited-history note */}
      {summary?.low_confidence && (
        <div className="ed-card p-3 border-l-[3px] border-l-amber-500 bg-amber-50/40">
          <p className="text-[12px] text-amber-700">
            <span className="font-semibold">Limited history:</span> some configurations have few backtest folds.
            Metrics are directional; treat significance tests as indicative rather than definitive.
          </p>
        </div>
      )}

      {/* Summary cards */}
      {summaryQ.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="ed-card p-4">
            <p className="stat-label">Beats Random Walk</p>
            <p className="stat-value">
              {summary.configs_beating_rw}<span className="text-[var(--text-xmuted)]"> / {summary.total_configs}</span>
            </p>
            <p className="text-[11px] text-[var(--text-muted)] mt-1">{beatPct}% of target/horizon configs</p>
          </div>
          <div className="ed-card p-4">
            <p className="stat-label">Best Skill vs RW</p>
            <p className={`stat-value ${summary.best_skill_score != null && summary.best_skill_score > 0 ? 'text-[var(--positive)]' : 'text-amber-600'}`}>
              {summary.best_skill_score == null ? '—'
                : `${summary.best_skill_score >= 0 ? '+' : ''}${(summary.best_skill_score * 100).toFixed(1)}%`}
            </p>
            <p className="text-[11px] text-[var(--text-muted)] mt-1">{summary.best_config ?? 'no challenger'}</p>
          </div>
          <div className="ed-card p-4">
            <p className="stat-label">Backtest Coverage</p>
            <p className="stat-value">{summary.total_folds}<span className="text-[13px] font-normal text-[var(--text-muted)]"> folds</span></p>
            <p className="text-[11px] text-[var(--text-muted)] mt-1 font-mono">
              {summary.backtest_start?.slice(0, 7) ?? '—'} → {summary.backtest_end?.slice(0, 7) ?? '—'}
            </p>
          </div>
        </div>
      )}

      {/* Predicted-vs-actual chart */}
      <div className="ed-card p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <p className="section-label mb-0">Predicted vs Actual</p>
        </div>

        {targets.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {targets.map(t => {
              const isActive = activeTarget === t
              return (
                <button
                  key={t}
                  onClick={() => { setTarget(t); setHorizon(null) }}
                  className={`px-3 py-1 rounded-[6px] text-[12px] font-medium border transition-colors ${
                    isActive
                      ? 'bg-[var(--primary)] text-white border-transparent'
                      : 'bg-[var(--surface-2)] text-[var(--text-secondary)] border-[var(--border)] hover:border-[var(--border-strong)]'
                  }`}
                >
                  {t}
                </button>
              )
            })}
          </div>
        )}

        {horizons.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {horizons.map(h => {
              const isActive = activeHorizon === h
              return (
                <button
                  key={h}
                  onClick={() => setHorizon(h)}
                  className={`px-2.5 py-1 rounded-[6px] text-[11px] font-mono border transition-colors ${
                    isActive
                      ? 'bg-[var(--accent)] text-white border-transparent'
                      : 'bg-[var(--surface-2)] text-[var(--text-secondary)] border-[var(--border)] hover:border-[var(--border-strong)]'
                  }`}
                >
                  {h}mo
                </button>
              )
            })}
          </div>
        )}

        {metricsQ.isLoading || predQ.isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : predQ.isError ? (
          <p className="text-[var(--negative)] text-sm">Failed to load predictions</p>
        ) : chartData.length === 0 ? (
          <p className="text-[var(--text-muted)] text-sm">No backtest predictions available yet</p>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -16 }}>
              <CartesianGrid vertical={false} stroke="var(--surface-2)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--text-xmuted)', fontFamily: 'DM Mono, monospace' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-xmuted)', fontFamily: 'DM Mono, monospace' }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
              <Tooltip content={<ChartTooltip />} />
              <Legend iconType="plainline" iconSize={16} wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
              <Line
                type="monotone" dataKey="Actual" stroke={SERIES_COLOR.Actual}
                strokeWidth={2.5} dot={false} connectNulls
              />
              {seriesNames.map(name => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={SERIES_COLOR[name] ?? '#8a7a60'}
                  strokeWidth={1.5}
                  strokeDasharray="5 3"
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Metrics tables, grouped by target/horizon */}
      {metricsQ.isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : metricsQ.isError ? (
        <p className="text-[var(--negative)] text-sm">Failed to load validation metrics</p>
      ) : groups.length === 0 ? (
        <div className="ed-card p-6">
          <p className="text-[var(--text-muted)] text-sm">
            No backtest results are available yet. Run the walk-forward backtest to populate this page.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map(g => (
            <GroupTable key={`${g.target}|${g.horizon}`} target={g.target} horizon={g.horizon} rows={g.rows} />
          ))}
        </div>
      )}

      {/* Methodology + honest caveat */}
      <div className="ed-card p-6">
        <p className="section-label">Methodology</p>
        <div className="space-y-3 text-[13px] text-[var(--text-secondary)] leading-relaxed">
          <p>
            Each model is scored on an <span className="font-semibold text-[var(--text-primary)]">expanding-window walk-forward backtest</span>:
            at every origin the model trains only on data available up to that point, then forecasts the value{' '}
            <span className="font-mono">h</span> months ahead. This leakage-free rolling origin mirrors how the model would have been used in real time.
          </p>
          <p>
            <span className="font-semibold text-[var(--text-primary)]">MASE</span> (mean absolute scaled error) divides forecast error by the in-sample naive one-step error —
            values <span className="font-mono">&lt; 1</span> beat the naive benchmark. The{' '}
            <span className="font-semibold text-[var(--text-primary)]">skill score</span> is{' '}
            <span className="font-mono">1 − RMSE_model / RMSE_randomwalk</span>; positive means the model improves on a random walk.
            The <span className="font-semibold text-[var(--text-primary)]">Diebold–Mariano</span> test (with the Harvey–Leybourne–Newbold small-sample correction)
            checks whether that error difference is statistically distinguishable from the random-walk baseline.
          </p>
          <p className="text-[var(--text-muted)]">
            Cells are coloured green only where a model genuinely beats the baseline (MASE&nbsp;&lt;&nbsp;1 and positive skill), amber otherwise;
            the random-walk row is shown as the neutral reference. Macroeconomic series are hard to beat, so a model failing to outperform the random walk
            is itself a credible, honest finding.
          </p>
          <p className="text-[11px] text-[var(--text-xmuted)] border-t border-[var(--border)] pt-3">
            Caveat: backtests run over a limited monthly history with a modest number of folds
            {summary?.total_folds ? ` (~${summary.total_folds} random-walk folds in total)` : ''}. DM p-values are indicative, not definitive,
            and should not be read as strong evidence on their own.
          </p>
        </div>
      </div>
    </div>
  )
}
