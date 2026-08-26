# Build context is the monorepo root (see docker-compose.yml).
FROM python:3.12-slim AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY libs/trustbuy_common/ /app/libs/trustbuy_common/
COPY services/gateway/ /app/services/gateway/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/services/gateway/requirements.txt

WORKDIR /app/services/gateway

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
