package com.amazon.reviewclassifier.exception;

import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.RestClientException;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Translates exceptions into HTTP responses in one place.
 *
 * <p>Spring selects the <i>most specific</i> handler by walking the thrown
 * exception's class hierarchy, so precedence below is by type, not by
 * declaration order.
 *
 * <p><b>What changed and why.</b> This class previously mapped the whole of
 * {@link RuntimeException} to <b>404 Not Found</b>. Since {@code RuntimeException}
 * is the superclass of {@code NullPointerException},
 * {@code IndexOutOfBoundsException} and essentially every unchecked exception,
 * any genuine bug in the service layer surfaced to the caller as "not found" —
 * misleading for clients and actively hostile to debugging. Now only
 * {@link PredictionNotFoundException} yields a 404, and anything unrecognised
 * yields a 500 with the stack trace logged server-side and <i>not</i> leaked to
 * the client.
 */
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    /** Bean-validation failure on an {@code @Valid} request body. */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(MethodArgumentNotValidException ex) {
        List<String> errors = ex.getBindingResult().getFieldErrors().stream()
                .map(e -> e.getField() + ": " + e.getDefaultMessage())
                .toList();
        Map<String, Object> body = body(HttpStatus.BAD_REQUEST,
                errors.isEmpty() ? "Validation failed" : errors.get(0));
        body.put("errors", errors);
        return ResponseEntity.badRequest().body(body);
    }

    /** A prediction was requested by an ID that does not exist. */
    @ExceptionHandler(PredictionNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(PredictionNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(body(HttpStatus.NOT_FOUND, ex.getMessage()));
    }

    /**
     * Losing a delete race: two callers deleted the same row and one lost.
     * Semantically that is still "it isn't there", so 404 is the honest answer.
     */
    @ExceptionHandler(EmptyResultDataAccessException.class)
    public ResponseEntity<Map<String, Object>> handleMissingRow(EmptyResultDataAccessException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(body(HttpStatus.NOT_FOUND, "Record no longer exists"));
    }

    /** The NLP service is unreachable, refused the connection, or timed out. */
    @ExceptionHandler(RestClientException.class)
    public ResponseEntity<Map<String, Object>> handleRestClient(RestClientException ex) {
        log.error("NLP service call failed: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(body(HttpStatus.SERVICE_UNAVAILABLE,
                        "NLP service unavailable — the analysis engine is not responding"));
    }

    /** Malformed input that got past validation, e.g. a negative page number. */
    @ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
    public ResponseEntity<Map<String, Object>> handleBadRequest(RuntimeException ex) {
        log.warn("Bad request: {}", ex.getMessage());
        return ResponseEntity.badRequest()
                .body(body(HttpStatus.BAD_REQUEST, ex.getMessage()));
    }

    /**
     * Catch-all. Logs the full trace for operators and returns a generic
     * message to the client — raw exception text can disclose class names, SQL
     * fragments and filesystem paths.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleUnexpected(Exception ex) {
        log.error("Unhandled exception", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(body(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error"));
    }

    /**
     * Builds the response body. {@code error} and {@code message} carry the
     * same text: the frontend historically read {@code error}, while
     * {@code message} is the more conventional key. Emitting both keeps old and
     * new clients working without a coordinated release.
     */
    private Map<String, Object> body(HttpStatus status, String message) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", LocalDateTime.now());
        body.put("status", status.value());
        body.put("error", message);
        body.put("message", message);
        return body;
    }
}
