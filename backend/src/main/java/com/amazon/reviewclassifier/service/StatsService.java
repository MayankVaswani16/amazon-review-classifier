package com.amazon.reviewclassifier.service;

import com.amazon.reviewclassifier.dto.AspectImpactDTO;
import com.amazon.reviewclassifier.dto.StatsResponseDTO;
import com.amazon.reviewclassifier.repository.PredictionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

/**
 * Dashboard aggregates.
 *
 * <p>Every figure is computed <b>in the database</b>. Loading rows into the JVM
 * and counting them in Java would be O(n) heap and would fall over on a large
 * table; these queries return at most a handful of rows regardless of how many
 * predictions exist.
 *
 * <p>NLP-service failures are deliberately swallowed here. The dashboard is a
 * read-only view and should still render every database-derived figure when the
 * analysis engine is down — unlike prediction, where an NLP failure must
 * propagate because the result would be meaningless. That difference in policy
 * is why stats and prediction live in separate services.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class StatsService {

    /**
     * Minimum mentions before an aspect is eligible for the impact ranking.
     * Without a floor, a single angry review yields a lift of 1.0 and tops the
     * chart on no evidence at all.
     */
    private static final int MIN_MENTIONS = 3;

    private final PredictionRepository predictionRepository;
    private final NlpClientService nlpClientService;

    @Transactional(readOnly = true)
    public StatsResponseDTO getStats(String batchId) {
        String scope = (batchId == null || batchId.isBlank()) ? null : batchId;

        // One GROUP BY instead of a countByLabel call per label — and unlike the
        // hardcoded pair it replaced, this does not silently drop "mixed".
        Map<String, Long> byLabel = predictionRepository.countGroupedByLabel().stream()
                .collect(Collectors.toMap(
                        row -> String.valueOf(row[0]),
                        row -> ((Number) row[1]).longValue(),
                        Long::sum));

        long total = byLabel.values().stream().mapToLong(Long::longValue).sum();
        Double avgConfidence = predictionRepository.findAverageConfidence();
        Double avgConflict = predictionRepository.findAverageConflictScore();

        return StatsResponseDTO.builder()
                .totalPredictions(total)
                .positivePredictions(byLabel.getOrDefault("positive", 0L))
                .negativePredictions(byLabel.getOrDefault("negative", 0L))
                .mixedPredictions(byLabel.getOrDefault("mixed", 0L))
                .lowSignalPredictions(safeCount(predictionRepository::countLowSignal))
                // AVG() over an empty table returns SQL NULL — which is exactly
                // the state a fresh deployment is in, hence the null guards.
                .averageConfidence(avgConfidence != null ? avgConfidence : 0.0)
                .averageConflictScore(avgConflict != null ? avgConflict : 0.0)
                .topNouns(toWordCounts(predictionRepository.findTopNouns()))
                .topAdjectives(toWordCounts(predictionRepository.findTopAdjectives()))
                .aspectImpact(computeAspectImpact(scope))
                .baselineNegativeRate(negativeRate(scope))
                .smoteDistribution(fetchQuietly(nlpClientService::getSmoteStats, "SMOTE stats"))
                .modelMetrics(fetchQuietly(nlpClientService::getMetrics, "model metrics"))
                .batchId(scope)
                .batches(recentBatches())
                .build();
    }

    /**
     * Builds the Aspect Actionability Matrix.
     *
     * <p>The database returns raw counts per aspect; the ranking maths happens
     * here, where the corpus baseline is known:
     *
     * <pre>
     *   lift(a)   = P(negative | mentions a) - P(negative)
     *   impact(a) = log1p(mentions) x severity(a) x max(lift(a), 0)
     * </pre>
     *
     * <p>Volume is log-damped so a single dominant aspect cannot monopolise the
     * ranking, and lift is floored at zero because an aspect people mention when
     * they are <i>happy</i> is not a work item.
     */
    private List<AspectImpactDTO> computeAspectImpact(String batchId) {
        double baseline = negativeRate(batchId);
        List<Object[]> rows;
        try {
            rows = predictionRepository.findAspectImpact(batchId);
        } catch (Exception e) {
            // The aspect table only fills once predictions are written under the
            // current schema; an empty dashboard must not 500.
            log.warn("Aspect impact query failed: {}", e.getMessage());
            return List.of();
        }

        List<AspectImpactDTO> impacts = new ArrayList<>(rows.size());
        for (Object[] row : rows) {
            long mentions = num(row[1]);
            if (mentions < MIN_MENTIONS) {
                continue;
            }
            long negativeMentions = num(row[2]);
            double meanPolarity = row[3] == null ? 0.0 : ((Number) row[3]).doubleValue();
            long reviews = num(row[4]);
            long negativeReviews = num(row[5]);

            double negativeRate = reviews > 0 ? (double) negativeReviews / reviews : 0.0;
            double lift = negativeRate - baseline;
            // Severity: how harsh the negative language is, clamped to [0, 1].
            double severity = negativeMentions > 0 ? Math.min(1.0, Math.abs(meanPolarity)) : 0.0;
            double impact = Math.log1p(mentions) * severity * Math.max(lift, 0.0);

            impacts.add(AspectImpactDTO.builder()
                    .aspect(String.valueOf(row[0]))
                    .mentions(mentions)
                    .negativeMentions(negativeMentions)
                    .positiveMentions(Math.max(0, mentions - negativeMentions))
                    .meanPolarity(round(meanPolarity))
                    .negativeRate(round(negativeRate))
                    .lift(round(lift))
                    .impactScore(round(impact))
                    .build());
        }

        impacts.sort(Comparator.comparingDouble(AspectImpactDTO::getImpactScore).reversed());
        return impacts.stream().limit(10).collect(Collectors.toList());
    }

    private double negativeRate(String batchId) {
        try {
            Double rate = predictionRepository.findNegativeRate(batchId);
            return rate != null ? rate : 0.0;
        } catch (Exception e) {
            log.warn("Negative-rate query failed: {}", e.getMessage());
            return 0.0;
        }
    }

    private List<Map<String, Object>> recentBatches() {
        try {
            return predictionRepository.findRecentBatches().stream()
                    .map(row -> {
                        Map<String, Object> m = new LinkedHashMap<>();
                        m.put("batchId", String.valueOf(row[0]));
                        m.put("count", num(row[1]));
                        m.put("latest", String.valueOf(row[2]));
                        return m;
                    })
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.warn("Batch listing failed: {}", e.getMessage());
            return List.of();
        }
    }

    private List<Map<String, Object>> toWordCounts(List<Object[]> rows) {
        return rows.stream()
                .map(row -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("word", row[0]);
                    // Cast via Number rather than directly to Long: different
                    // JDBC drivers return COUNT(*) as BigInteger, Long or Integer.
                    m.put("count", num(row[1]));
                    return m;
                })
                .collect(Collectors.toList());
    }

    /** Runs an NLP call, degrading to an empty map rather than failing the page. */
    private Map<String, Object> fetchQuietly(
            java.util.function.Supplier<Map<String, Object>> call, String what) {
        try {
            Map<String, Object> result = call.get();
            return result != null ? result : Map.of();
        } catch (Exception e) {
            log.warn("Could not fetch {}: {}", what, e.getMessage());
            return Map.of();
        }
    }

    private long safeCount(java.util.function.Supplier<Long> call) {
        try {
            Long v = call.get();
            return v != null ? v : 0L;
        } catch (Exception e) {
            return 0L;
        }
    }

    private static long num(Object value) {
        return value == null ? 0L : ((Number) value).longValue();
    }

    private static double round(double v) {
        return Math.round(v * 10000.0) / 10000.0;
    }
}
