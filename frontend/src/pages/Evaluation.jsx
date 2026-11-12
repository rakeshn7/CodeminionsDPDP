import { AlertTriangle, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import MetricCharts from '../components/MetricCharts'

const metricCards = [
  ['Total documents tested', 'total_documents_tested'],
  ['Ground-truth entities', 'ground_truth_entities'],
  ['Detected entities', 'detected_entities'],
  ['Precision', 'precision'],
  ['Recall', 'recall'],
  ['F1-score', 'f1'],
  ['Confirmed outbound PII leakage', 'raw_pii_leakage_count'],
  ['Reinsertion accuracy', 'reinsertion_accuracy'],
  ['Average processing latency', 'average_latency_ms'],
]

function displayMetric(value, key) {
  if (value == null || !Number.isFinite(value)) return '—'
  if (key === 'average_latency_ms') return `${value} ms`
  if (['precision', 'recall', 'f1', 'reinsertion_accuracy'].includes(key)) {
    return `${(value * 100).toFixed(2)}%`
  }
  return value
}

export default function Evaluation() {
  const [results, setResults] = useState(null)
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let active = true

    const loadResults = async () => {
      try {
        const response = await fetch('/evaluation-results.json')
        if (response.status === 404) {
          if (active) setStatus('not-evaluated')
          return
        }
        if (!response.ok) throw new Error('Evaluation result request failed')
        if (!response.headers.get('content-type')?.includes('application/json')) {
          if (active) setStatus('not-evaluated')
          return
        }

        const result = await response.json()
        if (active) {
          setResults(result)
          setStatus(result.status === 'failed' ? 'failed' : result.status === 'completed' ? 'completed' : 'not-evaluated')
        }
      } catch {
        if (active) setStatus('failed')
      }
    }

    loadResults()
    return () => {
      active = false
    }
  }, [])

  const summary = results?.summary || {}
  const entityMetrics = Array.isArray(results?.entity_metrics) ? results.entity_metrics : []
  const unavailable = status === 'not-evaluated' || status === 'failed'

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Evaluation & Metrics</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Organizer dataset evaluation</h2>
        </div>
        <div className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">
          {status === 'loading' ? <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-300" /> : <AlertTriangle className="h-3.5 w-3.5 text-amber-300" />}
          {status === 'loading' ? 'Loading evaluation results' : status === 'completed' ? 'Evaluation completed' : status === 'failed' ? 'Evaluation failed' : 'Not yet evaluated'}
        </div>
      </div>

      {unavailable && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          <p className="font-medium">Ground-truth labels unavailable; no organizer corpus has been supplied.</p>
          <p className="mt-2 text-amber-100/80">
            The provided MeitY and Gazette links are regulatory references, and the Presidio page describes recognizers. They do not contain annotated PII test documents. No precision, recall, leakage, reinsertion, or latency results are reported until real documents are processed through the backend and compared with ground truth.
          </p>
          {status === 'failed' && <p className="mt-2">The evaluation result could not be loaded. Check the evaluation output and try again.</p>}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {metricCards.map(([title, key]) => (
          <div key={key} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <p className="text-sm text-slate-400">{title}</p>
            <p className="mt-3 text-2xl font-semibold text-white">
              {status === 'completed' ? displayMetric(summary[key], key) : '—'}
            </p>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-lg font-semibold text-white">Per-entity detection results</h3>
          {results?.matching_method && <span className="text-xs text-slate-400">Matching: {results.matching_method}</span>}
        </div>
        <div className="overflow-x-auto rounded-xl border border-slate-700">
          <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
            <thead className="bg-slate-950 text-slate-300">
              <tr>
                <th className="px-4 py-3 font-medium">Entity type</th>
                <th className="px-4 py-3 font-medium">TP</th>
                <th className="px-4 py-3 font-medium">FP</th>
                <th className="px-4 py-3 font-medium">FN</th>
                <th className="px-4 py-3 font-medium">Precision</th>
                <th className="px-4 py-3 font-medium">Recall</th>
                <th className="px-4 py-3 font-medium">F1</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-900 text-slate-200">
              {status === 'completed' && entityMetrics.length ? entityMetrics.map((metric) => (
                <tr key={metric.name}>
                  <td className="px-4 py-3 font-medium text-white">{metric.name}</td>
                  <td className="px-4 py-3">{metric.tp ?? '—'}</td>
                  <td className="px-4 py-3">{metric.fp ?? '—'}</td>
                  <td className="px-4 py-3">{metric.fn ?? '—'}</td>
                  <td className="px-4 py-3">{displayMetric(metric.precision, 'precision')}</td>
                  <td className="px-4 py-3">{displayMetric(metric.recall, 'recall')}</td>
                  <td className="px-4 py-3">{displayMetric(metric.f1, 'f1')}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    {status === 'loading' ? 'Checking for evaluation results…' : 'Per-entity results are not available.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {status === 'completed' && results?.source && <p className="mt-3 text-xs text-slate-400">Source: {results.source}</p>}
      </div>

      <MetricCharts
        requestTrend={Array.isArray(results?.request_trend) ? results.request_trend : []}
        piiByCategory={Array.isArray(results?.pii_by_category) ? results.pii_by_category : []}
        entityMetrics={status === 'completed' ? entityMetrics : []}
      />
    </div>
  )
}
