package com.amazon.reviewclassifier.config;

import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

/**
 * HTTP client used to reach the Python NLP service.
 *
 * <p><b>Why the timeouts matter.</b> A bare {@code new RestTemplate()} — which
 * is what this class used to return — has <i>infinite</i> connect and read
 * timeouts. If the NLP service accepts the TCP connection but never responds
 * (swapping, deadlocked, mid-GC), the calling Tomcat thread blocks forever.
 * Under load that exhausts the servlet thread pool, and then endpoints with no
 * NLP dependency at all — {@code /api/history}, {@code /api/health} — stop
 * responding too. A slow dependency becomes a total outage.
 *
 * <p>Bounded timeouts turn that into a fast, local failure which
 * {@code GlobalExceptionHandler} reports as 503 Service Unavailable.
 */
@Configuration
public class RestTemplateConfig {

    /** A TCP connect on the compose network should be effectively instant. */
    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(5);

    /**
     * Generous, because a cold bulk chunk runs spaCy over 500 documents. Still
     * finite: the point is to bound the damage, not to be fast.
     */
    private static final Duration READ_TIMEOUT = Duration.ofSeconds(120);

    @Bean
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        return builder
                .setConnectTimeout(CONNECT_TIMEOUT)
                .setReadTimeout(READ_TIMEOUT)
                .build();
    }
}
