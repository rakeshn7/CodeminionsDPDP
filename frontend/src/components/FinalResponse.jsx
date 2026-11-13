import { CheckCircle2, RefreshCw, TriangleAlert } from 'lucide-react'

function renderRestoredText(rawText = '') {
  const parts = (rawText || '').split(/(<[A-Z_]+\d*?>)/g)

  return parts.map((part, idx) => {
    if (part.startsWith('<') && part.endsWith('>')) {
      return (
        <span key={`${part}-${idx}`} className="rounded-md border border-emerald-300 bg-emerald-50 px-1.5 py-0.5 font-mono text-[11px] font-bold text-emerald-700">
          {part}
        </span>
      )
    }
    return <span key={`${part}-${idx}`}>{part}</span>
  })
}

export default function FinalResponse({
  finalResponse,
  restored = [],
  missing = [],
  unknown = [],
  malformed = [],
  expectedPlaceholders = [],
  status = 'pending',
}) {
  const restorationComplete = status === 'processed'
    && expectedPlaceholders.length > 0
    && expectedPlaceholders.every((placeholder) => restored.includes(placeholder))
    && missing.length === 0
    && unknown.length === 0
    && malformed.length === 0
    && !expectedPlaceholders.some((placeholder) => finalResponse?.includes(placeholder))
  const restorationStatus = status !== 'processed'
    ? 'Awaiting backend response'
    : expectedPlaceholders.length === 0
    ? 'No placeholders to restore'
    : restorationComplete
    ? 'All reported placeholders restored'
    : 'Restoration needs review'

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-slate-700">
          <RefreshCw className="h-4 w-4 text-emerald-600" />
          Final response
        </div>
        <div className={`inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs ${restorationComplete ? 'text-emerald-700 font-semibold' : 'text-amber-700'}`}>
          {restorationComplete ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> : <TriangleAlert className="h-3.5 w-3.5 text-amber-600" />}
          {restorationStatus}
        </div>
      </div>

      <div className="min-h-[220px] rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-900 font-mono">
        {status === 'processed' ? renderRestoredText(finalResponse) : <span className="text-slate-400 font-sans italic">Waiting for a real backend response...</span>}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500 font-semibold">Restored entities</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {restored.length ? restored.map((placeholder) => (
              <span key={placeholder} className="rounded-md border border-emerald-300 bg-emerald-50 px-2 py-0.5 font-mono text-[11px] font-bold text-emerald-700">
                {placeholder}
              </span>
            )) : <span className="text-xs text-slate-500">None</span>}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500 font-semibold">Unresolved placeholders</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {[...missing, ...unknown, ...malformed].length ? [...missing, ...unknown, ...malformed].map((placeholder) => (
              <span key={placeholder} className="rounded-md border border-rose-300 bg-rose-50 px-2 py-0.5 font-mono text-[11px] font-bold text-rose-700">
                {placeholder}
              </span>
            )) : <span className="text-xs text-emerald-700 font-medium">0 unresolved</span>}
          </div>
        </div>
      </div>
    </div>
  )
}
