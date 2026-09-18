package com.amazon.reviewclassifier.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PredictionRequestDTO {

    /**
     * {@code @NotBlank} rejects null, empty <i>and</i> whitespace-only input —
     * "   " is not a valid review. {@code @Size} bounds it: without an upper
     * limit a multi-megabyte body is an easy memory-exhaustion vector, and
     * spaCy parsing cost grows with length.
     */
    @NotBlank(message = "Review text must not be blank")
    @Size(max = 20000, message = "Review text must be at most 20000 characters")
    private String text;
}
