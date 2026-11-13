const textInput = document.getElementById('page-text')
const status = document.getElementById('status')
const analyzeButton = document.getElementById('analyze')

document.getElementById('get-selection').addEventListener('click', async () => {
  status.className = ''
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (!tab?.id) throw new Error('No active browser tab was found.')
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.getSelection()?.toString() || '',
    })
    const selected = result?.result?.trim()
    if (!selected) throw new Error('Select text on the page first, then try again.')
    textInput.value = selected
    status.textContent = 'Selected text is ready for local analysis.'
  } catch (error) {
    status.className = 'error'
    status.textContent = error.message || 'Could not read the page selection.'
  }
})

analyzeButton.addEventListener('click', async () => {
  const text = textInput.value.trim()
  status.className = ''
  if (!text) {
    status.className = 'error'
    status.textContent = 'Select or enter text before analyzing.'
    return
  }
  analyzeButton.disabled = true
  status.textContent = 'Sending text to the local backend...'
  try {
    const response = await fetch('http://127.0.0.1:8000/api/documents/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        filename: 'selected-page.txt',
        run_llm: document.getElementById('run-llm').checked,
        provider: 'configured_provider',
      }),
    })
    const result = await response.json()
    if (!response.ok) throw new Error(result.detail || `Backend returned HTTP ${response.status}.`)
    const safeResult = {
      status: result.status,
      detected_languages: result.detected_languages,
      sanitized_text: result.sanitized_text,
      entities: result.entities,
      validation_findings: result.validation_findings,
      llm_analysis: {
        status: result.llm_analysis?.status,
        summary: result.llm_analysis?.summary,
        findings: result.llm_analysis?.findings,
        error: result.llm_analysis?.error,
      },
    }
    status.textContent = ''
    const output = document.createElement('pre')
    output.textContent = JSON.stringify(safeResult, null, 2)
    status.append(output)
  } catch (error) {
    status.className = 'error'
    status.textContent = error.message || 'The local backend could not process this text.'
  } finally {
    analyzeButton.disabled = false
  }
})
