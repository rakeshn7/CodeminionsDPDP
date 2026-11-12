import { AlertTriangle, CheckCircle2, FileCode2, Loader2, RefreshCw } from 'lucide-react'
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

  const loadResults = async (showLoading = false) => {
    if (showLoading) setStatus('loading')
    try {
      const response = await fetch('/evaluation-results.json?t=' + Date.now())
      if (response.status === 404) {
        setStatus('not-evaluated')
        return
      }
      if (!response.ok) throw new Error('Evaluation result request failed')

      const result = await response.json()
      setResults(result)
      setStatus(result.status === 'failed' ? 'failed' : 'completed')
    } catch {
      setStatus('failed')
    }
  }

  useEffect(() => {
    let active = true

    fetch('/evaluation-results.json?t=' + Date.now())
      .then((res) => {
        if (res.status === 404) {
          if (active) setStatus('not-evaluated')
          return null
        }
        if (!res.ok) throw new Error('Evaluation result request failed')
        return res.json()
      })
      .then((result) => {
        if (!result || !active) return
        setResults(result)
        setStatus(result.status === 'failed' ? 'failed' : 'completed')
      })
      .catch(() => {
        if (active) setStatus('failed')
      })

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
          <h2 className="mt-2 text-2xl font-semibold text-white">DPDP Benchmark Dataset Evaluation</h2>
          <p className="mt-1 text-sm text-slate-400">
            Automated performance analysis on 50 synthetic Indian enterprise documents across 7 PII categories.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={loadResults}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-medium text-slate-300 hover:border-slate-600 hover:text-white"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Reload Results
          </button>
          <div className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">
            {status === 'loading' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-300" />
            ) : status === 'completed' ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <AlertTriangle className="h-3.5 w-3.5 text-amber-300" />
            )}
            {status === 'loading'
              ? 'Loading evaluation results'
              : status === 'completed'
              ? 'Verified Benchmark Evaluation'
              : 'Evaluation not found'}
          </div>
        </div>
      </div>

      {unavailable && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          <p className="font-medium">No benchmark evaluation results found.</p>
          <p className="mt-2 text-amber-100/80">
            Run the evaluation script to calculate precision, recall, F1, leakage, and reinsertion metrics on the 50-document synthetic dataset:
          </p>
          <pre className="mt-2 rounded-lg bg-slate-950 p-2 font-mono text-xs text-amber-200">
            python evaluation/evaluate.py
          </pre>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {metricCards.map(([title, key]) => (
          <div key={key} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel transition hover:border-slate-700">
            <p className="text-sm text-slate-400">{title}</p>
            <p className="mt-3 text-2xl font-semibold text-white">
              {status === 'completed' ? displayMetric(summary[key], key) : '—'}
            </p>
          </div>
        ))}
      </div>

      {/* Entity Metrics Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-lg font-semibold text-white">Per-Entity Detection Performance</h3>
            <p className="text-xs text-slate-400">Exact span & type matching: (type, start_offset, end_offset)</p>
          </div>
          {results?.matching_method && (
            <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-blue-300">
              {results.matching_method}
            </span>
          )}
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
                <th className="px-4 py-3 font-medium">F1 Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-900 text-slate-200">
              {status === 'completed' && entityMetrics.length ? (
                entityMetrics.map((metric) => (
                  <tr key={metric.name} className="hover:bg-slate-800/40">
                    <td className="px-4 py-3 font-mono font-medium text-white">{metric.name}</td>
                    <td className="px-4 py-3 text-emerald-300">{metric.tp ?? '—'}</td>
                    <td className="px-4 py-3 text-rose-300">{metric.fp ?? '—'}</td>
                    <td className="px-4 py-3 text-amber-300">{metric.fn ?? '—'}</td>
                    <td className="px-4 py-3 font-semibold text-slate-100">{displayMetric(metric.precision, 'precision')}</td>
                    <td className="px-4 py-3 font-semibold text-slate-100">{displayMetric(metric.recall, 'recall')}</td>
                    <td className="px-4 py-3 font-semibold text-blue-300">{displayMetric(metric.f1, 'f1')}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    {status === 'loading' ? 'Checking for evaluation results…' : 'Per-entity results are not available.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {status === 'completed' && results?.source && (
          <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
            <FileCode2 className="h-4 w-4 text-slate-500" />
            <span>Benchmark source: {results.source}</span>
          </div>
        )}
      </div>

      {/* Visualizations with Recharts */}
      <MetricCharts
        requestTrend={Array.isArray(results?.request_trend) ? results.request_trend : []}
        piiByCategory={Array.isArray(results?.pii_by_category) ? results.pii_by_category : []}
        entityMetrics={status === 'completed' ? entityMetrics : []}
      />
    </div>
  )
}
