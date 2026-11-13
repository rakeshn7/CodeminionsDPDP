import {
  AlertCircle,
  AlertTriangle,
  Loader2,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'
import { useEffect, useState } from 'react'

import BeforeAfterViewer from '../components/BeforeAfterViewer'
import ContextualReviewPanel from '../components/ContextualReviewPanel'
import DocumentUploader from '../components/DocumentUploader'
import DocumentViewer from '../components/DocumentViewer'
import EntityTable from '../components/EntityTable'
import FinalResponse from '../components/FinalResponse'
import LanguagePanel from '../components/LanguagePanel'
import OriginalInput from '../components/OriginalInput'
import ReportDownloader from '../components/ReportDownloader'
import SanitizedOutput from '../components/SanitizedOutput'
import ValidationPanel from '../components/ValidationPanel'
import { sampleDocuments } from '../data/samples'
import {
  analyzeDocument,
  getOcrStatus,
  getSafeApiError,
  processRequest,
} from '../services/api'

export default function PrivacyGateway({ initialWorkflow = 'intelligent_document' }) {
  const [activeWorkflow] = useState(initialWorkflow)
  const [inputText, setInputText] = useState(sampleDocuments[0].text)
  const [editableText, setEditableText] = useState('')
  const [runLlm, setRunLlm] = useState(true)
  const [task, setTask] = useState('summarize')
  const [processing, setProcessing] = useState(false)
  const [processingAction, setProcessingAction] = useState('')
  const [error, setError] = useState('')
  const [selectedSampleId, setSelectedSampleId] = useState(sampleDocuments[0].id)

  // Document review state
  const [documentAnalysis, setDocumentAnalysis] = useState(null)
  const [awaitingEditedReview, setAwaitingEditedReview] = useState(false)
  const [ocrDiagnostics, setOcrDiagnostics] = useState(null)
  const [reviewStatus, setReviewStatus] = useState({})
  const [selectedFindingIndex, setSelectedFindingIndex] = useState(null)

  // Legacy gateway response state
  const [legacyResponse, setLegacyResponse] = useState(null)
  const [legacyEntities, setLegacyEntities] = useState([])

  useEffect(() => {
    let active = true
    getOcrStatus()
      .then((data) => {
        if (active) setOcrDiagnostics(data)
      })
      .catch(() => {
        if (active) {
          setOcrDiagnostics({
            available: false,
            setup_instructions: 'OCR availability could not be checked. Image and scanned-file text extraction may be unavailable.',
          })
        }
      })
    return () => {
      active = false
    }
  }, [])

  const handleAnalyzeDocument = async ({
    file,
    text,
    filename,
    runLlm: requestReview = runLlm,
    extractOnly = false,
  }) => {
    setProcessing(true)
    setProcessingAction(extractOnly ? 'extract' : 'analyze')
    setError('')
    setDocumentAnalysis(null)
    setReviewStatus({})
    setSelectedFindingIndex(null)
    try {
      const result = await analyzeDocument({
        file,
        text,
        filename,
        runLlm: extractOnly ? false : requestReview,
      })
      if (result.status !== 'success') {
        setError(result.error || 'The document could not be read. Check the file and try again.')
        return
      }
      if (extractOnly) {
        setEditableText(result.extracted_text || '')
        setAwaitingEditedReview(true)
      } else {
        setAwaitingEditedReview(false)
      }
      setDocumentAnalysis(result)
    } catch (requestError) {
      setError(getSafeApiError(requestError))
    } finally {
      setProcessing(false)
      setProcessingAction('')
    }
  }

  const handleManualTextChange = (text) => {
    setInputText(text)
    setSelectedSampleId('')
    setDocumentAnalysis(null)
    setError('')
  }

  const handleEditedTextChange = (text) => {
    setEditableText(text)
    setDocumentAnalysis(null)
    setError('')
  }

  const resetDocumentAnalysis = () => {
    setDocumentAnalysis(null)
    setEditableText('')
    setAwaitingEditedReview(false)
    setReviewStatus({})
    setSelectedFindingIndex(null)
  }

  const handleProcessLegacy = async () => {
    if (!inputText.trim()) {
      setError('Please provide document text before processing.')
      return
    }

    setProcessing(true)
    setError('')
    setLegacyResponse(null)
    setLegacyEntities([])
    try {
      const response = await processRequest({
        text: inputText,
        task,
        provider: 'configured_provider',
      })
      setLegacyResponse(response)
      setLegacyEntities(response.entities || [])
    } catch (requestError) {
      setError(getSafeApiError(requestError))
    } finally {
      setProcessing(false)
    }
  }

  const handleSelectSample = (sampleId) => {
    if (!sampleId) {
      setSelectedSampleId('')
      return
    }

    const sample = sampleDocuments.find((item) => item.id === sampleId)
    if (!sample) return

    setSelectedSampleId(sampleId)
    setInputText(sample.text)
    setError('')
    setDocumentAnalysis(null)
    setEditableText('')
    setAwaitingEditedReview(false)
    setLegacyResponse(null)
    setLegacyEntities([])
    setReviewStatus({})
    setSelectedFindingIndex(null)
  }

  const handleAcceptSuggestion = (idx) => {
    setReviewStatus((prev) => ({ ...prev, [idx]: 'accepted' }))
  }

  const handleRejectSuggestion = (idx) => {
    setReviewStatus((prev) => ({ ...prev, [idx]: 'rejected' }))
  }

  const riskBadge = (level) => {
    const riskScore = documentAnalysis?.risk_score
    const scoreText = Number.isFinite(riskScore) ? ` (${Math.round(riskScore * 100)}%)` : ''
    if (level === 'high') {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-300 bg-rose-50 px-3 py-1 text-xs font-bold text-rose-800">
          <ShieldAlert className="h-3.5 w-3.5 text-rose-600" />
          High risk{scoreText}
        </span>
      )
    }
    if (level === 'medium') {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-800">
          <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
          Medium risk{scoreText}
        </span>
      )
    }
    if (level === 'low') {
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
          Low risk{scoreText}
        </span>
      )
    }
    return (
      <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
        Risk assessment unavailable
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500 font-semibold">DPDP Privacy & Validation Gateway</p>
          <h2 className="mt-1 text-2xl font-bold text-slate-900">
            {activeWorkflow === 'intelligent_document' ? 'Document Review' : 'Text Privacy Gateway'}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {activeWorkflow === 'intelligent_document'
              ? 'Review documents, protect personal information, and check Indian identifiers before processing.'
              : 'Protect personal information before sending text for processing.'}
          </p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-rose-300 bg-rose-50 p-3.5 text-sm text-rose-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* ================= WORKFLOW A: INTELLIGENT DOCUMENT PIPELINE ================= */}
      {activeWorkflow === 'intelligent_document' && (
        <div className="space-y-6">
          {/* 1. Document Uploader */}
          <DocumentUploader
            onAnalyze={handleAnalyzeDocument}
            processing={processing}
            processingAction={processingAction}
            samples={sampleDocuments}
            selectedSampleId={selectedSampleId}
            onSelectSample={handleSelectSample}
            ocrStatus={ocrDiagnostics}
            manualText={inputText}
            onManualTextChange={handleManualTextChange}
            editableText={editableText}
            onEditableTextChange={handleEditedTextChange}
            runLlm={runLlm}
            onRunLlmChange={setRunLlm}
            onResetAnalysis={resetDocumentAnalysis}
          />

          {/* 2. Analysis Results Section */}
          {documentAnalysis && (
            <div className="space-y-6">
              {/* Top Metrics & Action Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-center gap-2.5">
                  {riskBadge(documentAnalysis.overall_risk)}
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
                    {documentAnalysis.filename} ({documentAnalysis.page_count} {documentAnalysis.page_count === 1 ? 'page' : 'pages'})
                  </span>
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
                    Latency: {Number.isFinite(documentAnalysis.metrics?.total_latency_ms)
                      ? `${documentAnalysis.metrics.total_latency_ms} ms`
                      : 'Not available'}
                  </span>
                </div>

                {/* Exporter Controls */}
                <ReportDownloader
                  analysisData={documentAnalysis}
                  filename={documentAnalysis.filename}
                />
              </div>

              {/* Multilingual Panel */}
              <LanguagePanel
                languageProfile={documentAnalysis.language_profile}
                detectedLanguages={documentAnalysis.detected_languages}
                isMixed={documentAnalysis.is_mixed_language}
              />

              {documentAnalysis.warnings?.length > 0 && (
                <section
                  aria-label="Document processing notes"
                  className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
                >
                  <h3 className="font-semibold">Processing notes</h3>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {documentAnalysis.warnings.map((warning, index) => (
                      <li key={`${index}-${warning}`}>{warning}</li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Document Viewer and Validation Panel in 2-column Layout */}
              <div className="grid gap-6 xl:grid-cols-2">
                <DocumentViewer
                  extractedText={documentAnalysis.extracted_text}
                  pages={documentAnalysis.pages}
                  entities={documentAnalysis.entities}
                  validationFindings={documentAnalysis.validation_findings}
                  filename={documentAnalysis.filename}
                />

                <ValidationPanel
                  findings={documentAnalysis.validation_findings}
                  onSelectFinding={(idx) => setSelectedFindingIndex(idx)}
                  selectedFindingIndex={selectedFindingIndex}
                  onAcceptSuggestion={handleAcceptSuggestion}
                  onRejectSuggestion={handleRejectSuggestion}
                  reviewStatus={reviewStatus}
                />
              </div>

              {/* Contextual review and sanitized text */}
              <div className="grid gap-6 xl:grid-cols-2">
                <ContextualReviewPanel
                  analysis={documentAnalysis.llm_analysis}
                  awaitingEditedReview={awaitingEditedReview}
                />

                <BeforeAfterViewer
                  extractedText={documentAnalysis.extracted_text}
                  sanitizedText={documentAnalysis.sanitized_text}
                  finalResponse={
                    documentAnalysis.llm_analysis?.status === 'success'
                      ? documentAnalysis.llm_analysis.summary
                      : ''
                  }
                  restoredResponse={
                    documentAnalysis.llm_analysis?.status === 'success'
                      ? documentAnalysis.llm_analysis.restored_summary
                      : ''
                  }
                  restoration={documentAnalysis.llm_analysis?.restoration}
                  placeholdersCount={Object.keys(documentAnalysis.placeholders_summary || {}).length}
                />
              </div>

              {/* Detected PII Entities Table */}
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900">
                    Detected Personal Identifiers (PII) ({documentAnalysis.entities?.length || 0})
                  </h3>
                  <span className="text-xs text-slate-500 font-medium">Zero raw values transmitted outbound</span>
                </div>
                <EntityTable entities={documentAnalysis.entities || []} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* ================= WORKFLOW B: LEGACY 3-PANEL PRIVACY GATEWAY ================= */}
      {activeWorkflow === 'legacy_gateway' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-slate-600">Task:</label>
              <select
                value={task}
                onChange={(e) => setTask(e.target.value)}
                disabled={processing}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-800 shadow-sm"
              >
                <option value="summarize">Summarize</option>
                <option value="extract">Extract</option>
              </select>
            </div>

            <button
              type="button"
              onClick={handleProcessLegacy}
              disabled={processing || !inputText.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                'Run Redaction & Reinsertion'
              )}
            </button>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <OriginalInput
              value={inputText}
              onChange={setInputText}
              onClear={() => setInputText('')}
              onSelectSample={handleSelectSample}
              samples={sampleDocuments}
              selectedSampleId={selectedSampleId}
              loading={processing}
            />
            <SanitizedOutput
              sanitizedText={legacyResponse?.sanitized_text || ''}
              entities={legacyEntities}
              hasResult={Boolean(legacyResponse)}
              leakageDetected={legacyResponse?.leakage_detected}
              placeholderCount={(legacyResponse?.sanitized_text?.match(/<[A-Z_]+_\d+>/g) || []).length}
            />
            <FinalResponse
              finalResponse={legacyResponse?.final_response || ''}
              restored={legacyResponse?.restoration?.restored}
              missing={legacyResponse?.restoration?.missing}
              unknown={legacyResponse?.restoration?.unknown}
              malformed={legacyResponse?.restoration?.malformed}
              expectedPlaceholders={legacyResponse?.entities?.map((e) => e.placeholder).filter(Boolean) || []}
              status={legacyResponse ? 'processed' : 'pending'}
            />
          </div>

          <EntityTable entities={legacyEntities} />
        </div>
      )}
    </div>
  )
}
