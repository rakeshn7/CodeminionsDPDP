import { Activity, DatabaseZap, FileSearch, Gauge, LockKeyhole, ShieldCheck, SlidersHorizontal } from 'lucide-react'

const navItems = [
  { label: 'Dashboard', icon: Gauge },
  { label: 'Privacy Gateway', icon: ShieldCheck },
  { label: 'Audit Logs', icon: Activity },
  { label: 'Evaluation & Metrics', icon: FileSearch },
  { label: 'Privacy Policies / Settings', icon: SlidersHorizontal },
]

export default function Sidebar({ activePage, setActivePage, sidebarOpen }) {
  return (
    <aside
      className={[
        'border-r border-slate-800 bg-slate-950/80 transition-all duration-200',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        'fixed inset-y-0 left-0 z-30 w-72 lg:static lg:w-72',
      ].join(' ')}
    >
      <div className="flex h-full flex-col px-3 py-5">
        <div className="mb-8 flex items-center gap-3 px-3">
          <div className="rounded-xl bg-emerald-500/15 p-2 text-emerald-300 ring-1 ring-emerald-500/20">
            <LockKeyhole className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500">PRIVACY</p>
            <p className="text-lg font-semibold text-white">Gateway</p>
          </div>
        </div>

        <nav className="space-y-2">
          {navItems.map(({ label, icon: Icon }) => {
            const isActive = activePage === label
            return (
              <button
                key={label}
                type="button"
                onClick={() => setActivePage(label)}
                className={[
                  'flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-500/10 text-blue-200 ring-1 ring-blue-500/25'
                    : 'text-slate-300 hover:bg-slate-900 hover:text-white',
                ].join(' ')}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </button>
            )
          })}
        </nav>

        <div className="mt-auto rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-100">
          <div className="mb-2 flex items-center gap-2">
            <DatabaseZap className="h-4 w-4 text-emerald-300" />
            <span className="font-medium">Protected mode</span>
          </div>
          <p className="text-xs text-emerald-200/80">Live sanitization and reinsertion checks are enabled for monitored workloads.</p>
        </div>
      </div>
    </aside>
  )
}
