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

    @GetMapping
    public ResponseEntity<Page<PredictionResponseDTO>> getHistory(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return ResponseEntity.ok(predictionService.getHistory(page, size));
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
