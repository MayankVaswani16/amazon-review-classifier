import axios from 'axios'

/**
 * Single source of truth for the backend contract.
 *
 * Every network call in the application goes through this file. No component
 * ever constructs a URL or sets a header, which means adding auth is one
 * interceptor, changing the base URL is one line, and mocking the API in tests
 * is mocking one module.
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8081'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
})

/**
 * Normalises an axios error into a message worth showing a user.
 *
 * The backend emits both `error` and `message`; validation failures also carry
 * an `errors` array. Previously the UI only read `data.error`, so validation
 * messages fell through to a generic fallback and the real reason was lost.
 */
export function errorMessage(err, fallback = 'Something went wrong') {
  const data = err?.response?.data
  if (!data) {
    if (err?.code === 'ECONNABORTED') return 'Request timed out'
    return err?.message || fallback
  }
  if (Array.isArray(data.errors) && data.errors.length) return data.errors[0]
  return data.error || data.message || fallback
}

// ── Prediction ───────────────────────────────────────────────────────
export const predictReview = (text) => client.post('/api/predict', { text })

/** Per-token attribution and the minimal edit that flips the verdict. */
export const explainReview = (text, topK = 12) =>
  client.post('/api/explain', { text }, { params: { topK } })

// ── Async bulk job ───────────────────────────────────────────────────
export const startBulkJob = (reviews) =>
  client.post('/api/predict/bulk/async', { reviews })

export const getBulkProgress = (jobId) =>
  client.get(`/api/predict/bulk/progress/${jobId}`)

export const getBulkResult = (jobId) =>
  client.get(`/api/predict/bulk/result/${jobId}`)

export const deleteBatch = (batchId) => client.delete(`/api/batch/${batchId}`)

// ── History ──────────────────────────────────────────────────────────
export const getHistory = (page = 0, size = 10, batchId = null) =>
  client.get('/api/history', { params: { page, size, ...(batchId ? { batchId } : {}) } })

export const getHistoryById = (id) => client.get(`/api/history/${id}`)

export const deleteHistory = (id) => client.delete(`/api/history/${id}`)

// ── Stats and model introspection ────────────────────────────────────
export const getStats = (batchId = null) =>
  client.get('/api/stats', { params: batchId ? { batchId } : {} })

export const getModelMetrics = () => client.get('/api/model/metrics')

export const getModelFeatures = (k = 20) =>
  client.get('/api/model/features', { params: { k } })

// ── t-SNE images ─────────────────────────────────────────────────────
// Returns a URL, not a promise: these are used as <img src> so the browser
// fetches them natively rather than pulling bytes through JavaScript.
export const getTsneBefore = () => `${API_BASE_URL}/api/tsne/before`
export const getTsneAfter = () => `${API_BASE_URL}/api/tsne/after`

// ── Health ───────────────────────────────────────────────────────────
export const getHealth = () => client.get('/api/health')

export default client
