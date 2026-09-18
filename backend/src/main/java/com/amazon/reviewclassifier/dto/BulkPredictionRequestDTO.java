package com.amazon.reviewclassifier.dto;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BulkPredictionRequestDTO {

    /**
     * {@code @NotEmpty} rather than {@code @NotBlank} — a list cannot be
     * "blank". The size cap bounds the request: previously any payload was
     * accepted, so a single POST could pin the service for hours.
     */
    @NotEmpty(message = "Reviews list must not be empty")
    @Size(max = 50000, message = "At most 50000 reviews per request")
    private List<String> reviews;
}
