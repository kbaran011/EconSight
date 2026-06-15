import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchForecasts } from '../api/client'
import { Skeleton } from '../components/ui/skeleton'
import {
  ComposedChart, Line, Area, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Legend,
} from 'recharts'

interface TooltipEntry { name: string; value: number | null }
interface TooltipProps { active?: boolean; payload?: TooltipEntry[]; label?: string }
const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-[var(--border)] rounded-lg shadow-sm px-3 py-2 text-left min-w-[140px]">
      <p className="text-[11px] text-[var(--text-muted)] mb-2">{label}</p>
      {payload.map((p) => p.value != null && (
        <div key={p.name} className="flex justify-between gap-4 text-[12px]">
          <span className="text-[var(--text-muted)]">{p.name}</span>
          <span className="font-serif font-bold text-[var(--text-primary)]">{typeof p.value === 'number' ? p.value.toFixed(4) : p.value}</span>
        </div>
      ))}
    </div>
  )
}

export default function Forecasts() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['forecasts'], queryFn: fetchForecasts })

  const targets = [...new Set(data?.map(f => f.target) ?? [])]
  const [target, setTarget] = useState('')
  const activeTarget = target || targets[0] || ''

  const rows = data?.filter(f => f.target === activeTarget) ?? []

  const chartData = rows.map(f => ({
    date: f.period_date.slice(0, 7),
    Forecast:  +(f.point_forecast).toFixed(4),
    P10:       f.p10 != null ? +f.p10.toFixed(4) : null,
    P90:       f.p90 != null ? +f.p90.toFixed(4) : null,
    Upside:    f.scenario_upside   != null ? +f.scenario_upside.toFixed(4)   : null,
    Base:      f.scenario_base     != null ? +f.scenario_base.toFixed(4)     : null,
    Downside:  f.scenario_downside != null ? +f.scenario_downside.toFixed(4) : null,
  }))

  const hasInterval  = chartData.some(d => d.P10 != null && d.P90 != null)
  const hasScenarios = chartData.some(d => d.Base != null)

  const latestForecast = rows.at(-1)

  return (
    <div className="space-y-6">
      <div>
        <p className="section-label">Econometric Projections</p>
        <h1 className="font-serif font-bold text-[28px] tracking-tight text-[var(--text-primary)]">Forecasts</h1>
        <p className="text-sm text-[var(--text-muted)] mt-0.5">VAR / XGBoost models with Monte Carlo scenario bands</p>
      </div>

      {/* Target selector */}
      {targets.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {targets.map(t => {
            const isActive = activeTarget === t
            return (
              <button
                key={t}
                onClick={() => setTarget(t)}
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

      {/* Summary stats */}
      {latestForecast && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Point Forecast', value: latestForecast.point_forecast?.toFixed(4) },
            { label: 'P10 (Bear)',     value: latestForecast.p10?.toFixed(4) ?? '—' },
            { label: 'P90 (Bull)',     value: latestForecast.p90?.toFixed(4) ?? '—' },
            { label: 'Model',          value: latestForecast.model_type },
          ].map(s => (
            <div key={s.label} className="ed-card p-4">
              <p className="stat-label">{s.label}</p>
              <p className="stat-value text-base">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Chart */}
      <div className="ed-card p-6">
        <div className="flex items-start justify-between gap-4 mb-2">
          <p className="section-label mb-0">{activeTarget} — 12-Month Horizon</p>
          {latestForecast && latestForecast.p10 != null && latestForecast.p90 != null && (
            <p className="text-[12px] text-[var(--text-secondary)] max-w-xs text-right leading-relaxed">
              <span className="font-semibold text-[var(--text-primary)]">{latestForecast.model_type}</span> projects{' '}
              <span className="font-mono text-[var(--primary)] font-semibold">{latestForecast.point_forecast.toFixed(3)}</span>
              {' '}at 12 months — P10/P90 range{' '}
              <span className="font-mono text-[var(--text-secondary)]">{latestForecast.p10.toFixed(3)}–{latestForecast.p90.toFixed(3)}</span>
            </p>
          )}
        </div>
        {isLoading ? <Skeleton className="h-64 w-full" /> : isError ? (
          <p className="text-red-500 text-sm">Failed to load forecasts</p>
        ) : chartData.length === 0 ? (
          <p className="text-[var(--text-muted)] text-sm">No forecast data available</p>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <ComposedChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -16 }}>
              <CartesianGrid vertical={false} stroke="var(--surface-2)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--text-xmuted)', fontFamily: 'DM Mono, monospace' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-xmuted)', fontFamily: 'DM Mono, monospace' }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend iconType="plainline" iconSize={16} wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
              {hasInterval && <Area type="monotone" dataKey="P90" fill="rgba(26,122,85,0.10)" stroke="none" name="P90" />}
              {hasInterval && <Area type="monotone" dataKey="P10" fill="#ffffff" stroke="none" name="P10" />}
              <Line type="monotone" dataKey="Forecast" stroke="#1a7a55" strokeWidth={2} dot={false} />
              {hasScenarios && <Line type="monotone" dataKey="Upside"   stroke="#1a6a3a" strokeWidth={1.5} strokeDasharray="5 3" dot={false} />}
              {hasScenarios && <Line type="monotone" dataKey="Base"     stroke="#1a7a55" strokeOpacity={0.6} strokeWidth={1.5} strokeDasharray="5 3" dot={false} />}
              {hasScenarios && <Line type="monotone" dataKey="Downside" stroke="#c9483a" strokeWidth={1.5} strokeDasharray="5 3" dot={false} />}
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Detail table */}
      {rows.length > 0 && (
        <div className="ed-card overflow-hidden mt-6">
          <div className="px-6 py-4 border-b border-[var(--border)]">
            <p className="section-label mb-0">Forecast Detail</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[var(--surface-2)]">
                <tr>
                  {['Period', 'Horizon', 'Model', 'Forecast', 'P10', 'P90', 'Base', 'Upside', 'Downside'].map(h => (
                    <th key={h} className="table-th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((f, i) => (
                  <tr key={i} className={`hover:bg-[var(--surface-2)] transition-colors ${i % 2 === 0 ? '' : 'bg-[var(--surface-2)]/40'}`}>
                    <td className="table-td font-medium text-[var(--text-primary)]">{f.period_date.slice(0, 7)}</td>
                    <td className="table-td">{f.horizon_months}mo</td>
                    <td className="table-td text-[var(--text-muted)]">{f.model_type}</td>
                    <td className="table-td font-medium">{f.point_forecast.toFixed(4)}</td>
                    <td className="table-td text-[var(--text-secondary)]">{f.p10?.toFixed(4) ?? '—'}</td>
                    <td className="table-td text-[var(--text-secondary)]">{f.p90?.toFixed(4) ?? '—'}</td>
                    <td className="table-td text-amber-600">{f.scenario_base?.toFixed(4) ?? '—'}</td>
                    <td className="table-td text-emerald-600">{f.scenario_upside?.toFixed(4) ?? '—'}</td>
                    <td className="table-td text-red-500">{f.scenario_downside?.toFixed(4) ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
