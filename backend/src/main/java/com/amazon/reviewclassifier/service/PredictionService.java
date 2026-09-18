package com.amazon.reviewclassifier.service;

import com.amazon.reviewclassifier.dto.*;
import com.amazon.reviewclassifier.entity.AspectOpinion;
import com.amazon.reviewclassifier.entity.Prediction;
import com.amazon.reviewclassifier.exception.PredictionNotFoundException;
import com.amazon.reviewclassifier.repository.PredictionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class PredictionService {

    /**
     * Reviews per NLP call. Bounds the request payload, bounds how many spaCy
     * documents the Python side holds at once, and gives the progress bar
     * something to report — without chunking there is nothing between 0 and 100.
     */
    private static final int CHUNK_SIZE = 500;

    /** Separator for the legacy flat pair encoding. */
    private static final String PAIR_SEPARATOR = "::";

    private final NlpClientService nlpClientService;
    private final PredictionRepository predictionRepository;
    private final BulkJobStore bulkJobStore;

    /**
     * Separate bean on purpose — see {@link BulkChunkProcessor}. Calling a
     * {@code @Transactional} method on {@code this} would bypass the proxy and
     * silently ignore the annotation.
     */
    private final BulkChunkProcessor chunkProcessor;

    // ── Single prediction ──────────────────────────────────────────────────

    @Transactional
    public PredictionResponseDTO predict(String text) {
        NlpPredictionResponseDTO nlp = nlpClientService.predict(text);
        Prediction entity = savePrediction(text, nlp, null);
        return toResponseDTO(entity, nlp.getFeatureSentimentPairs());
    }

    // ── Bulk ───────────────────────────────────────────────────────────────

    /**
     * Synchronous bulk prediction.
     *
     * @deprecated Superseded by {@link #predictBulkAsync}. Retained only for
     *         backward compatibility: it blocks a request thread for the whole
     *         job, which times out well before 20,000 reviews finish.
     */
    @Deprecated
    @Transactional
    public List<PredictionResponseDTO> predictBulk(List<String> reviews) {
        NlpBulkResponseDTO nlpBulk = nlpClientService.predictBulk(reviews);
        List<PredictionResponseDTO> results = new ArrayList<>(reviews.size());
        for (int i = 0; i < reviews.size(); i++) {
            NlpPredictionResponseDTO nlp = nlpBulk.getResults().get(i);
            Prediction entity = savePrediction(reviews.get(i), nlp, null);
            results.add(toResponseDTO(entity, nlp.getFeatureSentimentPairs()));
        }
        return results;
    }

    /**
     * Analyses a batch of reviews on a background thread, reporting progress.
     *
     * <p><b>The truncate is gone.</b> This method used to begin with
     * {@code predictionRepository.truncateAll()}, so every bulk upload wiped the
     * entire predictions table. The intent was reasonable — the dashboard should
     * reflect the analysis you just ran, not a blend of every dataset ever
     * uploaded — but the implementation was irreversible, unauthenticated,
     * unconfirmed data loss triggered by an endpoint whose name gave no hint of
     * it. Worse, with two concurrent uploads the second TRUNCATE destroyed the
     * first job's committed rows while the first user was told it succeeded.
     *
     * <p>Every row is now tagged with a {@code batchId} instead, and the
     * dashboard filters by batch. Same clean per-dataset reporting, no data loss,
     * and concurrent uploads isolate naturally.
     *
     * <p><b>Transaction scope.</b> Each chunk commits in its own transaction via
     * {@link #processChunk}. Previously one transaction spanned the entire job,
     * so nothing was visible until the very end — the progress bar read 90% while
     * the History page was still empty — and a single Hikari connection was
     * pinned across ~40 HTTP round trips to Python.
     */
    @Async
    public void predictBulkAsync(String jobId, String batchId, List<String> reviews) {
        List<PredictionResponseDTO> allResults = new ArrayList<>(reviews.size());
        try {
            for (int start = 0; start < reviews.size(); start += CHUNK_SIZE) {
                int end = Math.min(start + CHUNK_SIZE, reviews.size());
                List<String> chunk = reviews.subList(start, end);

                allResults.addAll(chunkProcessor.process(
                        chunk,
                        batchId,
                        (text, nlp) -> buildEntity(text, nlp, batchId),
                        (entity, nlp) -> toResponseDTO(entity, nlp.getFeatureSentimentPairs())));

                bulkJobStore.updateProgress(jobId, allResults.size());
            }

            bulkJobStore.completeJob(jobId, allResults);
            log.info("Bulk job {} completed — {} reviews, batch {}",
                    jobId, allResults.size(), batchId);

        } catch (Exception e) {
            // Essential: an exception escaping an @Async void method goes to the
            // executor's uncaught handler and is effectively invisible, leaving
            // the job stuck in PROCESSING and the browser polling forever.
            log.error("Bulk job {} failed after {} reviews: {}",
                    jobId, allResults.size(), e.getMessage(), e);
            bulkJobStore.failJob(jobId, e.getMessage());
        }
    }

    // ── History ────────────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public Page<PredictionResponseDTO> getHistory(int page, int size, String batchId) {
        if (page < 0) {
            throw new IllegalArgumentException("page must be >= 0");
        }
        if (size < 1 || size > 100) {
            // Without a cap, ?size=1000000 attempts to materialise the whole
            // table along with every eagerly-fetched collection.
            throw new IllegalArgumentException("size must be between 1 and 100");
        }

        Pageable pageable = PageRequest.of(page, size);
        Page<Prediction> results = (batchId == null || batchId.isBlank())
                ? predictionRepository.findAllByOrderByCreatedAtDesc(pageable)
                : predictionRepository.findByBatchIdOrderByCreatedAtDesc(batchId, pageable);

        return results.map(p -> toResponseDTO(p, deserializePairs(p.getFeatureSentimentPairs())));
    }

    @Transactional(readOnly = true)
    public PredictionResponseDTO getById(Long id) {
        Prediction p = predictionRepository.findById(id)
                .orElseThrow(() -> new PredictionNotFoundException(id));
        return toResponseDTO(p, deserializePairs(p.getFeatureSentimentPairs()));
    }

    /**
     * Deletes one prediction.
     *
     * <p>Single round trip rather than the previous {@code existsById} followed
     * by {@code deleteById}, which was a check-then-act race: two concurrent
     * deletes could both pass the check, and the loser threw an
     * {@code EmptyResultDataAccessException} that the old handler reported as a
     * confusing 404-by-accident. Now the not-found path is explicit.
     */
    @Transactional
    public void delete(Long id) {
        Prediction entity = predictionRepository.findById(id)
                .orElseThrow(() -> new PredictionNotFoundException(id));
        predictionRepository.delete(entity);
    }

    /** Deletes every row from one bulk upload. */
    @Transactional
    public int deleteBatch(String batchId) {
        int removed = predictionRepository.deleteByBatchId(batchId);
        log.info("Deleted {} rows from batch {}", removed, batchId);
        return removed;
    }

    // ── Mapping ────────────────────────────────────────────────────────────

    private Prediction savePrediction(String text, NlpPredictionResponseDTO nlp, String batchId) {
        return predictionRepository.save(buildEntity(text, nlp, batchId));
    }

    /** Builds (but does not persist) the entity for one analysed review. */
    Prediction buildEntity(String text, NlpPredictionResponseDTO nlp, String batchId) {
        return Prediction.builder()
                .reviewText(text)
                .label(nlp.getLabel())
                .confidence(nlp.getConfidence())
                .batchId(batchId)
                .nouns(safeList(nlp.getNouns()))
                .adjectives(safeList(nlp.getAdjectives()))
                .featureSentimentPairs(serializePairs(nlp.getFeatureSentimentPairs()))
                .aspects(toAspectEntities(nlp.getAspects()))
                .processedText(nlp.getProcessedText())
                .conflictScore(nlp.getConflictScore())
                .coverage(nlp.getCoverage())
                .lowSignal(nlp.getLowSignal())
                .build();
    }

    /**
     * Flattens pairs into the legacy {@code "noun::adjective"} form.
     *
     * <p>The size guard matters: this previously called {@code pair.get(1)}
     * unconditionally, so a malformed NLP response threw
     * {@code IndexOutOfBoundsException} — which the old exception handler then
     * reported as a 404. In the bulk path it aborted the entire job.
     */
    private List<String> serializePairs(List<List<String>> pairs) {
        if (pairs == null || pairs.isEmpty()) {
            return new ArrayList<>();
        }
        return pairs.stream()
                .filter(pair -> pair != null && pair.size() >= 2)
                .filter(pair -> pair.get(0) != null && pair.get(1) != null)
                .map(pair -> pair.get(0) + PAIR_SEPARATOR + pair.get(1))
                .collect(Collectors.toCollection(ArrayList::new));
    }

    /**
     * Splits the legacy encoding back apart.
     *
     * <p>{@code limit = 2} is deliberate: a token containing "::" would
     * otherwise produce three or more parts and silently corrupt the pair. This
     * is reachable, because extraction runs on raw text where punctuation
     * survives. The structured {@code aspects} field has no such problem — this
     * exists only to keep rows written by the old version readable.
     */
    private List<List<String>> deserializePairs(List<String> serialized) {
        if (serialized == null || serialized.isEmpty()) {
            return new ArrayList<>();
        }
        return serialized.stream()
                .filter(s -> s != null && !s.isBlank())
                .map(s -> {
                    String[] parts = s.split(PAIR_SEPARATOR, 2);
                    return parts.length == 2
                            ? List.of(parts[0], parts[1])
                            : List.of(parts[0], "");
                })
                .collect(Collectors.toCollection(ArrayList::new));
    }

    private List<AspectOpinion> toAspectEntities(List<AspectOpinionDTO> aspects) {
        if (aspects == null || aspects.isEmpty()) {
            return new ArrayList<>();
        }
        return aspects.stream()
                .filter(a -> a.getAspect() != null && !a.getAspect().isBlank())
                .map(a -> AspectOpinion.builder()
                        .aspect(truncate(a.getAspect(), 128))
                        .opinion(truncate(a.getOpinion(), 128))
                        .polarity(a.getPolarity() != null ? a.getPolarity() : 0.0)
                        .label(a.getLabel() != null ? a.getLabel() : "neutral")
                        .negated(Boolean.TRUE.equals(a.getNegated()))
                        .build())
                .collect(Collectors.toCollection(ArrayList::new));
    }

    private PredictionResponseDTO toResponseDTO(Prediction entity, List<List<String>> pairs) {
        return PredictionResponseDTO.builder()
                .id(entity.getId())
                .reviewText(entity.getReviewText())
                .label(entity.getLabel())
                .confidence(entity.getConfidence())
                .nouns(entity.getNouns())
                .adjectives(entity.getAdjectives())
                .featureSentimentPairs(pairs != null ? pairs : new ArrayList<>())
                .processedText(entity.getProcessedText())
                .createdAt(entity.getCreatedAt())
                .batchId(entity.getBatchId())
                .conflictScore(entity.getConflictScore())
                .coverage(entity.getCoverage())
                .lowSignal(entity.getLowSignal())
                .aspects(fromAspectEntities(entity.getAspects()))
                .build();
    }

    private List<AspectOpinionDTO> fromAspectEntities(List<AspectOpinion> aspects) {
        if (aspects == null || aspects.isEmpty()) {
            return Collections.emptyList();
        }
        return aspects.stream()
                .map(a -> AspectOpinionDTO.builder()
                        .aspect(a.getAspect())
                        .opinion(a.getOpinion())
                        .polarity(a.getPolarity())
                        .label(a.getLabel())
                        .negated(a.getNegated())
                        .build())
                .collect(Collectors.toList());
    }

    private static List<String> safeList(List<String> input) {
        return input == null ? new ArrayList<>() : new ArrayList<>(input);
    }

    private static String truncate(String value, int max) {
        if (value == null) return null;
        return value.length() <= max ? value : value.substring(0, max);
    }
}
