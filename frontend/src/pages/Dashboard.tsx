import { useQuery } from '@tanstack/react-query'
import { fetchHealthScore, fetchIndicators } from '../api/client'
import type { IndicatorRow } from '../api/client'
import { Skeleton } from '../components/ui/skeleton'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'

const INDICATORS: {
  key: keyof IndicatorRow
  label: string
  unit: string
  invert?: boolean   // true = lower is better (e.g. unemployment)
}[] = [
  { key: 'cpi_yoy',           label: 'CPI Inflation YoY',  unit: '%',  invert: true  },
  { key: 'unemployment_rate', label: 'Unemployment Rate',  unit: '%',  invert: true  },
  { key: 'overnight_rate',    label: 'Overnight Rate',     unit: '%'                 },
  { key: 'cadusd',            label: 'CAD / USD',          unit: ''                  },
  { key: 'bond_10yr',         label: '10-yr Bond Yield',   unit: '%'                 },
  { key: 'yield_spread',      label: 'Yield Spread',       unit: 'pp'                },
  { key: 'cpi',               label: 'CPI Index',          unit: ''                  },
  { key: 'm2pp',              label: 'M2++ Money Supply',  unit: '$M'                },
]

function scoreColor(s: number) {
  if (s >= 7) return { text: 'text-emerald-600', ring: '#059669', bg: '#ecfdf5', label: 'Strong' }
  if (s >= 5) return { text: 'text-amber-600',   ring: '#d97706', bg: '#fffbeb', label: 'Moderate' }
  return       { text: 'text-red-600',            ring: '#dc2626', bg: '#fef2f2', label: 'Weak' }
}

function ScoreGauge({ score }: { score: number }) {
  const { text, ring, bg, label } = scoreColor(score)
  const r = 52
  const circ = 2 * Math.PI * r
  const dash = circ * (score / 10)
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-2">
      <div className="relative">
        <svg width="148" height="148" viewBox="0 0 148 148">
          <circle cx="74" cy="74" r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
          <circle
            cx="74" cy="74" r={r} fill="none"
            stroke={ring} strokeWidth="10"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            transform="rotate(-90 74 74)"
            style={{ transition: 'stroke-dasharray 1s ease' }}
          />
          <text x="74" y="70" textAnchor="middle" fontSize="27" fontWeight="700" fontFamily="Inter, sans-serif" fill="#0f172a">
            {score.toFixed(1)}
          </text>
          <text x="74" y="88" textAnchor="middle" fontSize="11" fontFamily="Inter, sans-serif" fill="#94a3b8">
            out of 10
          </text>
        </svg>
      </div>
      <div className="text-center">
        <span className={`inline-flex items-center gap-1.5 text-[12px] font-semibold px-3 py-1 rounded-full`}
          style={{ color: ring, backgroundColor: bg }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: ring }} />
          {label} Conditions
        </span>
      </div>
    </div>
  )
}

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  const points = data.map((v, i) => ({ i, v }))
  return (
    <ResponsiveContainer width="100%" height={36}>
      <LineChart data={points} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg px-3 py-2">
      <p className="text-[11px] text-slate-400 mb-0.5">{label}</p>
      <p className="text-[14px] font-semibold text-blue-700">{payload[0].value}</p>
    </div>
  )
}

export default function Dashboard() {
  const healthQ     = useQuery({ queryKey: ['health-score'], queryFn: fetchHealthScore })
  const indicatorsQ = useQuery({ queryKey: ['indicators'],   queryFn: fetchIndicators  })

  const allRows = indicatorsQ.data ?? []
  const latest  = allRows.at(-1)
  const prev    = allRows.at(-2)

  const historyData = healthQ.data?.history.slice(-18).map(h => ({
    date: h.period_date.slice(0, 7),
    score: +h.score.toFixed(2),
  }))

  function delta(key: keyof IndicatorRow) {
    const a = latest?.[key] as number | null
    const b = prev?.[key]   as number | null
    if (a == null || b == null) return null
    return a - b
  }

  function sparklineData(key: keyof IndicatorRow) {
    return allRows.slice(-12).map(r => r[key] as number).filter(v => v != null)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <p className="section-title">Overview</p>
          <h1 className="text-2xl font-semibold text-slate-900">Economic Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">Canadian macroeconomic conditions</p>
        </div>
        {latest && (
          <span className="text-[12px] text-slate-400 bg-white border border-slate-200 rounded-lg px-3 py-1.5 shadow-sm">
            Data as of <span className="font-medium text-slate-600">{latest.period_date.slice(0, 7)}</span>
          </span>
        )}
      </div>

      {/* Top row: gauge + sparkline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <p className="section-title">Composite Health Score</p>
          {healthQ.isLoading
            ? <Skeleton className="h-48 w-full rounded-xl" />
            : healthQ.data
              ? <ScoreGauge score={healthQ.data.latest_score} />
              : <p className="text-red-500 text-sm">Failed to load</p>}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 lg:col-span-2">
          <p className="section-title">Health Score Trend</p>
          <p className="text-sm font-medium text-slate-700 mb-4">Last 18 months</p>
          {healthQ.isLoading
            ? <Skeleton className="h-44 w-full rounded-xl" />
            : historyData && (
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={historyData} margin={{ top: 0, right: 4, bottom: 0, left: -16 }}>
                  <CartesianGrid vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} interval={3} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <ReferenceLine y={5} stroke="#e2e8f0" strokeDasharray="4 2" />
                  <Tooltip content={<ChartTooltip />} />
                  <Line type="monotone" dataKey="score" stroke="#1d4ed8" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
        </div>
      </div>

      {/* Indicator cards with sparklines */}
      <div>
        <p className="section-title">Key Indicators — Latest Period</p>
        {indicatorsQ.isLoading
          ? <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
            </div>
          : latest
            ? <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {INDICATORS.map(({ key, label, unit, invert }) => {
                  const val  = latest[key] as number | null
                  const d    = delta(key)
                  const up   = d != null && d > 0
                  const down = d != null && d < 0
                  // For inverted indicators (lower = better), colour logic flips
                  const good = invert ? down : up
                  const bad  = invert ? up   : down
                  const spark = sparklineData(key)
                  const sparkColor = good ? '#059669' : bad ? '#dc2626' : '#94a3b8'

                  return (
                    <div key={key} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-col gap-2">
                      <p className="stat-label">{label}</p>
                      <div className="flex items-end justify-between gap-2">
                        <div>
                          <p className="stat-value">
                            {val != null ? `${(+val).toFixed(2)}${unit}` : '—'}
                          </p>
                          {d != null && (
                            <p className={`text-[11px] font-medium mt-0.5 ${good ? 'text-emerald-600' : bad ? 'text-red-500' : 'text-slate-400'}`}>
                              {up ? '▲' : down ? '▼' : '–'} {Math.abs(d).toFixed(2)}{unit}
                            </p>
                          )}
                        </div>
                      </div>
                      {spark.length > 2 && <MiniSparkline data={spark} color={sparkColor} />}
                    </div>
                  )
                })}
              </div>
            : <p className="text-red-500 text-sm">Failed to load indicators</p>
        }
      </div>
    </div>
  )
}
