package com.amazon.reviewclassifier.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PredictionRequestDTO {

    @NotBlank(message = "Review text must not be blank")
    private String text;
}
