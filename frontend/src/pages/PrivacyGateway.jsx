import { AlertCircle, CheckCircle2, Loader2, ShieldCheck, Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'
import EntityTable from '../components/EntityTable'
import FinalResponse from '../components/FinalResponse'
import OriginalInput from '../components/OriginalInput'
import SanitizedOutput from '../components/SanitizedOutput'
import { sampleDocuments } from '../data/samples'
import { processRequest } from '../services/api'

const defaultEntityList = [
  { type: 'PERSON', placeholder: '<PERSON_1>', status: 'Detected' },
  { type: 'AADHAAR', placeholder: '<AADHAAR_1>', status: 'Detected' },
  { type: 'PAN', placeholder: '<PAN_1>', status: 'Detected' },
  { type: 'ADDRESS', placeholder: '<ADDRESS_1>', status: 'Detected' },
]

function normalizeEntities(entities = []) {
  if (!Array.isArray(entities)) return []

  return entities.map((entity, index) => {
    if (typeof entity === 'string') {
      return { type: entity, placeholder: `<${entity}_${index + 1}>`, status: 'Detected' }
    }

    return {
      type: entity.type || entity.entity_type || 'UNKNOWN',
      placeholder: entity.placeholder || entity.label || `<${(entity.type || entity.entity_type || 'ENTITY').toUpperCase()}_${index + 1}>`,
      status: entity.status || 'Detected',
    }
  })
}

export default function PrivacyGateway() {
  const [inputText, setInputText] = useState(sampleDocuments[0].text)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')
  const [response, setResponse] = useState(null)
  const [entityList, setEntityList] = useState(defaultEntityList)
  const [selectedSampleId, setSelectedSampleId] = useState(sampleDocuments[0].id)

  const placeholderCount = useMemo(() => {
    const matches = (response?.sanitized_text || '').match(/<[A-Z_]+\d*?>/g) || []
    return matches.length
  }, [response])

  const handleProcess = async () => {
    if (!inputText.trim()) {
      setError('Please provide a document before processing.')
      return
    }

    setProcessing(true)
    setError('')

    try {
      const result = await processRequest({
        text: inputText,
        task: 'summarize',
        provider: 'configured_provider',
      })

      const normalizedEntities = normalizeEntities(result?.entities || defaultEntityList)
      setEntityList(normalizedEntities)
      setResponse(result)
    } catch (requestError) {
      console.error('Secure processing failed:', requestError)
      setError('The backend API is unavailable or failed. Check the server and try again.')
      setResponse(null)
      setEntityList([])
    } finally {
      setProcessing(false)
    }
  }

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (file.name.toLowerCase().endsWith('.txt')) {
      const reader = new FileReader()
      reader.onload = () => {
        setInputText(String(reader.result || ''))
      }
      reader.readAsText(file)
      return
    }

    setError('PDF parsing is not available in this frontend build. Please upload a TXT file or paste the document directly.')
  }

  const handleSelectSample = (sampleId) => {
    const sample = sampleDocuments.find((item) => item.id === sampleId)
    if (!sample) return

    setSelectedSampleId(sampleId)
    setInputText(sample.text)
    setError('')
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Privacy Gateway</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Secure document processing</h2>
        </div>
        <button
          type="button"
          onClick={handleProcess}
          disabled={processing}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {processing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {processing ? 'Processing securely...' : 'PROCESS SECURELY'}
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-100">
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-3">
        <OriginalInput
          value={inputText}
          onChange={setInputText}
          onClear={() => setInputText('')}
          onFileUpload={handleFileUpload}
          samples={sampleDocuments}
          onSelectSample={handleSelectSample}
          loading={processing}
          selectedSampleId={selectedSampleId}
        />

        <SanitizedOutput
          sanitizedText={response?.sanitized_text || 'Pending secure sanitization output'}
          entities={entityList}
          leakageDetected={Boolean(response?.leakage_detected)}
          placeholderCount={placeholderCount}
        />

        <FinalResponse
          finalResponse={response?.final_response || response?.llm_response || 'Pending final AI response after reinsertion'}
          restored={response?.restoration?.restored || []}
          missing={response?.restoration?.missing || []}
          status={response?.restoration?.restored?.length ? 'restored' : (response ? 'partial' : 'Ready')}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
        <EntityTable entities={entityList} />

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
          <h3 className="text-lg font-semibold text-white">Processing metrics</h3>
          <div className="mt-4 space-y-3 text-sm text-slate-300">
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Gateway latency</span>
              <span>{response?.metrics?.processing_latency_ms ?? '—'} ms</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Model</span>
              <span>{response?.model || 'Not yet processed'}</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Request ID</span>
              <span className="font-mono text-xs text-blue-200">{response?.request_id || '—'}</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Security status</span>
              <span className={`inline-flex items-center gap-2 ${response?.status === 'success' ? 'text-emerald-300' : 'text-slate-300'}`}>
                {response?.status === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
                {response?.status || 'Awaiting response'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
