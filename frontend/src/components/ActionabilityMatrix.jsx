/**
 * Aspect Actionability Matrix.
 *
 * Answers "what should I fix first?" rather than "what gets mentioned most?".
 * Those are different questions and the answers usually differ: the
 * most-mentioned aspect in a review corpus is typically something
 * uncontroversial, while the aspect actually driving unhappiness may be
 * mentioned far less often.
 *
 * The ranking is volume x severity x lift, where lift is how far the negative
 * rate among reviews mentioning an aspect sits above the corpus baseline.
 */
export default function ActionabilityMatrix({ aspects, baselineNegativeRate }) {
  if (!aspects?.length) {
    return (
      <div className="glass-card p-6 space-y-2">
        <h3 className="text-base font-semibold" style={{ color: '#e4e1e9' }}>
          Aspect Actionability Matrix
        </h3>
        <p className="text-sm" style={{ color: '#64748b' }}>
          Not enough data yet. Analyse a batch of reviews — an aspect needs at least three
          mentions before its lift is statistically meaningful.
        </p>
      </div>
    )
  }

  const maxImpact = Math.max(...aspects.map((a) => a.impactScore), 0.0001)
  const baselinePct = ((baselineNegativeRate || 0) * 100).toFixed(0)

  return (
    <div className="glass-card p-6 space-y-5">
      <div className="space-y-1">
        <h3 className="text-base font-semibold" style={{ color: '#e4e1e9' }}>
          Aspect Actionability Matrix
        </h3>
        <p className="text-xs leading-relaxed" style={{ color: '#908fa0' }}>
          Ranked by how strongly mentioning each feature predicts an unhappy customer — not by
          how often it comes up. <strong style={{ color: '#c7c4d7' }}>Lift</strong> is the gap
          between an aspect's negative rate and the {baselinePct}% corpus baseline. A feature
          can be mentioned constantly and still have negative lift, meaning people who talk
          about it tend to be <em>happy</em>.
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl" style={{ background: '#0e0e13' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Priority</th>
              <th>Aspect</th>
              <th className="text-right">Mentions</th>
              <th className="text-right">Negative</th>
              <th className="text-right">Lift</th>
              <th style={{ minWidth: '140px' }}>Impact</th>
            </tr>
          </thead>
          <tbody>
            {aspects.map((a, i) => {
              const width = (a.impactScore / maxImpact) * 100
              const actionable = a.impactScore > 0
              return (
                <tr key={a.aspect}>
                  <td>
                    <span
                      className="inline-flex items-center justify-center w-6 h-6 rounded-full text-[11px] font-bold"
                      style={{
                        background: actionable ? 'rgba(255,180,171,0.15)' : 'rgba(144,143,160,0.1)',
                        color: actionable ? '#ffb4ab' : '#64748b',
                      }}
                    >
                      {i + 1}
                    </span>
                  </td>
                  <td className="font-medium" style={{ color: '#e4e1e9' }}>
                    {a.aspect}
                  </td>
                  <td className="text-right tabular-nums" style={{ color: '#908fa0' }}>
                    {a.mentions}
                  </td>
                  <td className="text-right tabular-nums" style={{ color: '#ffb4ab' }}>
                    {a.negativeMentions}
                  </td>
                  <td
                    className="text-right tabular-nums font-semibold"
                    style={{ color: a.lift > 0 ? '#ffb4ab' : '#4edea3' }}
                    title={
                      a.lift > 0
                        ? 'Mentioning this makes a negative review more likely than baseline'
                        : 'Mentioning this makes a negative review less likely than baseline'
                    }
                  >
                    {a.lift > 0 ? '+' : ''}
                    {(a.lift * 100).toFixed(0)}pp
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div
                        className="flex-1 h-2 rounded-full overflow-hidden"
                        style={{ background: '#1b1b20' }}
                      >
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{
                            width: `${Math.max(width, actionable ? 4 : 0)}%`,
                            background: actionable
                              ? 'linear-gradient(90deg, #93000a, #ffb4ab)'
                              : '#2a292f',
                          }}
                        />
                      </div>
                      <span
                        className="text-[11px] tabular-nums w-10 text-right"
                        style={{ color: '#64748b' }}
                      >
                        {a.impactScore.toFixed(2)}
                      </span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {aspects[0]?.impactScore > 0 && (
        <div
          className="rounded-xl p-4 text-xs leading-relaxed"
          style={{
            background: 'rgba(255, 180, 171, 0.06)',
            border: '1px solid rgba(255, 180, 171, 0.2)',
            color: '#c7c4d7',
          }}
        >
          <strong style={{ color: '#ffb4ab' }}>Fix first: {aspects[0].aspect}.</strong> Mentioned{' '}
          {aspects[0].mentions} times, {aspects[0].negativeMentions} of them negative. Reviews
          mentioning it are {(aspects[0].lift * 100).toFixed(0)} percentage points more likely to
          be negative than the corpus average.
        </div>
      )}
    </div>
  )
}
