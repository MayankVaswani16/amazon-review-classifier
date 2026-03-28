# Technical Concerns & Debt

## 🛑 Critical Risks
- **In-Memory Volatility:** Async bulk jobs are likely tracked in-memory (`BulkJobStore`). A backend restart will cause all active jobs to be lost, leaving the frontend in a permanent polling state. This is especially risky for long-running CSV imports (e.g., thousands of reviews).
- **Model Persistence:** The NLP service trains on "synthetic data" if no model is found on startup (`sentiment_model.train()` in `main.py`). This ensures the service runs but may lead to inaccurate/inconsistent predictions until a real model is provided or trained on actual data.

## ⚠️ Technical Debt
- **Testing Gap:** Extreme lack of automated unit and integration tests across all three services (Java, Python, React). This makes refactoring highly risky and increases reliance on manual QA.
- **Database Migrations:** Relying on `hibernate.ddl-auto=update` instead of structured migrations (Flyway/Liquibase). This makes schema changes difficult to track, roll back, or deploy safely across environments.
- **Error Transparency:** NLP service error handling (`detail=str(e)`) may leak internal Python stack traces or implementation details to the client, which is a potential security risk in production.

## 🔒 Security & Robustness
- **Auth/AuthZ:** No explicit security layer (Spring Security or similar) is visible, suggesting the internal API is currently unprotected and relies on network-level security.
- **Hardcoded Defaults:** While using environment variables, the fallback to `postgres/postgres` for database credentials in `application.properties` and `docker-compose.yml` is a common surface for misconfiguration.
- **Direct Model Access:** The NLP service loads a single global model; concurrent heavy requests might lead to performance bottlenecks if inference is computationally expensive.

## 🧩 Fragile Areas
- **Bulk CSV Parsing:** Handled in the frontend via `papaparse`. Large files (e.g., >10MB) might cause UI lag or browser memory issues before the data is even sent to the backend.
- **Service Dependency:** The backend requires both `db` and `nlp-service` to be healthy before it can fully function (as seen in `docker-compose.yml` health checks), creating a tight coupling.
- **Backward Compatibility:** `PredictionController` maintains a synchronous bulk endpoint (`/predict/bulk`) alongside the newer async one, which may mislead users into using suboptimal paths for large datasets.
- **Logger Configuration:** Python logging is set to `INFO` globally, which might be too verbose for production or hide critical debug information if not properly piped to a log aggregator.
