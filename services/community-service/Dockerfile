# Build context is the monorepo root (see docker-compose.yml).
FROM python:3.12-slim AS base

# tesseract-ocr: real OCR on report attachments (app/ocr.py) - curl for
# the container healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY libs/ /app/libs/
COPY services/community-service/ /app/services/community-service/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/services/community-service/requirements.txt

WORKDIR /app/services/community-service

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

