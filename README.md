# Amazon Review Sentiment Classifier

A full-stack NLP application that analyses Amazon product reviews. It classifies
sentiment, extracts **aspect-level opinions with polarity** ("battery life → terrible"),
explains *why* it decided what it decided, and ranks which product features are actually
driving unhappy customers.

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

## Sentiment Engine

The classifier is a **hybrid** of two independent signals:

1. **Learned** — TF-IDF (uni + bigrams) into a calibrated Logistic Regression.
   Strong on vocabulary it has seen, useless on vocabulary it hasn't.
2. **Rule-based** — a valence lexicon with negation scope, intensifiers and
   contrastive handling (`lexicon.py`). Weaker on nuance, but it has no
   out-of-vocabulary problem and gets negation right by construction.

They are combined by a weighted blend in which **each engine's weight reflects how
much it actually knows about the text in front of it** — the model's by vocabulary
coverage, the lexicon's by the magnitude of its score. Critically, a lexicon score of
`0.0` means *"no opinion"*, not *"neutral opinion"*; conflating the two was measured
to cost ~9 points of accuracy.

The relative weight is **measured, not hand-picked**: after training, both engines are
scored on an out-of-distribution benchmark and the weight is set from their odds ratio.
Train on real data and the weight shifts back toward the model automatically.

### Pipeline

1. **clean_text** — strip HTML, URLs, non-letters; lowercase (apostrophes kept so
   contractions survive as negators)
2. **remove_stopwords** — NLTK stopwords **minus negation words**. NLTK's list contains
   "not"; removing it turns "not good" into "good" and silently inverts the label
3. **lemmatize_text** — spaCy `en_core_web_sm`
4. **TF-IDF** — `ngram_range=(1,2)`, which is what lets "not good" be learned as a
   feature distinct from "good". Step 2 only pays off because of this
5. **Split** — 80/20 stratified. The vectoriser is fitted on the **training split only**
6. **SMOTE** — training split only; before the split it would interpolate synthetic
   points between rows that later land in test, which is textbook leakage
7. **t-SNE** — diagnostic projections; never used at prediction time
8. **Calibrated Logistic Regression** — so 0.8 confidence means something

## Honest evaluation

| Measure | Score | What it means |
| --- | --- | --- |
| In-distribution accuracy | **99.1%** | Held-out split of the training corpus. **Not a real-world estimate** — the test data comes from the same generator as the training data, so this largely measures how well the model memorised the grammar |
| Out-of-distribution (model only) | **70.2%** | Hand-written realistic reviews with negation, sarcasm, mixed sentiment, misspellings |
| Out-of-distribution (lexicon only) | **77.2%** | |
| **Out-of-distribution (hybrid)** | **80.7%** | The number that matters |

The gap between 99% and 81% is the honest generalisation story, and both numbers are
published in the UI rather than only the flattering one.

**To make this production-grade, supply real training data.** Point `DATASET_PATH` at a
labelled CSV (columns `text`/`review` + `label`/`rating`; 1–2★ → negative, 4–5★ →
positive, 3★ dropped) and the service trains on it instead of the bootstrap corpus.

```bash
cp your-amazon-reviews.csv nlp-service/data/reviews.csv
docker-compose up --build
```

## Features

- **Analyzer** — sentiment with confidence, **aspect-level polarity**, engine-agreement
  and low-signal warnings, and a "Why this verdict?" explanation
- **Explainability** — per-token contributions that sum **exactly** to the decision
  logit (linear models make this exact, not approximate like LIME/SHAP), plus a
  **counterfactual**: the minimal set of words whose removal flips the verdict
- **Aspect Actionability Matrix** — the novel one. Ranks product aspects by
  `volume × severity × lift`, where lift is how much mentioning an aspect raises the
  odds of a negative review above the corpus baseline. A frequency chart ranks the
  most-talked-about feature first; this ranks the one actually costing you customers
- **Dashboard** — stat cards, sentiment split (including **mixed**), top features,
  actionability matrix, live model metrics, SMOTE distribution, t-SNE
- **History** — paginated, batch-scoped, with delete
- **Bulk Upload** — CSV upload, async job with live progress, batch-tagged results

### Why the Actionability Matrix is different

Given a jacket corpus where *colour* is mentioned 46 times and *zipper* 34:

```
ASPECT      MENTIONS   NEG   MEAN POL    LIFT   IMPACT
zipper            34    30      -0.46   +0.47    0.974   <- fix this
colour            46     0      +0.58   -0.42    0.000   <- mentioned MORE, not a problem
```

Frequency ranks *colour* first. Lift correctly ranks *zipper* first, because reviews
mentioning the zipper are 47 percentage points more likely to be negative.

## Tests

```bash
cd nlp-service && python -m pytest -q     # 51 tests
```

Covering negation and contrast handling, aspect extraction with negation, exact
attribution (contributions sum to the logit), counterfactual validity, blend
abstention behaviour, and batch/single prediction equivalence.

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
