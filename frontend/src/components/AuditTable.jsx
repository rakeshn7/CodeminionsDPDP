import { Fragment } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

export default function AuditTable({ rows = [], expandedId, onToggleExpand, searchQuery, statusFilter, onRequestClick }) {
  const filteredRows = rows.filter((row) => {
    const matchesQuery = !searchQuery || row.request_id.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = !statusFilter || row.leakage_status === statusFilter
    return matchesQuery && matchesStatus
  })

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80 shadow-panel">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
          <thead className="bg-slate-950 text-slate-300">
            <tr>
              <th className="px-4 py-3 font-medium">Request ID</th>
              <th className="px-4 py-3 font-medium">Timestamp</th>
              <th className="px-4 py-3 font-medium">External model</th>
              <th className="px-4 py-3 font-medium">Entity types</th>
              <th className="px-4 py-3 font-medium">Leakage</th>
              <th className="px-4 py-3 font-medium">Latency</th>
              <th className="px-4 py-3 font-medium">Restoration</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-900 text-slate-200">
            {filteredRows.length ? filteredRows.map((row) => {
              const expanded = expandedId === row.request_id
              return (
                <Fragment key={row.request_id}>
                  <tr className="align-top hover:bg-slate-950/60">
                    <td className="px-4 py-3 font-mono text-xs text-blue-200">
                      <button type="button" className="underline decoration-dotted underline-offset-4" onClick={() => onRequestClick(row.request_id)}>
                        {row.request_id}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">{new Date(row.timestamp).toLocaleString()}</td>
                    <td className="px-4 py-3 text-xs text-slate-300">{row.external_model}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        {(row.entity_types || []).map((entity, index) => (
                          <span key={`${row.request_id}-${entity}-${index}`} className="rounded-full border border-slate-600 bg-slate-800 px-2 py-1 text-[10px] uppercase tracking-wide text-slate-200">
                            {entity}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full border px-2 py-1 text-[10px] font-medium ${row.leakage_status === 'blocked' ? 'border-red-500/30 bg-red-500/10 text-red-200' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'}`}>
                        {row.leakage_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">{row.latency_ms} ms</td>
                    <td className="px-4 py-3 text-xs text-slate-300">{row.restoration_status}</td>
                    <td className="px-4 py-3">
                      <button type="button" onClick={() => onToggleExpand(row.request_id)} className="inline-flex items-center gap-1 text-xs text-blue-200">
                        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />} {expanded ? 'Hide' : 'Details'}
                      </button>
                    </td>
                  </tr>
                  {expanded && (
                    <tr className="bg-slate-950/80">
                      <td colSpan={8} className="px-4 py-4">
                        <div className="grid gap-3 lg:grid-cols-2">
                          <div className="rounded-xl border border-slate-700 bg-slate-900 p-3">
                            <p className="mb-2 text-xs uppercase tracking-[0.22em] text-slate-400">Sanitized outbound payload</p>
                            <p className="text-xs leading-6 text-slate-200">{row.sanitized_payload}</p>
                          </div>
                          <div className="rounded-xl border border-slate-700 bg-slate-900 p-3">
                            <p className="mb-2 text-xs uppercase tracking-[0.22em] text-slate-400">Status summary</p>
                            <ul className="space-y-2 text-xs text-slate-200">
                              <li>Leakage verification: {row.leakage_status}</li>
                              <li>Restoration: {row.restoration_status}</li>
                              <li>Processing latency: {row.latency_ms} ms</li>
                            </ul>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            }) : (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-slate-400">No records match the current filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
