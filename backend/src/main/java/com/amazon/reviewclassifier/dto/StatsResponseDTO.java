package com.amazon.reviewclassifier.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StatsResponseDTO {

    private long totalPredictions;
    private long positivePredictions;
    private long negativePredictions;

    /** Reviews whose aspects genuinely disagreed with each other. */
    private long mixedPredictions;

    /**
     * Reviews where neither engine had real evidence.
     *
     * <p>Surfacing this is a credibility feature: it tells the user how much of
     * the dashboard rests on guesses rather than signal, instead of presenting
     * every row with equal authority.
     */
    private long lowSignalPredictions;

    private double averageConfidence;

    /** Mean aspect disagreement across the corpus, 0..1. */
    private double averageConflictScore;

    private List<Map<String, Object>> topNouns;
    private List<Map<String, Object>> topAdjectives;

    /** The prioritised "fix this first" ranking. */
    private List<AspectImpactDTO> aspectImpact;

    /** Corpus-wide negative rate — the baseline lift is measured against. */
    private double baselineNegativeRate;

    private Map<String, Object> smoteDistribution;

    /** Live model evaluation, including the out-of-distribution estimate. */
    private Map<String, Object> modelMetrics;

    /** Batch currently being displayed; null means "everything". */
    private String batchId;

    /** Recent bulk uploads available to scope the dashboard by. */
    private List<Map<String, Object>> batches;
}
