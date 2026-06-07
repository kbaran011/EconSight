import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchIndicators } from '../api/client'
import type { IndicatorRow } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Skeleton } from '../components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts'

const SERIES: { key: keyof IndicatorRow; label: string; color: string }[] = [
  { key: 'cpi', label: 'CPI', color: '#2563eb' },
  { key: 'cpi_yoy', label: 'CPI YoY %', color: '#dc2626' },
  { key: 'unemployment_rate', label: 'Unemployment %', color: '#16a34a' },
  { key: 'overnight_rate', label: 'Overnight Rate %', color: '#9333ea' },
  { key: 'cadusd', label: 'CAD/USD', color: '#ea580c' },
  { key: 'bond_10yr', label: '10-yr Bond %', color: '#0891b2' },
  { key: 'yield_spread', label: 'Yield Spread', color: '#65a30d' },
  { key: 'm2pp', label: 'M2++ ($M)', color: '#b45309' },
]

export default function Indicators() {
  const [selected, setSelected] = useState<keyof IndicatorRow>('cpi_yoy')
  const { data, isLoading, isError } = useQuery({ queryKey: ['indicators'], queryFn: fetchIndicators })

  const series = SERIES.find(s => s.key === selected)
  const chartData = data?.map(row => ({
    date: row.period_date.slice(0, 7),
    value: row[selected] != null ? +(row[selected] as number).toFixed(4) : null,
  })).filter(d => d.value != null)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Economic Indicators</h1>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">{series?.label ?? selected}</CardTitle>
          <Select value={String(selected)} onValueChange={v => setSelected(v as keyof IndicatorRow)}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SERIES.map(s => <SelectItem key={s.key} value={s.key}>{s.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent>
          {isLoading ? <Skeleton className="h-64 w-full" /> : isError ? (
            <p className="text-red-500 text-sm">Failed to load indicators</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={5} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke={series?.color ?? '#2563eb'} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Data table */}
      <Card>
        <CardHeader><CardTitle className="text-base">Raw Data</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          {isLoading ? <Skeleton className="h-40 w-full" /> : data && (
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b text-gray-500">
                  <th className="py-2 pr-4">Period</th>
                  {SERIES.slice(0, 6).map(s => <th key={s.key} className="py-2 pr-4">{s.label}</th>)}
                </tr>
              </thead>
              <tbody>
                {[...data].reverse().slice(0, 24).map(row => (
                  <tr key={row.period_date} className="border-b hover:bg-gray-50">
                    <td className="py-1.5 pr-4 font-medium">{row.period_date.slice(0, 7)}</td>
                    {SERIES.slice(0, 6).map(s => (
                      <td key={s.key} className="py-1.5 pr-4 text-gray-700">
                        {row[s.key] != null ? (+(row[s.key] as number)).toFixed(2) : '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
