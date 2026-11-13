const BACKEND_URL = 'http://127.0.0.1:8000'
const MAX_TEXT_LENGTH = 100000

const elements = {
  text: document.getElementById('page-text'),
  analyze: document.getElementById('analyze'),
  analyzeLabel: document.getElementById('analyze-label'),
  spinner: document.getElementById('spinner'),
  selection: document.getElementById('get-selection'),
  clear: document.getElementById('clear'),
  runLlm: document.getElementById('run-llm'),
  status: document.getElementById('status'),
  results: document.getElementById('results'),
  languages: document.getElementById('languages'),
  entities: document.getElementById('entities'),
  sanitized: document.getElementById('sanitized'),
  validation: document.getElementById('validation'),
  ai: document.getElementById('ai-analysis'),
}

let activeController = null
let requestVersion = 0

function setStatus(message = '', isError = false) {
  elements.status.textContent = message
  elements.status.classList.toggle('error', isError)
}

function makeListItem(text) {
  const item = document.createElement('li')
  item.textContent = text
  return item
}

function resetResults() {
  elements.results.hidden = true
  elements.languages.replaceChildren()
  elements.entities.replaceChildren()
  elements.sanitized.textContent = ''
  elements.validation.replaceChildren()
  elements.ai.replaceChildren()
}

function showResults(result, submittedText) {
  const languages = result.detected_languages
  const entities = result.entities
  const validation = result.validation_findings
  const analysis = result.llm_analysis

  if (
    result.status !== 'success'
    || !Array.isArray(languages)
    || !Array.isArray(entities)
    || typeof result.sanitized_text !== 'string'
    || !Array.isArray(validation)
    || !analysis
    || typeof analysis !== 'object'
    || Array.isArray(analysis)
  ) {
    throw new Error('The backend returned an incomplete or invalid analysis response.')
  }

  elements.languages.replaceChildren()
  if (languages.length) {
    for (const language of languages) {
      const badge = document.createElement('span')
      badge.className = 'badge'
      badge.textContent = String(language)
      elements.languages.append(badge)
    }
  } else {
    elements.languages.textContent = 'No language detected.'
    elements.languages.className = 'muted'
  }

  elements.entities.replaceChildren()
  const confirmedPlaceholders = new Set()
  for (const entity of entities) {
    if (!entity || typeof entity.type !== 'string') continue
    const placeholder = typeof entity.placeholder === 'string'
      ? entity.placeholder
      : 'Value masked'
    const item = makeListItem(`${entity.type}: ${placeholder}`)
    if (
      entity.type === 'PERSON'
      && !confirmedPlaceholders.has(placeholder)
      && Number.isInteger(entity.start)
      && Number.isInteger(entity.end)
      && entity.start >= 0
      && entity.end > entity.start
      && entity.end <= submittedText.length
    ) {
      confirmedPlaceholders.add(placeholder)
      const candidate = submittedText.slice(entity.start, entity.end)
      if (candidate.trim()) {
        const prompt = document.createElement('span')
        prompt.textContent = ` Is “${candidate}” actually a person's name? `
        item.append(prompt)

        const buttons = []
        for (const [label, answer] of [['Yes', 'confirmed'], ['No', 'rejected']]) {
          const button = document.createElement('button')
          button.type = 'button'
          button.className = 'secondary'
          button.textContent = label
          button.addEventListener('click', () => {
            prompt.textContent = answer === 'confirmed'
              ? ` Confirmed as a person's name: ${candidate}`
              : ` Marked as not a person's name: ${candidate}. Review the text and analyze again.`
            for (const responseButton of buttons) responseButton.disabled = true
          })
          item.append(button)
          buttons.push(button)
        }
      }
    }
    elements.entities.append(item)
  }
  if (!elements.entities.childElementCount) {
    elements.entities.append(makeListItem('No PII was detected.'))
  }

  elements.sanitized.textContent = result.sanitized_text || 'No text to display.'

  elements.validation.replaceChildren()
  for (const finding of validation) {
    if (!finding || typeof finding !== 'object') continue
    const severity = ['ERROR', 'WARNING', 'INFO'].includes(finding.severity)
      ? finding.severity
      : 'INFO'
    const location = typeof finding.location === 'string' ? finding.location : 'Document'
    const explanation = typeof finding.explanation === 'string'
      ? finding.explanation
      : 'Review this validation item.'
    elements.validation.append(makeListItem(`${severity} · ${location}: ${explanation}`))
  }
  if (!elements.validation.childElementCount) {
    elements.validation.append(makeListItem('No validation alerts.'))
  }

  elements.ai.replaceChildren()
  if (analysis.status === 'success') {
    const summaryText = typeof analysis.summary === 'string' ? analysis.summary : ''
    const restoredSummary = typeof analysis.restored_summary === 'string'
      ? analysis.restored_summary
      : ''
    if (restoredSummary) {
      const restored = document.createElement('p')
      restored.textContent = `Locally restored summary:\n${restoredSummary}`
      elements.ai.append(restored)
    }
    if (summaryText && summaryText !== restoredSummary) {
      const summary = document.createElement('p')
      summary.className = 'muted'
      summary.textContent = restoredSummary
        ? `Provider response (PII-masked):\n${summaryText}`
        : summaryText
      elements.ai.append(summary)
    }
    if (Array.isArray(analysis.findings) && analysis.findings.length) {
      const findings = document.createElement('ul')
      for (const finding of analysis.findings) {
        if (!finding || typeof finding !== 'object') continue
        const severity = ['ERROR', 'WARNING', 'INFO'].includes(finding.severity)
          ? finding.severity
          : 'INFO'
        const category = typeof finding.category === 'string' ? finding.category : 'AI finding'
        const explanation = typeof finding.explanation === 'string' ? finding.explanation : ''
        const location = typeof finding.location === 'string' && finding.location
          ? ` · ${finding.location}`
          : ''
        const suggestion = typeof finding.suggestion === 'string' && finding.suggestion
          ? ` Suggested action: ${finding.suggestion}`
          : ''
        findings.append(makeListItem(
          `${severity} · ${category}${location}: ${explanation}${suggestion}`,
        ))
      }
      elements.ai.append(findings)
    }
    const restoration = analysis.restoration
    if (restoration && typeof restoration === 'object') {
      const notes = []
      if (Array.isArray(restoration.missing) && restoration.missing.length) {
        notes.push(`Placeholders omitted by the response: ${restoration.missing.join(', ')}`)
      }
      if (Array.isArray(restoration.unknown) && restoration.unknown.length) {
        notes.push(`Unrecognized placeholders left unchanged: ${restoration.unknown.join(', ')}`)
      }
      if (Array.isArray(restoration.malformed) && restoration.malformed.length) {
        notes.push(`Malformed placeholders left unchanged: ${restoration.malformed.join(', ')}`)
      }
      if (notes.length) {
        const note = document.createElement('p')
        note.className = 'muted'
        note.textContent = notes.join('\n')
        elements.ai.append(note)
      }
    }
    if (!elements.ai.childElementCount) {
      elements.ai.textContent = 'The provider completed analysis without a summary or findings.'
    }
  } else if (analysis.status === 'skipped') {
    const note = document.createElement('p')
    note.className = 'muted'
    note.textContent = 'AI review was not requested. To enable it, check “Request optional external AI review” and analyze again. The backend masks detected PII before sending text to the provider.'
    elements.ai.append(note)
  } else {
    const message = typeof analysis.error === 'string' && analysis.error
      ? analysis.error
      : 'AI review failed without a provider error message. Local detection and validation are still available; check that the backend and provider are configured.'
    const note = document.createElement('p')
    note.className = 'muted'
    note.textContent = message
    elements.ai.append(note)
  }

  elements.results.hidden = false
}

async function getSelectedText() {
  setStatus('')
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (!tab?.id) {
      setStatus('No active webpage is available. Your pasted text is unchanged; press Analyze to continue.')
      return
    }
    const [injected] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.getSelection()?.toString() || '',
    })
    const selection = injected?.result?.trim()
    if (!selection) {
      setStatus('No webpage text is selected. Your pasted text is unchanged; press Analyze to continue.')
      return
    }
    elements.text.value = selection.slice(0, MAX_TEXT_LENGTH)
    resetResults()
    setStatus('Selected text is ready. It has not been sent yet.')
  } catch {
    setStatus(
      'Chrome could not read this page selection. Your pasted text is unchanged; press Analyze, or select text on a regular webpage and try again.',
      true,
    )
  }
}

async function analyzeText() {
  const text = elements.text.value.trim()
  resetResults()
  setStatus('')
  if (!text) {
    setStatus('Paste webpage text or explicitly read a page selection first.', true)
    return
  }
  if (text.length > MAX_TEXT_LENGTH) {
    setStatus('Text exceeds the backend limit of 100,000 characters.', true)
    return
  }

  const currentRequest = ++requestVersion
  const controller = new AbortController()
  activeController = controller
  const timeout = setTimeout(() => controller.abort(), 120000)
  elements.analyze.disabled = true
  elements.selection.disabled = true
  elements.analyzeLabel.textContent = 'Analyzing…'
  elements.spinner.hidden = false
  setStatus('Sending text to the local privacy gateway…')

  try {
    let response
    try {
      response = await fetch(`${BACKEND_URL}/api/documents/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          filename: 'selected-page.txt',
          run_llm: elements.runLlm.checked,
          provider: 'configured_provider',
        }),
        signal: controller.signal,
      })
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('The request timed out or was cancelled. Check the backend and try again.')
      }
      throw new Error(
        'Cannot reach the local backend at http://127.0.0.1:8000. Start FastAPI and verify extension CORS settings.',
      )
    }

    let result
    try {
      result = await response.json()
    } catch {
      throw new Error('The backend returned an invalid response. Check that the local API is running correctly.')
    }
    if (!response.ok) {
      const detail = typeof result?.detail === 'string' ? result.detail : ''
      throw new Error(detail || `The backend could not analyze this text (HTTP ${response.status}).`)
    }

    showResults(result, text)
    setStatus('Analysis complete. Raw text was not saved by the extension.')
  } catch (error) {
    if (currentRequest !== requestVersion) return
    setStatus(
      error instanceof Error ? error.message : 'Analysis failed. Check the backend and try again.',
      true,
    )
  } finally {
    clearTimeout(timeout)
    if (currentRequest === requestVersion) {
      activeController = null
      elements.analyze.disabled = false
      elements.selection.disabled = false
      elements.analyzeLabel.textContent = 'Analyze'
      elements.spinner.hidden = true
    }
  }
}

function clearPopup() {
  requestVersion += 1
  activeController?.abort()
  activeController = null
  elements.text.value = ''
  elements.runLlm.checked = false
  elements.analyze.disabled = false
  elements.selection.disabled = false
  elements.analyzeLabel.textContent = 'Analyze'
  elements.spinner.hidden = true
  resetResults()
  setStatus('')
}

elements.selection.addEventListener('click', getSelectedText)
elements.analyze.addEventListener('click', analyzeText)
elements.clear.addEventListener('click', clearPopup)
