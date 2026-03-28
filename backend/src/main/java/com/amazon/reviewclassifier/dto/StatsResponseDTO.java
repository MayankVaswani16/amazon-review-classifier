package com.amazon.reviewclassifier.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StatsResponseDTO {

    private long totalPredictions;
    private long positivePredictions;
    private long negativePredictions;
    private double averageConfidence;
    private List<Map<String, Object>> topNouns;
    private List<Map<String, Object>> topAdjectives;
    private Map<String, Object> smoteDistribution;
}
