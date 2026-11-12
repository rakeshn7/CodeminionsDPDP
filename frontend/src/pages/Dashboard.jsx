import { AlertTriangle, CheckCircle2, Clock3, FileText, ShieldAlert, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { defaultMetrics } from '../data/samples'
import { getMetrics } from '../services/api'
import MetricCharts from '../components/MetricCharts'
import StatCard from '../components/StatCard'

export default function Dashboard() {
  const [metrics, setMetrics] = useState(defaultMetrics)
  const [status, setStatus] = useState('demo')

  useEffect(() => {
    let active = true

    const loadMetrics = async () => {
      try {
        const result = await getMetrics()
        if (active && result) {
          setMetrics({
            ...defaultMetrics,
            ...result,
          })
          setStatus('live')
        }
      } catch (error) {
        console.warn('Using demo metrics because the backend is unavailable:', error)
        setStatus('demo')
      }
    }

    loadMetrics()
    return () => {
      active = false
    }
  }, [])

  const entityMetrics = [
    { name: 'PERSON', precision: 0.97, recall: 0.95 },
    { name: 'AADHAAR', precision: 0.98, recall: 0.96 },
    { name: 'PAN', precision: 0.96, recall: 0.94 },
    { name: 'ADDRESS', precision: 0.94, recall: 0.91 },
    { name: 'GSTIN', precision: 0.95, recall: 0.92 },
    { name: 'PASSPORT', precision: 0.93, recall: 0.90 },
  ]

  const gatewayActivity = [
    { source: 'Loan processing', detail: 'Masked 18 identifiers before outbound model call', time: '2 min ago', state: 'safe' },
    { source: 'Insurance claim', detail: 'Blocked high-risk GSTIN transmission', time: '11 min ago', state: 'blocked' },
    { source: 'KYC verification', detail: 'Restored placeholders after local response generation', time: '28 min ago', state: 'restored' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Overview</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Executive dashboard</h2>
        </div>
        <div className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">
          {status === 'live' ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" /> : <AlertTriangle className="h-3.5 w-3.5 text-amber-300" />}
          {status === 'live' ? 'Live backend metrics' : 'Demo metrics only'}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-5">
        <StatCard title="Total requests processed" value={metrics.totalRequests} detail="Across all monitored workloads" tone="blue" icon={FileText} />
        <StatCard title="Total PII entities detected" value={metrics.piiEntitiesDetected} detail="Synthetically or live detected" tone="amber" icon={ShieldAlert} />
        <StatCard title="Outbound leakage incidents" value={metrics.outboundLeakageIncidents} detail="Only verified incidents" tone="red" icon={ShieldAlert} />
        <StatCard title="Average gateway latency" value={`${metrics.avgLatencyMs} ms`} detail="Median routing overhead" tone="green" icon={Clock3} />
        <StatCard title="Reinsertion accuracy" value={`${metrics.reinsertionAccuracy}%`} detail="Placeholder restoration score" tone="blue" icon={ShieldCheck} />
      </div>

      <MetricCharts requestTrend={metrics.requestTrend} piiByCategory={metrics.piiByCategory} entityMetrics={entityMetrics} />

      <div className="grid gap-5 xl:grid-cols-[1.4fr_0.8fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
          <h3 className="mb-4 text-lg font-semibold text-white">Recent gateway activity</h3>
          <div className="space-y-3">
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
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
          <h3 className="mb-4 text-lg font-semibold text-white">Safe vs blocked outbound requests</h3>
          <div className="space-y-4">
            <div>
              <div className="mb-2 flex items-center justify-between text-sm text-slate-200">
                <span>Safe outbound</span>
                <span>84%</span>
              </div>
              <div className="h-2.5 rounded-full bg-slate-800">
                <div className="h-full w-[84%] rounded-full bg-emerald-500" />
              </div>
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between text-sm text-slate-200">
                <span>Blocked</span>
                <span>16%</span>
              </div>
              <div className="h-2.5 rounded-full bg-slate-800">
                <div className="h-full w-[16%] rounded-full bg-rose-500" />
              </div>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-950/70 p-3 text-sm text-slate-300">
              <p className="font-medium text-white">System health</p>
              <p className="mt-2">Protected gateway is operating within baseline leakage thresholds for the current workload.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
