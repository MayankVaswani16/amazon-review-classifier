package com.amazon.reviewclassifier.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NlpPredictionResponseDTO {
    private String label;
    private Double confidence;
    private List<String> nouns;
    private List<String> adjectives;
    private List<List<String>> featureSentimentPairs;
    private String processedText;
}
