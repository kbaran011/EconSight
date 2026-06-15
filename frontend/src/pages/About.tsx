import { Link } from 'react-router-dom'

const STACK = [
  { category: 'Data Engineering', items: 'Python 3.12 · PostgreSQL 16 · SQL marts · httpx · tenacity · Pydantic' },
  { category: 'Econometrics',     items: 'statsmodels · XGBoost · SHAP · scikit-learn · pandas · matplotlib' },
  { category: 'Backend API',      items: 'FastAPI · uvicorn · psycopg3 · ChromaDB · sentence-transformers · WeasyPrint' },
  { category: 'AI / LLM',         items: 'Llama 3.3-70b via Groq · RAG pipeline · SQL generation · semantic retrieval' },
  { category: 'Frontend',         items: 'React · TypeScript · Tailwind CSS · shadcn/ui · Recharts · TanStack Query' },
  { category: 'DevOps',           items: 'GitHub Actions · Docker Compose · Railway · pytest · mypy · ruff' },
]

const DATA_SOURCES = [
  { name: 'Statistics Canada',        series: 'GDP, CPI, Unemployment Rate, IPPI, Retail Trade (5 series)' },
  { name: 'Bank of Canada Valet API', series: 'Overnight Rate, CAD/USD, 10-yr Bond Yield, M2++ (4 series)' },
]

const CAPABILITIES = [
  {
    title: 'Live Data Pipeline',
    desc: 'Async concurrent ingestion from StatCan & BoC APIs into a PostgreSQL medallion warehouse (Bronze → Silver → Gold). Idempotent upserts — safe to re-run at any time.',
  },
  {
    title: 'Econometric Models',
    desc: 'VAR/VECM for impulse response analysis, XGBoost for 12-month forecasts with SHAP explainability, and Monte Carlo simulation for P10/P50/P90 scenario bands.',
  },
  {
    title: 'Composite Health Score',
    desc: '10 indicators z-score normalised against their 15-year history, sign-adjusted so higher = better, then averaged into a 0–10 index updated each month.',
  },
  {
    title: 'RAG Q&A',
    desc: 'Natural language questions are routed to either live SQL queries or semantic search over the analysis notebook — powered by Llama 3.3-70b via Groq.',
  },
]

export default function About() {
  return (
    <div className="space-y-10 max-w-4xl">

      {/* Hero */}
      <div className="ed-card p-8">
        <div className="flex items-start gap-5">
          <div className="w-14 h-14 rounded-xl bg-[var(--primary)] flex items-center justify-center shadow-sm shrink-0">
            <span className="text-white text-xl font-bold tracking-tight font-serif">ES</span>
          </div>
          <div>
            <p className="section-label">About This Project</p>
            <h1 className="font-serif font-bold text-[28px] tracking-tight text-[var(--text-primary)] mb-2">EconSight</h1>
            <p className="text-[15px] text-[var(--text-secondary)] leading-relaxed max-w-2xl">
              A full-stack decision intelligence platform for Canadian macro analysis — covering data engineering,
              econometric modelling, AI-powered Q&A, and consulting-grade output delivery.
              Built to demonstrate production-grade engineering and applied economics end-to-end.
            </p>
            <div className="flex flex-wrap items-center gap-2 mt-4">
              {['McGill B.A. CS & Economics', 'Full-Stack Portfolio Project'].map(tag => (
                <span key={tag} className="text-[12px] font-medium text-[var(--text-secondary)] bg-[var(--surface-2)] border border-[var(--border)] rounded-full px-3 py-1">
                  {tag}
                </span>
              ))}
              <a
                href="https://github.com/kbaran011/EconSight"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-[12px] font-medium text-white bg-[var(--text-primary)] hover:opacity-80 rounded-full px-3 py-1 transition-opacity"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                </svg>
                View on GitHub
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Problem statement */}
      <div>
        <p className="section-label">Problem Statement</p>
        <div className="ed-card p-6 space-y-3">
          <p className="text-[15px] text-[var(--text-secondary)] leading-relaxed">
            Canadian SMEs make capital allocation, hiring, and pricing decisions without access to the macro-economic
            intelligence available to large enterprises. Publicly available data from Statistics Canada and the Bank of
            Canada is fragmented, requires technical expertise to interpret, and arrives with publication lag.
          </p>
          <p className="text-[15px] text-[var(--text-secondary)] leading-relaxed">
            EconSight aggregates, models, and surfaces this data through a consulting-grade interface — giving
            decision-makers a live composite health score, 12-month forecasts with scenario bands, and a natural
            language Q&A layer that answers questions against both live database queries and a semantic index of the full analysis.
          </p>
        </div>
      </div>

      {/* Capabilities */}
      <div>
        <p className="section-label">What It Does</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {CAPABILITIES.map(({ title, desc }, i) => (
            <div key={title} className={`ed-card p-5 border-l-[3px] ${i % 2 === 0 ? 'border-l-[var(--primary)]' : 'border-l-[var(--accent)]'}`}>
              <p className="font-serif font-semibold text-[15px] text-[var(--text-primary)] mb-2">{title}</p>
              <p className="text-[13px] text-[var(--text-secondary)] leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Architecture */}
      <div>
        <p className="section-label">Architecture</p>
        <div className="ed-card p-6">
          <div className="grid grid-cols-3 gap-0 text-center text-[12px] mb-5">
            {[
              { label: 'Bronze (raw.*)',     color: 'bg-amber-50 text-amber-700 border-amber-200' },
              { label: 'Silver (staging.*)', color: 'bg-[var(--surface-2)] text-[var(--text-secondary)] border-[var(--border)]' },
              { label: 'Gold (marts.*)',     color: 'bg-[var(--primary)]/10 text-[var(--primary)] border-[var(--primary)]/20' },
            ].map(({ label, color }, i) => (
              <div key={label} className="relative flex flex-col items-center">
                <div className={`w-full py-2.5 px-2 rounded font-medium border ${color}`}>{label}</div>
                {i < 2 && (
                  <span className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 text-[var(--text-muted)] text-base z-10">→</span>
                )}
              </div>
            ))}
          </div>
          <p className="text-[13px] text-[var(--text-secondary)] leading-relaxed">
            Raw API responses land in <code className="bg-[var(--surface-2)] rounded px-1">raw.*</code> tables via idempotent upsert,
            SQL views clean and type-cast to <code className="bg-[var(--surface-2)] rounded px-1">staging.*</code>, and materialised tables
            in <code className="bg-[var(--surface-2)] rounded px-1">marts.*</code> serve the API, forecast models, and RAG pipeline.
          </p>
        </div>
      </div>

      {/* Tech stack */}
      <div>
        <p className="section-label">Technology Stack</p>
        <div className="ed-card overflow-hidden">
          <table className="w-full">
            <tbody>
              {STACK.map((row, i) => (
                <tr key={row.category} className={`border-b border-[var(--border)] last:border-0 ${i % 2 === 0 ? '' : 'bg-[var(--surface-2)]/50'}`}>
                  <td className="py-3 px-6 text-[11px] font-bold text-[var(--text-muted)] uppercase tracking-wider w-44 whitespace-nowrap">
                    {row.category}
                  </td>
                  <td className="py-3 px-6 text-[13px] text-[var(--text-secondary)]">{row.items}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Data sources */}
      <div>
        <p className="section-label">Data Sources</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {DATA_SOURCES.map(ds => (
            <div key={ds.name} className="ed-card p-5">
              <p className="text-[14px] font-semibold text-[var(--text-primary)] mb-1">{ds.name}</p>
              <p className="text-[13px] text-[var(--text-secondary)]">{ds.series}</p>
              <p className="text-[11px] text-[var(--text-muted)] mt-2">Public API · Monthly frequency · Free</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="bg-[var(--primary)] rounded-xl p-6 flex items-center justify-between gap-4">
        <div>
          <p className="text-white font-semibold text-[15px] mb-0.5">Explore the dashboard</p>
          <p className="text-white/70 text-[13px]">Live data · 36 months of history · AI-powered Q&A</p>
        </div>
        <Link
          to="/dashboard"
          className="shrink-0 bg-white text-[var(--primary)] text-[13px] font-semibold px-5 py-2.5 rounded-lg hover:bg-[var(--surface-2)] transition-colors"
        >
          Go to Dashboard →
        </Link>
      </div>

    </div>
  )
}
