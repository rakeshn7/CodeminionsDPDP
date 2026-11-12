import { ShieldAlert, ShieldCheck } from 'lucide-react'

function renderHighlightedText(rawText = '', emphasis = '#3b82f6') {
  const parts = (rawText || '').split(/(<[A-Z_]+\d*?>)/g)

  return parts.map((part, index) => {
    if (part.startsWith('<') && part.endsWith('>')) {
      return (
        <span key={`${part}-${index}`} className="rounded-md border border-blue-500/40 bg-blue-500/10 px-1.5 py-0.5 font-mono text-[11px] text-blue-200" style={{ boxShadow: `inset 0 0 0 1px ${emphasis}40` }}>
          {part}
        </span>
      )
    }
    return <span key={`${part}-${index}`}>{part}</span>
  })
}

export default function SanitizedOutput({ sanitizedText, entities = [], leakageDetected, placeholderCount }) {
  const safeStatus = leakageDetected ? 'Leakage detected' : 'Outbound safe'
  const statusTone = leakageDetected ? 'text-rose-300' : 'text-emerald-300'

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.2em] text-slate-300">
          <ShieldCheck className="h-4 w-4 text-emerald-300" />
          Sanitized Outbound Payload
        </div>
        <div className={`inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-xs ${statusTone}`}>
          {leakageDetected ? <ShieldAlert className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
          {safeStatus}
        </div>
      </div>

      <div className="min-h-[220px] rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm leading-6 text-slate-100">
        {sanitizedText ? renderHighlightedText(sanitizedText) : 'Waiting for sanitized payload...'}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-slate-700 bg-slate-950/70 p-3">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Detected entity types</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {entities.length ? entities.map((entity, idx) => (
              <span key={`${entity.type || 'entity'}-${idx}`} className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-xs font-medium text-blue-200">
                {entity.type || 'UNKNOWN'}
              </span>
            )) : <span className="text-sm text-slate-400">No entities detected</span>}
          </div>
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-950/70 p-3">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Placeholder count</p>
          <p className="mt-2 text-2xl font-semibold text-white">{placeholderCount}</p>
        </div>
      </div>
    </div>
  )
}
