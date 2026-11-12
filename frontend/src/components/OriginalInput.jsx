import { FileText, X } from 'lucide-react'

function highlightTextCount(value) {
  return value.length
}

export default function OriginalInput({ value, onChange, onClear, onSelectSample, samples, onFileUpload, loading, selectedSampleId }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.2em] text-slate-300">
          <FileText className="h-4 w-4 text-blue-300" />
          Original Document
        </div>
        <button
          type="button"
          onClick={onClear}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-300"
        >
          <X className="h-3.5 w-3.5" />
          Clear
        </button>
      </div>

      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 items-center gap-2">
          <label className="flex cursor-pointer items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950 px-3 py-2 text-xs font-medium text-slate-300 hover:border-blue-400/60">
            Upload TXT/PDF
            <input type="file" className="hidden" accept=".txt,.pdf" onChange={onFileUpload} />
          </label>
          <select
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500"
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
        className="min-h-[320px] w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm leading-6 text-slate-100 outline-none focus:border-blue-500"
        placeholder="Paste or upload a document requiring privacy-safe LLM processing..."
        disabled={loading}
      />

      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <span>Character count</span>
        <span className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 font-medium text-slate-200">{highlightTextCount(value || '')}</span>
      </div>
    </div>
  )
}
