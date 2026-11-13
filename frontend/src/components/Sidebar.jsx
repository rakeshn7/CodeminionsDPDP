import { Activity, DatabaseZap, FileSearch, Gauge, LockKeyhole, ShieldCheck, SlidersHorizontal } from 'lucide-react'

const navItems = [
  { label: 'Dashboard', icon: Gauge },
  { label: 'Privacy Gateway', icon: ShieldCheck },
  { label: 'Text Privacy Gateway', icon: FileSearch },
  { label: 'Audit Logs', icon: Activity },
  { label: 'Evaluation & Metrics', icon: FileSearch },
  { label: 'Privacy Policies / Settings', icon: SlidersHorizontal },
]

export default function Sidebar({ activePage, setActivePage, setSidebarOpen, sidebarOpen }) {
  return (
    <aside
      className={[
        'border-r border-slate-200 bg-white transition-all duration-200',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        'fixed left-0 top-[69px] bottom-0 z-30 w-72 lg:static lg:z-auto lg:w-72',
      ].join(' ')}
    >
      <div className="flex h-full flex-col px-3 py-5">
        <div className="mb-8 flex items-center gap-3 px-3">
          <div className="rounded-xl bg-emerald-50 p-2 text-emerald-700 ring-1 ring-emerald-200">
            <LockKeyhole className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500 font-semibold">PRIVACY</p>
            <p className="text-lg font-semibold text-slate-900">Gateway</p>
          </div>
        </div>

        <nav className="space-y-1.5">
          {navItems.map(({ label, icon: Icon }) => {
            const isActive = activePage === label
            return (
              <button
                key={label}
                type="button"
                onClick={() => {
                  setActivePage(label)
                  setSidebarOpen(false)
                }}
                className={[
                  'flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700 ring-1 ring-blue-200 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
                ].join(' ')}
              >
                <Icon className={`h-4 w-4 ${isActive ? 'text-blue-600' : 'text-slate-500'}`} />
                <span>{label}</span>
              </button>
            )
          })}
        </nav>

        <div className="mt-auto rounded-2xl border border-emerald-200 bg-emerald-50 p-3.5 text-sm text-emerald-900">
          <div className="mb-1.5 flex items-center gap-2">
            <DatabaseZap className="h-4 w-4 text-emerald-700" />
            <span className="font-semibold text-xs">Backend-connected mode</span>
          </div>
          <p className="text-xs text-emerald-800 leading-relaxed">Results appear only after a successful backend response.</p>
        </div>
      </div>
    </aside>
  )
}
