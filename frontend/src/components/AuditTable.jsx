import { Fragment } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

function listValues(values = []) {
  return values.length ? values.join(', ') : 'None'
}

export default function AuditTable({
  rows = [],
  details = {},
  detailLoadingId,
  expandedId,
  onRequestClick,
  searchQuery,
  statusFilter,
}) {
  const filteredRows = rows.filter((row) => {
    const matchesQuery = !searchQuery
      || row.request_id?.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = !statusFilter || row.status === statusFilter
    return matchesQuery && matchesStatus
  })

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-50 text-slate-700">
            <tr>
              <th className="px-4 py-3 font-semibold">Request ID</th>
              <th className="px-4 py-3 font-semibold">Timestamp</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Provider / model</th>
              <th className="px-4 py-3 font-semibold">Entity counts</th>
              <th className="px-4 py-3 font-semibold">Leakage verified</th>
              <th className="px-4 py-3 font-semibold">Latency</th>
              <th className="px-4 py-3 font-semibold">Restoration</th>
              <th className="px-4 py-3 font-semibold" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
            {filteredRows.length ? filteredRows.map((row) => {
              const expanded = expandedId === row.request_id
              const detail = details[row.request_id]
              const restoration = detail?.restoration_status || row.restoration_status || {}
              const events = detail?.security_events || row.security_events || []
              const entityCounts = row.entity_counts || {}

              return (
                <Fragment key={row.request_id}>
                  <tr className="align-top transition-colors hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono text-xs font-medium text-blue-600">
                      <button type="button" className="underline decoration-dotted underline-offset-4 hover:text-blue-800" onClick={() => onRequestClick(row.request_id)}>
                        {row.request_id}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">{new Date(row.timestamp).toLocaleString()}</td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        row.status === 'SUCCESS' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}>
                        {row.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      {[row.provider, row.model].filter(Boolean).join(' / ') || 'Not available'}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      {Object.entries(entityCounts).map(([type, count]) => `${type}: ${count}`).join(', ') || 'None'}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        row.leakage_verified ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {row.leakage_verified ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs font-medium text-slate-700">{row.processing_latency_ms} ms</td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      {listValues(restoration.restored)}
                    </td>
                    <td className="px-4 py-3">
                      <button type="button" onClick={() => onRequestClick(row.request_id)} className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800">
                        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        {expanded ? 'Hide' : 'Details'}
                      </button>
                    </td>
                  </tr>
                  {expanded && (
                    <tr className="bg-slate-50/80">
                      <td colSpan={9} className="px-4 py-4">
                        {detailLoadingId === row.request_id ? (
                          <p className="text-sm text-slate-500">Loading request details…</p>
                        ) : (
                          <div className="grid gap-3 lg:grid-cols-2">
                            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
                              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Restoration status</p>
                              <ul className="space-y-2 text-xs text-slate-700">
                                <li><strong className="text-slate-900">Restored:</strong> {listValues(restoration.restored)}</li>
                                <li><strong className="text-slate-900">Missing:</strong> {listValues(restoration.missing)}</li>
                                <li><strong className="text-slate-900">Unknown:</strong> {listValues(restoration.unknown)}</li>
                                <li><strong className="text-slate-900">Malformed:</strong> {listValues(restoration.malformed)}</li>
                              </ul>
                            </div>
                            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
                              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Security events</p>
                              {events.length ? (
                                <ul className="space-y-2 text-xs text-slate-700">
                                  {events.map((event, index) => (
                                    <li key={`${event.event_type}-${event.timestamp}-${index}`}>
                                      <span className="font-semibold text-slate-900">{event.event_type}</span> · {new Date(event.timestamp).toLocaleString()}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="text-xs text-slate-500">No security events recorded.</p>
                              )}
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            }) : (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-slate-500">
                  {rows.length ? 'No records match the current filters.' : 'No audit records are available.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
