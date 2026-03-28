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
    <div className="page-container space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="section-title text-3xl">Prediction History</h1>
          <p className="text-dark-400 text-sm mt-1">{totalElements} total predictions</p>
        </div>
      </div>

      {predictions.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <FiClock className="mx-auto text-dark-600 mb-4" size={48} />
          <p className="text-dark-400 text-lg">No predictions yet</p>
          <p className="text-dark-500 text-sm mt-1">Your analyzed reviews will appear here</p>
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dark-700/50 bg-dark-800/30">
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">ID</th>
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Review</th>
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Label</th>
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Confidence</th>
                    <th className="text-left py-3 px-4 text-dark-400 font-medium">Date</th>
                    <th className="text-right py-3 px-4 text-dark-400 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((pred) => (
                    <tr
                      key={pred.id}
                      className="border-b border-dark-800/50 hover:bg-dark-800/30 transition-colors"
                    >
                      <td className="py-3 px-4 text-dark-400 font-mono text-xs">#{pred.id}</td>
                      <td className="py-3 px-4 text-dark-200 max-w-xs truncate">
                        {pred.reviewText}
                      </td>
                      <td className="py-3 px-4">
                        <span className={pred.label === 'positive' ? 'badge-positive' : 'badge-negative'}>
                          {pred.label}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-dark-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                pred.label === 'positive' ? 'bg-emerald-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${(pred.confidence * 100)}%` }}
                            />
                          </div>
                          <span className="text-dark-300 text-xs">
                            {(pred.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-dark-400 text-xs whitespace-nowrap">
                        {new Date(pred.createdAt).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleDelete(pred.id)}
                          className="btn-danger text-xs flex items-center gap-1 ml-auto"
                          id={`delete-btn-${pred.id}`}
                        >
                          <FiTrash2 size={12} />
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
              <p className="text-dark-500 text-sm">
                Page {page + 1} of {totalPages}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="p-2 rounded-lg bg-dark-800/50 border border-dark-700/30 text-dark-300
                             hover:bg-dark-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  <FiChevronLeft size={18} />
                </button>
                {[...Array(Math.min(5, totalPages))].map((_, i) => {
                  const pageNum = Math.max(0, Math.min(page - 2, totalPages - 5)) + i
                  if (pageNum >= totalPages) return null
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPage(pageNum)}
                      className={`w-9 h-9 rounded-lg text-sm font-medium transition-all ${
                        pageNum === page
                          ? 'bg-primary-600 text-white shadow-lg shadow-primary-500/25'
                          : 'bg-dark-800/50 border border-dark-700/30 text-dark-300 hover:bg-dark-700/50'
                      }`}
                    >
                      {pageNum + 1}
                    </button>
                  )
                })}
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="p-2 rounded-lg bg-dark-800/50 border border-dark-700/30 text-dark-300
                             hover:bg-dark-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  <FiChevronRight size={18} />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
