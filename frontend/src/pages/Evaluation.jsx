import { AlertTriangle, CheckCircle2, FileCode2, Loader2, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import MetricCharts from '../components/MetricCharts'

async function fetchEvaluationResults() {
  const response = await fetch(`/evaluation-results.json?t=${Date.now()}`)
  if (response.status === 404) return null
  if (!response.ok) throw new Error('Evaluation result request failed')
  return response.json()
}

const metricCards = [
  ['Total documents tested', 'total_documents_tested'],
  ['Documents succeeded', 'documents_succeeded'],
  ['Documents failed', 'documents_failed'],
  ['Ground-truth entities', 'ground_truth_entities'],
  ['Detected entities', 'detected_entities'],
  ['Precision', 'precision'],
  ['Recall', 'recall'],
  ['F1-score', 'f1'],
  ['Documents flagged for raw PII leakage', 'raw_pii_leakage_count'],
  ['Reinsertion accuracy', 'reinsertion_accuracy'],
  ['Average processing latency', 'average_latency_ms'],
]

function displayMetric(value, key) {
  if (value == null || !Number.isFinite(value)) return '—'
  if (key === 'average_latency_ms') return `${value} ms`
  if (key === 'reinsertion_accuracy') return `${value.toFixed(2)}%`
  if (['precision', 'recall', 'f1'].includes(key)) {
    return `${(value * 100).toFixed(2)}%`
  }
  return value
}

export default function Evaluation() {
  const [results, setResults] = useState(null)
  const [status, setStatus] = useState('loading')
  const [reloadVersion, setReloadVersion] = useState(0)

  useEffect(() => {
    let active = true

    fetchEvaluationResults()
      .then((result) => {
        if (!active) return
        setResults(result)
        setStatus(
          result === null
            ? 'not-evaluated'
            : result.status === 'completed'
            ? 'completed'
            : 'failed',
        )
      })
      .catch(() => {
        if (!active) return
        setResults(null)
        setStatus('failed')
      })

    return () => {
      active = false
    }
  }, [reloadVersion])

  const summary = results?.summary || {}
  const entityMetrics = Array.isArray(results?.entity_metrics) ? results.entity_metrics : []
  const isReference = results?.evaluation_mode === 'reference_simulation'
  const isLive = results?.evaluation_mode === 'live_backend'

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Evaluation & Metrics</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">DPDP Benchmark Dataset Evaluation</h2>
          <p className="mt-1 text-sm text-slate-600">
            Synthetic corpus: 50 Indian enterprise documents across 7 PII categories. This page displays the selected run's saved result.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => {
              setStatus('loading')
              setReloadVersion((version) => version + 1)
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 hover:text-slate-900"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Reload Results
          </button>
          <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm">
            {status === 'loading' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" />
            ) : status === 'completed' ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            ) : (
              <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
            )}
            {status === 'loading'
              ? 'Loading evaluation results'
              : status === 'completed'
              ? isReference
                ? 'Reference simulation'
                : isLive
                ? 'Live evaluation complete'
                : 'Evaluation result'
              : status === 'failed'
              ? results ? 'Evaluation incomplete' : 'Results unavailable'
              : 'Evaluation not found'}
          </div>
        </div>
      </div>

      {isReference && results && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/80 p-4 text-sm text-blue-900 shadow-xs">
          <p className="font-semibold">Reference simulation — not live backend measurements.</p>
          <p className="mt-2 text-blue-800">
            The reference simulator uses dataset regexes and copies PERSON and ADDRESS ground-truth
            spans. Its scores do not measure backend detector accuracy, and it makes no Groq requests.
          </p>
        </div>
      )}

      {status === 'failed' && results && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-sm text-rose-900 shadow-xs">
          <p className="font-semibold">Evaluation did not complete successfully.</p>
          <p className="mt-2 text-rose-800">
            {summary.documents_failed ?? results?.failed_documents?.length ?? 0} document(s) failed.
            No reference results were substituted for failed live requests.
          </p>
        </div>
      )}

      {status === 'failed' && !results && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 text-sm text-amber-900 shadow-xs">
          Evaluation result data could not be loaded. No evaluation or provider request was started by this page.
        </div>
      )}

      {status === 'not-evaluated' && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 text-sm text-amber-900 shadow-xs">
          <p className="font-semibold">No benchmark evaluation results found.</p>
          <p className="mt-2 text-amber-800">
            Opening this page does not run evaluation or call the provider. Run the reference
            simulator for local behavior, or explicitly opt in to a limited live run:
          </p>
          <pre className="mt-2 rounded-lg border border-slate-200 bg-slate-100 p-2.5 font-mono text-xs text-slate-800">
            python evaluation/evaluate.py --mode reference{'\n'}
            python evaluation/evaluate.py --mode live --limit 5 --confirm-live
          </pre>
          <p className="mt-2 text-amber-800">
            Live mode sends up to the selected number of synthetic documents through the backend
            and may make that many Groq requests.
          </p>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {metricCards.map(([title, key]) => (
          <div key={key} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300">
            <p className="text-sm font-medium text-slate-500">{title}</p>
            <p className="mt-3 text-2xl font-bold text-slate-900">
              {status === 'completed' ? displayMetric(summary[key], key) : '—'}
            </p>
          </div>
        ))}
      </div>

      {/* Entity Metrics Table */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Per-Entity Detection Metrics</h3>
            <p className="text-xs text-slate-500">Exact span & type matching: (type, start_offset, end_offset)</p>
          </div>
          {results?.matching_method && (
            <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
              {results.matching_method}
            </span>
          )}
        </div>
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-slate-700">
              <tr>
                <th className="px-4 py-3 font-semibold">Entity type</th>
                <th className="px-4 py-3 font-semibold">TP</th>
                <th className="px-4 py-3 font-semibold">FP</th>
                <th className="px-4 py-3 font-semibold">FN</th>
                <th className="px-4 py-3 font-semibold">Precision</th>
                <th className="px-4 py-3 font-semibold">Recall</th>
                <th className="px-4 py-3 font-semibold">F1 Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
              {status === 'completed' && entityMetrics.length ? (
                entityMetrics.map((metric) => (
                  <tr key={metric.name} className="transition-colors hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono font-medium text-slate-900">{metric.name}</td>
                    <td className="px-4 py-3 font-medium text-emerald-700">{metric.tp ?? '—'}</td>
                    <td className="px-4 py-3 font-medium text-rose-700">{metric.fp ?? '—'}</td>
                    <td className="px-4 py-3 font-medium text-amber-700">{metric.fn ?? '—'}</td>
                    <td className="px-4 py-3 font-semibold text-slate-900">{displayMetric(metric.precision, 'precision')}</td>
                    <td className="px-4 py-3 font-semibold text-slate-900">{displayMetric(metric.recall, 'recall')}</td>
                    <td className="px-4 py-3 font-semibold text-blue-600">{displayMetric(metric.f1, 'f1')}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    {status === 'loading' ? 'Checking for evaluation results…' : 'Per-entity results are not available.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {results?.source && (
          <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
            <FileCode2 className="h-4 w-4 text-slate-400" />
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
