package com.amazon.reviewclassifier.service;

import com.amazon.reviewclassifier.dto.StatsResponseDTO;
import com.amazon.reviewclassifier.repository.PredictionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class StatsService {

    private final PredictionRepository predictionRepository;
    private final NlpClientService nlpClientService;

    public StatsResponseDTO getStats() {
        long total = predictionRepository.count();
        long positive = predictionRepository.countByLabel("positive");
        long negative = predictionRepository.countByLabel("negative");
        Double avgConfidence = predictionRepository.findAverageConfidence();

        // Use native aggregate queries instead of loading all entities
        List<Map<String, Object>> topNouns = predictionRepository.findTopNouns().stream()
                .map(row -> {
                    Map<String, Object> m = new HashMap<>();
                    m.put("word", row[0]);
                    m.put("count", ((Number) row[1]).longValue());
                    return m;
                })
                .collect(Collectors.toList());

        List<Map<String, Object>> topAdjs = predictionRepository.findTopAdjectives().stream()
                .map(row -> {
                    Map<String, Object> m = new HashMap<>();
                    m.put("word", row[0]);
                    m.put("count", ((Number) row[1]).longValue());
                    return m;
                })
                .collect(Collectors.toList());

        // Get SMOTE distribution from NLP service
        Map<String, Object> smoteDist = new HashMap<>();
        try {
            smoteDist = nlpClientService.getSmoteStats();
        } catch (Exception e) {
            log.warn("Could not fetch SMOTE stats: {}", e.getMessage());
        }

        return StatsResponseDTO.builder()
                .totalPredictions(total)
                .positivePredictions(positive)
                .negativePredictions(negative)
                .averageConfidence(avgConfidence != null ? avgConfidence : 0.0)
                .topNouns(topNouns)
                .topAdjectives(topAdjs)
                .smoteDistribution(smoteDist)
                .build();
    }
}
