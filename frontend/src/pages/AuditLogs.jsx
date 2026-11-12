import { Search, ShieldAlert, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import AuditTable from '../components/AuditTable'
import { defaultAuditData } from '../data/samples'
import { getAudit, getAuditById } from '../services/api'

export default function AuditLogs() {
  const [rows, setRows] = useState(defaultAuditData)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortOrder, setSortOrder] = useState('desc')
  const [expandedId, setExpandedId] = useState(null)

  useEffect(() => {
    let active = true

    const loadAuditData = async () => {
      try {
        const response = await getAudit()
        if (active && Array.isArray(response)) {
          setRows(response)
        }
      } catch (error) {
        console.warn('Audit API is unavailable; using demo audit logs.', error)
      }
    }

    loadAuditData()
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
    try {
      const detail = await getAuditById(requestId)
      if (detail) {
        setExpandedId(requestId)
      }
    } catch (error) {
      console.warn('Request detail fetch failed:', error)
      setExpandedId(requestId)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Audit Logs</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Request history and leak verification</h2>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.25fr_0.65fr_0.4fr]">
        <label className="flex items-center gap-3 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-300">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by request ID"
            className="w-full border-0 bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
          />
        </label>

        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
          className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-blue-500"
        >
          <option value="">Filter by status</option>
          <option value="safe">Safe</option>
          <option value="blocked">Blocked</option>
          <option value="partial">Partial</option>
        </select>

        <select
          value={sortOrder}
          onChange={(event) => setSortOrder(event.target.value)}
          className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-blue-500"
        >
          <option value="desc">Newest first</option>
          <option value="asc">Oldest first</option>
        </select>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span>Verified safe</span>
            <ShieldCheck className="h-4 w-4 text-emerald-300" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-white">{rows.filter((row) => row.leakage_status === 'safe').length}</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span>Blocked</span>
            <ShieldAlert className="h-4 w-4 text-rose-300" />
          </div>
          <p className="mt-2 text-2xl font-semibold text-white">{rows.filter((row) => row.leakage_status === 'blocked').length}</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span>Average latency</span>
          </div>
          <p className="mt-2 text-2xl font-semibold text-white">{Math.round(rows.reduce((sum, row) => sum + Number(row.latency_ms || 0), 0) / Math.max(rows.length, 1))} ms</p>
        </div>
      </div>

      <AuditTable
        rows={sortedRows}
        expandedId={expandedId}
        onToggleExpand={(requestId) => setExpandedId((current) => current === requestId ? null : requestId)}
        searchQuery={search}
        statusFilter={statusFilter}
        onRequestClick={handleRequestClick}
      />
    </div>
  )
}
