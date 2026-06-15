import { useState } from 'react'
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query'
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import Ask from './pages/Ask'
import About from './pages/About'
import Dashboard from './pages/Dashboard'
import Forecasts from './pages/Forecasts'
import Indicators from './pages/Indicators'
import Report from './pages/Report'
import { fetchHealthScore, fetchStatus } from './api/client'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: true,
    },
  },
})

const NAV_LINKS = [
  ['/dashboard',  'Dashboard'],
  ['/indicators', 'Indicators'],
  ['/forecasts',  'Forecasts'],
  ['/ask',        'Ask'],
  ['/report',     'Report'],
  ['/about',      'About'],
] as const

function ScoreBadge() {
  const { data } = useQuery({ queryKey: ['health-score'], queryFn: fetchHealthScore })
  if (!data) return null
  const s = data.latest_score
  return (
    <span>Health {s.toFixed(1)} / 10</span>
  )
}

function DataFreshness() {
  const qc = useQueryClient()
  const { data, isFetching } = useQuery({
    queryKey: ['status'],
    queryFn: fetchStatus,
    refetchInterval: (q) => (q.state.data?.seeding_status === 'seeding' ? 5000 : 60_000),
  })

  const period = data?.latest_data_date?.slice(0, 7)
  const isError = data?.seeding_status === 'error'
  const isSeeding = data?.seeding_status === 'seeding'

  let label = '…'
  if (isError) label = 'Seed failed'
  else if (isSeeding) label = 'Seeding…'
  else if (!data) label = '…'
  else if (period) label = period
  else label = 'No data'

  return (
    <div className="hidden xl:flex items-center gap-1.5 shrink-0">
      <span
        className={`inline-flex items-center gap-1.5 text-[11px] font-medium border rounded-full px-2.5 py-0.5 whitespace-nowrap ${
          isError
            ? 'text-red-600 bg-red-50 border-red-200'
            : isSeeding
              ? 'text-amber-600 bg-amber-50 border-amber-200'
              : 'bg-[var(--nav-badge-bg)] border-[var(--nav-badge-border)] text-[var(--nav-link)]'
        }`}
        title={period ? `Data through ${period}` : undefined}
      >
        {!isError && !isSeeding && period && (
          <span className="font-normal">As of</span>
        )}
        <span className={period && !isSeeding && !isError ? 'font-mono font-semibold tabular-nums' : ''}>
          {label}
        </span>
      </span>
      <button
        type="button"
        title="Refresh data"
        disabled={isFetching}
        onClick={() => {
          void qc.invalidateQueries()
        }}
        className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-white/8 text-[var(--nav-link)] hover:bg-white/15 hover:ring-1 hover:ring-[var(--nav-link)] transition-colors disabled:opacity-50"
      >
        <svg
          className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      </button>
    </div>
  )
}

function Nav() {
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const active = pathname === '/' ? '/dashboard' : pathname
  const { data: status } = useQuery({
    queryKey: ['status'],
    queryFn: fetchStatus,
    refetchInterval: (q) => (q.state.data?.seeding_status === 'seeding' ? 5000 : 60_000),
  })
  const mobilePeriod = status?.latest_data_date?.slice(0, 7)

  return (
    <header className="bg-[var(--primary)] sticky top-0 z-20">
      <div className="max-w-screen-xl mx-auto px-4 sm:px-8 flex items-center h-14 gap-3 min-w-0">
        <Link to="/dashboard" className="flex items-center gap-2.5 shrink-0">
          <div className="bg-[var(--accent)] text-white rounded-[4px] w-7 h-7 flex items-center justify-center shadow-sm">
            <span className="text-[11px] font-bold tracking-tight">ES</span>
          </div>
          <span className="font-serif font-bold text-[16px] text-[var(--nav-text)]">EconSight</span>
        </Link>

        <div className="w-px h-4 bg-white/15 shrink-0 hidden md:block" />

        <nav className="hidden md:flex flex-1 items-center justify-center gap-0.5 min-w-0 overflow-x-auto">
          {NAV_LINKS.map(([to, label]) => {
            const isActive = active === to || (active.startsWith(to) && to !== '/dashboard')
            return (
              <Link
                key={to}
                to={to}
                className={`px-2.5 lg:px-3 py-1.5 rounded-md text-[12px] font-medium transition-colors whitespace-nowrap ${
                  isActive
                    ? 'bg-[var(--nav-link-active-bg)] text-[var(--nav-text)]'
                    : 'text-[var(--nav-link)] hover:text-[var(--nav-text)] hover:bg-[var(--nav-link-active-bg)]'
                }`}
              >
                {label}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-2 shrink-0 ml-auto md:ml-0">
          <DataFreshness />
          <div className="bg-[var(--nav-badge-bg)] border border-[var(--nav-badge-border)] text-[var(--nav-badge-text)] font-mono text-[11px] px-3 py-1 rounded-full hidden lg:flex items-center gap-1.5">
            <span className="nav-live-dot" />
            <ScoreBadge />
          </div>
          <button
            type="button"
            className="md:hidden p-2 rounded-md text-[var(--nav-link)] hover:bg-white/10"
            aria-label="Open menu"
            onClick={() => setMenuOpen(o => !o)}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {menuOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
            </svg>
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav className="md:hidden bg-[var(--primary)] border-t border-white/10 px-4 py-2 space-y-1">
          {NAV_LINKS.map(([to, label]) => {
            const isActive = active === to
            return (
              <Link
                key={to}
                to={to}
                onClick={() => setMenuOpen(false)}
                className={`block px-3 py-2 rounded-md text-[14px] font-medium ${
                  isActive
                    ? 'bg-[var(--nav-link-active-bg)] text-[var(--nav-text)]'
                    : 'text-[var(--nav-link)]'
                }`}
              >
                {label}
              </Link>
            )
          })}
          {mobilePeriod && (
            <p className="px-3 pt-2 text-[11px] text-[var(--nav-link)] border-t border-white/10 mt-1">
              As of{' '}
              <span className="font-mono font-semibold tabular-nums">{mobilePeriod}</span>
            </p>
          )}
        </nav>
      )}
    </header>
  )
}

function Footer() {
  return (
    <footer className="bg-[var(--primary)] mt-16">
      <div className="max-w-screen-xl mx-auto px-4 sm:px-8 py-6 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-[var(--accent)] flex items-center justify-center">
            <span className="text-white text-[9px] font-bold">ES</span>
          </div>
          <span className="text-[13px] font-medium text-[var(--nav-text)]">EconSight</span>
          <span className="text-white/20 text-xs">·</span>
          <span className="text-[12px] text-[var(--nav-link)]">Canadian Macroeconomic Decision Intelligence</span>
        </div>
        <div className="flex items-center gap-4 text-[12px] text-[var(--nav-link)]">
          <span>McGill University · B.A. CS & Economics</span>
          <span className="text-white/20">|</span>
          <a
            href="https://github.com/kbaran011"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[var(--nav-text)] transition-colors"
          >
            github.com/kbaran011
          </a>
        </div>
      </div>
    </footer>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-[var(--bg)] flex flex-col">
          <Nav />
          <main className="flex-1 max-w-screen-xl mx-auto w-full px-4 sm:px-8 py-8">
            <Routes>
              <Route path="/"           element={<Dashboard />} />
              <Route path="/dashboard"  element={<Dashboard />} />
              <Route path="/indicators" element={<Indicators />} />
              <Route path="/forecasts"  element={<Forecasts />} />
              <Route path="/ask"        element={<Ask />} />
              <Route path="/report"     element={<Report />} />
              <Route path="/about"      element={<About />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
