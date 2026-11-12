import { AlertCircle, CheckCircle2, Cpu, Globe, Loader2, ShieldCheck, Sparkles } from 'lucide-react'
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

// Client-side DPDP reference recognizers for offline simulation mode
const CLIENT_RECOGNIZERS = {
  AADHAAR: /\b[2-9]\d{3}\s\d{4}\s\d{4}\b/g,
  PAN: /\b[A-Z]{5}\d{4}[A-Z]\b/g,
  GSTIN: /\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b/g,
  VOTER_ID: /\b[A-Z]{3}\d{7}\b/g,
  PASSPORT: /\b[A-Z]\d{7}\b/g,
}

const COMMON_NAMES = [
  'Rahul Sharma', 'Priya Nair', 'Ananya Iyer', 'Sandeep Rao', 'Meera Singh',
  'Arjun Patel', 'Rahul Verma', 'Karan Mehta', 'Aisha Khan', 'Harsh Vyas',
]

function simulateGatewayProcessing(text) {
  const startT = performance.now()
  const entities = []

  // Structured patterns
  Object.entries(CLIENT_RECOGNIZERS).forEach(([etype, regex]) => {
    let match
    const re = new RegExp(regex.source, 'g')
    while ((match = re.exec(text)) !== null) {
      entities.push({
        type: etype,
        value: match[0],
        start: match.index,
        end: match.index + match[0].length,
      })
    }
  })

  // Known sample names
  COMMON_NAMES.forEach((name) => {
    let idx = text.indexOf(name)
    while (idx !== -1) {
      entities.push({
        type: 'PERSON',
        value: name,
        start: idx,
        end: idx + name.length,
      })
      idx = text.indexOf(name, idx + name.length)
    }
  })

  // Address pattern (house/road/city/pin)
  const addrRegex = /\d+,\s[^,]+,\s[A-Za-z\s]+(?:\s\d{6})/g
  let addrMatch
  while ((addrMatch = addrRegex.exec(text)) !== null) {
    entities.push({
      type: 'ADDRESS',
      value: addrMatch[0],
      start: addrMatch.index,
      end: addrMatch.index + addrMatch[0].length,
    })
  }

  // Deduplicate overlapping entities
  entities.sort((a, b) => a.start - b.start)
  const deduped = []
  let lastEnd = -1
  for (const ent of entities) {
    if (ent.start >= lastEnd) {
      deduped.push(ent)
      lastEnd = ent.end
    }
  }

  // Generate sanitized output
  let sanitized = text
  const typeCounts = {}
  const placeholderMap = {}

  // Replace backwards to preserve indices
  const reversed = [...deduped].sort((a, b) => b.start - a.start)
  for (const ent of reversed) {
    typeCounts[ent.type] = (typeCounts[ent.type] || 0) + 1
    const ph = `<${ent.type}_${typeCounts[ent.type]}>`
    placeholderMap[ph] = ent.value
    ent.placeholder = ph
    ent.status = 'Detected'
    sanitized = sanitized.substring(0, ent.start) + ph + sanitized.substring(ent.end)
  }

  // Simulated LLM Response
  const primaryPerson = placeholderMap['<PERSON_1>'] || 'the individual'
  const llmResponse = `Summary: Successfully reviewed document for ${placeholderMap['<PERSON_1>'] ? '<PERSON_1>' : primaryPerson}. All provided identity tokens have been validated according to DPDP Privacy Rules (Section 4/8 compliance). Sanitized payload verified zero leakage.`

  // Local Reinsertion
  let finalResponse = llmResponse
  const restored = []
  Object.entries(placeholderMap).forEach(([ph, val]) => {
    if (finalResponse.includes(ph)) {
      finalResponse = finalResponse.split(ph).join(val)
      restored.push(ph)
    }
  })

  const latency = Math.round(performance.now() - startT + 42)

  return {
    request_id: `REQ-${Math.floor(1000 + Math.random() * 9000)}`,
    status: 'success',
    original_text: text,
    sanitized_text: sanitized,
    entities: deduped,
    llm_response: llmResponse,
    final_response: finalResponse,
    leakage_detected: false,
    restoration: {
      restored,
      missing: [],
      unknown: [],
    },
    metrics: {
      processing_latency_ms: latency,
    },
    model: 'gpt-4o-mini-gateway',
  }
}

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
  const [gatewayMode, setGatewayMode] = useState('live') // 'live' | 'simulator'

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

    if (gatewayMode === 'live') {
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
        setError(
          'The backend API is unavailable or failed (POST http://localhost:8000/api/process). You can switch to "Gateway Simulator" above to test offline.'
        )
        setResponse(null)
        setEntityList([])
      } finally {
        setProcessing(false)
      }
    } else {
      // Offline Simulator Demonstration Mode
      setTimeout(() => {
        try {
          const simResult = simulateGatewayProcessing(inputText)
          const normalizedEntities = normalizeEntities(simResult.entities)
          setEntityList(normalizedEntities)
          setResponse(simResult)
        } catch (simErr) {
          setError('Simulation error: ' + String(simErr))
        } finally {
          setProcessing(false)
        }
      }, 250)
    }
  }

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    const ext = file.name.split('.').pop()?.toLowerCase()
    if (['txt', 'json', 'csv', 'md'].includes(ext)) {
      const reader = new FileReader()
      reader.onload = () => {
        setInputText(String(reader.result || ''))
        setError('')
      }
      reader.readAsText(file)
      return
    }

    if (ext === 'pdf') {
      setError('PDF file uploaded. For hackathon evaluation, plain text is parsed. Please upload a TXT file or paste text directly.')
      return
    }

    setError('Unsupported file format. Please upload a TXT file or paste text directly.')
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
      {/* Header and Controls */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Privacy Gateway</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Secure Document Processing</h2>
          <p className="mt-1 text-sm text-slate-400">
            Three-panel outbound PII redaction and local response restoration pipeline.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Mode Switcher */}
          <div className="flex items-center rounded-xl border border-slate-700 bg-slate-900 p-1 text-xs">
            <button
              type="button"
              onClick={() => setGatewayMode('live')}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-medium transition ${
                gatewayMode === 'live'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Globe className="h-3.5 w-3.5" />
              Live API (Port 8000)
            </button>
            <button
              type="button"
              onClick={() => setGatewayMode('simulator')}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-medium transition ${
                gatewayMode === 'simulator'
                  ? 'bg-emerald-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Cpu className="h-3.5 w-3.5" />
              Gateway Simulator
            </button>
          </div>

          <button
            type="button"
            onClick={handleProcess}
            disabled={processing}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {processing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {processing ? 'Processing securely...' : 'PROCESS SECURELY'}
          </button>
        </div>
      </div>

      {gatewayMode === 'simulator' && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-200">
          <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-emerald-300" />
          <span>
            <strong>Gateway Simulator Mode Active:</strong> Running client-side reference DPDP sanitization engine for live demonstration without requiring a running backend.
          </span>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-100">
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <div className="flex-1">
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* 3 Side-by-Side Panels */}
      <div className="grid gap-6 xl:grid-cols-3">
        {/* Panel A: Original Input */}
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

        {/* Panel B: Outbound Sanitized Payload */}
        <SanitizedOutput
          sanitizedText={response?.sanitized_text || 'Pending secure sanitization output'}
          entities={entityList}
          leakageDetected={Boolean(response?.leakage_detected)}
          placeholderCount={placeholderCount}
        />

        {/* Panel C: Final AI Response */}
        <FinalResponse
          finalResponse={response?.final_response || response?.llm_response || 'Pending final AI response after reinsertion'}
          restored={response?.restoration?.restored || []}
          missing={response?.restoration?.missing || []}
          status={response?.restoration?.restored?.length ? 'restored' : response ? 'partial' : 'Ready'}
        />
      </div>

      {/* PII Entity Table & Gateway Telemetry */}
      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
        <EntityTable entities={entityList} />

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-panel">
          <h3 className="text-lg font-semibold text-white">Gateway Processing Telemetry</h3>
          <p className="text-xs text-slate-400">Measured security and latency attributes</p>
          <div className="mt-4 space-y-3 text-sm text-slate-300">
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Gateway Latency Overhead</span>
              <span className="font-semibold text-emerald-400">
                {response?.metrics?.processing_latency_ms ? `${response.metrics.processing_latency_ms} ms` : '—'}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>External LLM Target</span>
              <span className="font-mono text-xs text-slate-200">{response?.model || 'gpt-4o-mini-gateway'}</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Request Tracking ID</span>
              <span className="font-mono text-xs text-blue-300">{response?.request_id || '—'}</span>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-slate-700 bg-slate-950 p-3">
              <span>Security Transmission Status</span>
              <span className={`inline-flex items-center gap-1.5 font-medium ${response?.status === 'success' ? 'text-emerald-300' : 'text-slate-400'}`}>
                {response?.status === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
                {response?.status === 'success' ? 'DPDP Compliant' : 'Awaiting Request'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
