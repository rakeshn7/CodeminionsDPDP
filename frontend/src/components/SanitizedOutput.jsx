import { ShieldAlert, ShieldCheck } from 'lucide-react'

function renderHighlightedText(rawText = '') {
  const parts = (rawText || '').split(/(<[A-Z_]+\d*?>)/g)

  return parts.map((part, index) => {
    if (part.startsWith('<') && part.endsWith('>')) {
      return (
        <span key={`${part}-${index}`} className="rounded-md border border-blue-300 bg-blue-50 px-1.5 py-0.5 font-mono text-[11px] font-bold text-blue-700">
          {part}
        </span>
      )
    }
    return <span key={`${part}-${index}`}>{part}</span>
  })
}

export default function SanitizedOutput({ sanitizedText, entities = [], hasResult, leakageDetected, placeholderCount }) {
  const safeStatus = !hasResult
    ? 'Awaiting backend result'
    : leakageDetected
    ? 'Leakage detected'
    : 'Leakage not detected'
  const statusTone = !hasResult
    ? 'text-slate-500'
    : leakageDetected
    ? 'text-rose-700 font-bold'
    : 'text-emerald-700 font-semibold'

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-slate-700">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          Sanitized Text Preview
        </div>
        <div className={`inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs ${statusTone}`}>
          {hasResult && leakageDetected
            ? <ShieldAlert className="h-3.5 w-3.5" />
            : <ShieldCheck className="h-3.5 w-3.5" />}
          {safeStatus}
        </div>
      </div>

      <div className="min-h-[220px] rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-900 font-mono">
        {hasResult ? renderHighlightedText(sanitizedText) : <span className="text-slate-400 font-sans italic">Waiting for a real backend response...</span>}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500 font-semibold">Detected entity types</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {entities.length ? entities.map((entity, idx) => (
              <span key={`${entity.type || 'entity'}-${idx}`} className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
                {entity.type || 'UNKNOWN'}
              </span>
            )) : <span className="text-xs text-slate-500">No entities detected</span>}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500 font-semibold">Placeholder count</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{placeholderCount}</p>
        </div>
      </div>
    </div>
  )
}
