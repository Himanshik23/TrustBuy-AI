#!/bin/sh
set -e

# 1. Ensure a dev RSA keypair exists in the shared /keys volume (no-op if
#    one is already there - see trustbuy_auth/keys.py).
python -m trustbuy_auth

# 2. Apply database migrations. Migrations are owned by trustbuy_db
#    (shared schema, ARCHITECTURE.md §7), not by this service.
cd /app/libs/trustbuy_db
alembic -c alembic.ini upgrade head
cd /app/services/auth-service

# 3. Start the API.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

