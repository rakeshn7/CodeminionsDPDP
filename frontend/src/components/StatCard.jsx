import { ArrowUpRight } from 'lucide-react'

export default function StatCard({ title, value, detail, tone = 'blue', icon: Icon }) {
  const toneMap = {
    blue: 'bg-blue-50 text-blue-700 ring-blue-200',
    green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    red: 'bg-rose-50 text-rose-700 ring-rose-200',
    amber: 'bg-amber-50 text-amber-700 ring-amber-200',
    purple: 'bg-purple-50 text-purple-700 ring-purple-200',
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-3 text-3xl font-bold text-slate-900">{value}</p>
        </div>
        <div className={`rounded-xl p-2 ring-1 ${toneMap[tone] || toneMap.blue}`}>
          {Icon ? <Icon className="h-5 w-5" /> : <ArrowUpRight className="h-5 w-5" />}
        </div>
      </div>
      {detail && <p className="mt-4 text-xs text-slate-600">{detail}</p>}
    </div>
  )
}
