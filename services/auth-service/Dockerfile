# Build context is the monorepo root (see docker-compose.yml) so this
# image can COPY the shared libs/ packages it depends on.
FROM python:3.12-slim AS base

# psycopg2-binary + cryptography need these at build time on slim images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY libs/ /app/libs/
COPY services/auth-service/ /app/services/auth-service/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/services/auth-service/requirements.txt

WORKDIR /app/services/auth-service
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
