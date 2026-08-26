# Build context is the monorepo root (see docker-compose.yml).
FROM python:3.12-slim AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY libs/ /app/libs/
COPY services/catalog-service/ /app/services/catalog-service/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/services/catalog-service/requirements.txt

WORKDIR /app/services/catalog-service

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
