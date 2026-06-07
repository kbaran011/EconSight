import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import Ask from './pages/Ask'
import Dashboard from './pages/Dashboard'
import Forecasts from './pages/Forecasts'
import Indicators from './pages/Indicators'
import Report from './pages/Report'

const queryClient = new QueryClient()

const NAV_LINKS = [
  ['/dashboard', 'Dashboard'],
  ['/indicators', 'Indicators'],
  ['/forecasts', 'Forecasts'],
  ['/ask', 'Ask'],
  ['/report', 'Report'],
] as const

function Nav() {
  const { pathname } = useLocation()
  const active = pathname === '/' ? '/dashboard' : pathname
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div className="max-w-screen-xl mx-auto px-8 flex items-center gap-8 h-14">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mr-4">
          <div className="w-6 h-6 rounded bg-blue-700 flex items-center justify-center">
            <span className="text-white text-[10px] font-bold leading-none">ES</span>
          </div>
          <span className="font-semibold text-slate-900 text-[15px] tracking-tight">EconSight</span>
          <span className="text-slate-300 text-xs ml-1 hidden sm:inline">Canadian Economic Intelligence</span>
        </div>

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          {NAV_LINKS.map(([to, label]) => {
            const isActive = active === to
            return (
              <Link
                key={to}
                to={to}
                className={`px-3 py-1.5 rounded text-[13px] font-medium transition-colors ${
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

        {/* Right side tag */}
        <div className="ml-auto hidden md:flex items-center gap-2">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
            Portfolio Project
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        </div>
      </div>
    </header>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-100">
          <Nav />
          <main className="max-w-screen-xl mx-auto px-8 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/indicators" element={<Indicators />} />
              <Route path="/forecasts" element={<Forecasts />} />
              <Route path="/ask" element={<Ask />} />
              <Route path="/report" element={<Report />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
