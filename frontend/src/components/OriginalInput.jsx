import { FileText, X } from 'lucide-react'

function highlightTextCount(value) {
  return value.length
}

export default function OriginalInput({ value, onChange, onClear, onSelectSample, samples, onFileUpload, loading, selectedSampleId }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-slate-700">
          <FileText className="h-4 w-4 text-blue-600" />
          ORIGINAL DOCUMENT
        </div>
        <button
          type="button"
          onClick={onClear}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100"
        >
          <X className="h-3.5 w-3.5" />
          Clear
        </button>
      </div>

      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 items-center gap-2">
          <label className="flex cursor-pointer items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 hover:border-blue-500">
            Upload text file
            <input type="file" className="hidden" accept=".txt,.md,.csv,.json" onChange={onFileUpload} />
          </label>
          <select
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-blue-500 shadow-sm font-medium"
            value={selectedSampleId || ''}
            onChange={(event) => onSelectSample(event.target.value)}
          >
            <option value="">Select sample document</option>
            {samples.map((sample) => (
              <option key={sample.id} value={sample.id}>{sample.title}</option>
            ))}
          </select>
        </div>
      </div>

      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-[320px] w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-900 outline-none focus:border-blue-500 focus:bg-white"
        placeholder="Paste or upload a document to review..."
        disabled={loading}
      />

      <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
        <span>Character count</span>
        <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 font-semibold text-slate-700">{highlightTextCount(value || '')}</span>
      </div>
    </div>
  )
}
