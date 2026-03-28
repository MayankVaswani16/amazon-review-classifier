# Testing Patterns & Infrastructure

## ☕ Backend (Spring Boot)
- **Framework:** Spring Boot Starter Test (includes JUnit 5, Mockito, AssertJ).
- **Current State:** Sparse automated tests found in the repository.
- **Test Locations:** `src/test/java` (standard) - currently contains minimal or generated content.
- **Observations:** `target/test-classes` existence suggests prior test execution, though source files may have been removed or moved.
- **Best Practices:** Use `@WebMvcTest` for controllers and `@DataJpaTest` for repositories to maintain isolation.

## ⚛️ Frontend (React)
- **Framework:** No explicit testing framework (Jest/Vitest) configured in `package.json`.
- **Current State:** Manual verification appears to be the primary testing strategy.
- **Recommendation:** Implement Vitest/React Testing Library for critical UI components.
- **Mocking:** Axios calls should be mocked using `axios-mock-adapter` or `msw` for reliable unit tests.

## 🐍 NLP Service (Python)
- **Framework:** No explicit testing framework (pytest) configured in `requirements.txt`.
- **Current State:** Manual testing via FastAPI's `/docs` (Swagger UI) interface.
- **Integration Tests:** Could be implemented using FastAPI's `TestClient` to verify endpoint logic without full model initialization.

## 🛠️ Infrastructure Testing
- **Docker Health:** `docker-compose.yml` includes health checks for `db`, `nlp-service`, and `backend`.
- **Backend Health Check:** `curl -f http://localhost:8080/api/health`
- **NLP Health Check:** `curl -f http://localhost:8001/nlp/health`
- **Strategy:** Integration-heavy testing favored over unit testing due to multi-service nature.
