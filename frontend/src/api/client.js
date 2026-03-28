import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8081'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Prediction ───────────────────────────────────────────────────────
export const predictReview = (text) =>
  client.post('/api/predict', { text })

export const predictBulk = (reviews) =>
  client.post('/api/predict/bulk', { reviews })

// ── Async Bulk Job ──────────────────────────────────────────────────
export const startBulkJob = (reviews) =>
  client.post('/api/predict/bulk/async', { reviews })

export const getBulkProgress = (jobId) =>
  client.get(`/api/predict/bulk/progress/${jobId}`)

export const getBulkResult = (jobId) =>
  client.get(`/api/predict/bulk/result/${jobId}`)

// ── History ──────────────────────────────────────────────────────────
export const getHistory = (page = 0, size = 10) =>
  client.get('/api/history', { params: { page, size } })

export const getHistoryById = (id) =>
  client.get(`/api/history/${id}`)

export const deleteHistory = (id) =>
  client.delete(`/api/history/${id}`)

// ── Stats ────────────────────────────────────────────────────────────
export const getStats = () =>
  client.get('/api/stats')

// ── t-SNE images ─────────────────────────────────────────────────────
export const getTsneBefore = () =>
  `${API_BASE_URL}/api/tsne/before`

export const getTsneAfter = () =>
  `${API_BASE_URL}/api/tsne/after`

// ── Health ───────────────────────────────────────────────────────────
export const getHealth = () =>
  client.get('/api/health')

export default client
