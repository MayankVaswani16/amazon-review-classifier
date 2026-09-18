package com.amazon.reviewclassifier.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * What the Python NLP service returns for one review.
 *
 * <p>{@code @JsonIgnoreProperties(ignoreUnknown = true)} matters here: the NLP
 * service is versioned and deployed independently, and without it, adding a
 * field on the Python side would break every request on the Java side with an
 * {@code UnrecognizedPropertyException}. Tolerating unknown fields is what makes
 * the two services independently releasable.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class NlpPredictionResponseDTO {

    // ── Original wire format ───────────────────────────────────────────────
    private String label;
    private Double confidence;
    private List<String> nouns;
    private List<String> adjectives;
    private List<List<String>> featureSentimentPairs;
    private String processedText;

    // ── Aspect-level analysis ──────────────────────────────────────────────
    private List<AspectOpinionDTO> aspects;

    /** Aspect disagreement, 0..1. High means a genuinely mixed review. */
    private Double conflictScore;
    private Boolean isMixed;

    // ── Engine transparency ────────────────────────────────────────────────
    /** What the learned classifier said on its own. */
    private String modelLabel;
    private Double modelConfidence;

    /** What the rule-based lexicon said on its own. */
    private String lexiconLabel;
    private Double lexiconScore;

    /** Share of tokens the learned model recognised, 0..1. */
    private Double coverage;

    /** True when neither engine had evidence — treat the verdict as a guess. */
    private Boolean lowSignal;

    /** True when blended confidence sits inside the grey band. */
    private Boolean uncertain;

    /** True when the two engines agreed. */
    private Boolean agreement;
}
