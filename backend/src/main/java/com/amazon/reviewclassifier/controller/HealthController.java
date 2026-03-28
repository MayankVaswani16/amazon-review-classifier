package com.amazon.reviewclassifier.controller;

import com.amazon.reviewclassifier.service.NlpClientService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class HealthController {

    private final NlpClientService nlpClientService;

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP"));
    }

    @GetMapping("/tsne/before")
    public ResponseEntity<byte[]> tsneBefore() {
        byte[] image = nlpClientService.getTsneImage("before");
        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_PNG)
                .body(image);
    }

    @GetMapping("/tsne/after")
    public ResponseEntity<byte[]> tsneAfter() {
        byte[] image = nlpClientService.getTsneImage("after");
        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_PNG)
                .body(image);
    }
}
