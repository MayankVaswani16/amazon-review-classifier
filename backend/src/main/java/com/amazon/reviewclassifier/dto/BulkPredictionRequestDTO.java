package com.amazon.reviewclassifier.dto;

import jakarta.validation.constraints.NotEmpty;
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

    @NotEmpty(message = "Reviews list must not be empty")
    private List<String> reviews;
}
