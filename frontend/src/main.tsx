import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, Route, Routes, NavLink } from 'react-router-dom'
import './index.css'
import Accounts from './pages/Accounts'
import Groups from './pages/Groups'
import Dashboard from './pages/Dashboard'

const qc = new QueryClient()

function Shell() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded ${isActive ? 'bg-slate-800 text-white' : 'text-slate-700 hover:bg-slate-200'}`
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link to="/" className="font-semibold">Copy Trading</Link>
          <nav className="flex gap-1">
            <NavLink to="/" end className={linkClass}>Dashboard</NavLink>
            <NavLink to="/accounts" className={linkClass}>Accounts</NavLink>
            <NavLink to="/groups" className={linkClass}>Groups</NavLink>
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/groups" element={<Groups />} />
        </Routes>
      </main>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
