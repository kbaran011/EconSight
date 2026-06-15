import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchIndicators } from '../api/client'
import type { IndicatorRow } from '../api/client'
import { Skeleton } from '../components/ui/skeleton'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, ReferenceLine,
} from 'recharts'

const SERIES: { key: keyof IndicatorRow; label: string; unit: string; color: string }[] = [
  { key: 'gdp',               label: 'GDP',                unit: '$M', color: '#0f766e' },
  { key: 'cpi_yoy',           label: 'CPI Inflation YoY', unit: '%',  color: '#1d4ed8' },
  { key: 'cpi',               label: 'CPI Index',          unit: '',   color: '#7c3aed' },
  { key: 'unemployment_rate', label: 'Unemployment Rate',  unit: '%',  color: '#0891b2' },
  { key: 'ippi',              label: 'IPPI',               unit: '',   color: '#b45309' },
  { key: 'retail_trade',      label: 'Retail Trade',       unit: '$M', color: '#be185d' },
  { key: 'overnight_rate',    label: 'Overnight Rate',     unit: '%',  color: '#d97706' },
  { key: 'cadusd',            label: 'CAD / USD',          unit: '',   color: '#059669' },
  { key: 'bond_10yr',         label: '10-yr Bond Yield',   unit: '%',  color: '#dc2626' },
  { key: 'yield_spread',      label: 'Yield Spread',       unit: 'pp', color: '#9333ea' },
  { key: 'm2pp',              label: 'M2++ Money Supply',  unit: '$M', color: '#0284c7' },
]

const CustomTooltip = ({ active, payload, label, unit }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg px-3 py-2.5 text-left">
      <p className="text-[11px] text-slate-400 mb-1">{label}</p>
      <p className="text-[14px] font-semibold text-slate-800">{payload[0].value}{unit}</p>
    </div>
  )
}

export default function Indicators() {
  const [selectedKey, setSelectedKey] = useState<keyof IndicatorRow>('cpi_yoy')
  const { data, isLoading, isError } = useQuery({ queryKey: ['indicators'], queryFn: fetchIndicators })

  const series = SERIES.find(s => s.key === selectedKey)!
  const chartData = data?.map(row => ({
    date: row.period_date.slice(0, 7),
    value: row[selectedKey] != null ? +(row[selectedKey] as number).toFixed(4) : null,
  })).filter(d => d.value != null)

  const latest = data?.at(-1)
  const prev   = data?.at(-2)
  const latestVal = latest?.[selectedKey] as number | null
  const prevVal   = prev?.[selectedKey] as number | null
  const change    = latestVal != null && prevVal != null ? latestVal - prevVal : null

  return (
    <div className="space-y-6">
      <div>
        <p className="section-label">Data Explorer</p>
        <h1 className="text-2xl font-semibold text-slate-900">Economic Indicators</h1>
        <p className="text-sm text-slate-500 mt-0.5">Monthly macroeconomic series — Statistics Canada & Bank of Canada</p>
      </div>

      {/* Series selector */}
      <div className="flex flex-wrap gap-2">
        {SERIES.map(s => (
          <button
            key={s.key}
            onClick={() => setSelectedKey(s.key)}
            className={`text-[12px] font-medium px-3 py-1.5 rounded-full border transition-colors ${
              selectedKey === s.key
                ? 'bg-blue-700 text-white border-blue-700'
                : 'bg-white text-slate-600 border-slate-200 hover:border-blue-300 hover:text-blue-700'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Chart card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-start justify-between mb-5">
          <div>
            <p className="section-label">{series.label}</p>
            {latestVal != null && (
              <p className="text-3xl font-semibold text-slate-900">
                {latestVal.toFixed(2)}{series.unit}
              </p>
            )}
            {change != null && (
              <p className={`text-[12px] font-medium mt-0.5 ${change > 0 ? 'text-emerald-600' : change < 0 ? 'text-red-500' : 'text-slate-400'}`}>
                {change > 0 ? '▲' : change < 0 ? '▼' : '–'} {Math.abs(change).toFixed(2)}{series.unit} month-over-month
              </p>
            )}
          </div>
          <span className="text-[11px] font-medium text-slate-400 bg-slate-50 border border-slate-200 rounded px-2 py-1">
            {data?.length ?? 0} periods
          </span>
        </div>

        {isLoading ? <Skeleton className="h-56 w-full" /> : isError ? (
          <p className="text-red-500 text-sm">Failed to load data</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -16 }}>
              <CartesianGrid vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} interval={5} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              {selectedKey === 'yield_spread' && <ReferenceLine y={0} stroke="#e2e8f0" strokeDasharray="4 2" />}
              <Tooltip content={<CustomTooltip unit={series.unit} />} />
              <Line type="monotone" dataKey="value" stroke={series.color} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Data table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <p className="section-label mb-0">Historical Data</p>
        </div>
        {isLoading ? <div className="p-6"><Skeleton className="h-40 w-full" /></div> : data && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="table-th">Period</th>
                  {SERIES.map(s => <th key={s.key} className="table-th whitespace-nowrap">{s.label}</th>)}
                </tr>
              </thead>
              <tbody>
                {[...data].reverse().slice(0, 24).map((row, i) => (
                  <tr key={row.period_date} className={`hover:bg-slate-50 transition-colors ${i % 2 === 0 ? '' : 'bg-slate-50/40'}`}>
                    <td className="table-td font-medium text-slate-900">{row.period_date.slice(0, 7)}</td>
                    {SERIES.map(s => (
                      <td key={s.key} className="table-td">
                        {row[s.key] != null ? `${(+(row[s.key] as number)).toFixed(2)}${s.unit}` : <span className="text-slate-300">—</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
