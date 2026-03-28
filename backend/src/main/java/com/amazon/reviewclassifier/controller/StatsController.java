package com.amazon.reviewclassifier.controller;

import com.amazon.reviewclassifier.dto.StatsResponseDTO;
import com.amazon.reviewclassifier.service.StatsService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class StatsController {

    private final StatsService statsService;

    @GetMapping("/stats")
    public ResponseEntity<StatsResponseDTO> getStats() {
        return ResponseEntity.ok(statsService.getStats());
    }
}
