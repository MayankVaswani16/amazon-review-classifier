package com.amazon.reviewclassifier.exception;

/**
 * Thrown when a prediction is requested by an ID that does not exist.
 *
 * <p>This type exists so "not found" can be distinguished from "something went
 * wrong". Previously the service threw a bare {@link RuntimeException} and the
 * global handler mapped <i>every</i> {@code RuntimeException} to 404 — which
 * meant a {@code NullPointerException} anywhere in the service layer was
 * reported to the client as "Not Found". That is actively misleading: it hides
 * real bugs behind a status code that says the request was fine.
 */
public class PredictionNotFoundException extends RuntimeException {

    public PredictionNotFoundException(Long id) {
        super("Prediction not found: " + id);
    }

    public PredictionNotFoundException(String message) {
        super(message);
    }
}
