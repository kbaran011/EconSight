import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import Ask from './pages/Ask'
import About from './pages/About'
import Dashboard from './pages/Dashboard'
import Forecasts from './pages/Forecasts'
import Indicators from './pages/Indicators'
import Report from './pages/Report'
import { fetchHealthScore } from './api/client'

const queryClient = new QueryClient()

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
  const color = s >= 7 ? 'text-emerald-600 bg-emerald-50 border-emerald-200'
              : s >= 5 ? 'text-amber-600 bg-amber-50 border-amber-200'
              :           'text-red-600 bg-red-50 border-red-200'
  return (
    <span className={`hidden lg:inline-flex items-center gap-1.5 text-[11px] font-semibold border rounded-full px-2.5 py-0.5 ${color}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      Health {s.toFixed(1)} / 10
    </span>
  )
}

function Nav() {
  const { pathname } = useLocation()
  const active = pathname === '/' ? '/dashboard' : pathname
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div className="max-w-screen-xl mx-auto px-8 flex items-center h-14 gap-6">
        {/* Logo */}
        <Link to="/dashboard" className="flex items-center gap-2.5 shrink-0">
          <div className="w-7 h-7 rounded-lg bg-blue-700 flex items-center justify-center shadow-sm">
            <span className="text-white text-[11px] font-bold tracking-tight">ES</span>
          </div>
          <span className="font-semibold text-slate-900 text-[15px] tracking-tight">EconSight</span>
        </Link>

        <span className="hidden sm:block text-slate-200 text-lg select-none">|</span>
        <span className="hidden sm:block text-[11px] font-medium text-slate-400 tracking-wide uppercase whitespace-nowrap">
          Canadian Economic Intelligence
        </span>

        {/* Nav links */}
        <nav className="flex items-center gap-0.5 ml-2">
          {NAV_LINKS.map(([to, label]) => {
            const isActive = active === to || (active.startsWith(to) && to !== '/dashboard')
            return (
              <Link
                key={to}
                to={to}
                className={`px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors whitespace-nowrap ${
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                }`}
              >
                {label}
              </Link>
            )
          })}
        </nav>

        {/* Right: live health score */}
        <div className="ml-auto flex items-center gap-3">
          <ScoreBadge />
          <span className="hidden md:flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live
          </span>
        </div>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white mt-16">
      <div className="max-w-screen-xl mx-auto px-8 py-6 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-blue-700 flex items-center justify-center">
            <span className="text-white text-[9px] font-bold">ES</span>
          </div>
          <span className="text-[13px] font-medium text-slate-700">EconSight</span>
          <span className="text-slate-300 text-xs">·</span>
          <span className="text-[12px] text-slate-400">Canadian Macroeconomic Decision Intelligence</span>
        </div>
        <div className="flex items-center gap-4 text-[12px] text-slate-400">
          <span>McGill University · B.Sc. CS & Economics</span>
          <span className="text-slate-200">|</span>
          <span>IBM Montreal Strategy & Data Consulting Portfolio</span>
        </div>
      </div>
    </footer>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-100 flex flex-col">
          <Nav />
          <main className="flex-1 max-w-screen-xl mx-auto w-full px-8 py-8">
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
