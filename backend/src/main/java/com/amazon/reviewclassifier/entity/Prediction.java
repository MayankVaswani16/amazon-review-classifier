package com.amazon.reviewclassifier.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.BatchSize;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * One analysed review.
 *
 * <p><b>Indexes.</b> {@code created_at} is indexed because the history page
 * sorts by it on every single request; without it that is a sequential scan
 * plus a sort every time. {@code label} supports the dashboard's per-label
 * counts, and {@code batch_id} supports per-upload scoping. PostgreSQL does not
 * index foreign-key columns automatically (unlike InnoDB), so the collection
 * tables declare theirs explicitly too.
 *
 * <p><b>{@code @BatchSize} on the collections.</b> These are
 * {@code @ElementCollection}s, which Hibernate fetches with a separate query
 * per parent row. Loading a page of 10 predictions therefore issued
 * 1 + 1 + (3 x 10) = 32 queries — the classic N+1. {@code @BatchSize} makes
 * Hibernate fetch collections for many parents in one
 * {@code WHERE prediction_id IN (...)} per collection, taking that to ~6.
 */
@Entity
@Table(
        name = "predictions",
        indexes = {
                @Index(name = "idx_predictions_created_at", columnList = "createdAt"),
                @Index(name = "idx_predictions_label", columnList = "label"),
                @Index(name = "idx_predictions_batch_id", columnList = "batchId"),
        }
)
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@ToString(exclude = {"nouns", "adjectives", "featureSentimentPairs", "aspects"})
public class Prediction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String reviewText;

    /** positive | negative | mixed */
    @Column(nullable = false)
    private String label;

    @Column(nullable = false)
    private Double confidence;

    /**
     * Groups every row created by a single bulk upload.
     *
     * <p>This replaces the previous behaviour, where each bulk run called
     * {@code TRUNCATE TABLE predictions CASCADE} so the dashboard would reflect
     * only the current analysis. That was irreversible, unauthenticated data
     * loss triggered by an endpoint whose name gave no hint of it — and two
     * concurrent uploads silently destroyed each other's rows. Scoping by batch
     * gives the same clean per-dataset dashboard while keeping the history.
     */
    @Column(length = 64)
    private String batchId;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(
            name = "prediction_nouns",
            joinColumns = @JoinColumn(name = "prediction_id"),
            indexes = @Index(name = "idx_nouns_prediction_id", columnList = "prediction_id")
    )
    @Column(name = "noun")
    @BatchSize(size = 50)
    @Builder.Default
    private List<String> nouns = new ArrayList<>();

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(
            name = "prediction_adjectives",
            joinColumns = @JoinColumn(name = "prediction_id"),
            indexes = @Index(name = "idx_adjectives_prediction_id", columnList = "prediction_id")
    )
    @Column(name = "adjective")
    @BatchSize(size = 50)
    @Builder.Default
    private List<String> adjectives = new ArrayList<>();

    /**
     * Legacy flat encoding, retained so rows written by the old version stay
     * readable and the existing API shape keeps working.
     *
     * @deprecated Superseded by {@link #aspects}, which stores the feature and
     *         the opinion in separate columns. The {@code "noun::adjective"}
     *         string was corrupted by any token containing {@code "::"}, and
     *         carried no polarity — so "battery::terrible" was indistinguishable
     *         from a negated "not terrible".
     */
    @Deprecated
    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(
            name = "prediction_feature_sentiment_pairs",
            joinColumns = @JoinColumn(name = "prediction_id"),
            indexes = @Index(name = "idx_pairs_prediction_id", columnList = "prediction_id")
    )
    @Column(name = "pair", columnDefinition = "TEXT")
    @BatchSize(size = 50)
    @Builder.Default
    private List<String> featureSentimentPairs = new ArrayList<>();

    /** Structured aspect opinions with polarity — the replacement for the above. */
    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(
            name = "prediction_aspects",
            joinColumns = @JoinColumn(name = "prediction_id"),
            indexes = @Index(name = "idx_aspects_prediction_id", columnList = "prediction_id")
    )
    @BatchSize(size = 50)
    @Builder.Default
    private List<AspectOpinion> aspects = new ArrayList<>();

    @Column(columnDefinition = "TEXT")
    private String processedText;

    /** Aspect-level disagreement, 0..1. High means a genuinely mixed review. */
    @Column
    private Double conflictScore;

    /** Share of tokens the learned model recognised, 0..1. */
    @Column
    private Double coverage;

    /** True when neither engine had evidence — the verdict is barely a guess. */
    @Column
    private Boolean lowSignal;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
    }
}
