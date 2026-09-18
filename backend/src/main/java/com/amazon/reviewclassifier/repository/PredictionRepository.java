package com.amazon.reviewclassifier.repository;

import com.amazon.reviewclassifier.entity.Prediction;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PredictionRepository extends JpaRepository<Prediction, Long> {

    // ── History ────────────────────────────────────────────────────────────

    Page<Prediction> findAllByOrderByCreatedAtDesc(Pageable pageable);

    Page<Prediction> findByBatchIdOrderByCreatedAtDesc(String batchId, Pageable pageable);

    long countByLabel(String label);

    long countByBatchId(String batchId);

    // ── Aggregate stats ────────────────────────────────────────────────────

    @Query("SELECT AVG(p.confidence) FROM Prediction p")
    Double findAverageConfidence();

    /**
     * All label counts in one round trip.
     *
     * <p>Replaces two separate {@code countByLabel} calls and, unlike them, does
     * not assume the label set is exactly {positive, negative}. The engine can
     * now also return "mixed", which the hardcoded pair silently dropped.
     */
    @Query("SELECT p.label, COUNT(p) FROM Prediction p GROUP BY p.label")
    List<Object[]> countGroupedByLabel();

    @Query("SELECT COUNT(p) FROM Prediction p WHERE p.lowSignal = true")
    long countLowSignal();

    @Query("SELECT AVG(p.conflictScore) FROM Prediction p WHERE p.conflictScore IS NOT NULL")
    Double findAverageConflictScore();

    // ── Top words ──────────────────────────────────────────────────────────
    //
    // Native SQL because JPQL has no clean way to query an @ElementCollection
    // table standalone (the collection is not an entity), and LIMIT is not
    // standard JPQL. The aggregation runs in the database, so memory use stays
    // constant regardless of table size.

    @Query(value = """
            SELECT noun AS word, COUNT(*) AS cnt
            FROM prediction_nouns
            GROUP BY noun
            ORDER BY cnt DESC
            LIMIT 10
            """, nativeQuery = true)
    List<Object[]> findTopNouns();

    @Query(value = """
            SELECT adjective AS word, COUNT(*) AS cnt
            FROM prediction_adjectives
            GROUP BY adjective
            ORDER BY cnt DESC
            LIMIT 10
            """, nativeQuery = true)
    List<Object[]> findTopAdjectives();

    // ── Aspect Actionability Matrix ────────────────────────────────────────

    /**
     * Ranks product aspects by how strongly mentioning them predicts an unhappy
     * customer.
     *
     * <p>Frequency alone is misleading — the most-mentioned aspect is usually
     * uncontroversial. What matters is <b>lift</b>: how far the negative rate
     * among reviews mentioning an aspect sits above the corpus baseline. An
     * aspect can be mentioned constantly and never be the reason anyone is
     * unhappy, and this ranks that aspect last rather than first.
     *
     * <p>Columns returned, in order:
     * <ol>
     *   <li>{@code aspect} — the feature, as extracted</li>
     *   <li>{@code mentions} — total opinions expressed about it</li>
     *   <li>{@code negative_mentions}</li>
     *   <li>{@code mean_polarity} — average signed polarity</li>
     *   <li>{@code reviews} — distinct reviews mentioning it</li>
     *   <li>{@code negative_reviews} — of those, how many were negative overall</li>
     * </ol>
     * Lift and the final impact score are computed in the service layer, where
     * the corpus baseline is already known.
     *
     * <p>{@code HAVING COUNT(*) >= 3} suppresses statistical noise: without it a
     * single angry review would top the chart with a lift of 1.0.
     *
     * <p>Note this is PostgreSQL-specific ({@code FILTER (WHERE ...)}). That is
     * an accepted trade-off — the aggregate is far clearer than the portable
     * {@code SUM(CASE WHEN ... THEN 1 ELSE 0 END)} equivalent.
     */
    @Query(value = """
            SELECT a.aspect                                                 AS aspect,
                   COUNT(*)                                                 AS mentions,
                   COUNT(*) FILTER (WHERE a.aspect_label = 'negative')      AS negative_mentions,
                   AVG(a.polarity)                                          AS mean_polarity,
                   COUNT(DISTINCT p.id)                                     AS reviews,
                   COUNT(DISTINCT p.id) FILTER (WHERE p.label = 'negative')  AS negative_reviews
            FROM prediction_aspects a
            JOIN predictions p ON p.id = a.prediction_id
            WHERE (CAST(:batchId AS text) IS NULL OR p.batch_id = :batchId)
            GROUP BY a.aspect
            HAVING COUNT(*) >= 3
            ORDER BY negative_mentions DESC, mentions DESC
            LIMIT 50
            """, nativeQuery = true)
    List<Object[]> findAspectImpact(@Param("batchId") String batchId);

    /** Corpus-wide negative rate, used as the lift baseline. */
    @Query(value = """
            SELECT COUNT(*) FILTER (WHERE label = 'negative')::float8 / NULLIF(COUNT(*), 0)
            FROM predictions
            WHERE (CAST(:batchId AS text) IS NULL OR batch_id = :batchId)
            """, nativeQuery = true)
    Double findNegativeRate(@Param("batchId") String batchId);

    // ── Maintenance ────────────────────────────────────────────────────────

    /**
     * Deletes every row belonging to one bulk upload.
     *
     * <p>This is the scoped replacement for the old {@code truncateAll()}, which
     * ran {@code TRUNCATE TABLE predictions CASCADE} on every bulk run and wiped
     * the entire table. Deleting by batch is addressable, cannot destroy another
     * user's data, and — unlike TRUNCATE, which takes an ACCESS EXCLUSIVE lock —
     * does not block concurrent readers of unrelated rows.
     */
    @Modifying
    @Query("DELETE FROM Prediction p WHERE p.batchId = :batchId")
    int deleteByBatchId(@Param("batchId") String batchId);

    /** Distinct batches, newest first — powers the dashboard's batch selector. */
    @Query(value = """
            SELECT batch_id, COUNT(*) AS cnt, MAX(created_at) AS latest
            FROM predictions
            WHERE batch_id IS NOT NULL
            GROUP BY batch_id
            ORDER BY latest DESC
            LIMIT 20
            """, nativeQuery = true)
    List<Object[]> findRecentBatches();
}
