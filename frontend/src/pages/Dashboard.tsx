import { useQuery } from '@tanstack/react-query'
import { fetchHealthScore, fetchIndicators } from '../api/client'
import { Skeleton } from '../components/ui/skeleton'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer,
} from 'recharts'

const INDICATORS = [
  { key: 'cpi_yoy',          label: 'CPI Inflation YoY', unit: '%' },
  { key: 'unemployment_rate', label: 'Unemployment Rate', unit: '%' },
  { key: 'overnight_rate',    label: 'Overnight Rate',    unit: '%' },
  { key: 'cadusd',            label: 'CAD / USD',         unit: '' },
  { key: 'bond_10yr',         label: '10-yr Bond Yield',  unit: '%' },
  { key: 'yield_spread',      label: 'Yield Spread',      unit: 'pp' },
  { key: 'cpi',               label: 'CPI Index',         unit: '' },
  { key: 'm2pp',              label: 'M2++ Money Supply',  unit: '$M' },
]

function scoreColor(s: number) {
  if (s >= 7) return { text: 'text-emerald-600', ring: '#059669', label: 'Strong' }
  if (s >= 5) return { text: 'text-amber-600',   ring: '#d97706', label: 'Moderate' }
  return       { text: 'text-red-600',            ring: '#dc2626', label: 'Weak' }
}

function ScoreGauge({ score }: { score: number }) {
  const { text, ring, label } = scoreColor(score)
  const pct = score / 10
  const r = 52
  const circ = 2 * Math.PI * r
  const dash = circ * pct
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-2">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
        <circle
          cx="70" cy="70" r={r} fill="none"
          stroke={ring} strokeWidth="10"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
        <text x="70" y="66" textAnchor="middle" fontSize="26" fontWeight="700" fontFamily="Inter" fill="#0f172a">
          {score.toFixed(1)}
        </text>
        <text x="70" y="84" textAnchor="middle" fontSize="11" fontFamily="Inter" fill="#94a3b8">
          out of 10
        </text>
      </svg>
      <span className={`text-sm font-semibold ${text}`}>{label} Economic Conditions</span>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg px-3 py-2">
      <p className="text-[11px] text-slate-400 mb-0.5">{label}</p>
      <p className="text-[13px] font-semibold text-blue-700">{payload[0].value}</p>
    </div>
  )
}

export default function Dashboard() {
  const healthQ = useQuery({ queryKey: ['health-score'], queryFn: fetchHealthScore })
  const indicatorsQ = useQuery({ queryKey: ['indicators'], queryFn: fetchIndicators })

  const latest = indicatorsQ.data?.at(-1)
  const prev   = indicatorsQ.data?.at(-2)
  const historyData = healthQ.data?.history.slice(-18).map(h => ({
    date: h.period_date.slice(0, 7),
    score: +h.score.toFixed(2),
  }))

  function delta(key: string) {
    const a = latest?.[key as keyof typeof latest] as number | null
    const b = prev?.[key as keyof typeof prev] as number | null
    if (a == null || b == null) return null
    return a - b
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <p className="section-title">Overview</p>
        <h1 className="text-2xl font-semibold text-slate-900">Economic Dashboard</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Canadian macroeconomic conditions · {latest?.period_date?.slice(0, 7) ?? '—'}
        </p>
      </div>

      {/* Top row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Health score */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex flex-col">
          <p className="section-title">Composite Health Score</p>
          {healthQ.isLoading
            ? <Skeleton className="h-44 w-full" />
            : healthQ.data
              ? <ScoreGauge score={healthQ.data.latest_score} />
              : <p className="text-red-500 text-sm">Failed to load</p>
          }
        </div>

        {/* Trend chart */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 lg:col-span-2">
          <p className="section-title">Health Score Trend</p>
          <p className="text-sm font-medium text-slate-700 mb-4">Last 18 months</p>
          {healthQ.isLoading
            ? <Skeleton className="h-44 w-full" />
            : historyData && (
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={historyData} margin={{ top: 0, right: 4, bottom: 0, left: -16 }}>
                  <CartesianGrid vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} interval={3} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="score" stroke="#1d4ed8" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )
          }
        </div>
      </div>

      {/* Indicator grid */}
      <div>
        <p className="section-title">Key Indicators — Latest Period</p>
        {indicatorsQ.isLoading
          ? <div className="grid grid-cols-2 md:grid-cols-4 gap-3">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}</div>
          : latest ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {INDICATORS.map(({ key, label, unit }) => {
                const val = latest[key as keyof typeof latest] as number | null
                const d   = delta(key)
                const up  = d != null && d > 0
                const down = d != null && d < 0
                return (
                  <div key={key} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
                    <p className="stat-label">{label}</p>
                    <p className="stat-value">{val != null ? `${(+val).toFixed(2)}${unit}` : '—'}</p>
                    {d != null && (
                      <p className={`text-[11px] mt-1 font-medium ${up ? 'text-emerald-600' : down ? 'text-red-500' : 'text-slate-400'}`}>
                        {up ? '▲' : down ? '▼' : '–'} {Math.abs(d).toFixed(2)}{unit} MoM
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          ) : <p className="text-red-500 text-sm">Failed to load indicators</p>
        }
      </div>
    </div>
  )
}
