import { useState } from 'react'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import PrivacyGateway from './pages/PrivacyGateway'
import AuditLogs from './pages/AuditLogs'
import Evaluation from './pages/Evaluation'
import Settings from './pages/Settings'

const pages = {
  Dashboard: <Dashboard />,
  'Privacy Gateway': <PrivacyGateway />,
  'Audit Logs': <AuditLogs />,
  'Evaluation & Metrics': <Evaluation />,
  'Privacy Policies / Settings': <Settings />,
}

function App() {
  const [activePage, setActivePage] = useState('Dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Navbar activePage={activePage} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="mx-auto flex max-w-[1600px]">
        <Sidebar activePage={activePage} setActivePage={setActivePage} sidebarOpen={sidebarOpen} />
        <div className="flex-1 p-4 lg:p-6">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-4 shadow-panel lg:p-6">
            {pages[activePage]}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
