package com.amazon.reviewclassifier.controller;

import com.amazon.reviewclassifier.dto.PredictionResponseDTO;
import com.amazon.reviewclassifier.service.PredictionService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/history")
@RequiredArgsConstructor
public class HistoryController {

    private final PredictionService predictionService;

    /**
     * Paginated history, newest first.
     *
     * <p>{@code size} is validated in the service and capped at 100. Without a
     * cap, {@code ?size=1000000} attempts to materialise the whole table along
     * with every eagerly-fetched collection.
     *
     * @param batchId optional — scopes results to a single bulk upload.
     */
    @GetMapping
    public ResponseEntity<Page<PredictionResponseDTO>> getHistory(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String batchId) {
        return ResponseEntity.ok(predictionService.getHistory(page, size, batchId));
    }

    @GetMapping("/{id}")
    public ResponseEntity<PredictionResponseDTO> getById(@PathVariable Long id) {
        return ResponseEntity.ok(predictionService.getById(id));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        predictionService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
