package com.amazon.reviewclassifier.dto;

import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * State of one asynchronous bulk prediction job.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BulkJobProgressDTO {

    private String jobId;
    private int total;
    private int processed;

    /** PROCESSING | COMPLETED | FAILED */
    private String status;
    private String error;

    /** The batch every row from this job was tagged with. */
    private String batchId;

    /**
     * Populated only once {@code status == COMPLETED}.
     *
     * <p>{@code @JsonIgnore} keeps this out of any serialised response. It was
     * previously marked {@code transient}, which does nothing here — that is a
     * <i>Java serialisation</i> keyword and Jackson ignores it entirely, so the
     * field would have been serialised in full. Since it can hold 20,000 nested
     * DTOs and the browser polls progress every 500 ms, shipping it by accident
     * would be a serious problem.
     */
    @JsonIgnore
    private List<PredictionResponseDTO> results;
}
