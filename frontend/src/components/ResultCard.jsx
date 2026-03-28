export default function ResultCard({ result }) {
  if (!result) return null

  const isPositive = result.label === 'positive'
  const confidencePct = (result.confidence * 100).toFixed(1)

  return (
    <div className="glass-card p-6 animate-slide-up space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Analysis Result</h3>
        <span className={isPositive ? 'badge-positive text-sm' : 'badge-negative text-sm'}>
          {result.label.toUpperCase()}
        </span>
      </div>

      {/* Confidence Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-dark-400">Confidence</span>
          <span className={`font-semibold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
            {confidencePct}%
          </span>
        </div>
        <div className="h-3 bg-dark-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-1000 ease-out ${
              isPositive
                ? 'bg-gradient-to-r from-emerald-500 to-emerald-400'
                : 'bg-gradient-to-r from-red-500 to-red-400'
            }`}
            style={{ width: `${confidencePct}%` }}
          />
        </div>
      </div>

      {/* Nouns & Adjectives */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Nouns */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-dark-300 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-sky-500" />
            Product Features (Nouns)
          </h4>
          <div className="flex flex-wrap gap-2">
            {result.nouns && result.nouns.length > 0 ? (
              result.nouns.map((noun, i) => (
                <span key={i} className="badge-noun">{noun}</span>
              ))
            ) : (
              <span className="text-dark-500 text-xs">No nouns detected</span>
            )}
          </div>
        </div>

        {/* Adjectives */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-dark-300 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-violet-500" />
            Sentiment Descriptors (Adjectives)
          </h4>
          <div className="flex flex-wrap gap-2">
            {result.adjectives && result.adjectives.length > 0 ? (
              result.adjectives.map((adj, i) => (
                <span key={i} className="badge-adjective">{adj}</span>
              ))
            ) : (
              <span className="text-dark-500 text-xs">No adjectives detected</span>
            )}
          </div>
        </div>
      </div>

      {/* Feature-Sentiment Pairs Table */}
      {result.featureSentimentPairs && result.featureSentimentPairs.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-dark-300">Feature → Sentiment Pairs</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-700">
                  <th className="text-left py-2 px-3 text-dark-400 font-medium">Feature</th>
                  <th className="text-left py-2 px-3 text-dark-400 font-medium">Sentiment</th>
                </tr>
              </thead>
              <tbody>
                {result.featureSentimentPairs.map((pair, i) => (
                  <tr key={i} className="border-b border-dark-800/50 hover:bg-dark-800/30 transition-colors">
                    <td className="py-2 px-3 text-sky-400">{pair[0]}</td>
                    <td className="py-2 px-3 text-violet-400">{pair[1]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Processed Text */}
      {result.processedText && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-dark-300">Processed Text</h4>
          <p className="text-xs text-dark-400 bg-dark-800/50 rounded-lg p-3 font-mono leading-relaxed">
            {result.processedText}
          </p>
        </div>
      )}
    </div>
  )
}
