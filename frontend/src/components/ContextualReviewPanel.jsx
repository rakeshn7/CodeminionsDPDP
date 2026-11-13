import { AlertCircle, CheckCircle2, ShieldCheck } from 'lucide-react'

export default function ContextualReviewPanel({ analysis, awaitingEditedReview = false }) {
  const isSuccess = analysis?.status === 'success'
  const isFailed = analysis?.status === 'failed'
  const isSkipped = analysis?.status === 'skipped'
  const findings = Array.isArray(analysis?.findings) ? analysis.findings : []

  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <h3 className="font-semibold text-slate-900">Contextual review</h3>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
            isSuccess
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
              : isFailed
              ? 'border-rose-200 bg-rose-50 text-rose-700'
              : 'border-slate-200 bg-slate-50 text-slate-600'
          }`}
        >
          {isSuccess ? <CheckCircle2 className="h-3.5 w-3.5" /> : null}
          {isFailed ? <AlertCircle className="h-3.5 w-3.5" /> : null}
          {isSuccess
            ? 'Complete'
            : isFailed
            ? 'Unavailable'
            : isSkipped && analysis?.error
            ? 'Skipped for safety'
            : 'Not requested'}
        </span>
      </div>

      <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs leading-relaxed text-emerald-800">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
        <p>
          Personal information detected by local checks is replaced before text is sent for
          external review. Automated detection may not identify every sensitive value.
        </p>
      </div>

      {isFailed && (
        <div role="status" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <p className="font-semibold">Contextual review could not be completed.</p>
          {analysis.error && <p className="mt-1">{analysis.error}</p>}
          <p className="mt-1 text-rose-700">
            Document extraction and local validation results are still available.
          </p>
        </div>
      )}

      {isSkipped && (
        <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <p className="font-semibold">
            {analysis?.error
              ? 'External review was skipped to protect document data.'
              : 'No external contextual review was run.'}
          </p>
          <p className="mt-1 text-amber-800">
            {analysis?.error
              ? analysis.error
              : awaitingEditedReview
              ? 'Review or correct the extracted text, keep “Request external contextual review” enabled, then select “Analyze edited text”.'
              : 'Enable “Request external contextual review” before analyzing the text to receive a provider-generated summary and findings.'}
          </p>
        </div>
      )}

      {isSuccess && (
        <div className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Contextual findings ({findings.length})
          </h4>
          {findings.length === 0 ? (
            <p className="text-sm text-slate-600">No contextual findings were returned.</p>
          ) : (
            findings.map((finding, index) => (
              <article
                key={`${finding.category}-${finding.location}-${index}`}
                className="rounded-xl border border-slate-200 bg-slate-50 p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-xs font-semibold text-slate-700">
                    {finding.category || 'Finding'}
                  </span>
                  {finding.location && (
                    <span className="text-xs text-slate-500">{finding.location}</span>
                  )}
                </div>
                {finding.explanation && (
                  <p className="mt-2 text-sm leading-relaxed text-slate-800">
                    {finding.explanation}
                  </p>
                )}
                {finding.suggestion && (
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">
                    <span className="font-semibold text-slate-700">Suggested action:</span>{' '}
                    {finding.suggestion}
                  </p>
                )}
              </article>
            ))
          )}
        </div>
      )}

      {!analysis && (
        <p className="text-sm text-slate-600">No contextual review result is available.</p>
      )}
    </section>
  )
}
