import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { FiTrash2, FiChevronLeft, FiChevronRight, FiClock } from 'react-icons/fi'
import { getHistory, deleteHistory } from '../api/client'
import Spinner from '../components/Spinner'

export default function History() {
  const [data, setData] = useState(null)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const pageSize = 10

  useEffect(() => {
    fetchHistory()
  }, [page])

  const fetchHistory = async () => {
    setLoading(true)
    try {
      const res = await getHistory(page, pageSize)
      setData(res.data)
    } catch (err) {
      toast.error('Failed to load history')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteHistory(id)
      toast.success('Prediction deleted')
      fetchHistory()
    } catch (err) {
      toast.error('Failed to delete prediction')
    }
  }

  if (loading && !data) return <Spinner size="lg" text="Loading history..." />

  const predictions = data?.content || []
  const totalPages = data?.totalPages || 0
  const totalElements = data?.totalElements || 0

  return (
    <div className="page-container space-y-8 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="section-title text-3xl" style={{ letterSpacing: '-0.03em' }}>Prediction History</h1>
          <p className="text-sm mt-1.5" style={{ color: '#908fa0' }}>
            {totalElements.toLocaleString()} total predictions
          </p>
        </div>
      </div>

      {predictions.length === 0 ? (
        <div className="glass-card p-16 text-center">
          <FiClock className="mx-auto mb-4" size={44} style={{ color: '#464554' }} strokeWidth={1.5} />
          <p className="text-lg font-medium" style={{ color: '#c7c4d7' }}>No predictions yet</p>
          <p className="text-sm mt-1.5" style={{ color: '#64748b' }}>Your analyzed reviews will appear here</p>
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Review</th>
                    <th>Label</th>
                    <th>Confidence</th>
                    <th>Date</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((pred) => (
                    <tr key={pred.id}>
                      <td className="font-mono text-xs" style={{ color: '#64748b' }}>#{pred.id}</td>
                      <td className="max-w-xs truncate" style={{ color: '#c7c4d7' }}>
                        {pred.reviewText}
                      </td>
                      <td>
                        <span className={pred.label === 'positive' ? 'badge-positive' : 'badge-negative'}>
                          {pred.label}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-2.5">
                          <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: '#0e0e13' }}>
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${(pred.confidence * 100)}%`,
                                background: pred.label === 'positive'
                                  ? '#4edea3'
                                  : '#ffb4ab',
                              }}
                            />
                          </div>
                          <span className="text-xs font-medium" style={{ color: '#c7c4d7' }}>
                            {(pred.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td className="text-xs whitespace-nowrap" style={{ color: '#908fa0' }}>
                        {new Date(pred.createdAt).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="text-right">
                        <button
                          onClick={() => handleDelete(pred.id)}
                          className="btn-danger flex items-center gap-1.5 ml-auto"
                          id={`delete-btn-${pred.id}`}
                        >
                          <FiTrash2 size={12} strokeWidth={2} />
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm" style={{ color: '#64748b' }}>
                Page {page + 1} of {totalPages}
              </p>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="p-2 rounded-lg transition-all duration-200 disabled:opacity-20 disabled:cursor-not-allowed"
                  style={{
                    background: '#1b1b20',
                    color: '#c7c4d7',
                    border: '1px solid rgba(144, 143, 160, 0.08)',
                  }}
                >
                  <FiChevronLeft size={16} strokeWidth={2} />
                </button>
                {[...Array(Math.min(5, totalPages))].map((_, i) => {
                  const pageNum = Math.max(0, Math.min(page - 2, totalPages - 5)) + i
                  if (pageNum >= totalPages) return null
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPage(pageNum)}
                      className="w-9 h-9 rounded-lg text-sm font-medium transition-all duration-200"
                      style={
                        pageNum === page
                          ? {
                              background: 'linear-gradient(135deg, #8083ff, #6366f1)',
                              color: '#e1e0ff',
                              boxShadow: '0 4px 16px rgba(99, 102, 241, 0.3)',
                            }
                          : {
                              background: '#1b1b20',
                              color: '#908fa0',
                              border: '1px solid rgba(144, 143, 160, 0.08)',
                            }
                      }
                    >
                      {pageNum + 1}
                    </button>
                  )
                })}
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="p-2 rounded-lg transition-all duration-200 disabled:opacity-20 disabled:cursor-not-allowed"
                  style={{
                    background: '#1b1b20',
                    color: '#c7c4d7',
                    border: '1px solid rgba(144, 143, 160, 0.08)',
                  }}
                >
                  <FiChevronRight size={16} strokeWidth={2} />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
