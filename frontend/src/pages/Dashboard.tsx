import { useQuery } from '@tanstack/react-query'
import { fetchHealthScore, fetchIndicators } from '../api/client'
import type { IndicatorRow } from '../api/client'
import { Skeleton } from '../components/ui/skeleton'
import {
  LineChart, Line, Bar, BarChart, Cell,
  XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer,
} from 'recharts'

const INDICATORS: {
  key: keyof IndicatorRow
  label: string
  unit: string
  invert?: boolean   // true = lower is better (e.g. unemployment)
}[] = [
  { key: 'gdp',               label: 'GDP',                unit: '$M'                },
  { key: 'cpi_yoy',           label: 'CPI Inflation YoY',  unit: '%',  invert: true  },
  { key: 'cpi',               label: 'CPI Index',          unit: ''                  },
  { key: 'unemployment_rate', label: 'Unemployment Rate',  unit: '%',  invert: true  },
  { key: 'ippi',              label: 'IPPI',               unit: ''                  },
  { key: 'retail_trade',      label: 'Retail Trade',       unit: '$M'                },
  { key: 'overnight_rate',    label: 'Overnight Rate',     unit: '%'                 },
  { key: 'cadusd',            label: 'CAD / USD',          unit: ''                  },
  { key: 'bond_10yr',         label: '10-yr Bond Yield',   unit: '%'                 },
  { key: 'yield_spread',      label: 'Yield Spread',       unit: 'pp'                },
  { key: 'm2pp',              label: 'M2++ Money Supply',  unit: '$M'                },
]

function scoreColor(s: number) {
  if (s >= 7) return { ring: '#1a7a55', label: 'Strong' }
  if (s >= 5) return { ring: '#d97706', label: 'Moderate' }
  return       { ring: '#c9483a',        label: 'Weak' }
}

function ringBg(ring: string): string {
  if (ring === '#1a7a55') return 'rgba(26,122,85,0.10)'
  if (ring === '#d97706') return 'rgba(217,119,6,0.10)'
  return 'rgba(201,72,58,0.10)'
}

function ScoreGauge({ score }: { score: number }) {
  const { ring, label } = scoreColor(score)
  const bg = ringBg(ring)
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
          <text x="74" y="70" textAnchor="middle" fontSize="27" fontWeight="700" fontFamily="Source Serif 4, serif" fill="var(--primary)">
            {score.toFixed(1)}
          </text>
          <text x="74" y="88" textAnchor="middle" fontSize="11" fontFamily="Source Serif 4, serif" fill="var(--text-xmuted)">
            out of 10
          </text>
        </svg>
      </div>
      <div className="text-center">
        <span className="inline-flex items-center gap-1.5 text-[12px] font-semibold px-3 py-1 rounded-full"
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

interface TooltipProps { active?: boolean; payload?: { value: number }[]; label?: string }
const ChartTooltip = ({ active, payload, label }: TooltipProps) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white rounded-lg border border-[var(--border)] shadow-sm px-3 py-2">
      <p className="text-[11px] text-[var(--text-muted)] mb-0.5">{label}</p>
      <p className="text-[14px] font-serif font-bold text-[var(--primary)]">{payload[0].value}</p>
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

  const chartData = historyData ?? []

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
          <span className="page-eyebrow">Overview</span>
          <h1 className="font-serif font-bold text-[28px] tracking-tight text-[var(--text-primary)]">Economic Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">Canadian macroeconomic conditions</p>
        </div>
        {latest && (
          <span className="text-[12px] text-slate-400 bg-white border border-slate-200 rounded-lg px-3 py-1.5 shadow-sm">
            Data as of <span className="font-medium text-slate-600">{latest.period_date.slice(0, 7)}</span>
          </span>
        )}
      </div>

      {/* Top row: gauge + bar chart trend */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="ed-card p-6" style={{ animation: 'fadeSlideUp 0.4s ease-out both' }}>
          <p className="section-label">Composite Health Score</p>
          {healthQ.isLoading
            ? <Skeleton className="h-48 w-full rounded-xl" />
            : healthQ.data
              ? <ScoreGauge score={healthQ.data.latest_score} />
              : <p className="text-red-500 text-sm">Failed to load</p>}
        </div>

        <div className="ed-card p-6 lg:col-span-2" style={{ animation: 'fadeSlideUp 0.4s ease-out both', animationDelay: '80ms' }}>
          <p className="section-label">Health Score Trend</p>
          <p className="text-sm font-medium text-slate-700 mb-4">Last 18 months</p>
          {healthQ.isLoading
            ? <Skeleton className="h-44 w-full rounded-xl" />
            : chartData.length > 0 && (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={chartData} margin={{ top: 0, right: 4, bottom: 0, left: -16 }}>
                  <CartesianGrid vertical={false} stroke="var(--surface-2)" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--text-xmuted)', fontFamily: 'DM Mono, monospace' }} interval={3} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 10, fill: 'var(--text-xmuted)', fontFamily: 'DM Mono, monospace' }} axisLine={false} tickLine={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="score" fill="#1a7a55">
                    {chartData.map((_, i) => (
                      <Cell key={i} fill="#1a7a55" fillOpacity={i === chartData.length - 1 ? 1 : 0.25} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
        </div>
      </div>

      {/* Indicator cards with sparklines */}
      <div>
        <p className="section-label">Key Indicators — Latest Period</p>
        {indicatorsQ.isLoading
          ? <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
            </div>
          : latest
            ? <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {INDICATORS.map(({ key, label, unit, invert }, index) => {
                  const val  = latest[key] as number | null
                  const d    = delta(key)
                  const up   = d != null && d > 0
                  const down = d != null && d < 0
                  // For inverted indicators (lower = better), colour logic flips
                  const good = invert ? down : up
                  const bad  = invert ? up   : down
                  const spark = sparklineData(key)
                  const sparkColor = good ? '#1a7a55' : bad ? '#c9483a' : '#94a3b8'

                  const deltaClass = up && good
                    ? 'delta delta-up-good'
                    : up && bad
                    ? 'delta delta-up-bad'
                    : down && good
                    ? 'delta delta-dn-good'
                    : down && bad
                    ? 'delta delta-dn-bad'
                    : 'delta delta-neutral'

                  return (
                    <div
                      key={key}
                      className="ed-card p-4 flex flex-col gap-2 transition-all duration-150 hover:-translate-y-px hover:shadow-[0_4px_16px_rgba(26,122,85,0.08)]"
                      style={{
                        borderTop: `3px solid ${invert ? 'var(--accent)' : 'var(--primary)'}`,
                        animation: 'fadeSlideUp 0.4s ease-out both',
                        animationDelay: `${index * 60}ms`,
                      }}
                    >
                      <p className="stat-label">{label}</p>
                      <div className="flex items-end justify-between gap-2">
                        <div>
                          <p className="stat-value">
                            {val != null ? `${(+val).toFixed(2)}` : '—'}<span className="text-[14px] font-normal text-[var(--text-muted)]">{unit}</span>
                          </p>
                          {d != null && (
                            <p className={deltaClass}>
                              {up ? '▲' : down ? '▼' : '–'} {Math.abs(d).toFixed(2)}{unit}
                            </p>
                          )}
                        </div>
                      </div>
                      {spark.length > 2 && (
                        <div
                          className="h-7 rounded bg-[var(--surface-2)] mt-1 overflow-hidden"
                          style={{ animation: 'fadeSlideUp 0.3s ease-out both', animationDelay: '0.2s' }}
                        >
                          <MiniSparkline data={spark} color={sparkColor} />
                        </div>
                      )}
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
