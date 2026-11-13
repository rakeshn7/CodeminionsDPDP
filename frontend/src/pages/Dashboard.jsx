import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileText,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'
import { useEffect, useState } from 'react'

import MetricCharts from '../components/MetricCharts'
import StatCard from '../components/StatCard'
import { getMetrics, getSafeApiError } from '../services/api'

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let active = true

    getMetrics()
      .then((result) => {
        if (!active) return
        setMetrics(result)
        setStatus('live')
      })
      .catch((requestError) => {
        if (!active) return
        setError(getSafeApiError(requestError))
        setStatus('unavailable')
      })

    return () => {
      active = false
    }
  }, [refreshKey])

  const available = status === 'live'
  const value = (key) =>
    available && Number.isFinite(metrics?.[key]) ? metrics[key] : 'Not available'
  const riskValue = (level) =>
    available && Number.isFinite(metrics?.risk_distribution?.[level])
      ? metrics.risk_distribution[level]
      : 'Not available'

  return (
    <div className="space-y-6">
      {/* Header and Live indicator */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500 font-semibold">Executive Overview</p>
          <h2 className="mt-1 text-2xl font-bold text-slate-900">Document Privacy & Validation Dashboard</h2>
          <p className="mt-1 text-sm text-slate-600">
            Real-time telemetry aggregated from active gateway audit logs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => {
              setStatus('loading')
              setRefreshKey((k) => k + 1)
            }}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50"
          >
            <RefreshCw className="h-3.5 w-3.5 text-slate-500" />
            Refresh Metrics
          </button>

          <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm">
            {available ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            ) : (
              <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
            )}
            {status === 'loading'
              ? 'Loading metrics...'
              : available
              ? 'Live Backend Telemetry'
              : 'Backend Metrics Unavailable'}
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-sm text-amber-800">
          {error}
        </div>
      )}

      {/* Primary KPI StatCards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Total Requests Processed"
          value={value('total_requests')}
          detail="Live audited document operations"
          tone="blue"
          icon={FileText}
        />
        <StatCard
          title="Total PII Entities Redacted"
          value={value('total_pii_detected')}
          detail="Indian identifiers & personal data protected"
          tone="purple"
          icon={ShieldCheck}
        />
        <StatCard
          title="Documents Flagged with Errors"
          value={value('documents_with_errors')}
          detail="Validation inconsistencies or policy blocks"
          tone="amber"
          icon={ShieldAlert}
        />
        <StatCard
          title="Average Processing Latency"
          value={
            available && Number.isFinite(metrics?.average_processing_latency_ms)
              ? `${metrics.average_processing_latency_ms} ms`
              : 'Not available'
          }
          detail="End-to-end detection & validation runtime"
          tone="green"
          icon={Clock3}
        />
      </div>

      {/* Real Live Charts from Audit Records */}
      <MetricCharts
        requestTrend={metrics?.request_trend || []}
        piiByCategory={metrics?.pii_by_category || []}
        entityMetrics={[]}
      />

      {/* Risk and Operational Health Breakdown */}
      <div className="grid gap-5 md:grid-cols-2">
        {/* Risk Distribution Card */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
            <ShieldAlert className="h-5 w-5 text-amber-600" />
            <h3 className="font-semibold text-slate-900">Privacy Risk Distribution</h3>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-3 text-center">
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-3">
              <p className="text-xs font-semibold text-rose-700">High Risk</p>
              <p className="mt-1 text-2xl font-bold text-rose-800">
                {riskValue('High')}
              </p>
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
              <p className="text-xs font-semibold text-amber-700">Medium Risk</p>
              <p className="mt-1 text-2xl font-bold text-amber-800">
                {riskValue('Medium')}
              </p>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
              <p className="text-xs font-semibold text-emerald-700">Low Risk</p>
              <p className="mt-1 text-2xl font-bold text-emerald-800">
                {riskValue('Low')}
              </p>
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Risk estimates are based on the request metadata recorded by the backend.
          </p>
        </div>

        {/* Operational Guardrails Card */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
            <ShieldCheck className="h-5 w-5 text-emerald-600" />
            <h3 className="font-semibold text-slate-900">Operational Details</h3>
          </div>
          <div className="mt-4 space-y-2.5 text-xs text-slate-700">
            <div className="flex items-center justify-between rounded-lg bg-slate-50 p-2.5 border border-slate-100">
              <span>Outbound verification:</span>
              <span className="font-semibold text-slate-600">Not reported by metrics API</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-slate-50 p-2.5 border border-slate-100">
              <span>Raw input logging status:</span>
              <span className="font-semibold text-slate-600">Not reported by metrics API</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-slate-50 p-2.5 border border-slate-100">
              <span>Script coverage:</span>
              <span className="font-semibold text-slate-600">Not reported by metrics API</span>
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Review authenticated audit records for per-request processing details.
          </p>
        </div>
      </div>
    </div>
  )
}
