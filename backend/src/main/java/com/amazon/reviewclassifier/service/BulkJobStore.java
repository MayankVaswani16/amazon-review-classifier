package com.amazon.reviewclassifier.service;

import com.amazon.reviewclassifier.dto.BulkJobProgressDTO;
import com.amazon.reviewclassifier.dto.PredictionResponseDTO;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

/**
 * In-memory store for tracking bulk prediction job progress.
 * Jobs are short-lived and cleaned up after results are fetched.
 */
@Component
public class BulkJobStore {

    private final ConcurrentHashMap<String, BulkJobProgressDTO> jobs = new ConcurrentHashMap<>();

    public void createJob(String jobId, int total) {
        jobs.put(jobId, BulkJobProgressDTO.builder()
                .jobId(jobId)
                .total(total)
                .processed(0)
                .status("PROCESSING")
                .build());
    }

    public void updateProgress(String jobId, int processedSoFar) {
        BulkJobProgressDTO job = jobs.get(jobId);
        if (job != null) {
            job.setProcessed(processedSoFar);
        }
    }

    public void completeJob(String jobId, List<PredictionResponseDTO> results) {
        BulkJobProgressDTO job = jobs.get(jobId);
        if (job != null) {
            job.setProcessed(job.getTotal());
            job.setStatus("COMPLETED");
            job.setResults(results);
        }
    }

    public void failJob(String jobId, String error) {
        BulkJobProgressDTO job = jobs.get(jobId);
        if (job != null) {
            job.setStatus("FAILED");
            job.setError(error);
        }
    }

    public BulkJobProgressDTO getProgress(String jobId) {
        return jobs.get(jobId);
    }

    public void removeJob(String jobId) {
        jobs.remove(jobId);
    }
}
