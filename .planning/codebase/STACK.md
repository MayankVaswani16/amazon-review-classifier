# Technology Stack

## Core Services

### ☕ Backend (Spring Boot)
- **Runtime:** Java 17
- **Framework:** Spring Boot 3.2.1
- **Build System:** Maven
- **Primary Dependencies:**
  - `spring-boot-starter-web`: RESTful API support
  - `spring-boot-starter-data-jpa`: Database abstraction
  - `postgresql`: Database driver
  - `spring-boot-starter-validation`: Bean validation
  - `lombok`: Boilerplate reduction
  - `spring-boot-starter-actuator`: Health check and monitoring
- **Config:** `src/main/resources/application.properties` (likely)

### ⚛️ Frontend (React)
- **Runtime:** Node.js (via Vite)
- **Framework:** React 18.2.0
- **Styling:** Tailwind CSS 3.4.0, PostCSS
- **Build Tool:** Vite 5.0.8
- **Primary Dependencies:**
  - `react-router-dom`: SPA routing
  - `axios`: HTTP client
  - `recharts`: Data visualization
  - `papaparse`: CSV parsing for bulk upload
  - `react-hot-toast`: Notifications
  - `react-icons`: Icon sets

### 🐍 NLP Service (FastAPI)
- **Runtime:** Python 3.10+ (standard for recent FastAPI)
- **Framework:** FastAPI 0.104.1
- **Server:** Uvicorn 0.24.0
- **ML/DS Libraries:**
  - `scikit-learn`: ML models
  - `spacy`: NLP pipelines
  - `nltk`: Natural language toolkit
  - `numpy`: Numerical processing
  - `imbalanced-learn`: Handling class imbalance
- **Data Handling:** `pydantic` v2, `Pillow` (image processing, though primarily text-focused project)

## 🐳 Infrastructure
- **Containerization:** Docker with `docker-compose.yml`
- **Frontend Server:** Nginx (used in production Docker build)
- **Database:** PostgreSQL 15-alpine
