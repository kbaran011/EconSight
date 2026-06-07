import { Link } from 'react-router-dom'

const PHASES = [
  {
    number: '01',
    title:  'Data Engineering Foundation',
    status: 'complete',
    weeks:  'Weeks 1–3',
    items: [
      'PostgreSQL 16 with medallion architecture (Bronze → Silver → Gold)',
      'Async concurrent ingestion from Statistics Canada & Bank of Canada Valet API',
      'dbt models for staging views and mart tables with idempotent upserts',
      'Apache Airflow DAGs for scheduled pipeline runs',
      'GitHub Actions CI with pytest and mypy',
    ],
  },
  {
    number: '02',
    title:  'Econometric Modelling',
    status: 'complete',
    weeks:  'Weeks 4–6',
    items: [
      'VAR/VECM impulse response analysis for macro interdependencies',
      'XGBoost forecasting with SHAP explainability',
      'MLflow experiment tracking and model registry',
      'Monte Carlo simulation for scenario distributions (P10/P50/P90)',
      'Composite Economic Health Score (10-point index)',
    ],
  },
  {
    number: '03',
    title:  'Consulting Interface',
    status: 'complete',
    weeks:  'Weeks 7–9',
    items: [
      'FastAPI backend with typed schemas and async DB access',
      'RAG pipeline: ChromaDB + sentence-transformers + Llama 3.3 via Groq',
      'PDF report generation: WeasyPrint executive brief + nbconvert full analysis',
      'React + TypeScript + Tailwind frontend with live API integration',
      'Natural language Q&A over economic data (SQL and semantic routing)',
    ],
  },
  {
    number: '04',
    title:  'Production & Storytelling',
    status: 'upcoming',
    weeks:  'Weeks 10–12',
    items: [
      'Docker Compose for one-command full-stack deployment',
      'GitHub Actions CI for frontend lint + backend tests',
      'Consulting deck: problem → methodology → findings → recommendations',
      'Loom demo recording for portfolio presentation',
    ],
  },
]

const STACK = [
  { category: 'Data Engineering', items: 'Python 3.14 · PostgreSQL 16 · dbt 1.8 · Apache Airflow 2.9 · httpx · Pydantic' },
  { category: 'Econometrics',     items: 'statsmodels · XGBoost · SHAP · scikit-learn · MLflow · pandas · matplotlib' },
  { category: 'Backend API',      items: 'FastAPI · uvicorn · psycopg3 · ChromaDB · sentence-transformers · WeasyPrint' },
  { category: 'AI / LLM',         items: 'Llama 3.3-70b via Groq · RAG pipeline · SQL generation · semantic retrieval' },
  { category: 'Frontend',         items: 'React 19 · TypeScript · Tailwind CSS · shadcn/ui · Recharts · TanStack Query' },
  { category: 'DevOps',           items: 'GitHub Actions · Docker (Phase 4) · pytest · mypy · ruff' },
]

const DATA_SOURCES = [
  { name: 'Statistics Canada',        series: 'GDP, CPI, Unemployment Rate, IPPI, Retail Trade (5 series)' },
  { name: 'Bank of Canada Valet API', series: 'Overnight Rate, CAD/USD, 10-yr Bond Yield, M2++ (4 series)' },
]

export default function About() {
  return (
    <div className="space-y-10 max-w-4xl">
      {/* Hero */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
        <div className="flex items-start gap-5">
          <div className="w-14 h-14 rounded-xl bg-blue-700 flex items-center justify-center shadow-sm shrink-0">
            <span className="text-white text-xl font-bold tracking-tight">ES</span>
          </div>
          <div>
            <p className="section-title">About This Project</p>
            <h1 className="text-2xl font-semibold text-slate-900 mb-2">EconSight</h1>
            <p className="text-[15px] text-slate-600 leading-relaxed max-w-2xl">
              A full-stack decision intelligence platform for Canadian SMEs — built to demonstrate end-to-end
              capability across data engineering, econometric modelling, and AI-powered insight delivery.
              Developed as a portfolio project showcasing production-grade software and applied economics.
            </p>
            <div className="flex flex-wrap items-center gap-2 mt-4">
              {['McGill B.A. CS & Economics', 'Portfolio Project', 'Phase 3 of 4 Complete'].map(tag => (
                <span key={tag} className="text-[12px] font-medium text-slate-600 bg-slate-100 border border-slate-200 rounded-full px-3 py-1">
                  {tag}
                </span>
              ))}
              <a
                href="https://github.com/kbaran011"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-[12px] font-medium text-white bg-slate-800 hover:bg-slate-700 rounded-full px-3 py-1 transition-colors"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                </svg>
                github.com/kbaran011
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Problem statement */}
      <div>
        <p className="section-title">Problem Statement</p>
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-3">
          <p className="text-[15px] text-slate-700 leading-relaxed">
            Canadian SMEs make capital allocation, hiring, and pricing decisions without access to the macro-economic
            intelligence available to large enterprises. Publicly available data from Statistics Canada and the Bank of
            Canada is fragmented, requires technical expertise to interpret, and arrives with significant publication lag.
          </p>
          <p className="text-[15px] text-slate-700 leading-relaxed">
            EconSight aggregates, models, and surfaces this data through a consulting-grade interface — giving
            decision-makers a live composite health score, 12-month forecasts with scenario bands, and a natural
            language Q&A layer that can answer specific questions against both live database queries and a semantic
            index of the full analysis.
          </p>
        </div>
      </div>

      {/* Phase roadmap */}
      <div>
        <p className="section-title">Project Phases</p>
        <div className="space-y-3">
          {PHASES.map(phase => (
            <div key={phase.number} className={`bg-white rounded-xl border shadow-sm overflow-hidden ${
              phase.status === 'complete' ? 'border-slate-200' : 'border-dashed border-slate-300'
            }`}>
              <div className="flex items-center gap-4 px-6 py-4 border-b border-slate-100">
                <span className={`text-[11px] font-bold font-mono px-2.5 py-1 rounded ${
                  phase.status === 'complete'
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-slate-100 text-slate-400 border border-slate-200'
                }`}>
                  {phase.status === 'complete' ? '✓ Done' : 'Upcoming'}
                </span>
                <div>
                  <p className="text-[11px] text-slate-400 font-medium">{phase.weeks}</p>
                  <p className="text-[15px] font-semibold text-slate-800">
                    Phase {phase.number} — {phase.title}
                  </p>
                </div>
              </div>
              <ul className="px-6 py-4 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-1.5">
                {phase.items.map(item => (
                  <li key={item} className="flex items-start gap-2 text-[13px] text-slate-600">
                    <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${
                      phase.status === 'complete' ? 'bg-emerald-400' : 'bg-slate-300'
                    }`} />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Architecture */}
      <div>
        <p className="section-title">Architecture</p>
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="grid grid-cols-3 gap-0 text-center text-[12px] mb-5">
            {['Bronze (raw.*)', 'Silver (staging.*)', 'Gold (marts.*)'].map((layer, i) => (
              <div key={layer} className="relative flex flex-col items-center">
                <div className={`w-full py-2.5 px-2 rounded font-medium ${
                  i === 0 ? 'bg-amber-50 text-amber-700 border border-amber-200'
                  : i === 1 ? 'bg-slate-100 text-slate-600 border border-slate-200'
                  : 'bg-blue-50 text-blue-700 border border-blue-200'
                }`}>
                  {layer}
                </div>
                {i < 2 && (
                  <span className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 text-slate-400 text-base z-10">→</span>
                )}
              </div>
            ))}
          </div>
          <p className="text-[13px] text-slate-500 leading-relaxed">
            Medallion architecture in PostgreSQL. Raw API responses land in <code className="bg-slate-100 rounded px-1">raw.*</code> tables,
            dbt views clean and type-cast to <code className="bg-slate-100 rounded px-1">staging.*</code>, and dbt-materialized tables
            in <code className="bg-slate-100 rounded px-1">marts.*</code> serve as the query layer for the API, models, and RAG pipeline.
            The read-only <code className="bg-slate-100 rounded px-1">econsight_reader</code> role isolates API database access.
          </p>
        </div>
      </div>

      {/* Tech stack */}
      <div>
        <p className="section-title">Technology Stack</p>
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full">
            <tbody>
              {STACK.map((row, i) => (
                <tr key={row.category} className={`border-b border-slate-100 last:border-0 ${i % 2 === 0 ? '' : 'bg-slate-50/50'}`}>
                  <td className="py-3 px-6 text-[12px] font-semibold text-slate-500 uppercase tracking-wider w-48 whitespace-nowrap">
                    {row.category}
                  </td>
                  <td className="py-3 px-6 text-[13px] text-slate-700">{row.items}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Data sources */}
      <div>
        <p className="section-title">Data Sources</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {DATA_SOURCES.map(ds => (
            <div key={ds.name} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <p className="text-[14px] font-semibold text-slate-800 mb-1">{ds.name}</p>
              <p className="text-[13px] text-slate-500">{ds.series}</p>
              <p className="text-[11px] text-slate-400 mt-2">Public API · Monthly frequency · Free</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="bg-blue-700 rounded-xl p-6 flex items-center justify-between gap-4">
        <div>
          <p className="text-white font-semibold text-[15px] mb-0.5">Explore the dashboard</p>
          <p className="text-blue-200 text-[13px]">Live data · 36 months of history · AI-powered Q&A</p>
        </div>
        <Link
          to="/dashboard"
          className="shrink-0 bg-white text-blue-700 text-[13px] font-semibold px-5 py-2.5 rounded-lg hover:bg-blue-50 transition-colors"
        >
          Go to Dashboard →
        </Link>
      </div>
    </div>
  )
}
