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
  'Privacy Gateway': <PrivacyGateway initialWorkflow="intelligent_document" />,
  'Text Privacy Gateway': <PrivacyGateway initialWorkflow="legacy_gateway" />,
  'Audit Logs': <AuditLogs />,
  'Evaluation & Metrics': <Evaluation />,
  'Privacy Policies / Settings': <Settings />,
}

function App() {
  const [activePage, setActivePage] = useState('Dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Navbar activePage={activePage} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="mx-auto flex max-w-[1600px]">
        {sidebarOpen && (
          <button
            type="button"
            className="fixed inset-x-0 top-[69px] bottom-0 z-20 bg-slate-950/30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation"
          />
        )}
        <Sidebar
          activePage={activePage}
          setActivePage={setActivePage}
          setSidebarOpen={setSidebarOpen}
          sidebarOpen={sidebarOpen}
        />
        <div className="flex-1 p-4 lg:p-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm lg:p-6">
            {pages[activePage]}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
