package com.amazon.reviewclassifier.service;

import com.amazon.reviewclassifier.dto.NlpBulkResponseDTO;
import com.amazon.reviewclassifier.dto.NlpPredictionResponseDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;

/**
 * The only class that knows how to reach the Python NLP service.
 *
 * <p>An anti-corruption layer: every detail of the transport — base URL, paths,
 * content types, response shapes — is confined here, so the rest of the
 * application never sees an HTTP concept. Swapping scikit-learn for a hosted
 * inference endpoint would change this file and nothing else.
 */
@Service
@Slf4j
public class NlpClientService {

    private final RestTemplate restTemplate;
    private final String nlpBaseUrl;

    public NlpClientService(RestTemplate restTemplate,
                            @Value("${nlp.service.url}") String nlpBaseUrl) {
        this.restTemplate = restTemplate;
        this.nlpBaseUrl = nlpBaseUrl;
    }

    // ── Prediction ─────────────────────────────────────────────────────────

    public NlpPredictionResponseDTO predict(String text) {
        return post("/nlp/predict", Map.of("text", text), NlpPredictionResponseDTO.class);
    }

    public NlpBulkResponseDTO predictBulk(List<String> reviews) {
        return post("/nlp/predict/bulk", Map.of("reviews", reviews), NlpBulkResponseDTO.class);
    }

    // ── Explainability ─────────────────────────────────────────────────────

    /** Per-token attribution plus the minimal edit that flips the verdict. */
    public Map<String, Object> explain(String text, int topK) {
        return postForMap("/nlp/explain", Map.of("text", text, "topK", topK));
    }

    /** Aspect Actionability Matrix computed over a corpus of reviews. */
    public Map<String, Object> actionability(List<String> reviews, int topK) {
        return postForMap("/nlp/actionability", Map.of("reviews", reviews, "topK", topK));
    }

    // ── Model introspection ────────────────────────────────────────────────

    public Map<String, Object> getMetrics() {
        return getForMap("/nlp/metrics");
    }

    public Map<String, Object> getTopFeatures(int k) {
        return getForMap("/nlp/model/features?k=" + k);
    }

    public Map<String, Object> getSmoteStats() {
        return getForMap("/nlp/smote-stats");
    }

    public byte[] getTsneImage(String which) {
        return restTemplate.getForEntity(nlpBaseUrl + "/nlp/tsne/" + which, byte[].class)
                .getBody();
    }

    // ── Transport helpers ──────────────────────────────────────────────────

    private <T> T post(String path, Object body, Class<T> responseType) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Object> request = new HttpEntity<>(body, headers);
        return restTemplate
                .exchange(nlpBaseUrl + path, HttpMethod.POST, request, responseType)
                .getBody();
    }

    /**
     * POST returning an arbitrarily shaped JSON object.
     *
     * <p>{@link ParameterizedTypeReference} — note the trailing {@code {}},
     * which creates an anonymous subclass — is required because Java erases
     * generics: {@code Map.class} carries nothing about {@code <String, Object>}
     * at runtime. The anonymous subclass captures the full generic type in its
     * class signature, which survives erasure and is recoverable by reflection,
     * so Jackson knows what to deserialise into.
     */
    private Map<String, Object> postForMap(String path, Object body) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Object> request = new HttpEntity<>(body, headers);
        return restTemplate.exchange(
                nlpBaseUrl + path,
                HttpMethod.POST,
                request,
                new ParameterizedTypeReference<Map<String, Object>>() {}
        ).getBody();
    }

    private Map<String, Object> getForMap(String path) {
        return restTemplate.exchange(
                nlpBaseUrl + path,
                HttpMethod.GET,
                null,
                new ParameterizedTypeReference<Map<String, Object>>() {}
        ).getBody();
    }
}
