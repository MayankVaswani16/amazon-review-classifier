/**
 * Model transparency panel.
 *
 * Publishes the model's real evaluation numbers in the product itself, including
 * the unflattering one. Most sentiment demos quote a single accuracy figure
 * measured on a held-out split of their own training data; when that data is
 * generated, the number mostly reflects how well the model memorised the
 * generator, and it is meaningless as a guide to real-world behaviour.
 *
 * Showing the in-distribution and out-of-distribution scores side by side makes
 * the generalisation gap visible rather than hiding it.
 */
export default function ModelHonesty({ metrics }) {
  if (!metrics || !Object.keys(metrics).length) {
    return null
  }

  const ood = metrics.outOfDistribution || {}
  const perClass = metrics.perClass || {}
  const cm = metrics.confusionMatrix || {}

  const pct = (v) => (v == null || Number.isNaN(v) ? '—' : `${(v * 100).toFixed(1)}%`)
  const inDist = metrics.accuracy
  const outDist = ood.lexiconAccuracy != null && ood.modelAccuracy != null
    ? Math.max(ood.modelAccuracy, ood.lexiconAccuracy)
    : null
  const gap = inDist != null && outDist != null ? inDist - outDist : null

  return (
    <div className="glass-card p-6 space-y-5">
      <div className="space-y-1">
        <h3 className="text-base font-semibold" style={{ color: '#e4e1e9' }}>
          Model Evaluation
        </h3>
        <p className="text-xs" style={{ color: '#908fa0' }}>
          Trained on {metrics.trainedOn || 'unknown data'} · {metrics.vocabularySize?.toLocaleString()}{' '}
          features · model v{metrics.modelVersion}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          className="rounded-xl p-4 space-y-1"
          style={{ background: '#0e0e13', border: '1px solid rgba(144,143,160,0.08)' }}
        >
          <p className="text-[10px] uppercase tracking-wide" style={{ color: '#64748b' }}>
            In-distribution accuracy
          </p>
          <p className="text-2xl font-bold tabular-nums" style={{ color: '#908fa0' }}>
            {pct(inDist)}
          </p>
          <p className="text-[11px] leading-relaxed" style={{ color: '#64748b' }}>
            Held-out split of the training corpus. Flattering and not a real-world estimate — the
            test data comes from the same source as the training data.
          </p>
        </div>

        <div
          className="rounded-xl p-4 space-y-1"
          style={{
            background: 'rgba(99,102,241,0.06)',
            border: '1px solid rgba(99,102,241,0.25)',
          }}
        >
          <p className="text-[10px] uppercase tracking-wide" style={{ color: '#a5b4fc' }}>
            Out-of-distribution accuracy
          </p>
          <p className="text-2xl font-bold tabular-nums" style={{ color: '#e4e1e9' }}>
            {pct(outDist)}
          </p>
          <p className="text-[11px] leading-relaxed" style={{ color: '#908fa0' }}>
            Hand-written realistic reviews the model never saw — negation, sarcasm, mixed
            sentiment, misspellings. <strong>This is the number that matters.</strong>
          </p>
        </div>
      </div>

      {gap != null && gap > 0.05 && (
        <div
          className="rounded-xl p-3 text-[11px] leading-relaxed"
          style={{
            background: 'rgba(251,191,36,0.06)',
            border: '1px solid rgba(251,191,36,0.25)',
            color: '#fbbf24',
          }}
        >
          <strong>Generalisation gap: {(gap * 100).toFixed(0)} points.</strong> The model performs
          far better on data resembling its training set than on real review text. The fix is real
          training data — point <code>DATASET_PATH</code> at a labelled corpus and retrain.
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="Macro F1" value={metrics.macroF1} fmt={pct} />
        <Metric label="ROC AUC" value={metrics.rocAuc} fmt={pct} />
        <Metric
          label="CV F1 (5-fold)"
          value={metrics.crossValF1Mean}
          fmt={pct}
          sub={metrics.crossValF1Std != null ? `±${(metrics.crossValF1Std * 100).toFixed(1)}` : ''}
        />
        <Metric label="Blend weight" value={ood.blendWeight} fmt={(v) => v?.toFixed(2) ?? '—'}
                sub="lexicon vs model" />
      </div>

      {(perClass.positive || perClass.negative) && (
        <div className="overflow-x-auto rounded-xl" style={{ background: '#0e0e13' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Class</th>
                <th className="text-right">Precision</th>
                <th className="text-right">Recall</th>
                <th className="text-right">F1</th>
                <th className="text-right">Support</th>
              </tr>
            </thead>
            <tbody>
              {['negative', 'positive'].map(
                (cls) =>
                  perClass[cls] && (
                    <tr key={cls}>
                      <td style={{ color: cls === 'positive' ? '#4edea3' : '#ffb4ab' }}>{cls}</td>
                      <td className="text-right tabular-nums">{pct(perClass[cls].precision)}</td>
                      <td className="text-right tabular-nums">{pct(perClass[cls].recall)}</td>
                      <td className="text-right tabular-nums">{pct(perClass[cls].f1)}</td>
                      <td className="text-right tabular-nums" style={{ color: '#64748b' }}>
                        {perClass[cls].support}
                      </td>
                    </tr>
                  )
              )}
            </tbody>
          </table>
        </div>
      )}

      {cm.truePositive != null && (
        <p className="text-[11px]" style={{ color: '#64748b' }}>
          Confusion matrix — TP {cm.truePositive} · TN {cm.trueNegative} · FP {cm.falsePositive} ·
          FN {cm.falseNegative}
        </p>
      )}
    </div>
  )
}

function Metric({ label, value, fmt, sub }) {
  return (
    <div className="rounded-xl p-3" style={{ background: '#0e0e13' }}>
      <p className="text-[10px] uppercase tracking-wide" style={{ color: '#64748b' }}>
        {label}
      </p>
      <p className="text-sm font-semibold mt-0.5 tabular-nums" style={{ color: '#e4e1e9' }}>
        {fmt(value)}
      </p>
      {sub && (
        <p className="text-[10px] mt-0.5" style={{ color: '#64748b' }}>
          {sub}
        </p>
      )}
    </div>
  )
}
