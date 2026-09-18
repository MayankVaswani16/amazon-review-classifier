package com.amazon.reviewclassifier.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * One opinion about one product aspect, stored in its own columns.
 *
 * <p>This replaces the old {@code "noun::adjective"} flat string, which had two
 * real defects. Any token containing {@code "::"} corrupted the split — and the
 * extraction runs on raw text where punctuation survives, so it was reachable.
 * And it carried no polarity at all, which meant "battery -> terrible" and
 * "battery -> <i>not</i> terrible" were stored identically.
 *
 * <p>Being {@code @Embeddable} it lives in an {@code @ElementCollection} table
 * with no identity of its own, which is correct: an aspect opinion has no
 * meaning outside the review it came from and is never queried independently.
 */
@Embeddable
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AspectOpinion {

    /** The product feature being discussed, e.g. "battery life". */
    @Column(name = "aspect", length = 128)
    private String aspect;

    /** The opinion word, e.g. "terrible". */
    @Column(name = "opinion", length = 128)
    private String opinion;

    /** Normalised polarity in (-1, 1); negative means a complaint. */
    @Column(name = "polarity")
    private Double polarity;

    /** positive | negative | neutral */
    @Column(name = "aspect_label", length = 16)
    private String label;

    /** True when the opinion was negated ("is not terrible"). */
    @Column(name = "negated")
    private Boolean negated;
}
