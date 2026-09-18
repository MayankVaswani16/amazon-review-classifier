package com.amazon.reviewclassifier.service;

import com.amazon.reviewclassifier.dto.NlpBulkResponseDTO;
import com.amazon.reviewclassifier.dto.NlpPredictionResponseDTO;
import com.amazon.reviewclassifier.dto.PredictionResponseDTO;
import com.amazon.reviewclassifier.entity.Prediction;
import com.amazon.reviewclassifier.repository.PredictionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.function.BiFunction;

/**
 * Analyses and persists one chunk of a bulk job, in its own transaction.
 *
 * <p><b>Why this is a separate bean.</b> Spring implements {@code @Transactional}
 * with a proxy. A call from one method to another <i>inside the same class</i>
 * goes direct to the target object and never passes through that proxy, so the
 * annotation is silently ignored — the method just joins the caller's
 * transaction, or runs with none. Putting the chunk logic in its own bean means
 * {@code PredictionService} calls it through the container and
 * {@code REQUIRES_NEW} actually takes effect.
 *
 * <p>That matters here because the whole point is per-chunk durability: rows
 * become visible to the History page while the job is still running, and a
 * failure at 95% does not roll back the 19,000 rows already committed.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class BulkChunkProcessor {

    private final NlpClientService nlpClientService;
    private final PredictionRepository predictionRepository;

    /**
     * @param mapper builds the response DTO from the saved entity; supplied by
     *               {@link PredictionService} so the mapping logic lives in one
     *               place rather than being duplicated here.
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public List<PredictionResponseDTO> process(
            List<String> chunk,
            String batchId,
            BiFunction<String, NlpPredictionResponseDTO, Prediction> entityBuilder,
            BiFunction<Prediction, NlpPredictionResponseDTO, PredictionResponseDTO> mapper) {

        NlpBulkResponseDTO nlpBulk = nlpClientService.predictBulk(chunk);
        List<NlpPredictionResponseDTO> nlpResults =
                nlpBulk == null ? null : nlpBulk.getResults();

        // Fail loudly on a misaligned response rather than silently pairing the
        // wrong review with the wrong verdict.
        if (nlpResults == null || nlpResults.size() != chunk.size()) {
            throw new IllegalStateException(String.format(
                    "NLP service returned %d results for %d reviews",
                    nlpResults == null ? 0 : nlpResults.size(), chunk.size()));
        }

        List<PredictionResponseDTO> out = new ArrayList<>(chunk.size());
        for (int i = 0; i < chunk.size(); i++) {
            NlpPredictionResponseDTO nlp = nlpResults.get(i);
            Prediction saved = predictionRepository.save(entityBuilder.apply(chunk.get(i), nlp));
            out.add(mapper.apply(saved, nlp));
        }
        return out;
    }
}
