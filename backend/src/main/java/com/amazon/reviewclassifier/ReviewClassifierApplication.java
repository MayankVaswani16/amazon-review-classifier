package com.amazon.reviewclassifier;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Application entry point.
 *
 * <p>{@code @EnableAsync} activates the proxying that makes {@code @Async} on
 * the bulk pipeline actually run in the background — without it the annotation
 * is silently ignored and the "async" job blocks the request thread for minutes.
 *
 * <p>{@code @EnableScheduling} activates {@code BulkJobStore}'s eviction sweep.
 * Without it, finished jobs are never expired and their result lists leak.
 */
@SpringBootApplication
@EnableAsync
@EnableScheduling
public class ReviewClassifierApplication {
    public static void main(String[] args) {
        SpringApplication.run(ReviewClassifierApplication.class, args);
    }
}
