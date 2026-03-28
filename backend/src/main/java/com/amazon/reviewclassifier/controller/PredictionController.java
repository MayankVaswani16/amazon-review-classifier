package com.amazon.reviewclassifier.controller;

import com.amazon.reviewclassifier.dto.BulkJobProgressDTO;
import com.amazon.reviewclassifier.dto.BulkPredictionRequestDTO;
import com.amazon.reviewclassifier.dto.PredictionRequestDTO;
import com.amazon.reviewclassifier.dto.PredictionResponseDTO;
import com.amazon.reviewclassifier.service.BulkJobStore;
import com.amazon.reviewclassifier.service.PredictionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class PredictionController {

    private final PredictionService predictionService;
    private final BulkJobStore bulkJobStore;

    @PostMapping("/predict")
    public ResponseEntity<PredictionResponseDTO> predict(
            @Valid @RequestBody PredictionRequestDTO request) {
        PredictionResponseDTO result = predictionService.predict(request.getText());
        return ResponseEntity.ok(result);
    }

    /** Original synchronous bulk endpoint (backward compatibility). */
    @PostMapping("/predict/bulk")
    public ResponseEntity<List<PredictionResponseDTO>> predictBulk(
            @Valid @RequestBody BulkPredictionRequestDTO request) {
        List<PredictionResponseDTO> results = predictionService.predictBulk(request.getReviews());
        return ResponseEntity.ok(results);
    }

    /** Start an async bulk job — returns immediately with a jobId. */
    @PostMapping("/predict/bulk/async")
    public ResponseEntity<Map<String, String>> startBulkJob(
            @Valid @RequestBody BulkPredictionRequestDTO request) {
        String jobId = UUID.randomUUID().toString();
        bulkJobStore.createJob(jobId, request.getReviews().size());
        predictionService.predictBulkAsync(jobId, request.getReviews());
        return ResponseEntity.accepted().body(Map.of("jobId", jobId));
    }

    /** Poll progress of a running bulk job. */
    @GetMapping("/predict/bulk/progress/{jobId}")
    public ResponseEntity<Map<String, Object>> getBulkProgress(@PathVariable String jobId) {
        BulkJobProgressDTO job = bulkJobStore.getProgress(jobId);
        if (job == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(Map.of(
                "jobId", job.getJobId(),
                "total", job.getTotal(),
                "processed", job.getProcessed(),
                "status", job.getStatus()
        ));
    }

    /** Fetch final results of a completed bulk job (also cleans up the job). */
    @GetMapping("/predict/bulk/result/{jobId}")
    public ResponseEntity<List<PredictionResponseDTO>> getBulkResult(@PathVariable String jobId) {
        BulkJobProgressDTO job = bulkJobStore.getProgress(jobId);
        if (job == null) {
            return ResponseEntity.notFound().build();
        }
        if (!"COMPLETED".equals(job.getStatus())) {
            return ResponseEntity.badRequest().build();
        }
        List<PredictionResponseDTO> results = job.getResults();
        bulkJobStore.removeJob(jobId);
        return ResponseEntity.ok(results);
    }
}

