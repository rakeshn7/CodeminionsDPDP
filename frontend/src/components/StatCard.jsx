import { ArrowUpRight } from 'lucide-react'

export default function StatCard({ title, value, detail, tone = 'blue', icon: Icon }) {
  const toneMap = {
    blue: 'bg-blue-500/10 text-blue-300 ring-blue-500/20',
    green: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/20',
    red: 'bg-rose-500/10 text-rose-300 ring-rose-500/20',
    amber: 'bg-amber-500/10 text-amber-300 ring-amber-500/20',
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-panel">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-slate-400">{title}</p>
          <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
        </div>
        <div className={`rounded-xl p-2 ring-1 ${toneMap[tone]}`}>
          {Icon ? <Icon className="h-5 w-5" /> : <ArrowUpRight className="h-5 w-5" />}
        </div>
      </div>
      {detail && <p className="mt-4 text-sm text-slate-300">{detail}</p>}
    </div>
  )
}
