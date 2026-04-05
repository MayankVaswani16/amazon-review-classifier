export default function ResultCard({ result }) {
  if (!result) return null

  const isPositive = result.label === 'positive'
  const confidencePct = (result.confidence * 100).toFixed(1)

  return (
    <div className="glass-card p-8 animate-slide-up space-y-8">
      {/* Header — Sentiment + Confidence */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="label-meta">Analysis Result</p>
          <div className="flex items-center gap-4">
            <span className={isPositive ? 'badge-positive text-sm' : 'badge-negative text-sm'}>
              {result.label.toUpperCase()}
            </span>
            <span className="text-2xl font-bold tracking-tight" style={{ color: '#e4e1e9' }}>
              {confidencePct}%
            </span>
          </div>
        </div>
      </div>

      {/* Confidence Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs">
          <span style={{ color: '#908fa0' }}>Confidence</span>
          <span className="font-semibold" style={{ color: isPositive ? '#4edea3' : '#ffb4ab' }}>
            {confidencePct}%
          </span>
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: '#0e0e13' }}>
          <div
            className="h-full rounded-full transition-all duration-1000 ease-out"
            style={{
              width: `${confidencePct}%`,
              background: isPositive
                ? 'linear-gradient(90deg, #00a572, #4edea3)'
                : 'linear-gradient(90deg, #93000a, #ffb4ab)',
            }}
          />
        </div>
      </div>

      {/* Nouns & Adjectives */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Nouns */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ background: '#38bdf8' }} />
            <h4 className="text-sm font-medium" style={{ color: '#c7c4d7' }}>
              Product Features
            </h4>
          </div>
          <div className="flex flex-wrap gap-2">
            {result.nouns && result.nouns.length > 0 ? (
              result.nouns.map((noun, i) => (
                <span key={i} className="badge-noun">{noun}</span>
              ))
            ) : (
              <span className="text-xs" style={{ color: '#64748b' }}>No nouns detected</span>
            )}
          </div>
        </div>

        {/* Adjectives */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ background: '#a78bfa' }} />
            <h4 className="text-sm font-medium" style={{ color: '#c7c4d7' }}>
              Sentiment Descriptors
            </h4>
          </div>
          <div className="flex flex-wrap gap-2">
            {result.adjectives && result.adjectives.length > 0 ? (
              result.adjectives.map((adj, i) => (
                <span key={i} className="badge-adjective">{adj}</span>
              ))
            ) : (
              <span className="text-xs" style={{ color: '#64748b' }}>No adjectives detected</span>
            )}
          </div>
        </div>
      </div>

      {/* Feature-Sentiment Pairs Table */}
      {result.featureSentimentPairs && result.featureSentimentPairs.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium" style={{ color: '#c7c4d7' }}>
            Feature → Sentiment Pairs
          </h4>
          <div className="overflow-x-auto rounded-xl" style={{ background: '#0e0e13' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Sentiment</th>
                </tr>
              </thead>
              <tbody>
                {result.featureSentimentPairs.map((pair, i) => (
                  <tr key={i}>
                    <td style={{ color: '#7dd3fc' }}>{pair[0]}</td>
                    <td style={{ color: '#c4b5fd' }}>{pair[1]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Processed Text */}
      {result.processedText && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium" style={{ color: '#c7c4d7' }}>Processed Text</h4>
          <p className="text-xs font-mono leading-relaxed rounded-xl p-4"
             style={{ background: '#0e0e13', color: '#908fa0' }}>
            {result.processedText}
          </p>
        </div>
      )}
    </div>
  )
}
