package com.amazon.reviewclassifier.service;

import com.amazon.reviewclassifier.dto.*;
import com.amazon.reviewclassifier.entity.Prediction;
import com.amazon.reviewclassifier.repository.PredictionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class PredictionService {

    private final NlpClientService nlpClientService;
    private final PredictionRepository predictionRepository;
    private final BulkJobStore bulkJobStore;

    /**
     * Predict sentiment for a single review.
     */
    public PredictionResponseDTO predict(String text) {
        NlpPredictionResponseDTO nlpResponse = nlpClientService.predict(text);
        Prediction entity = savePrediction(text, nlpResponse);
        return toResponseDTO(entity, nlpResponse.getFeatureSentimentPairs());
    }

    /**
     * Predict sentiment for multiple reviews (synchronous — kept for backward compatibility).
     */
    public List<PredictionResponseDTO> predictBulk(List<String> reviews) {
        NlpBulkResponseDTO nlpBulk = nlpClientService.predictBulk(reviews);
        List<PredictionResponseDTO> results = new ArrayList<>();

        for (int i = 0; i < reviews.size(); i++) {
            NlpPredictionResponseDTO nlpResp = nlpBulk.getResults().get(i);
            Prediction entity = savePrediction(reviews.get(i), nlpResp);
            results.add(toResponseDTO(entity, nlpResp.getFeatureSentimentPairs()));
        }
        return results;
    }

    /**
     * Predict sentiment for multiple reviews asynchronously with chunked progress tracking.
     */
    @org.springframework.scheduling.annotation.Async
    @org.springframework.transaction.annotation.Transactional
    public void predictBulkAsync(String jobId, List<String> reviews) {
        int chunkSize = 500;
        List<PredictionResponseDTO> allResults = new ArrayList<>();

        try {
            // Clear previous predictions so dashboard shows only the current analysis
            predictionRepository.truncateAll();

            for (int start = 0; start < reviews.size(); start += chunkSize) {
                int end = Math.min(start + chunkSize, reviews.size());
                List<String> chunk = reviews.subList(start, end);

                NlpBulkResponseDTO nlpBulk = nlpClientService.predictBulk(chunk);

                for (int i = 0; i < chunk.size(); i++) {
                    NlpPredictionResponseDTO nlpResp = nlpBulk.getResults().get(i);
                    Prediction entity = savePrediction(chunk.get(i), nlpResp);
                    allResults.add(toResponseDTO(entity, nlpResp.getFeatureSentimentPairs()));
                }

                bulkJobStore.updateProgress(jobId, allResults.size());
            }

            bulkJobStore.completeJob(jobId, allResults);
            log.info("Bulk job {} completed — {} reviews processed", jobId, allResults.size());
        } catch (Exception e) {
            log.error("Bulk job {} failed: {}", jobId, e.getMessage(), e);
            bulkJobStore.failJob(jobId, e.getMessage());
        }
    }

    /**
     * Get paginated prediction history.
     */
    public Page<PredictionResponseDTO> getHistory(int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        return predictionRepository.findAllByOrderByCreatedAtDesc(pageable)
                .map(p -> toResponseDTO(p, deserializePairs(p.getFeatureSentimentPairs())));
    }

    /**
     * Get a single prediction by ID.
     */
    public PredictionResponseDTO getById(Long id) {
        Prediction p = predictionRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Prediction not found: " + id));
        return toResponseDTO(p, deserializePairs(p.getFeatureSentimentPairs()));
    }

    /**
     * Delete a prediction by ID.
     */
    public void delete(Long id) {
        if (!predictionRepository.existsById(id)) {
            throw new RuntimeException("Prediction not found: " + id);
        }
        predictionRepository.deleteById(id);
    }

    // ── Private helpers ────────────────────────────────────────────────

    private Prediction savePrediction(String text, NlpPredictionResponseDTO nlp) {
        // Serialize feature-sentiment pairs as "noun::adjective" strings
        List<String> serializedPairs = nlp.getFeatureSentimentPairs() != null
                ? nlp.getFeatureSentimentPairs().stream()
                    .map(pair -> pair.get(0) + "::" + pair.get(1))
                    .collect(Collectors.toList())
                : new ArrayList<>();

        Prediction entity = Prediction.builder()
                .reviewText(text)
                .label(nlp.getLabel())
                .confidence(nlp.getConfidence())
                .nouns(nlp.getNouns() != null ? nlp.getNouns() : new ArrayList<>())
                .adjectives(nlp.getAdjectives() != null ? nlp.getAdjectives() : new ArrayList<>())
                .featureSentimentPairs(serializedPairs)
                .processedText(nlp.getProcessedText())
                .build();

        return predictionRepository.save(entity);
    }

    private PredictionResponseDTO toResponseDTO(Prediction entity, List<List<String>> pairs) {
        return PredictionResponseDTO.builder()
                .id(entity.getId())
                .reviewText(entity.getReviewText())
                .label(entity.getLabel())
                .confidence(entity.getConfidence())
                .nouns(entity.getNouns())
                .adjectives(entity.getAdjectives())
                .featureSentimentPairs(pairs)
                .processedText(entity.getProcessedText())
                .createdAt(entity.getCreatedAt())
                .build();
    }

    private List<List<String>> deserializePairs(List<String> serialized) {
        if (serialized == null) return new ArrayList<>();
        return serialized.stream()
                .map(s -> Arrays.asList(s.split("::")))
                .collect(Collectors.toList());
    }
}
