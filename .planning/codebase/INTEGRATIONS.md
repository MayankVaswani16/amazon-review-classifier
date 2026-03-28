# External Integrations & Services

## 🗄️ Database
- **Service:** PostgreSQL
- **Container Name:** `review-db`
- **Internal Port:** 5432
- **External Port:** 5432
- **Database Name:** `reviewdb`
- **Credentials:** `postgres/postgres` (managed via environment variables)

## 🔄 Service-to-Service Communication
- **Frontend -> Backend:**
  - Standard REST calls over HTTP
  - Development port: `8081` (mapped to `8080` in container)
- **Backend -> NLP Service:**
  - HTTP REST calls
  - Internal URL: `http://nlp-service:8001`
  - Health check path: `http://localhost:8001/nlp/health`

## 🔌 API Endpoints (NLP Service)
- **Base URL:** `http://nlp-service:8001`
- **Endpoints:**
  - `/nlp/health`: Service health monitoring
  - (Further investigation required for specific classification endpoints)
