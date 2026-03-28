# Coding Conventions

## ☕ Backend (Java/Spring Boot)
- **Framework:** Spring Boot 3.2+ (Jakarta EE).
- **Architecture:** Controller-Service-Repository pattern.
- **Dependency Injection:** Constructor-based DI using Lombok `@RequiredArgsConstructor`.
- **Data Transfer:** DTOs used for API request/response; Entities for database mapping.
- **REST Patterns:**
  - `ResponseEntity` for structured HTTP responses.
  - `UUID` for asynchronous job identifiers.
  - Endpoint prefix: `/api`.
- **Naming:** CamelCase for classes (`PredictionController`), camelCase for methods/variables.
- **Validation:** Java Bean Validation (`@Valid`, `@NotNull`) used on DTOs.

## ⚛️ Frontend (React/Vite)
- **Components:** Functional components with React Hooks.
- **Styling:** Tailwind CSS with utility-first approach.
- **Routing:** `react-router-dom` defined in `App.jsx`.
- **API Interaction:** Axios used for HTTP calls, encapsulated in the `api/` directory.
- **File Naming:** PascalCase for components/pages (`Analyzer.jsx`), camelCase for helpers/util subdirectories.
- **UI/UX:** Premium aesthetic with dark mode (`bg-dark-950`), custom gradients, and blur effects.

## 🐍 NLP Service (Python/FastAPI)
- **Framework:** FastAPI with Pydantic for schema validation.
- **ML Integration:** Scikit-learn models wrapped in FastAPI endpoints.
- **Type Hinting:** Extensive use of Python type hints for clarity and validation.
- **Project Structure:** Flat structure for small-scale microservices (files in root).
