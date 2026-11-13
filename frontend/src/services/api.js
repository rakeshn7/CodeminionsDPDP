import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export function getSafeApiError(error, { audit = false } = {}) {
  if (!axios.isAxiosError(error)) {
    return 'The request could not be completed.'
  }

  const status = error.response?.status
  if (audit && status === 401) {
    return 'Audit access is protected. Configure AUDIT_API_KEY in the local Vite server environment and restart it.'
  }
  if (audit && status === 503) {
    return 'Audit access is unavailable because the backend has not configured AUDIT_API_KEY.'
  }
  if (status === 413) {
    return 'The file exceeds the 25 MB upload limit.'
  }
  if (status === 422) {
    return 'The backend rejected the request. Check that the document is not empty and the selected task is supported.'
  }
  if (status === 502) {
    return 'The backend could not complete the protected provider request. No successful result was returned.'
  }
  if (status) {
    return `The backend request failed (HTTP ${status}).`
  }
  if (error.code === 'ECONNABORTED') {
    return 'The backend request timed out. No result was returned.'
  }
  return 'The backend is unavailable. Check that FastAPI is running on 127.0.0.1:8000.'
}

export const getHealth = async () => {
  const { data } = await api.get('/health')
  return data
}

export const processRequest = async ({ text, task = 'summarize', provider = 'configured_provider' }) => {
  const { data } = await api.post('/api/process', {
    text,
    task,
    provider,
  })
  return data
}

export const getAudit = async () => {
  const { data } = await api.get('/api/audit')
  return data
}

export const getAuditById = async (requestId) => {
  const { data } = await api.get(`/api/audit/${encodeURIComponent(requestId)}`)
  return data
}

export const getMetrics = async () => {
  const { data } = await api.get('/api/metrics')
  return data
}

export const getOcrStatus = async () => {
  const { data } = await api.get('/api/ocr/status')
  return data
}

export const analyzeDocument = async ({ file, text, filename, runLlm = true, provider = 'configured_provider' }) => {
  if (file) {
    const formData = new FormData()
    formData.append('file', file)
    if (provider) formData.append('provider', provider)
    formData.append('run_llm', String(runLlm))
    const { data } = await api.post('/api/documents/analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  }

  const { data } = await api.post('/api/documents/analyze', {
    text,
    filename: filename || 'document.txt',
    run_llm: runLlm,
    provider,
  })
  return data
}

export default api
