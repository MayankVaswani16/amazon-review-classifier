package com.amazon.reviewclassifier.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;
import java.util.List;

@Entity
@Table(name = "predictions")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Prediction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String reviewText;

    @Column(nullable = false)
    private String label;

    @Column(nullable = false)
    private Double confidence;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "prediction_nouns", joinColumns = @JoinColumn(name = "prediction_id"))
    @Column(name = "noun")
    private List<String> nouns;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "prediction_adjectives", joinColumns = @JoinColumn(name = "prediction_id"))
    @Column(name = "adjective")
    private List<String> adjectives;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "prediction_feature_sentiment_pairs", joinColumns = @JoinColumn(name = "prediction_id"))
    @Column(name = "pair", columnDefinition = "TEXT")
    private List<String> featureSentimentPairs;

    @Column(columnDefinition = "TEXT")
    private String processedText;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
    }
}
