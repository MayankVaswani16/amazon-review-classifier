FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps — install with retries to handle transient network errors
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 5 --timeout 120 -r requirements.txt

# Install spaCy model directly via pip wheel (more reliable than `python -m spacy download`)
RUN pip install --no-cache-dir --retries 5 --timeout 120 \
    https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# Download NLTK stopwords corpus into a fixed path
RUN python -c "import nltk; nltk.download('stopwords', download_dir='/usr/local/nltk_data', quiet=True)"
ENV NLTK_DATA=/usr/local/nltk_data

# Copy app
COPY . .

# Create model/image output directories
RUN mkdir -p models static

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD curl -f http://localhost:8001/nlp/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
