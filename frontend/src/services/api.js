import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

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
  const { data } = await api.get(`/api/audit/${requestId}`)
  return data
}

export const getMetrics = async () => {
  const { data } = await api.get('/api/metrics')
  return data
}

export default api
