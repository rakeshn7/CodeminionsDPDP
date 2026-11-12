import { CheckCircle2, RefreshCw, TriangleAlert } from 'lucide-react'

function renderRestoredText(rawText = '') {
  const parts = (rawText || '').split(/(<[A-Z_]+\d*?>)/g)

  return parts.map((part, idx) => {
    if (part.startsWith('<') && part.endsWith('>')) {
      return (
        <span key={`${part}-${idx}`} className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[11px] text-emerald-200">
          {part}
        </span>
      )
    }
    return <span key={`${part}-${idx}`}>{part}</span>
  })
}

export default function FinalResponse({ finalResponse, restored = [], missing = [], status = 'Ready' }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.2em] text-slate-300">
          <RefreshCw className="h-4 w-4 text-emerald-300" />
          Final AI Response
        </div>
        <div className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-emerald-300">
          {status === 'restored' ? <CheckCircle2 className="h-3.5 w-3.5" /> : <TriangleAlert className="h-3.5 w-3.5" />}
          {status === 'restored' ? 'Restoration status: success' : `Restoration status: ${status}`}
        </div>
      </div>

      <div className="min-h-[220px] rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm leading-6 text-slate-100">
        {finalResponse ? renderRestoredText(finalResponse) : 'Waiting for final LLM response...'}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-slate-700 bg-slate-950/70 p-3">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Restored information</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {restored.length ? restored.map((item, index) => (
              <span key={`${item}-${index}`} className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-200">{item}</span>
            )) : <span className="text-sm text-slate-400">No restored values</span>}
          </div>
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-950/70 p-3">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Missing placeholders</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {missing.length ? missing.map((item, index) => (
              <span key={`${item}-${index}`} className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-200">{item}</span>
            )) : <span className="text-sm text-slate-400">None detected</span>}
          </div>
        </div>
      </div>
    </div>
  )
}
