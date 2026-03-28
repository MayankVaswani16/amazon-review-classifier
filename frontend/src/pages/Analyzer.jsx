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
    <div className="page-container space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center space-y-3">
        <h1 className="text-4xl font-extrabold bg-gradient-to-r from-primary-400 via-accent-400 to-primary-400 bg-clip-text text-transparent">
          Sentiment Analyzer
        </h1>
        <p className="text-dark-400 max-w-lg mx-auto">
          Paste an Amazon product review below to analyze its sentiment, extract key features,
          and identify sentiment descriptors using NLP.
        </p>
      </div>

      {/* Input Section */}
      <div className="max-w-3xl mx-auto space-y-4">
        <div className="glass-card p-6 space-y-4">
          <textarea
            id="review-input"
            className="input-field min-h-[160px] resize-y"
            placeholder="Paste your Amazon product review here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={loading}
          />

          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2 text-dark-500 text-xs">
              <FiZap size={14} />
              <span>{text.length} characters</span>
            </div>
            <button
              id="analyze-button"
              className="btn-primary flex items-center gap-2"
              onClick={handleAnalyze}
              disabled={loading || !text.trim()}
            >
              <FiSend size={16} />
              {loading ? 'Analyzing...' : 'Analyze Review'}
            </button>
          </div>
        </div>

        {/* Sample reviews */}
        <div className="space-y-2">
          <p className="text-dark-500 text-xs font-medium uppercase tracking-wider">Try a sample review</p>
          <div className="flex flex-wrap gap-2">
            {sampleReviews.map((review, i) => (
              <button
                key={i}
                onClick={() => setText(review)}
                className="text-xs text-dark-400 bg-dark-800/50 border border-dark-700/30 rounded-lg px-3 py-2
                           hover:bg-dark-700/50 hover:text-dark-200 transition-all duration-200 text-left max-w-xs truncate"
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
