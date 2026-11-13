import { ChevronLeft, ChevronRight, Copy, FileText } from 'lucide-react'
import { useState } from 'react'

export default function DocumentViewer({
  extractedText = '',
  pages = [],
  entities = [],
  filename = 'document.txt',
}) {
  const [currentPage, setCurrentPage] = useState(1)
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState('')

  const totalPages = pages.length > 0 ? pages.length : 1
  const currentPageText = pages.length > 0 && pages[currentPage - 1]
    ? pages[currentPage - 1].text
    : extractedText

  const handleCopy = async () => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard access unavailable')
      await navigator.clipboard.writeText(extractedText)
      setCopyError('')
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopyError('Clipboard access is unavailable in this browser.')
    }
  }

  const renderHighlightedText = (text) => {
    if (!text) return <p className="italic text-slate-400">No document text available.</p>

    return (
      <div className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-slate-800">
        {text}
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      {/* Header and Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-blue-600" />
          <h3 className="font-semibold text-slate-900">{filename}</h3>
          <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs font-medium text-slate-600">
            {extractedText.length} characters
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Page Navigator if multi-page */}
          {totalPages > 1 && (
            <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700">
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
                className="rounded p-1 hover:bg-slate-200 disabled:opacity-40"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <span className="font-mono px-1 font-semibold">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages}
                className="rounded p-1 hover:bg-slate-200 disabled:opacity-40"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {/* Copy Button */}
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-100"
          >
            <Copy className="h-3.5 w-3.5" />
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      {copyError && <p role="status" className="mt-3 text-xs text-rose-700">{copyError}</p>}

      {/* Document View Body */}
      <div className="mt-4 max-h-[460px] overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-4">
        {renderHighlightedText(totalPages > 1 ? currentPageText : extractedText)}
      </div>

      {/* Entity Type Legend */}
      {entities.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
          <span className="font-semibold text-slate-700">Detected PII Tags:</span>
          {Array.from(new Set(entities.map((e) => e.type))).map((type) => (
            <span
              key={type}
              className="rounded-md border border-slate-200 bg-slate-100 px-2 py-0.5 font-mono text-[11px] font-semibold text-slate-800"
            >
              {type} ({entities.filter((e) => e.type === type).length})
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
