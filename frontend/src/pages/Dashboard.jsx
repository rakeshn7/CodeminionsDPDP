import { AlertTriangle, CheckCircle2, Clock3, FileText, ShieldAlert, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getMetrics } from '../services/api'
import MetricCharts from '../components/MetricCharts'
import StatCard from '../components/StatCard'

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let active = true

    const loadMetrics = async () => {
      try {
        const result = await getMetrics()
        if (active) {
          setMetrics(result || null)
          setStatus(result ? 'live' : 'unavailable')
        }
      } catch {
        if (active) setStatus('unavailable')
      }
    }

    loadMetrics()
    return () => {
      active = false
    }
  }, [])

  const requestTrend = Array.isArray(metrics?.requestTrend) ? metrics.requestTrend : []
  const piiByCategory = Array.isArray(metrics?.piiByCategory) ? metrics.piiByCategory : []
  const entityMetrics = Array.isArray(metrics?.entityMetrics) ? metrics.entityMetrics : []
  const gatewayActivity = Array.isArray(metrics?.recent_activity) ? metrics.recent_activity : []
  const hasOutboundCounts = Number.isFinite(metrics?.outbound_requests_passed)
    && Number.isFinite(metrics?.outbound_requests_blocked)
  const outboundTotal = hasOutboundCounts
    ? metrics.outbound_requests_passed + metrics.outbound_requests_blocked
    : 0

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Overview</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Executive dashboard</h2>
        </div>
        <div className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">
          {status === 'live' ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" /> : <AlertTriangle className="h-3.5 w-3.5 text-amber-300" />}
          {status === 'live' ? 'Backend metrics available' : status === 'loading' ? 'Loading backend metrics' : 'Metrics unavailable'}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-5">
        <StatCard title="Total requests processed" value={metrics?.totalRequests ?? '—'} detail="Backend-reported" tone="blue" icon={FileText} />
        <StatCard title="Total PII entities detected" value={metrics?.piiEntitiesDetected ?? '—'} detail="Backend-reported" tone="amber" icon={ShieldAlert} />
        <StatCard title="Outbound leakage incidents" value={metrics?.outboundLeakageIncidents ?? '—'} detail="Backend-reported" tone="red" icon={ShieldAlert} />
        <StatCard title="Average gateway latency" value={metrics?.avgLatencyMs == null ? '—' : `${metrics.avgLatencyMs} ms`} detail="Backend-reported" tone="green" icon={Clock3} />
        <StatCard title="Reinsertion accuracy" value={metrics?.reinsertionAccuracy == null ? '—' : `${metrics.reinsertionAccuracy}%`} detail="Measured evaluation only" tone="blue" icon={ShieldCheck} />
      </div>

      <MetricCharts requestTrend={requestTrend} piiByCategory={piiByCategory} entityMetrics={entityMetrics} />

      <div className="grid gap-5 xl:grid-cols-[1.4fr_0.8fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
          <h3 className="mb-4 text-lg font-semibold text-white">Recent gateway activity</h3>
          {gatewayActivity.length ? <div className="space-y-3">
            {gatewayActivity.map((activity) => (
              <div key={activity.source} className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-950/70 p-3">
                <div className={`mt-1 h-2.5 w-2.5 rounded-full ${activity.state === 'safe' ? 'bg-emerald-400' : activity.state === 'blocked' ? 'bg-rose-400' : 'bg-blue-400'}`} />
                <div className="flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-white">{activity.source}</p>
                    <span className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{activity.time}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-300">{activity.detail}</p>
                </div>
              </div>
            ))}
          </div> : <p className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-400">No backend activity records are available.</p>}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
          <h3 className="mb-4 text-lg font-semibold text-white">Safe vs blocked outbound requests</h3>
          {hasOutboundCounts && outboundTotal > 0 ? <div className="space-y-4">
            <div>
              <div className="mb-2 flex items-center justify-between text-sm text-slate-200">
                <span>Safe outbound</span>
                <span>{Math.round((metrics.outbound_requests_passed / outboundTotal) * 100)}%</span>
              </div>
              <div className="h-2.5 rounded-full bg-slate-800">
                <div className="h-full rounded-full bg-emerald-500" style={{ width: `${(metrics.outbound_requests_passed / outboundTotal) * 100}%` }} />
              </div>
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between text-sm text-slate-200">
                <span>Blocked</span>
                <span>{Math.round((metrics.outbound_requests_blocked / outboundTotal) * 100)}%</span>
              </div>
              <div className="h-2.5 rounded-full bg-slate-800">
                <div className="h-full rounded-full bg-rose-500" style={{ width: `${(metrics.outbound_requests_blocked / outboundTotal) * 100}%` }} />
              </div>
            </div>
          </div> : <p className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-400">Outbound pass/block counts have not been reported by the backend.</p>}
        </div>
      </div>
    </div>
  )
}
