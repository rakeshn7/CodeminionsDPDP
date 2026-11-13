import { AlertCircle, AlertTriangle, CheckCircle, CheckCircle2, Info, XCircle } from 'lucide-react'
import { useState } from 'react'

export default function ValidationPanel({
  findings = [],
  onSelectFinding,
  selectedFindingIndex,
  onAcceptSuggestion,
  onRejectSuggestion,
  reviewStatus = {},
}) {
  const [filterSeverity, setFilterSeverity] = useState('ALL')

  const counts = {
    ERROR: findings.filter((f) => f.severity === 'ERROR').length,
    WARNING: findings.filter((f) => f.severity === 'WARNING').length,
    INFO: findings.filter((f) => f.severity === 'INFO').length,
    TOTAL: findings.length,
  }

  const filtered = findings
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => filterSeverity === 'ALL' || item.severity === filterSeverity)

  const severityBadge = (severity) => {
    if (severity === 'ERROR') {
      return (
        <span className="inline-flex items-center gap-1 rounded-md border border-rose-200 bg-rose-50 px-2 py-0.5 text-xs font-semibold text-rose-700">
          <AlertCircle className="h-3 w-3" />
          ERROR
        </span>
      )
    }
    if (severity === 'WARNING') {
      return (
        <span className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
          <AlertTriangle className="h-3 w-3" />
          WARNING
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
        <Info className="h-3 w-3" />
        INFO
      </span>
    )
  }

  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      {/* Header and Summary Counts */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div>
          <h3 className="font-semibold text-slate-900">Smart Data Validation Engine</h3>
          <p className="text-xs text-slate-500">
            Deterministic rule engine for Indian phone numbers, emails, PAN, Aadhaar checksums, and dates.
          </p>
        </div>

        {/* Severity Count Pills */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setFilterSeverity('ALL')}
            className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
              filterSeverity === 'ALL' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:text-slate-900'
            }`}
          >
            All ({counts.TOTAL})
          </button>
          <button
            type="button"
            onClick={() => setFilterSeverity('ERROR')}
            className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
              filterSeverity === 'ERROR' ? 'border border-rose-300 bg-rose-100 text-rose-800' : 'bg-slate-100 text-rose-700 hover:bg-rose-50'
            }`}
          >
            Errors ({counts.ERROR})
          </button>
          <button
            type="button"
            onClick={() => setFilterSeverity('WARNING')}
            className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
              filterSeverity === 'WARNING' ? 'border border-amber-300 bg-amber-100 text-amber-800' : 'bg-slate-100 text-amber-700 hover:bg-amber-50'
            }`}
          >
            Warnings ({counts.WARNING})
          </button>
          <button
            type="button"
            onClick={() => setFilterSeverity('INFO')}
            className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
              filterSeverity === 'INFO' ? 'border border-blue-300 bg-blue-100 text-blue-800' : 'bg-slate-100 text-blue-700 hover:bg-blue-50'
            }`}
          >
            Info ({counts.INFO})
          </button>
        </div>
      </div>

      {/* Findings List */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <CheckCircle2 className="h-10 w-10 text-emerald-500" />
          <p className="mt-2 text-sm font-semibold text-slate-800">
            {counts.TOTAL === 0 ? 'No validation findings were reported.' : 'No findings match this filter.'}
          </p>
          {counts.TOTAL === 0 && (
            <p className="text-xs text-slate-500">The available validation checks completed without reported issues.</p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(({ item, index }) => {
            const isSelected = selectedFindingIndex === index
            const status = reviewStatus[index]

            return (
              <article
                key={`${item.category}-${item.location}-${index}`}
                className={`rounded-xl border p-3.5 transition ${
                  isSelected
                    ? 'border-blue-500 bg-blue-50/70 shadow-sm ring-1 ring-blue-300'
                    : 'border-slate-200 bg-slate-50/70'
                }`}
              >
                <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
                  <button
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() => onSelectFinding?.(index, item)}
                    className="flex min-w-0 flex-wrap items-center gap-2 text-left"
                  >
                    {severityBadge(item.severity)}
                    <span className="rounded bg-slate-200 px-2 py-0.5 font-mono text-xs font-bold text-slate-800">
                      {item.category}
                    </span>
                    <span className="break-words text-xs font-medium text-slate-500">{item.location}</span>
                  </button>

                  <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                    {status === 'accepted' && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                        <CheckCircle className="h-3 w-3" /> Accepted
                      </span>
                    )}
                    {status === 'rejected' && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-200 px-2 py-0.5 text-xs font-semibold text-slate-600">
                        <XCircle className="h-3 w-3" /> Dismissed
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-2.5 space-y-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs font-semibold text-slate-600">{item.field}:</span>
                    <span className="font-mono text-xs font-bold text-amber-800">{item.masked_value}</span>
                  </div>
                  <p className="text-sm font-medium text-slate-800">{item.explanation}</p>
                </div>

                {item.suggestion && (
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white p-2.5 text-xs">
                    <div className="flex items-center gap-1.5 text-blue-800">
                      <span className="font-bold text-blue-900">Action:</span>
                      <span>{item.suggestion}</span>
                    </div>

                    {/* Human in the loop review actions */}
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          onAcceptSuggestion?.(index, item)
                        }}
                        className={`rounded-md px-2.5 py-1 text-xs font-semibold transition shadow-sm ${
                          status === 'accepted'
                            ? 'bg-emerald-600 text-white'
                            : 'border border-slate-300 bg-white text-slate-700 hover:border-emerald-600 hover:text-emerald-700'
                        }`}
                      >
                        Accept
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          onRejectSuggestion?.(index, item)
                        }}
                        className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${
                          status === 'rejected'
                            ? 'bg-slate-300 text-slate-800'
                            : 'border border-slate-300 bg-white text-slate-600 hover:border-slate-400 hover:text-slate-900'
                        }`}
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
