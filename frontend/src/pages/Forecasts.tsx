import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchForecasts } from '../api/client'
import { Skeleton } from '../components/ui/skeleton'
import {
  ComposedChart, Line, Area, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Legend,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg px-3 py-2.5 text-left min-w-[140px]">
      <p className="text-[11px] text-slate-400 mb-2">{label}</p>
      {payload.map((p: any) => p.value != null && (
        <div key={p.name} className="flex justify-between gap-4 text-[12px]">
          <span className="text-slate-500">{p.name}</span>
          <span className="font-semibold text-slate-800">{typeof p.value === 'number' ? p.value.toFixed(4) : p.value}</span>
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
        <p className="section-title">Econometric Projections</p>
        <h1 className="text-2xl font-semibold text-slate-900">Forecasts</h1>
        <p className="text-sm text-slate-500 mt-0.5">VAR / XGBoost models with Monte Carlo scenario bands</p>
      </div>

      {/* Target selector */}
      {targets.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {targets.map(t => (
            <button
              key={t}
              onClick={() => setTarget(t)}
              className={`text-[12px] font-medium px-3 py-1.5 rounded-full border transition-colors ${
                activeTarget === t
                  ? 'bg-blue-700 text-white border-blue-700'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-blue-300 hover:text-blue-700'
              }`}
            >
              {t}
            </button>
          ))}
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
            <div key={s.label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <p className="stat-label">{s.label}</p>
              <p className="stat-value text-base">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Chart */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <p className="section-title mb-1">{activeTarget} — 12-Month Horizon</p>
        {isLoading ? <Skeleton className="h-64 w-full" /> : isError ? (
          <p className="text-red-500 text-sm">Failed to load forecasts</p>
        ) : chartData.length === 0 ? (
          <p className="text-slate-400 text-sm">No forecast data available</p>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <ComposedChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -16 }}>
              <CartesianGrid vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend iconType="plainline" iconSize={16} wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
              {hasInterval && <Area type="monotone" dataKey="P90" fill="#dbeafe" stroke="none" name="P90" />}
              {hasInterval && <Area type="monotone" dataKey="P10" fill="#fff" stroke="none" name="P10" />}
              <Line type="monotone" dataKey="Forecast" stroke="#1d4ed8" strokeWidth={2.5} dot={false} />
              {hasScenarios && <Line type="monotone" dataKey="Upside"   stroke="#059669" strokeWidth={1.5} strokeDasharray="5 3" dot={false} />}
              {hasScenarios && <Line type="monotone" dataKey="Base"     stroke="#d97706" strokeWidth={1.5} strokeDasharray="5 3" dot={false} />}
              {hasScenarios && <Line type="monotone" dataKey="Downside" stroke="#dc2626" strokeWidth={1.5} strokeDasharray="5 3" dot={false} />}
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Detail table */}
      {rows.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <p className="section-title mb-0">Forecast Detail</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  {['Period', 'Horizon', 'Model', 'Forecast', 'P10', 'P90', 'Base', 'Upside', 'Downside'].map(h => (
                    <th key={h} className="table-th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((f, i) => (
                  <tr key={i} className={`hover:bg-slate-50 transition-colors ${i % 2 === 0 ? '' : 'bg-slate-50/40'}`}>
                    <td className="table-td font-medium text-slate-900">{f.period_date.slice(0, 7)}</td>
                    <td className="table-td">{f.horizon_months}mo</td>
                    <td className="table-td text-slate-400">{f.model_type}</td>
                    <td className="table-td font-medium">{f.point_forecast.toFixed(4)}</td>
                    <td className="table-td text-slate-500">{f.p10?.toFixed(4) ?? '—'}</td>
                    <td className="table-td text-slate-500">{f.p90?.toFixed(4) ?? '—'}</td>
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
