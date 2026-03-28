# Directory Structure

## 📂 Root
- `/backend`: Spring Boot application code.
- `/frontend`: React application code.
- `/nlp-service`: Python FastAPI microservice.
- `docker-compose.yml`: Local infrastructure setup.

## ☕ Backend (`/backend`)
- `src/main/java/com/amazon/reviewclassifier/`
  - `controller/`: REST endpoints (e.g., SentimentController).
  - `service/`: Business logic and external service clients.
  - `repository/`: Spring Data JPA interfaces.
  - `entity/`: Database model definitions.
  - `dto/`: Request/Response data containers.
  - `config/`: Application configuration (CORS, etc.).
  - `exception/`: Error handling logic.
- `src/main/resources/`: Configuration files (properties/yaml).

## ⚛️ Frontend (`/frontend`)
- `src/`
  - `pages/`: High-level views (Dashboard, Analyzer, History).
  - `components/`: UI building blocks (Navbar, Spinner, ResultCard).
  - `api/`: Centralized API call logic.
  - `App.jsx`: Main routing and layout.
  - `main.jsx`: React mount point.
- `public/`: Static assets.
- `index.html`: Entry page shell.

## 🐍 NLP Service (`/nlp-service`)
- `main.py`: FastAPI entry point and routes.
- `model.py`: Model loader and classification logic.
- `schemas.py`: Pydantic schema definitions.
- `requirements.txt`: Python package dependencies.
- `Dockerfile`: Container image definition.
