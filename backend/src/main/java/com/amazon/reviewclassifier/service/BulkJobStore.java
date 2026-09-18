package com.amazon.reviewclassifier.service;

import com.amazon.reviewclassifier.dto.BulkJobProgressDTO;
import com.amazon.reviewclassifier.dto.PredictionResponseDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Tracks in-flight bulk prediction jobs.
 *
 * <p><b>Why a ConcurrentHashMap.</b> Two different threads touch this: the
 * {@code @Async} worker writes progress, and Tomcat request threads read it when
 * the browser polls. A plain {@code HashMap} can corrupt its internal structure
 * under concurrent modification.
 *
 * <p><b>What was fixed.</b>
 * <ul>
 *   <li><b>Unbounded growth.</b> Jobs were only ever removed when a client
 *       fetched their results. Close the tab mid-job and the entry — including
 *       up to 20,000 result DTOs — was retained for the lifetime of the JVM.
 *       Entries now expire on a timer.</li>
 *   <li><b>Torn reads.</b> {@code processed} was a plain {@code int} mutated by
 *       the worker and read by pollers with no synchronisation, so a reader
 *       could observe a stale value. It is now an {@link AtomicInteger}, and
 *       the other mutable fields are {@code volatile}.</li>
 *   <li><b>Delete-on-read.</b> Fetching results removed the job, making a GET
 *       non-idempotent: one dropped response and a ten-minute analysis was gone
 *       permanently. Results are now retained until they expire, so a retry
 *       works.</li>
 * </ul>
 *
 * <p>This remains process-local: it does not survive a restart, and it does not
 * work behind a load balancer with more than one backend instance (a poll could
 * hit the instance that does not own the job). Redis is the fix for both; for a
 * single-instance deployment this is sufficient and far simpler.
 */
@Component
@Slf4j
public class BulkJobStore {

    /** How long a finished job stays fetchable. */
    private static final Duration RETENTION = Duration.ofHours(1);

    /** Safety valve against unbounded growth if the sweeper ever stalls. */
    private static final int MAX_JOBS = 200;

    private final ConcurrentHashMap<String, Job> jobs = new ConcurrentHashMap<>();

    /** Internal state. A DTO is built on demand so callers cannot mutate this. */
    private static final class Job {
        final String jobId;
        final int total;
        final AtomicInteger processed = new AtomicInteger();
        volatile String status = "PROCESSING";
        volatile String error;
        volatile List<PredictionResponseDTO> results;
        volatile String batchId;
        volatile Instant updatedAt = Instant.now();

        Job(String jobId, int total) {
            this.jobId = jobId;
            this.total = total;
        }

        void touch() {
            this.updatedAt = Instant.now();
        }
    }

    public void createJob(String jobId, int total, String batchId) {
        if (jobs.size() >= MAX_JOBS) {
            evictOldest();
        }
        Job job = new Job(jobId, total);
        job.batchId = batchId;
        jobs.put(jobId, job);
        log.info("Bulk job {} created — {} reviews, batch {}", jobId, total, batchId);
    }

    public void updateProgress(String jobId, int processedSoFar) {
        Job job = jobs.get(jobId);
        if (job != null) {
            job.processed.set(processedSoFar);
            job.touch();
        }
    }

    public void completeJob(String jobId, List<PredictionResponseDTO> results) {
        Job job = jobs.get(jobId);
        if (job != null) {
            job.processed.set(job.total);
            job.results = results;
            job.status = "COMPLETED";
            job.touch();
        }
    }

    public void failJob(String jobId, String error) {
        Job job = jobs.get(jobId);
        if (job != null) {
            job.status = "FAILED";
            job.error = error;
            job.touch();
        }
    }

    public BulkJobProgressDTO getProgress(String jobId) {
        Job job = jobs.get(jobId);
        if (job == null) {
            return null;
        }
        return BulkJobProgressDTO.builder()
                .jobId(job.jobId)
                .total(job.total)
                .processed(job.processed.get())
                .status(job.status)
                .error(job.error)
                .batchId(job.batchId)
                .results(job.results)
                .build();
    }

    /**
     * Lightweight progress view for polling.
     *
     * <p>Deliberately excludes {@code results}: the browser polls this every
     * 500 ms, and serialising up to 20,000 nested DTOs on every tick would
     * saturate the connection and burn CPU on both ends.
     */
    public Map<String, Object> getProgressSummary(String jobId) {
        Job job = jobs.get(jobId);
        if (job == null) {
            return null;
        }
        return Map.of(
                "jobId", job.jobId,
                "total", job.total,
                "processed", job.processed.get(),
                "status", job.status,
                "batchId", job.batchId == null ? "" : job.batchId,
                "error", job.error == null ? "" : job.error
        );
    }

    public void removeJob(String jobId) {
        jobs.remove(jobId);
    }

    public int size() {
        return jobs.size();
    }

    /**
     * Expires finished jobs. Without this, a user who closes the tab before
     * fetching results leaks the whole result list permanently, because the job
     * would otherwise only be removed by a fetch that never comes.
     */
    @Scheduled(fixedDelay = 5 * 60 * 1000L, initialDelay = 60 * 1000L)
    public void evictExpired() {
        Instant cutoff = Instant.now().minus(RETENTION);
        int before = jobs.size();
        jobs.values().removeIf(job ->
                !"PROCESSING".equals(job.status) && job.updatedAt.isBefore(cutoff));
        int removed = before - jobs.size();
        if (removed > 0) {
            log.info("Evicted {} expired bulk job(s); {} remain", removed, jobs.size());
        }
    }

    private void evictOldest() {
        jobs.entrySet().stream()
                .filter(e -> !"PROCESSING".equals(e.getValue().status))
                .min((a, b) -> a.getValue().updatedAt.compareTo(b.getValue().updatedAt))
                .ifPresent(e -> {
                    jobs.remove(e.getKey());
                    log.warn("Job store at capacity — evicted {}", e.getKey());
                });
    }
}
