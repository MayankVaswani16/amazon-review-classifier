package com.amazon.reviewclassifier.service;

import com.amazon.reviewclassifier.dto.NlpBulkResponseDTO;
import com.amazon.reviewclassifier.dto.NlpPredictionResponseDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

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

    public NlpPredictionResponseDTO predict(String text) {
        String url = nlpBaseUrl + "/nlp/predict";
        Map<String, String> body = new HashMap<>();
        body.put("text", text);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, String>> request = new HttpEntity<>(body, headers);

        ResponseEntity<NlpPredictionResponseDTO> response =
                restTemplate.exchange(url, HttpMethod.POST, request, NlpPredictionResponseDTO.class);
        return response.getBody();
    }

    public NlpBulkResponseDTO predictBulk(List<String> reviews) {
        String url = nlpBaseUrl + "/nlp/predict/bulk";
        Map<String, List<String>> body = new HashMap<>();
        body.put("reviews", reviews);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, List<String>>> request = new HttpEntity<>(body, headers);

        ResponseEntity<NlpBulkResponseDTO> response =
                restTemplate.exchange(url, HttpMethod.POST, request, NlpBulkResponseDTO.class);
        return response.getBody();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getSmoteStats() {
        String url = nlpBaseUrl + "/nlp/smote-stats";
        ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
        return response.getBody();
    }

    public byte[] getTsneImage(String which) {
        String url = nlpBaseUrl + "/nlp/tsne/" + which;
        ResponseEntity<byte[]> response = restTemplate.getForEntity(url, byte[].class);
        return response.getBody();
    }
}
