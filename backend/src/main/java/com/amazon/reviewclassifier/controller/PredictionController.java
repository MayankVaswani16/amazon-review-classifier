package com.amazon.reviewclassifier.controller;

import com.amazon.reviewclassifier.dto.BulkJobProgressDTO;
import com.amazon.reviewclassifier.dto.BulkPredictionRequestDTO;
import com.amazon.reviewclassifier.dto.PredictionRequestDTO;
import com.amazon.reviewclassifier.dto.PredictionResponseDTO;
import com.amazon.reviewclassifier.service.BulkJobStore;
import com.amazon.reviewclassifier.service.NlpClientService;
import com.amazon.reviewclassifier.service.PredictionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
@Slf4j
public class PredictionController {

    private final PredictionService predictionService;
    private final BulkJobStore bulkJobStore;
    private final NlpClientService nlpClientService;

    // ── Single ─────────────────────────────────────────────────────────────

    @PostMapping("/predict")
    public ResponseEntity<PredictionResponseDTO> predict(
            @Valid @RequestBody PredictionRequestDTO request) {
        return ResponseEntity.ok(predictionService.predict(request.getText()));
    }

    /**
     * Why the model decided what it decided.
     *
     * <p>Returns per-token contributions that sum exactly to the decision logit,
     * plus the minimal set of terms whose removal flips the verdict.
     */
    @PostMapping("/explain")
    public ResponseEntity<Map<String, Object>> explain(
            @Valid @RequestBody PredictionRequestDTO request,
            @RequestParam(defaultValue = "12") int topK) {
        return ResponseEntity.ok(
                nlpClientService.explain(request.getText(), Math.min(Math.max(topK, 1), 50)));
    }

    // ── Bulk ───────────────────────────────────────────────────────────────

    /**
     * Synchronous bulk prediction.
     *
     * @deprecated Blocks a request thread for the whole job and times out well
     *         before a realistic batch finishes. Use {@code /predict/bulk/async}.
     */
    @Deprecated
    @PostMapping("/predict/bulk")
    public ResponseEntity<List<PredictionResponseDTO>> predictBulk(
            @Valid @RequestBody BulkPredictionRequestDTO request) {
        return ResponseEntity.ok(predictionService.predictBulk(request.getReviews()));
    }

    /**
     * Starts an async bulk job and returns immediately with a jobId.
     *
     * <p>202 Accepted, not 200: the work has been accepted but is not complete.
     *
     * <p>Note the ordering — the job is registered <i>before</i> the async
     * dispatch. Reversed, the background thread could try to update a job that
     * does not exist yet, and a fast client could poll and get a 404 for a job
     * that is genuinely running.
     */
    @PostMapping("/predict/bulk/async")
    public ResponseEntity<Map<String, String>> startBulkJob(
            @Valid @RequestBody BulkPredictionRequestDTO request) {

        String jobId = UUID.randomUUID().toString();
        String batchId = "batch-" + jobId.substring(0, 8);

        bulkJobStore.createJob(jobId, request.getReviews().size(), batchId);
        predictionService.predictBulkAsync(jobId, batchId, request.getReviews());

        return ResponseEntity.accepted().body(Map.of(
                "jobId", jobId,
                "batchId", batchId));
    }

    /**
     * Polls progress.
     *
     * <p>Returns a hand-built summary rather than the job DTO, because the DTO
     * holds the full result list — up to 20,000 nested objects — and the browser
     * polls this every 500 ms.
     */
    @GetMapping("/predict/bulk/progress/{jobId}")
    public ResponseEntity<Map<String, Object>> getBulkProgress(@PathVariable String jobId) {
        Map<String, Object> summary = bulkJobStore.getProgressSummary(jobId);
        return summary == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(summary);
    }

    /**
     * Fetches the results of a completed job.
     *
     * <p>This no longer deletes the job. Doing so made a GET non-idempotent: one
     * dropped response and the results of a ten-minute analysis were gone
     * permanently, even though every row was already committed to the database.
     * Jobs now expire on a timer instead, so a retry works.
     */
    @GetMapping("/predict/bulk/result/{jobId}")
    public ResponseEntity<?> getBulkResult(@PathVariable String jobId) {
        BulkJobProgressDTO job = bulkJobStore.getProgress(jobId);
        if (job == null) {
            return ResponseEntity.notFound().build();
        }

        if ("FAILED".equals(job.getStatus())) {
            // Previously a bare 400 with no body, so the failure reason — which
            // was sitting right there in the job — never reached the user.
            return ResponseEntity.status(500).body(Map.of(
                    "status", "FAILED",
                    "error", job.getError() == null ? "Bulk analysis failed" : job.getError(),
                    "processed", job.getProcessed(),
                    "total", job.getTotal()));
        }

        if (!"COMPLETED".equals(job.getStatus())) {
            return ResponseEntity.status(409).body(Map.of(
                    "status", job.getStatus(),
                    "error", "Job is still running",
                    "processed", job.getProcessed(),
                    "total", job.getTotal()));
        }

        List<PredictionResponseDTO> results = job.getResults();
        return ResponseEntity.ok(results == null ? List.of() : results);
    }

    /**
     * Deletes every row from one bulk upload.
     *
     * <p>The explicit, scoped replacement for the implicit table-wide TRUNCATE
     * that used to run on every bulk upload.
     */
    @DeleteMapping("/batch/{batchId}")
    public ResponseEntity<Map<String, Object>> deleteBatch(@PathVariable String batchId) {
        int removed = predictionService.deleteBatch(batchId);
        return ResponseEntity.ok(Map.of("batchId", batchId, "deleted", removed));
    }
}
