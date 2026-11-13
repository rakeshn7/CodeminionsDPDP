import { AlertTriangle, FileCheck, Loader2, UploadCloud } from 'lucide-react'
import { useRef, useState } from 'react'

const SUPPORTED_FORMATS = [
  'pdf', 'docx', 'pptx', 'txt', 'md', 'markdown', 'json', 'html', 'htm',
  'csv', 'xlsx', 'jpg', 'jpeg', 'png', 'webp', 'bmp', 'tif', 'tiff',
]
const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

export default function DocumentUploader({
  onAnalyze,
  processing = false,
  processingAction = '',
  samples = [],
  selectedSampleId = '',
  onSelectSample,
  ocrStatus = {},
  manualText = '',
  onManualTextChange,
  editableText = '',
  onEditableTextChange,
  runLlm = true,
  onRunLlmChange,
  onResetAnalysis,
}) {
  const [dragActive, setDragActive] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [fileError, setFileError] = useState('')
  const fileInputRef = useRef(null)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files?.length) handleFilesSelected(Array.from(e.dataTransfer.files))
  }

  const handleFileChange = (e) => {
    if (e.target.files?.length) handleFilesSelected(Array.from(e.target.files))
  }

  const handleFilesSelected = (files) => {
    if (files.length > 10) {
      setSelectedFiles([])
      setSelectedFile(null)
      setFileError('Select no more than 10 documents at a time.')
      return
    }
    const invalid = files.find((file) => {
      const extension = file.name.split('.').pop()?.toLowerCase()
      return !extension || !SUPPORTED_FORMATS.includes(extension) || file.size > MAX_FILE_SIZE_BYTES
    })
    if (invalid) {
      setSelectedFiles([])
      setSelectedFile(null)
      const extension = invalid.name.split('.').pop()?.toLowerCase()
      setFileError(
        !extension || !SUPPORTED_FORMATS.includes(extension)
          ? `Unsupported file type: ${invalid.name}`
          : `The file ${invalid.name} exceeds the 25 MB per-file upload limit.`,
      )
      return
    }
    setSelectedFiles(files)
    setSelectedFile(files[0])
    setFileError('')
    onSelectSample?.('')
    onManualTextChange?.('')
    onEditableTextChange?.('')
    onResetAnalysis?.()
  }

  const handleStartAnalysis = () => {
    if (selectedFiles.length > 1) {
      onAnalyze({ files: selectedFiles, runLlm })
      return
    }
    if (selectedFile) {
      onAnalyze({ file: selectedFile, runLlm: false, extractOnly: true })
    }
  }

  const handleAnalyzeText = () => {
    if (!manualText.trim()) return
    onAnalyze({ text: manualText, filename: 'manual-entry.txt', runLlm })
  }

  const handleAnalyzeEditedText = () => {
    if (!editableText.trim()) return
    onAnalyze({
      text: editableText,
      filename: selectedFile?.name || 'edited-document.txt',
      runLlm,
    })
  }

  const clearSelectedFile = () => {
    setSelectedFile(null)
    setSelectedFiles([])
    setFileError('')
    onEditableTextChange?.('')
    onResetAnalysis?.()
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      {/* Title & Format Badges */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Document Ingestion & Multi-Format Extraction</h3>
          <p className="text-xs text-slate-500">
            Secure local parsing for enterprise documents, scans, spreadsheets, and multi-script records.
          </p>
        </div>

        {/* Supported Format Pills */}
        <div className="flex flex-wrap gap-1.5">
          {['PDF', 'DOCX', 'PPTX', 'TXT / MD', 'JSON / HTML', 'CSV', 'XLSX', 'Images'].map((format) => (
            <span
              key={format}
              className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-mono text-slate-700 font-medium"
            >
              {format}
            </span>
          ))}
        </div>
      </div>

      {/* Drag & Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : selectedFile
            ? 'border-emerald-500 bg-emerald-50/50'
            : 'border-slate-300 bg-slate-50/70 hover:border-slate-400'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.pptx,.txt,.md,.markdown,.json,.html,.htm,.csv,.xlsx,.jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff"
          multiple
          onChange={handleFileChange}
          disabled={processing}
          className="hidden"
          id="file-upload-input"
        />

        {selectedFiles.length ? (
          <div className="flex flex-col items-center space-y-2">
            <FileCheck className="h-12 w-12 text-emerald-600" />
            <div>
              <p className="font-semibold text-slate-900">{selectedFiles.length} document{selectedFiles.length === 1 ? '' : 's'} selected</p>
              <ul className="mt-1 max-h-24 overflow-auto text-xs text-slate-600">
                {selectedFiles.map((file) => <li key={`${file.name}-${file.size}`}>{file.name}</li>)}
              </ul>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={clearSelectedFile}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50"
              >
                Change File
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center space-y-2">
            <UploadCloud className="h-12 w-12 text-blue-600" />
            <div>
              <p className="text-sm font-medium text-slate-700">
                Drag and drop documents here, or{' '}
                <label
                  htmlFor="file-upload-input"
                  className="cursor-pointer font-semibold text-blue-600 underline hover:text-blue-700"
                >
                  browse files
                </label>
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Select up to 10 files (25 MB each). Multiple files are analyzed separately.
              </p>
            </div>
          </div>
        )}
      </div>

      {fileError && (
        <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
          {fileError}
        </p>
      )}

      {/* Preset Samples Selector & Actions */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs font-medium text-slate-600">Or Select a Demonstration Sample:</label>
          <select
            value={selectedSampleId}
            onChange={(e) => {
              setSelectedFile(null)
              setSelectedFiles([])
              setFileError('')
              onEditableTextChange?.('')
              onResetAnalysis?.()
              if (fileInputRef.current) fileInputRef.current.value = ''
              onSelectSample(e.target.value)
            }}
            disabled={processing}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-800 outline-none focus:border-blue-500 shadow-sm"
          >
            <option value="">Choose a sample or upload a file</option>
            {samples.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-slate-700 font-medium cursor-pointer">
            <input
              type="checkbox"
              checked={runLlm}
              onChange={(e) => onRunLlmChange?.(e.target.checked)}
              disabled={processing}
              className="rounded border-slate-300 bg-white text-blue-600 focus:ring-0"
            />
            <span>Request external contextual review</span>
          </label>

          <button
            type="button"
            onClick={handleStartAnalysis}
            disabled={processing || !selectedFile}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-50"
          >
            {processing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {processingAction === 'extract'
                  ? 'Extracting text...'
                  : processingAction.startsWith('batch-')
                    ? `Processing ${processingAction.slice(6)} documents...`
                    : 'Please wait...'}
              </>
            ) : (
              selectedFiles.length > 1 ? `Analyze ${selectedFiles.length} documents` : 'Extract text for review'
            )}
          </button>
        </div>
      </div>

      {editableText.length > 0 && (
        <section className="space-y-3 rounded-xl border border-blue-200 bg-blue-50/40 p-4">
          <div>
            <h4 className="text-sm font-semibold text-slate-900">Review and edit extracted text</h4>
            <p className="mt-1 text-xs leading-relaxed text-slate-600">
              Correct extraction errors here. The edited text is rechecked locally before any optional external review.
            </p>
          </div>
          <textarea
            value={editableText}
            onChange={(event) => onEditableTextChange?.(event.target.value)}
            disabled={processing}
            rows={8}
            aria-label="Edit extracted document text"
            className="w-full resize-y rounded-xl border border-slate-300 bg-white p-3 font-mono text-sm leading-relaxed text-slate-800 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-slate-500">{editableText.length} characters</span>
            <button
              type="button"
              onClick={handleAnalyzeEditedText}
              disabled={processing || !editableText.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-50"
            >
              {processing ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {processing
                ? processingAction === 'extract'
                  ? 'Extracting document...'
                  : 'Reviewing edited text...'
                : 'Analyze edited text'}
            </button>
          </div>
        </section>
      )}

      <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
        <div>
          <h4 className="text-sm font-semibold text-slate-900">Enter text manually</h4>
          <p className="mt-1 text-xs text-slate-600">
            Paste or write text here to run the same local checks without uploading a file.
          </p>
        </div>
        <textarea
          value={manualText}
          onChange={(event) => onManualTextChange?.(event.target.value)}
          disabled={processing}
          rows={6}
          aria-label="Enter document text manually"
          placeholder="Paste or type document text..."
          className="w-full resize-y rounded-xl border border-slate-300 bg-white p-3 font-mono text-sm leading-relaxed text-slate-800 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-slate-500">{manualText.length} characters</span>
          <button
            type="button"
            onClick={handleAnalyzeText}
            disabled={processing || !manualText.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-50"
          >
            {processing ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {processing
              ? processingAction === 'extract'
                ? 'Extracting document...'
                : 'Analyzing text...'
              : 'Analyze entered text'}
          </button>
        </div>
      </section>

      {/* OCR Status Banner */}
      {ocrStatus && ocrStatus.available === false && (
        <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
          <div className="space-y-1">
            <p className="font-semibold">Local OCR Note (Scanned PDFs / Images):</p>
            <p className="text-amber-700 leading-relaxed">{ocrStatus.setup_instructions}</p>
          </div>
        </div>
      )}
    </div>
  )
}
