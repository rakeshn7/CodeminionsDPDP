import { Activity, BarChart3, ShieldCheck, Target } from 'lucide-react'
import { useEffect, useState } from 'react'

const defaultEvaluation = {
  summary: {
    total_documents_tested: 50,
    raw_pii_leakage_count: 4,
    placeholder_reinsertion_accuracy: 97.8,
    average_latency_ms: 214,
    min_latency_ms: 128,
    max_latency_ms: 332,
  },
  entity_metrics: [
    { name: 'PERSON', precision: 0.99, recall: 0.97, f1: 0.98 },
    { name: 'AADHAAR', precision: 0.98, recall: 0.96, f1: 0.97 },
    { name: 'PAN', precision: 0.97, recall: 0.95, f1: 0.96 },
    { name: 'GSTIN', precision: 0.94, recall: 0.92, f1: 0.93 },
    { name: 'VOTER_ID', precision: 0.93, recall: 0.91, f1: 0.92 },
    { name: 'PASSPORT', precision: 0.91, recall: 0.89, f1: 0.90 },
    { name: 'ADDRESS', precision: 0.96, recall: 0.94, f1: 0.95 },
  ],
  privacy_metrics: {
    outbound_requests_blocked: 12,
    outbound_requests_passed: 38,
    raw_pii_leakage_count: 4,
    placeholder_reinsertion_accuracy: 97.8,
  },
  source: 'synthetic benchmark snapshot',
}

export default function Evaluation() {
  const [results, setResults] = useState(defaultEvaluation)
  const [loaded, setLoaded] = useState('demo')

  useEffect(() => {
    const loadResults = async () => {
      try {
        const response = await fetch('/evaluation-results.json')
        if (!response.ok) throw new Error('results file not found')
        const json = await response.json()
        setResults(json)
        setLoaded('live')
      } catch (error) {
        console.warn('Evaluation results file missing; using demo metrics.', error)
        setLoaded('demo')
      }
    }

    loadResults()
  }, [])

  const summaryCards = [
    { title: 'Total documents tested', value: results.summary.total_documents_tested, detail: 'Synthetic benchmark suite', icon: Activity },
    { title: 'Raw PII leakage count', value: results.summary.raw_pii_leakage_count, detail: 'Outbound payload inspection', icon: ShieldCheck },
    { title: 'Reinsertion accuracy', value: `${results.summary.placeholder_reinsertion_accuracy}%`, detail: 'Placeholder restoration quality', icon: Target },
    { title: 'Average latency', value: `${results.summary.average_latency_ms} ms`, detail: 'Gateway overhead per request', icon: BarChart3 },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Evaluation & Metrics</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Privacy detection and performance benchmark</h2>
        </div>
        <div className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">
          {loaded === 'live' ? 'Live evaluation results loaded' : 'Demo evaluation snapshot'}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map(({ title, value, detail, icon: Icon }) => (
          <div key={title} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">{title}</span>
              <Icon className="h-4 w-4 text-blue-300" />
            </div>
            <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
            <p className="mt-2 text-xs text-slate-400">{detail}</p>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
        <h3 className="mb-4 text-lg font-semibold text-white">PII detection performance</h3>
        <div className="overflow-hidden rounded-xl border border-slate-700">
          <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
            <thead className="bg-slate-950 text-slate-300">
              <tr>
                <th className="px-4 py-3">Entity type</th>
                <th className="px-4 py-3">Precision</th>
                <th className="px-4 py-3">Recall</th>
                <th className="px-4 py-3">F1</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-900 text-slate-200">
              {results.entity_metrics.map((metric) => (
                <tr key={metric.name}>
                  <td className="px-4 py-3 font-medium text-white">{metric.name}</td>
                  <td className="px-4 py-3">{metric.precision.toFixed(2)}</td>
                  <td className="px-4 py-3">{metric.recall.toFixed(2)}</td>
                  <td className="px-4 py-3">{metric.f1.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
          <h3 className="mb-3 text-lg font-semibold text-white">Privacy performance</h3>
          <div className="space-y-3 text-sm text-slate-200">
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Raw PII leakage count</span>
              <span>{results.privacy_metrics.raw_pii_leakage_count}</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Outbound requests blocked</span>
              <span>{results.privacy_metrics.outbound_requests_blocked}</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Outbound requests passed</span>
              <span>{results.privacy_metrics.outbound_requests_passed}</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Placeholder reinsertion accuracy</span>
              <span>{results.privacy_metrics.placeholder_reinsertion_accuracy}%</span>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
          <h3 className="mb-3 text-lg font-semibold text-white">Performance</h3>
          <div className="space-y-3 text-sm text-slate-200">
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Average gateway latency</span>
              <span>{results.summary.average_latency_ms} ms</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Minimum latency</span>
              <span>{results.summary.min_latency_ms} ms</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Maximum latency</span>
              <span>{results.summary.max_latency_ms} ms</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Source</span>
              <span>{results.source}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
