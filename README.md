# Amazon Review Sentiment Classifier

A full-stack NLP-powered web application that analyzes Amazon product reviews for sentiment, extracts product features (nouns), sentiment descriptors (adjectives), and feature→sentiment pairs using spaCy dependency parsing.

![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue) ![React](https://img.shields.io/badge/Frontend-React_18-61DAFB) ![Spring Boot](https://img.shields.io/badge/Backend-Spring_Boot_3-6DB33F) ![FastAPI](https://img.shields.io/badge/NLP-FastAPI-009688) ![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL_15-4169E1)

## Architecture

```
React (5173) → Spring Boot (8080) ↔ PostgreSQL (5432)
                      ↓ internal only
             Python FastAPI NLP (8001)
```

- **Frontend** never calls the Python service directly
- **Spring Boot** is the single entry point for all API calls
- **NLP Service** handles text preprocessing, model inference, POS tagging, and dependency parsing

## Tech Stack

| Layer        | Technology                                        |
| ------------ | ------------------------------------------------- |
| Frontend     | React 18, TailwindCSS 3, Recharts, React Router 6, Axios |
| Backend      | Java 17, Spring Boot 3, Maven, Spring Data JPA, Lombok |
| NLP Service  | Python 3.11, FastAPI, spaCy, scikit-learn, imbalanced-learn |
| Database     | PostgreSQL 15                                     |
| Deployment   | Docker, docker-compose                            |

## NLP Pipeline

1. **clean_text** — Remove HTML, URLs, special characters; lowercase
2. **remove_stopwords** — NLTK stopwords minus negation words (not, never, can't, etc.)
3. **lemmatize_text** — spaCy `en_core_web_sm` lemmatizer
4. **TF-IDF** — `max_features=5000`, `ngram_range=(1,2)`, `sublinear_tf=True`
5. **Train/Test Split** — 80/20, stratified
6. **SMOTE** — Oversample minority class on training data only
7. **t-SNE** — 2D visualizations before and after SMOTE
8. **Logistic Regression** — `C=1.0`, `solver='lbfgs'`, `max_iter=1000`

## Features

- **Analyzer** — Single review sentiment analysis with confidence bar, noun/adjective badges, and feature-sentiment table
- **Dashboard** — Stat cards, donut chart, bar charts, SMOTE distribution, t-SNE visualizations
- **History** — Paginated prediction history with delete
- **Bulk Upload** — CSV upload with column selector, batch analysis, and CSV download

---

## Quick Start with Docker

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop/) & Docker Compose

### Run

```bash
docker-compose up --build
```

That's it! Wait for all services to become healthy, then open:

- **Frontend**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8080/api/health](http://localhost:8080/api/health)
- **NLP Service**: [http://localhost:8001/nlp/health](http://localhost:8001/nlp/health)

### Stop

```bash
docker-compose down
```

To also remove the PostgreSQL data volume:

```bash
docker-compose down -v
```

---

## Local Development Setup

### 1. PostgreSQL

Install and start PostgreSQL 15. Create a database:

```sql
CREATE DATABASE reviewdb;
```

### 2. NLP Service

```bash
cd nlp-service
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 3. Spring Boot Backend

```bash
cd backend
# Make sure JAVA_HOME points to JDK 17+
mvn spring-boot:run
```

Environment variables (optional, defaults work for local):
- `DB_URL` — default: `jdbc:postgresql://localhost:5432/reviewdb`
- `DB_USERNAME` — default: `postgres`
- `DB_PASSWORD` — default: `postgres`
- `NLP_SERVICE_URL` — default: `http://localhost:8001`

### 4. React Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## API Endpoints

| Method   | Endpoint            | Description              |
| -------- | ------------------- | ------------------------ |
| `POST`   | `/api/predict`      | Single review prediction |
| `POST`   | `/api/predict/bulk` | Batch predictions        |
| `GET`    | `/api/history`      | Paginated history        |
| `GET`    | `/api/history/{id}` | Single record            |
| `DELETE` | `/api/history/{id}` | Delete record            |
| `GET`    | `/api/stats`        | Aggregate analytics      |
| `GET`    | `/api/tsne/before`  | t-SNE before SMOTE (PNG) |
| `GET`    | `/api/tsne/after`   | t-SNE after SMOTE (PNG)  |
| `GET`    | `/api/health`       | Health check             |

## Folder Structure

```
amazon-review-classifier/
├── backend/                  # Spring Boot (Java 17)
│   ├── src/main/java/com/amazon/reviewclassifier/
│   │   ├── config/           # CORS, RestTemplate
│   │   ├── controller/       # REST controllers
│   │   ├── dto/              # Request/Response DTOs
│   │   ├── entity/           # JPA entities
│   │   ├── exception/        # Global error handler
│   │   ├── repository/       # Spring Data JPA
│   │   └── service/          # Business logic
│   ├── src/main/resources/
│   │   └── application.properties
│   ├── Dockerfile
│   └── pom.xml
├── nlp-service/              # FastAPI (Python 3.11)
│   ├── main.py               # FastAPI endpoints
│   ├── model.py              # ML pipeline + NLP
│   ├── schemas.py            # Pydantic models
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # React 18 + Vite
│   ├── src/
│   │   ├── api/client.js     # Centralized Axios client
│   │   ├── components/       # Navbar, Spinner, ResultCard
│   │   ├── pages/            # Analyzer, Dashboard, History, BulkUpload
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── nginx.conf
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## License

MIT
