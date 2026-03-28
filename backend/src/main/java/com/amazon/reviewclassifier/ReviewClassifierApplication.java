package com.amazon.reviewclassifier;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class ReviewClassifierApplication {
    public static void main(String[] args) {
        SpringApplication.run(ReviewClassifierApplication.class, args);
    }
}
