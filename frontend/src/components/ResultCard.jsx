import { useState } from 'react'
import toast from 'react-hot-toast'
import { explainReview, errorMessage } from '../api/client'

/**
 * Colour and copy for each verdict.
 *
 * The original code hardcoded `const isPositive = result.label === 'positive'`
 * and derived every colour from that boolean, baking a binary assumption into
 * the presentation layer. Adding "mixed" would have meant editing every ternary.
 * A lookup keeps label handling in one place.
 */
const LABELS = {
  positive: {
    text: '#4edea3',
    bar: 'linear-gradient(90deg, #00a572, #4edea3)',
    badge: 'badge-positive',
    blurb: 'Overall sentiment is positive',
  },
  negative: {
    text: '#ffb4ab',
    bar: 'linear-gradient(90deg, #93000a, #ffb4ab)',
    badge: 'badge-negative',
    blurb: 'Overall sentiment is negative',
  },
  mixed: {
    text: '#fbbf24',
    bar: 'linear-gradient(90deg, #b45309, #fbbf24)',
    badge: 'badge-adjective',
    blurb: 'This review praises some features and criticises others',
  },
}

const labelStyle = (label) => LABELS[label] || LABELS.mixed

function PolarityPill({ label, polarity }) {
  const colour =
    label === 'positive' ? '#4edea3' : label === 'negative' ? '#ffb4ab' : '#908fa0'
  const value = typeof polarity === 'number' ? polarity : 0
  return (
    <span
      className="text-[11px] font-semibold tabular-nums"
      style={{ color: colour }}
      title={`polarity ${value.toFixed(3)}`}
    >
      {value > 0 ? '+' : ''}
      {value.toFixed(2)}
    </span>
  )
}

export default function ResultCard({ result }) {
  const [explanation, setExplanation] = useState(null)
  const [explaining, setExplaining] = useState(false)

  if (!result) return null

  const style = labelStyle(result.label)
  const confidencePct = (result.confidence * 100).toFixed(1)
  const coveragePct = result.coverage != null ? (result.coverage * 100).toFixed(0) : null

  const handleExplain = async () => {
    setExplaining(true)
    try {
      const res = await explainReview(result.reviewText, 10)
      setExplanation(res.data)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not explain this prediction'))
    } finally {
      setExplaining(false)
    }
  }

  const maxContribution = explanation?.contributions?.length
    ? Math.max(...explanation.contributions.map((c) => Math.abs(c.contribution)))
    : 1

  return (
    <div className="glass-card p-8 animate-slide-up space-y-8">
      {/* Verdict */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="space-y-1">
          <p className="label-meta">Analysis Result</p>
          <div className="flex items-center gap-4">
            <span className={`${style.badge} text-sm`}>{result.label?.toUpperCase()}</span>
            <span className="text-2xl font-bold tracking-tight" style={{ color: '#e4e1e9' }}>
              {confidencePct}%
            </span>
          </div>
          <p className="text-xs pt-1" style={{ color: '#908fa0' }}>
            {style.blurb}
          </p>
        </div>

        <button
          onClick={handleExplain}
          disabled={explaining}
          className="text-xs rounded-lg px-3 py-2 transition-all duration-200"
          style={{
            background: '#1b1b20',
            color: '#c7c4d7',
            border: '1px solid rgba(99, 102, 241, 0.25)',
          }}
        >
          {explaining ? 'Analysing…' : explanation ? 'Refresh explanation' : 'Why this verdict?'}
        </button>
      </div>

      {/* Trust banners — the system stating what it does not know */}
      {result.lowSignal && (
        <div
          className="rounded-xl p-4 text-xs leading-relaxed"
          style={{
            background: 'rgba(251, 191, 36, 0.08)',
            border: '1px solid rgba(251, 191, 36, 0.3)',
            color: '#fbbf24',
          }}
        >
          <strong>Low signal.</strong> Neither the trained model nor the rule engine found much
          evidence here — the model recognised {coveragePct}% of the words and no clear sentiment
          terms were present. Treat this as a guess rather than a measurement.
        </div>
      )}

      {result.agreement === false && !result.lowSignal && (
        <div
          className="rounded-xl p-4 text-xs leading-relaxed"
          style={{
            background: 'rgba(99, 102, 241, 0.08)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            color: '#a5b4fc',
          }}
        >
          <strong>Engines disagree.</strong> The trained classifier said{' '}
          <em>{result.modelLabel}</em>; the rule-based lexicon said <em>{result.lexiconLabel}</em>.
          The verdict blends both, weighted by how much each actually knows about this text.
          Disagreement usually signals nuance — irony, hedging, or mixed opinions.
        </div>
      )}

      {/* Confidence */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs">
          <span style={{ color: '#908fa0' }}>Confidence</span>
          <span className="font-semibold" style={{ color: style.text }}>
            {confidencePct}%
          </span>
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: '#0e0e13' }}>
          <div
            className="h-full rounded-full transition-all duration-1000 ease-out"
            style={{ width: `${confidencePct}%`, background: style.bar }}
          />
        </div>
      </div>

      {/* Engine breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat
          label="Model says"
          value={result.modelLabel || '—'}
          sub={result.modelConfidence != null ? `${(result.modelConfidence * 100).toFixed(0)}%` : ''}
        />
        <Stat
          label="Lexicon says"
          value={result.lexiconLabel || '—'}
          sub={result.lexiconScore != null ? result.lexiconScore.toFixed(2) : ''}
        />
        <Stat
          label="Vocab coverage"
          value={coveragePct != null ? `${coveragePct}%` : '—'}
          sub="words the model knows"
        />
        <Stat
          label="Aspect conflict"
          value={result.conflictScore != null ? result.conflictScore.toFixed(2) : '0.00'}
          sub="0 = unanimous"
        />
      </div>

      {/* Aspect-level sentiment */}
      {result.aspects?.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium" style={{ color: '#c7c4d7' }}>
            Aspect Sentiment
          </h4>
          <div className="overflow-x-auto rounded-xl" style={{ background: '#0e0e13' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Opinion</th>
                  <th>Polarity</th>
                  <th>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {result.aspects.map((a, i) => (
                  <tr key={i}>
                    <td style={{ color: '#7dd3fc' }}>{a.aspect}</td>
                    <td style={{ color: '#c4b5fd' }}>
                      {a.negated && (
                        <span
                          className="text-[10px] mr-1 px-1 rounded"
                          style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24' }}
                          title="This opinion was negated — polarity is flipped"
                        >
                          NOT
                        </span>
                      )}
                      {a.opinion}
                    </td>
                    <td>
                      <PolarityPill label={a.label} polarity={a.polarity} />
                    </td>
                    <td className="text-xs" style={{ color: '#908fa0' }}>
                      {a.label}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Explanation */}
      {explanation && (
        <div className="space-y-5">
          <div className="space-y-3">
            <h4 className="text-sm font-medium" style={{ color: '#c7c4d7' }}>
              Evidence
            </h4>
            <p className="text-xs" style={{ color: '#64748b' }}>
              Each bar is a term's exact contribution to the decision. For a linear model these
              are not estimates — they sum precisely to the decision score, so nothing is hidden.
            </p>
            <div className="space-y-1.5">
              {explanation.contributions?.map((c, i) => {
                const pct = (Math.abs(c.contribution) / maxContribution) * 100
                const positive = c.direction === 'positive'
                return (
                  <div key={i} className="flex items-center gap-3 text-xs">
                    <span
                      className="font-mono w-40 truncate"
                      style={{ color: '#c7c4d7' }}
                      title={c.term}
                    >
                      {c.term}
                    </span>
                    <div
                      className="flex-1 h-2 rounded-full overflow-hidden"
                      style={{ background: '#0e0e13' }}
                    >
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${pct}%`, background: positive ? '#00a572' : '#93000a' }}
                      />
                    </div>
                    <span
                      className="w-16 text-right tabular-nums font-mono"
                      style={{ color: positive ? '#4edea3' : '#ffb4ab' }}
                    >
                      {c.contribution > 0 ? '+' : ''}
                      {c.contribution.toFixed(3)}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {explanation.counterfactual?.found && (
            <div
              className="rounded-xl p-4 space-y-2"
              style={{
                background: 'rgba(99, 102, 241, 0.06)',
                border: '1px solid rgba(99, 102, 241, 0.2)',
              }}
            >
              <h4 className="text-sm font-medium" style={{ color: '#a5b4fc' }}>
                What would change the verdict
              </h4>
              <p className="text-xs leading-relaxed" style={{ color: '#c7c4d7' }}>
                Removing{' '}
                {explanation.counterfactual.removedTerms.map((t, i) => (
                  <span key={i}>
                    <code
                      className="px-1.5 py-0.5 rounded font-mono"
                      style={{ background: '#0e0e13', color: '#fbbf24' }}
                    >
                      {t}
                    </code>
                    {i < explanation.counterfactual.removedTerms.length - 1 ? ' and ' : ''}
                  </span>
                ))}{' '}
                would flip this from{' '}
                <strong style={{ color: '#ffb4ab' }}>
                  {explanation.counterfactual.originalLabel}
                </strong>{' '}
                to{' '}
                <strong style={{ color: '#4edea3' }}>
                  {explanation.counterfactual.flippedLabel}
                </strong>
                .
              </p>
            </div>
          )}
        </div>
      )}

      {/* Extracted terms */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <TermGroup
          title="Product Features"
          dot="#38bdf8"
          items={result.nouns}
          cls="badge-noun"
          empty="No nouns detected"
        />
        <TermGroup
          title="Sentiment Descriptors"
          dot="#a78bfa"
          items={result.adjectives}
          cls="badge-adjective"
          empty="No adjectives detected"
        />
      </div>

      {/* Processed text */}
      {result.processedText && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium" style={{ color: '#c7c4d7' }}>
            Processed Text
          </h4>
          <p className="text-xs" style={{ color: '#64748b' }}>
            What the classifier actually saw after cleaning, stopword removal (negations kept) and
            lemmatisation.
          </p>
          <p
            className="text-xs font-mono leading-relaxed rounded-xl p-4"
            style={{ background: '#0e0e13', color: '#908fa0' }}
          >
            {result.processedText}
          </p>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, sub }) {
  return (
    <div className="rounded-xl p-3" style={{ background: '#0e0e13' }}>
      <p className="text-[10px] uppercase tracking-wide" style={{ color: '#64748b' }}>
        {label}
      </p>
      <p className="text-sm font-semibold mt-0.5" style={{ color: '#e4e1e9' }}>
        {value}
      </p>
      {sub && (
        <p className="text-[10px] mt-0.5" style={{ color: '#64748b' }}>
          {sub}
        </p>
      )}
    </div>
  )
}

function TermGroup({ title, dot, items, cls, empty }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full" style={{ background: dot }} />
        <h4 className="text-sm font-medium" style={{ color: '#c7c4d7' }}>
          {title}
        </h4>
      </div>
      <div className="flex flex-wrap gap-2">
        {items?.length > 0 ? (
          items.map((item, i) => (
            <span key={i} className={cls}>
              {item}
            </span>
          ))
        ) : (
          <span className="text-xs" style={{ color: '#64748b' }}>
            {empty}
          </span>
        )}
      </div>
    </div>
  )
}
