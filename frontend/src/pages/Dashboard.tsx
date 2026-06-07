import { useQuery } from '@tanstack/react-query'
import { fetchHealthScore, fetchIndicators } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Skeleton } from '../components/ui/skeleton'
import { RadialBarChart, RadialBar, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'

function ScoreGauge({ score }: { score: number }) {
  const pct = Math.round((score / 10) * 100)
  const color = score >= 7 ? '#16a34a' : score >= 5 ? '#ca8a04' : '#dc2626'
  return (
    <div className="flex flex-col items-center gap-1">
      <ResponsiveContainer width={180} height={180}>
        <RadialBarChart innerRadius="60%" outerRadius="90%" startAngle={180} endAngle={0} data={[{ value: pct, fill: color }]}>
          <RadialBar dataKey="value" cornerRadius={6} background={{ fill: '#e5e7eb' }} />
        </RadialBarChart>
      </ResponsiveContainer>
      <span className="text-4xl font-bold" style={{ color }}>{score.toFixed(2)}</span>
      <span className="text-sm text-gray-500">/ 10.0 economic health</span>
    </div>
  )
}

const INDICATOR_LABELS: Record<string, string> = {
  gdp: 'GDP',
  cpi: 'CPI',
  unemployment_rate: 'Unemployment %',
  overnight_rate: 'Overnight Rate %',
  cadusd: 'CAD/USD',
  bond_10yr: '10-yr Bond Yield %',
  cpi_yoy: 'CPI YoY %',
  yield_spread: 'Yield Spread',
}

export default function Dashboard() {
  const healthQ = useQuery({ queryKey: ['health-score'], queryFn: fetchHealthScore })
  const indicatorsQ = useQuery({ queryKey: ['indicators'], queryFn: fetchIndicators })

  const latest = indicatorsQ.data?.[indicatorsQ.data.length - 1]
  const historyData = healthQ.data?.history.slice(-12).map(h => ({
    date: h.period_date.slice(0, 7),
    score: +h.score.toFixed(2),
  }))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Economic Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Health Score */}
        <Card className="md:col-span-1">
          <CardHeader><CardTitle className="text-base">Economic Health Score</CardTitle></CardHeader>
          <CardContent>
            {healthQ.isLoading ? <Skeleton className="h-48 w-full" /> : healthQ.data ? (
              <ScoreGauge score={healthQ.data.latest_score} />
            ) : <p className="text-red-500 text-sm">Failed to load</p>}
          </CardContent>
        </Card>

        {/* Score history sparkline */}
        <Card className="md:col-span-2">
          <CardHeader><CardTitle className="text-base">Health Score — Last 12 Months</CardTitle></CardHeader>
          <CardContent>
            {healthQ.isLoading ? <Skeleton className="h-48 w-full" /> : historyData && (
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={historyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={2} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" stroke="#2563eb" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Latest indicator snapshot */}
      <Card>
        <CardHeader><CardTitle className="text-base">Latest Indicators — {latest?.period_date?.slice(0, 7) ?? '…'}</CardTitle></CardHeader>
        <CardContent>
          {indicatorsQ.isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-16" />)}
            </div>
          ) : latest ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(INDICATOR_LABELS).map(([key, label]) => {
                const val = latest[key as keyof typeof latest]
                return (
                  <div key={key} className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-500 mb-1">{label}</p>
                    <p className="text-lg font-semibold text-gray-800">{val != null ? (+val).toFixed(2) : '—'}</p>
                  </div>
                )
              })}
            </div>
          ) : <p className="text-red-500 text-sm">Failed to load indicators</p>}
        </CardContent>
      </Card>
    </div>
  )
}
