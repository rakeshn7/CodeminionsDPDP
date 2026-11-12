import { Bell, Menu, ShieldCheck, Sparkles } from 'lucide-react'

export default function Navbar({ activePage, setSidebarOpen, sidebarOpen }) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1600px] items-center justify-between px-4 py-3 lg:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-700 bg-slate-900 lg:hidden"
            onClick={() => setSidebarOpen((current) => !current)}
            aria-label="Toggle sidebar"
            aria-expanded={sidebarOpen}
          >
            <Menu className="h-5 w-5 text-slate-200" />
          </button>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/20">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Privacy Gateway</p>
              <h1 className="text-lg font-semibold text-white">Enterprise AI Privacy & Compliance Console</h1>
            </div>
          </div>
        </div>

        <div className="hidden items-center gap-3 md:flex">
          <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300">
            <Sparkles className="h-4 w-4 text-emerald-400" />
            {activePage}
          </div>
          <button type="button" className="rounded-xl border border-slate-800 bg-slate-900 p-2.5 text-slate-300" aria-label="Notifications">
            <Bell className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  )
}
