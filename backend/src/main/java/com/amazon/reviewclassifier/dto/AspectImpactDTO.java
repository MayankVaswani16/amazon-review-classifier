package com.amazon.reviewclassifier.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * One row of the Aspect Actionability Matrix.
 *
 * <p>Answers "what should I fix first?" rather than "what gets mentioned most?".
 * The distinction matters: the most-mentioned aspect in a review corpus is
 * usually something uncontroversial, while the aspect that actually drives
 * unhappiness may be mentioned far less often.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AspectImpactDTO {

    /** The product feature, e.g. "zipper". */
    private String aspect;

    /** Total opinions expressed about it. */
    private long mentions;

    private long negativeMentions;
    private long positiveMentions;

    /** Average signed polarity across all opinions, in (-1, 1). */
    private double meanPolarity;

    /** Share of reviews mentioning this aspect that were negative overall. */
    private double negativeRate;

    /**
     * {@code negativeRate} minus the corpus-wide negative rate.
     *
     * <p>The key number. Positive lift means mentioning this aspect makes a
     * review <i>more</i> likely to be negative than the baseline — i.e. it is
     * genuinely driving dissatisfaction rather than merely being popular.
     * Negative lift means the opposite: people who mention it tend to be happy.
     */
    private double lift;

    /**
     * Prioritisation score: log-damped volume x severity x positive lift.
     *
     * <p>Volume is log-damped so one very common aspect cannot monopolise the
     * ranking; severity is the mean magnitude of the negative opinions.
     */
    private double impactScore;
}
