import { Menu, ShieldCheck } from 'lucide-react'

export default function Navbar({ activePage, setSidebarOpen, sidebarOpen }) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1600px] items-center justify-between px-4 py-3 lg:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-slate-100 lg:hidden text-slate-700 hover:bg-slate-200"
            onClick={() => setSidebarOpen((current) => !current)}
            aria-label="Toggle sidebar"
            aria-expanded={sidebarOpen}
          >
            <Menu className="h-5 w-5 text-slate-700" />
          </button>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500 font-medium">Privacy Gateway</p>
              <h1 className="text-lg font-semibold text-slate-900">Privacy & Compliance Console</h1>
            </div>
          </div>
        </div>

        <div className="hidden items-center gap-3 md:flex">
          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700">
            {activePage}
          </div>
        </div>
      </div>
    </header>
  )
}
