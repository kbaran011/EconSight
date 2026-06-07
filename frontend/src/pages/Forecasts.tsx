import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchForecasts } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Skeleton } from '../components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { ComposedChart, Line, Area, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend } from 'recharts'

export default function Forecasts() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['forecasts'], queryFn: fetchForecasts })

  const targets = [...new Set(data?.map(f => f.target) ?? [])]
  const [target, setTarget] = useState<string>('')
  const activeTarget = target || targets[0] || ''

  const rows = data?.filter(f => f.target === activeTarget) ?? []

  const chartData = rows.map(f => ({
    date: f.period_date.slice(0, 7),
    forecast: +(f.point_forecast).toFixed(4),
    p10: f.p10 != null ? +f.p10.toFixed(4) : null,
    p90: f.p90 != null ? +f.p90.toFixed(4) : null,
    base: f.scenario_base != null ? +f.scenario_base.toFixed(4) : null,
    upside: f.scenario_upside != null ? +f.scenario_upside.toFixed(4) : null,
    downside: f.scenario_downside != null ? +f.scenario_downside.toFixed(4) : null,
  }))

  const hasInterval = chartData.some(d => d.p10 != null && d.p90 != null)
  const hasScenarios = chartData.some(d => d.base != null)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Forecasts</h1>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">
            {activeTarget ? `${activeTarget} — 12-month horizon` : 'Forecasts'}
          </CardTitle>
          {targets.length > 0 && (
            <Select value={activeTarget} onValueChange={setTarget}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {targets.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
              </SelectContent>
            </Select>
          )}
        </CardHeader>
        <CardContent>
          {isLoading ? <Skeleton className="h-72 w-full" /> : isError ? (
            <p className="text-red-500 text-sm">Failed to load forecasts</p>
          ) : chartData.length === 0 ? (
            <p className="text-gray-500 text-sm">No forecast data available.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                {hasInterval && (
                  <Area type="monotone" dataKey="p90" fill="#bfdbfe" stroke="none" name="P90" />
                )}
                {hasInterval && (
                  <Area type="monotone" dataKey="p10" fill="#fff" stroke="none" name="P10" />
                )}
                <Line type="monotone" dataKey="forecast" stroke="#2563eb" strokeWidth={2} dot={false} name="Forecast" />
                {hasScenarios && <Line type="monotone" dataKey="upside" stroke="#16a34a" strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="Upside" />}
                {hasScenarios && <Line type="monotone" dataKey="base" stroke="#ca8a04" strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="Base" />}
                {hasScenarios && <Line type="monotone" dataKey="downside" stroke="#dc2626" strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="Downside" />}
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {rows.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Forecast Detail</CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b text-gray-500">
                  <th className="py-2 pr-4">Period</th>
                  <th className="py-2 pr-4">Horizon (mo)</th>
                  <th className="py-2 pr-4">Model</th>
                  <th className="py-2 pr-4">Forecast</th>
                  <th className="py-2 pr-4">P10</th>
                  <th className="py-2 pr-4">P90</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((f, i) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="py-1.5 pr-4 font-medium">{f.period_date.slice(0, 7)}</td>
                    <td className="py-1.5 pr-4">{f.horizon_months}</td>
                    <td className="py-1.5 pr-4 text-gray-500">{f.model_type}</td>
                    <td className="py-1.5 pr-4">{f.point_forecast.toFixed(4)}</td>
                    <td className="py-1.5 pr-4">{f.p10?.toFixed(4) ?? '—'}</td>
                    <td className="py-1.5 pr-4">{f.p90?.toFixed(4) ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
