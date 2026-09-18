package com.amazon.reviewclassifier.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * One opinion about one product aspect, with polarity.
 *
 * <p>Field names match the Python service's camelCase JSON exactly so Jackson
 * binds them without a naming strategy or per-field annotations.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AspectOpinionDTO {

    /** The product feature, e.g. "battery life". */
    private String aspect;

    /** The opinion word, e.g. "terrible". */
    private String opinion;

    /** Normalised polarity in (-1, 1). Negative means a complaint. */
    private Double polarity;

    /** positive | negative | neutral */
    private String label;

    /** True when the opinion was negated ("is not terrible"). */
    private Boolean negated;

    /** Which dependency pattern found this: amod, acomp, verb, dobj, … */
    private String relation;

    /** The sentence it came from, for evidence display. */
    private String sentence;
}
