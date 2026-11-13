import { Check, Copy, FileCheck2, Lock, ShieldCheck } from 'lucide-react'
import { useState } from 'react'

export default function BeforeAfterViewer({
  extractedText = '',
  sanitizedText = '',
  finalResponse = '',
  restoredResponse = '',
  restoration,
  placeholdersCount = 0,
}) {
  const [activeTab, setActiveTab] = useState('sanitized')
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState('')

  const activeContent = {
    extracted: extractedText,
    sanitized: sanitizedText,
    final: finalResponse,
  }[activeTab]

  const handleCopy = async () => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard access unavailable')
      const content = activeTab === 'final' && restoredResponse
        ? `${activeContent}\n\nLocally restored summary:\n${restoredResponse}`
        : activeContent
      await navigator.clipboard.writeText(content)
      setCopyError('')
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopyError('Clipboard access is unavailable in this browser.')
    }
  }

  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      {/* Tab Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-slate-100 p-1">
          <button
            type="button"
            onClick={() => setActiveTab('extracted')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === 'extracted'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            1. Extracted text
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('sanitized')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === 'sanitized'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Lock className="h-3 w-3" />
            2. Sanitized text ({placeholdersCount} placeholders)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('final')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              activeTab === 'final'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileCheck2 className="h-3 w-3" />
            3. Review summary
          </button>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5 text-slate-600" />}
          {copied ? 'Copied' : 'Copy View'}
        </button>
      </div>

      {copyError && <p role="status" className="text-xs text-rose-700">{copyError}</p>}

      {/* Description Banner based on Active Tab */}
      {activeTab === 'extracted' && (
        <p className="text-xs text-slate-500 font-medium">
          Text extracted from the selected document. Personal information is shown only in this local view.
        </p>
      )}
      {activeTab === 'sanitized' && (
        <div className="flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 p-2.5 text-xs text-blue-900">
          <ShieldCheck className="h-4 w-4 shrink-0 text-blue-600" />
          <span>
            Personal information detected by local checks is replaced with placeholders before external review. Automated detection may not identify every sensitive value.
          </span>
        </div>
      )}
      {activeTab === 'final' && (
        <p className="text-xs text-slate-500 font-medium">
          The provider receives only sanitized text. Placeholders are shown in its summary, then restored locally below.
        </p>
      )}

      {/* Content Area */}
      <div className="max-h-[380px] overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-sm leading-relaxed text-slate-800 whitespace-pre-wrap">
        {activeContent || (
          <span className="font-sans italic text-slate-400">
            {activeTab === 'final'
              ? 'No review summary is available.'
              : 'No content available for this stage.'}
          </span>
        )}
      </div>

      {activeTab === 'final' && restoredResponse && (
        <section className="space-y-2 rounded-xl border border-emerald-200 bg-emerald-50/60 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-emerald-950">Locally restored summary</h4>
            {restoration && (
              <span className="text-xs text-emerald-800">
                {restoration.restored?.length || 0} placeholder(s) restored
              </span>
            )}
          </div>
          <p className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-slate-800">
            {restoredResponse}
          </p>
          {restoration?.missing?.length > 0 && (
            <p className="text-xs text-amber-800">
              Not present in the response: {restoration.missing.join(', ')}
            </p>
          )}
          {restoration?.unknown?.length > 0 && (
            <p className="text-xs text-amber-800">
              Unrecognized placeholders were left unchanged: {restoration.unknown.join(', ')}
            </p>
          )}
        </section>
      )}
    </div>
  )
}
