import { useState } from 'react'
import toast from 'react-hot-toast'
import { FiSend, FiZap } from 'react-icons/fi'
import { predictReview } from '../api/client'
import ResultCard from '../components/ResultCard'
import Spinner from '../components/Spinner'

const sampleReviews = [
  "This product is absolutely amazing! The quality is outstanding and it arrived faster than expected.",
  "Terrible purchase. The item broke after just one day of use. Complete waste of money.",
  "Decent product for the price. Not the best quality but gets the job done.",
  "Love this item! It exceeded all my expectations. The battery life is incredible.",
  "Very disappointed. The product doesn't match the description and customer service was unhelpful.",
]

export default function Analyzer() {
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleAnalyze = async () => {
    if (!text.trim()) {
      toast.error('Please enter a review to analyze')
      return
    }

    setLoading(true)
    setResult(null)
    try {
      const res = await predictReview(text)
      setResult(res.data)
      toast.success('Analysis complete!')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to analyze review')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container space-y-10 animate-fade-in">
      {/* Header */}
      <div className="text-center space-y-3 max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold tracking-tight" style={{ color: '#e4e1e9', letterSpacing: '-0.03em' }}>
          Sentiment Analyzer
        </h1>
        <p className="text-base leading-relaxed" style={{ color: '#908fa0' }}>
          Paste an Amazon product review below to analyze its sentiment, extract key features,
          and identify sentiment descriptors using NLP.
        </p>
      </div>

      {/* Input Section */}
      <div className="max-w-3xl mx-auto space-y-5">
        <div className="glass-card p-6 space-y-4">
          <textarea
            id="review-input"
            className="input-field min-h-[180px] resize-y text-[15px] leading-relaxed"
            placeholder="Paste your Amazon product review here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={loading}
          />

          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2 text-xs" style={{ color: '#64748b' }}>
              <FiZap size={13} strokeWidth={2} />
              <span>{text.length} characters</span>
            </div>
            <button
              id="analyze-button"
              className="btn-primary flex items-center gap-2 text-sm"
              onClick={handleAnalyze}
              disabled={loading || !text.trim()}
            >
              <FiSend size={15} strokeWidth={2} />
              {loading ? 'Analyzing...' : 'Analyze Review'}
            </button>
          </div>
        </div>

        {/* Sample reviews */}
        <div className="space-y-3">
          <p className="label-meta">Try a sample review</p>
          <div className="flex flex-wrap gap-2">
            {sampleReviews.map((review, i) => (
              <button
                key={i}
                onClick={() => setText(review)}
                className="text-xs rounded-lg px-3 py-2 text-left max-w-xs truncate transition-all duration-200"
                style={{
                  background: '#1b1b20',
                  color: '#908fa0',
                  border: '1px solid rgba(144, 143, 160, 0.08)',
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = '#2a292f'
                  e.target.style.color = '#c7c4d7'
                  e.target.style.borderColor = 'rgba(99, 102, 241, 0.2)'
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = '#1b1b20'
                  e.target.style.color = '#908fa0'
                  e.target.style.borderColor = 'rgba(144, 143, 160, 0.08)'
                }}
              >
                {review.substring(0, 60)}...
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading */}
      {loading && <Spinner text="Analyzing sentiment..." />}

      {/* Result */}
      {result && (
        <div className="max-w-3xl mx-auto">
          <ResultCard result={result} />
        </div>
      )}
    </div>
  )
}
