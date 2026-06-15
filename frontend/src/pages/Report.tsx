import { useState } from 'react'
import { downloadReport } from '../api/client'

const SECTIONS = [
  {
    title: 'Executive Brief',
    description: 'One-page client-ready summary covering the composite health score, key indicator readings, and top economic risks — formatted for C-suite delivery.',
    tag: 'WeasyPrint · PDF',
    color: 'primary',
  },
  {
    title: 'Full Analysis',
    description: 'Complete notebook output with VAR/VECM impulse responses, XGBoost SHAP charts, Monte Carlo scenario distributions, and 12-month forecasts.',
    tag: 'nbconvert · PDF',
    color: 'slate',
  },
]

export default function Report() {
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState<string | null>(null)
  const [done, setDone]     = useState(false)

  const handleDownload = async () => {
    setLoading(true)
    setError(null)
    setDone(false)
    try {
      const blob = await downloadReport()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = 'econsight-report.pdf'
      a.click()
      URL.revokeObjectURL(url)
      setDone(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Report generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <p className="section-label">Deliverable</p>
        <h1 className="text-2xl font-semibold text-slate-900">Economic Report</h1>
        <p className="text-sm text-[var(--text-secondary)] mt-0.5">
          Generate a combined PDF — executive brief merged with full econometric analysis.
        </p>
      </div>

      {/* Report sections */}
      <div className="space-y-3">
        {SECTIONS.map(s => (
          <div key={s.title} className="ed-card p-5 flex items-start gap-4">
            <div className={`mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
              s.color === 'primary' ? 'bg-[var(--primary)]/10' : 'bg-[var(--surface-2)]'
            }`}>
              <span className={`text-xs font-bold ${s.color === 'primary' ? 'text-[var(--primary)]' : 'text-[var(--text-muted)]'}`}>
                {s.color === 'primary' ? 'EX' : 'AN'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-[14px] font-semibold text-[var(--text-primary)]">{s.title}</p>
                <span className="text-[11px] text-[var(--text-muted)] bg-[var(--surface-2)] border border-[var(--border)] rounded px-2 py-0.5">{s.tag}</span>
              </div>
              <p className="text-[13px] text-[var(--text-secondary)] leading-relaxed">{s.description}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Download button */}
      <div className="ed-card p-8 max-w-lg mx-auto">
        <p className="text-[13px] text-[var(--text-secondary)] mb-4">
          Both sections are merged into a single PDF. Generation takes 15–30 seconds.
        </p>
        <button
          onClick={handleDownload}
          disabled={loading}
          className="inline-flex items-center gap-2 bg-[var(--primary)] text-white font-semibold px-6 py-3 rounded-[6px] hover:bg-[var(--primary-dark)] transition-colors disabled:opacity-50"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Generating report…
            </>
          ) : (
            <>
              <span>↓</span>
              Download PDF Report
            </>
          )}
        </button>

        {done && (
          <p className="text-[13px] text-emerald-600 font-medium mt-3">Report downloaded successfully.</p>
        )}
        {error && (
          <p className="text-[13px] text-red-500 mt-3">
            {error} — WeasyPrint or nbconvert may not be installed on this system.
          </p>
        )}
      </div>
    </div>
  )
}
