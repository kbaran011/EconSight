import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import Ask from './pages/Ask'
import Dashboard from './pages/Dashboard'
import Forecasts from './pages/Forecasts'
import Indicators from './pages/Indicators'
import Report from './pages/Report'

const queryClient = new QueryClient()

const NAV_LINKS = [
  ['/', 'Dashboard'],
  ['/indicators', 'Indicators'],
  ['/forecasts', 'Forecasts'],
  ['/ask', 'Ask'],
  ['/report', 'Report'],
] as const

function Nav() {
  const { pathname } = useLocation()
  return (
    <nav className="border-b bg-white px-6 py-3 flex items-center gap-6 text-sm font-medium shadow-sm">
      <span className="text-blue-700 font-bold text-base mr-2">EconSight</span>
      {NAV_LINKS.map(([to, label]) => (
        <Link
          key={to}
          to={to}
          className={`transition-colors ${pathname === to ? 'text-blue-700 font-semibold' : 'text-gray-500 hover:text-blue-700'}`}
        >
          {label}
        </Link>
      ))}
    </nav>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <Nav />
          <main className="max-w-7xl mx-auto px-6 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
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
