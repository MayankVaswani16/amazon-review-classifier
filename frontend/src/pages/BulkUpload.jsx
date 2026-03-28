import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import Papa from 'papaparse'
import { FiUploadCloud, FiDownload, FiFile, FiX, FiCheckCircle } from 'react-icons/fi'
import { startBulkJob, getBulkProgress, getBulkResult } from '../api/client'
import Spinner from '../components/Spinner'

export default function BulkUpload() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [columns, setColumns] = useState([])
  const [selectedColumn, setSelectedColumn] = useState('')
  const [reviews, setReviews] = useState([])
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [progress, setProgress] = useState({ processed: 0, total: 0 })
  const [completed, setCompleted] = useState(false)
  const fileInputRef = useRef(null)
  const pollRef = useRef(null)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const handleFileChange = (e) => {
    const f = e.target.files[0]
    if (!f) return
    if (!f.name.endsWith('.csv')) {
      toast.error('Please upload a CSV file')
      return
    }
    setFile(f)
    setResults([])
    setCompleted(false)

    Papa.parse(f, {
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        const cols = result.meta.fields || []
        setColumns(cols)
        setSelectedColumn(cols[0] || '')
        setReviews(result.data)
        toast.success(`Loaded ${result.data.length} rows`)
      },
      error: () => toast.error('Failed to parse CSV'),
    })
  }

  const pollProgress = useCallback((id) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await getBulkProgress(id)
        const { processed, total, status } = res.data

        setProgress({ processed, total })

        if (status === 'COMPLETED') {
          clearInterval(pollRef.current)
          pollRef.current = null

          // Fetch final results
          const resultRes = await getBulkResult(id)
          setResults(resultRes.data)
          setLoading(false)
          setCompleted(true)
          toast.success('Analysis Complete!')

          // Auto-redirect to dashboard after 2s
          setTimeout(() => navigate('/dashboard'), 2000)
        } else if (status === 'FAILED') {
          clearInterval(pollRef.current)
          pollRef.current = null
          setLoading(false)
          setJobId(null)
          toast.error('Bulk analysis failed on server')
        }
      } catch {
        // Silently ignore transient polling errors
      }
    }, 500)
  }, [navigate])

  const handleAnalyze = async () => {
    if (!selectedColumn) {
      toast.error('Please select a column')
      return
    }

    const texts = reviews
      .map((row) => row[selectedColumn])
      .filter((t) => t && t.trim())

    if (texts.length === 0) {
      toast.error('No valid reviews found in selected column')
      return
    }

    setLoading(true)
    setCompleted(false)
    setProgress({ processed: 0, total: texts.length })

    try {
      const res = await startBulkJob(texts)
      const id = res.data.jobId
      setJobId(id)
      pollProgress(id)
    } catch (err) {
      setLoading(false)
      toast.error(err.response?.data?.error || 'Failed to start bulk analysis')
    }
  }

  const handleDownload = () => {
    if (results.length === 0) return

    const csvData = results.map((r) => ({
      review: r.reviewText,
      label: r.label,
      confidence: r.confidence,
      nouns: (r.nouns || []).join('; '),
      adjectives: (r.adjectives || []).join('; '),
      feature_sentiment_pairs: (r.featureSentimentPairs || [])
        .map((p) => `${p[0]}:${p[1]}`)
        .join('; '),
      processed_text: r.processedText,
    }))

    const csv = Papa.unparse(csvData)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'sentiment_results.csv'
    a.click()
    URL.revokeObjectURL(url)
    toast.success('CSV downloaded!')
  }

  const clearFile = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    setFile(null)
    setColumns([])
    setSelectedColumn('')
    setReviews([])
    setResults([])
    setJobId(null)
    setProgress({ processed: 0, total: 0 })
    setCompleted(false)
    setLoading(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const pct = progress.total > 0
    ? Math.round((progress.processed / progress.total) * 1000) / 10
    : 0

  return (
    <div className="page-container space-y-8 animate-fade-in">
      <div className="text-center space-y-3">
        <h1 className="text-4xl font-extrabold bg-gradient-to-r from-primary-400 via-accent-400 to-primary-400 bg-clip-text text-transparent">
          Bulk Upload
        </h1>
        <p className="text-dark-400 max-w-lg mx-auto">
          Upload a CSV file with product reviews to analyze sentiment for all reviews at once.
        </p>
      </div>

      <div className="max-w-4xl mx-auto space-y-6">
        {/* Upload Area */}
        <div className="glass-card p-8">
          {!file ? (
            <label
              htmlFor="csv-upload"
              className="flex flex-col items-center justify-center gap-4 py-12 border-2 border-dashed
                         border-dark-600/50 rounded-xl cursor-pointer hover:border-primary-500/50
                         hover:bg-dark-800/30 transition-all duration-300"
            >
              <FiUploadCloud className="text-dark-500" size={48} />
              <div className="text-center">
                <p className="text-dark-300 font-medium">Drop your CSV file here or click to browse</p>
                <p className="text-dark-500 text-sm mt-1">Supports .csv files with review text columns</p>
              </div>
              <input
                type="file"
                id="csv-upload"
                ref={fileInputRef}
                accept=".csv"
                className="hidden"
                onChange={handleFileChange}
              />
            </label>
          ) : (
            <div className="space-y-4">
              {/* File info */}
              <div className="flex items-center justify-between bg-dark-800/50 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <FiFile className="text-primary-400" size={24} />
                  <div>
                    <p className="text-white font-medium">{file.name}</p>
                    <p className="text-dark-400 text-xs">{reviews.length} rows • {columns.length} columns</p>
                  </div>
                </div>
                <button onClick={clearFile} className="p-2 hover:bg-dark-700 rounded-lg transition-colors">
                  <FiX className="text-dark-400" size={18} />
                </button>
              </div>

              {/* Column Selector */}
              <div className="space-y-2">
                <label className="text-sm text-dark-300 font-medium">Select review text column</label>
                <select
                  id="column-selector"
                  value={selectedColumn}
                  onChange={(e) => setSelectedColumn(e.target.value)}
                  className="input-field"
                >
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              {/* Analyze Button */}
              <button
                id="bulk-analyze-button"
                className="btn-primary w-full flex items-center justify-center gap-2"
                onClick={handleAnalyze}
                disabled={loading}
              >
                {loading ? 'Analyzing...' : `Analyze ${reviews.length} Reviews`}
              </button>
            </div>
          )}
        </div>

        {/* ── Progress UI ─────────────────────────────────────────────── */}
        {loading && jobId && (
          <div className="glass-card p-6 space-y-4 animate-fade-in">
            <div className="flex items-center justify-between text-sm">
              <span className="text-dark-300 font-medium">
                Analyzed{' '}
                <span className="text-white font-semibold">
                  {progress.processed.toLocaleString()}
                </span>
                {' / '}
                <span className="text-white font-semibold">
                  {progress.total.toLocaleString()}
                </span>
                {' reviews'}
              </span>
              <span className="text-primary-400 font-bold text-lg">{pct}%</span>
            </div>

            {/* Progress bar */}
            <div className="w-full h-3 bg-dark-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary-500 to-accent-500 transition-all duration-300 ease-out"
                style={{ width: `${pct}%` }}
              />
            </div>

            <p className="text-dark-500 text-xs text-center">
              Processing in batches of 500 — please keep this page open
            </p>
          </div>
        )}

        {/* ── Completion Banner ────────────────────────────────────────── */}
        {completed && (
          <div className="glass-card p-6 flex items-center justify-center gap-3 animate-fade-in
                          border border-emerald-500/30 bg-emerald-500/5">
            <FiCheckCircle className="text-emerald-400" size={28} />
            <div>
              <p className="text-emerald-400 font-bold text-lg">Analysis Complete!</p>
              <p className="text-dark-400 text-sm">Redirecting to dashboard…</p>
            </div>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">
                Results ({results.length} reviews)
              </h2>
              <button
                id="download-csv-button"
                onClick={handleDownload}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 text-emerald-400
                           border border-emerald-500/30 rounded-lg hover:bg-emerald-500/30 transition-all"
              >
                <FiDownload size={16} />
                Download CSV
              </button>
            </div>

            <div className="glass-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-dark-700/50 bg-dark-800/30">
                      <th className="text-left py-3 px-4 text-dark-400 font-medium">#</th>
                      <th className="text-left py-3 px-4 text-dark-400 font-medium">Review</th>
                      <th className="text-left py-3 px-4 text-dark-400 font-medium">Label</th>
                      <th className="text-left py-3 px-4 text-dark-400 font-medium">Confidence</th>
                      <th className="text-left py-3 px-4 text-dark-400 font-medium">Nouns</th>
                      <th className="text-left py-3 px-4 text-dark-400 font-medium">Adjectives</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r, i) => (
                      <tr
                        key={i}
                        className="border-b border-dark-800/50 hover:bg-dark-800/30 transition-colors"
                      >
                        <td className="py-3 px-4 text-dark-500 text-xs">{i + 1}</td>
                        <td className="py-3 px-4 text-dark-200 max-w-xs truncate">{r.reviewText}</td>
                        <td className="py-3 px-4">
                          <span className={r.label === 'positive' ? 'badge-positive' : 'badge-negative'}>
                            {r.label}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-dark-300 text-xs">
                          {(r.confidence * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex flex-wrap gap-1">
                            {(r.nouns || []).slice(0, 3).map((n, j) => (
                              <span key={j} className="badge-noun text-[10px]">{n}</span>
                            ))}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex flex-wrap gap-1">
                            {(r.adjectives || []).slice(0, 3).map((a, j) => (
                              <span key={j} className="badge-adjective text-[10px]">{a}</span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
