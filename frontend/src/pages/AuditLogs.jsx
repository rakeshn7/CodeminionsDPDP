import { Search, ShieldAlert, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import AuditTable from '../components/AuditTable'
import { getAudit, getAuditById, getSafeApiError } from '../services/api'

export default function AuditLogs() {
  const [rows, setRows] = useState([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortOrder, setSortOrder] = useState('desc')
  const [expandedId, setExpandedId] = useState(null)
  const [details, setDetails] = useState({})
  const [loading, setLoading] = useState(true)
  const [detailLoadingId, setDetailLoadingId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    getAudit()
      .then((response) => {
        if (!active) return
        if (!Array.isArray(response?.records)) {
          setError('The backend returned an unexpected audit response.')
          return
        }
        setRows(response.records)
      })
      .catch((requestError) => {
        if (active) setError(getSafeApiError(requestError, { audit: true }))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  const sortedRows = [...rows].sort((a, b) => {
    const aTime = new Date(a.timestamp).getTime()
    const bTime = new Date(b.timestamp).getTime()
    return sortOrder === 'asc' ? aTime - bTime : bTime - aTime
  })

  const handleRequestClick = async (requestId) => {
    if (expandedId === requestId) {
      setExpandedId(null)
      return
    }

    setExpandedId(requestId)
    if (details[requestId]) return

    setDetailLoadingId(requestId)
    setError('')
    try {
      const detail = await getAuditById(requestId)
      setDetails((current) => ({ ...current, [requestId]: detail }))
    } catch (requestError) {
      setError(getSafeApiError(requestError, { audit: true }))
    } finally {
      setDetailLoadingId(null)
    }
  }

  const verifiedCount = rows.filter((row) => row.status === 'success' && row.leakage_verified).length
  const blockedCount = rows.filter((row) => row.status === 'blocked').length
  const averageLatency = rows.length
    ? Math.round(rows.reduce((sum, row) => sum + Number(row.processing_latency_ms || 0), 0) / rows.length)
    : null

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500 font-semibold">Audit Logs</p>
          <h2 className="mt-1 text-2xl font-bold text-slate-900">Protected Request Metadata</h2>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm">
          Requires backend audit authorization
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-sm text-amber-800">
          {error}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.25fr_0.65fr_0.4fr]">
        <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by request ID"
            className="w-full border-0 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
          />
        </label>

        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-blue-500 shadow-sm"
        >
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="blocked">Blocked</option>
          <option value="failed">Failed</option>
        </select>

        <select
          value={sortOrder}
          onChange={(event) => setSortOrder(event.target.value)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-blue-500 shadow-sm"
        >
          <option value="desc">Newest first</option>
          <option value="asc">Oldest first</option>
        </select>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between text-sm text-slate-500 font-medium">
            <span>Leakage check verified</span>
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-900">{loading ? '—' : verifiedCount}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between text-sm text-slate-500 font-medium">
            <span>Blocked requests</span>
            <ShieldAlert className="h-4 w-4 text-rose-600" />
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-900">{loading ? '—' : blockedCount}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between text-sm text-slate-500 font-medium">
            <span>Average latency</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            {loading || averageLatency == null ? 'Not available' : `${averageLatency} ms`}
          </p>
        </div>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500 shadow-sm">
          Loading audit records…
        </div>
      ) : (
        <AuditTable
          rows={sortedRows}
          details={details}
          detailLoadingId={detailLoadingId}
          expandedId={expandedId}
          onRequestClick={handleRequestClick}
          searchQuery={search}
          statusFilter={statusFilter}
        />
      )}
    </div>
  )
}
