package com.amazon.reviewclassifier.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

/**
 * What the API returns to the browser for one analysed review.
 *
 * <p>The first nine fields are the original contract and are unchanged, so
 * existing clients keep working. Everything after is additive.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PredictionResponseDTO {

    private Long id;
    private String reviewText;

    /** positive | negative | mixed */
    private String label;
    private Double confidence;
    private List<String> nouns;
    private List<String> adjectives;
    private List<List<String>> featureSentimentPairs;
    private String processedText;
    private LocalDateTime createdAt;

    // ── Aspect-level analysis ──────────────────────────────────────────────
    private List<AspectOpinionDTO> aspects;
    private Double conflictScore;

    // ── Engine transparency ────────────────────────────────────────────────
    // Surfaced so the UI can show *why* a verdict was reached and flag the
    // cases where the system genuinely does not know, instead of presenting
    // every answer with the same unearned authority.
    private String modelLabel;
    private Double modelConfidence;
    private String lexiconLabel;
    private Double lexiconScore;
    private Double coverage;
    private Boolean lowSignal;
    private Boolean uncertain;
    private Boolean agreement;

    /** Which bulk upload this row belongs to; null for single analyses. */
    private String batchId;
}
