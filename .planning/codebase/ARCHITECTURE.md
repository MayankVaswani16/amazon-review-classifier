# System Architecture

## 🏗️ High-Level Design
The system follows a microservices-inspired architecture with clear separation of concerns:
- **Frontend (Presentation):** React SPA for user interaction, data visualization, and bulk management.
- **Backend (Orchestration):** Spring Boot service managing business logic, data persistence, and service orchestration.
- **NLP Service (Domain):** Python FastAPI service dedicated to sentiment analysis using machine learning.
- **Database (Persistence):** PostgreSQL for storing review history and metadata.

## 🔄 Data Flow
1. **User Input:** User submits a single review or a bulk CSV file through the UI.
2. **API Orchestration:** Frontend calls the Spring Boot Backend.
3. **Classification:** Backend forwards the text to the NLP Service via REST.
4. **Analysis:** NLP Service processes the text using scikit-learn/spacy and returns a sentiment score/category.
5. **Persistence:** Backend saves the review and its result to the Database.
6. **Response:** Backend returns the classification results to the Frontend for display.

## 🧩 Service Architecture

### Backend (Spring Boot)
- **Controller Layer:** Handles REST requests (`com.amazon.reviewclassifier.controller`).
- **Service Layer:** Contains business logic and orchestrates calls to the NLP service (`com.amazon.reviewclassifier.service`).
- **Repository Layer:** Abstracted data access using Spring Data JPA (`com.amazon.reviewclassifier.repository`).
- **Persistence Layer:** JPA Entities mapping to PostgreSQL tables (`com.amazon.reviewclassifier.entity`).

### Frontend (React)
- **Routing:** Handled by `react-router-dom` in `App.jsx`.
- **State Management:** Local React state, with API calls encapsulated in the `api` directory.
- **Components:** Modular atomic components (`components`) and page-level components (`pages`).

### NLP Service (FastAPI)
- **API Wrapper:** FastAPI (`main.py`) provides the web interface.
- **Model Logic:** `model.py` handles the heavy lifting of ML inference.
- **Data Validation:** `schemas.py` ensures strict typing for API inputs/outputs.
