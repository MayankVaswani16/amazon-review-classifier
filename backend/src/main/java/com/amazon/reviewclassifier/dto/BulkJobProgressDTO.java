package com.amazon.reviewclassifier.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BulkJobProgressDTO {

    private String jobId;
    private int total;
    private int processed;
    private String status;  // PROCESSING, COMPLETED, FAILED
    private String error;

    // Results are only populated when status == COMPLETED
    private transient List<PredictionResponseDTO> results;
}
