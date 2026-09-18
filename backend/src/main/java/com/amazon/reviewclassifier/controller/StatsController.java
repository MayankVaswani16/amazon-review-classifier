package com.amazon.reviewclassifier.controller;

import com.amazon.reviewclassifier.dto.StatsResponseDTO;
import com.amazon.reviewclassifier.service.NlpClientService;
import com.amazon.reviewclassifier.service.StatsService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class StatsController {

    private final StatsService statsService;
    private final NlpClientService nlpClientService;

    /**
     * Dashboard aggregates.
     *
     * @param batchId optional — scopes every figure to one bulk upload, which
     *        is what makes the per-dataset view possible without deleting the
     *        rest of the history.
     */
    @GetMapping("/stats")
    public ResponseEntity<StatsResponseDTO> getStats(
            @RequestParam(required = false) String batchId) {
        return ResponseEntity.ok(statsService.getStats(batchId));
    }

    /**
     * Live model evaluation.
     *
     * <p>Exposes both the in-distribution score and the out-of-distribution
     * benchmark. The latter is the honest generalisation estimate; publishing
     * it alongside the flattering number is the point.
     */
    @GetMapping("/model/metrics")
    public ResponseEntity<Map<String, Object>> metrics() {
        return ResponseEntity.ok(nlpClientService.getMetrics());
    }

    /** The terms the classifier weights most heavily, globally. */
    @GetMapping("/model/features")
    public ResponseEntity<Map<String, Object>> features(
            @RequestParam(defaultValue = "20") int k) {
        return ResponseEntity.ok(nlpClientService.getTopFeatures(Math.min(Math.max(k, 1), 100)));
    }
}
