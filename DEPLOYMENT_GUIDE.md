# TrustBuy AI — Deployment Guide

Related: [README.md](README.md) · [PROJECT_REPORT.md](PROJECT_REPORT.md) · [ARCHITECTURE.md](ARCHITECTURE.md) §8 · [docs/SECURITY.md](docs/SECURITY.md)

## 1. Local development (Windows)

Prerequisites: Docker Desktop (with Compose v2 and WSL2 backend), Git. Node 20+ optional (only needed to run the frontend outside Docker).

```powershell
cd D:\practice\Desktop\TrustBuy
Copy-Item .env.example .env
docker compose --env-file .env -f infra/docker/docker-compose.yml up --build
```

Same commands work verbatim in the Bash tool / Git Bash (`cp` instead of `Copy-Item`). First run takes a few minutes (image builds, `npm install`, dependency downloads). Subsequent runs are fast (layer cache).

Once every container reports healthy:

| Service | URL |
|---|---|
| Web app | http://localhost:3010 |
| API Gateway | http://localhost:8090/api/v1 |
| Auth Service (direct) | http://localhost:8091 |
| Catalog Service (direct) | http://localhost:8092 |
| Community Service (direct) | http://localhost:8093 |
| Postgres | `localhost:5433` |
| Redis | `localhost:6380` |
| ChromaDB | http://localhost:8010 |

Open http://localhost:3010, paste a real product URL (a Shopify store product page is the most reliably-extracted source today - see [PROJECT_REPORT.md](PROJECT_REPORT.md) §4), and watch the investigation complete.

### Stopping / resetting

```powershell
# Stop, keep data
docker compose -f infra/docker/docker-compose.yml down

# Stop and wipe all data (Postgres, Chroma, JWT keys, uploaded files)
docker compose -f infra/docker/docker-compose.yml down -v
```

### Running the frontend outside Docker (faster UI iteration)

```powershell
cd apps\web
Copy-Item .env.local.example .env.local
npm install
npm run dev
```

Requires the backend half of the stack (`postgres`, `redis`, `chroma`, `auth-service`, `catalog-service`, `community-service`, `gateway`) still running via `docker compose up`.

## 2. Docker commands reference

```bash
# Build every image without starting anything
docker compose --env-file .env -f infra/docker/docker-compose.yml build

# Build and start one service only
docker compose --env-file .env -f infra/docker/docker-compose.yml up --build -d catalog-service

# Tail logs for one service
docker logs -f trustbuy-ai-platform-catalog-service-1

# Run the backend test suite for a service (any of auth-service, gateway, catalog-service, community-service)
docker exec trustbuy-ai-platform-catalog-service-1 sh -c "pip install --no-cache-dir pytest pytest-asyncio -q && python -m pytest -q"

# Open a shell in a running container
docker exec -it trustbuy-ai-platform-catalog-service-1 sh

# Generate a new Alembic migration after changing libs/trustbuy_db/trustbuy_db/models/
docker exec trustbuy-ai-platform-auth-service-1 sh -c "cd /app/libs/trustbuy_db && alembic -c alembic.ini revision --autogenerate -m 'describe the change'"
# Then: docker cp the generated file out of the container into libs/trustbuy_db/alembic/versions/,
# rename it to the next 000N_ prefix, review it (see PROJECT_REPORT.md §10 - Alembic's
# constraint-diffing produces harmless spurious noise on every run), then rebuild+restart
# any service that owns migrations (auth-service applies them automatically on boot).

# Inspect the Postgres database directly
docker exec -it trustbuy-ai-platform-postgres-1 psql -U trustbuy -d trustbuy

# Check what's actually stored on the local-disk StorageProvider
docker exec trustbuy-ai-platform-community-service-1 sh -c "find /data/uploads -type f"
```

## 3. Linting

```bash
pip install ruff
ruff check libs services            # Python - repo root, see ruff.toml
cd apps/web && npm run lint && npm run type-check   # TypeScript
```

## 4. Environment variables that matter for a real deployment

All of these are documented in `.env.example` with inline comments; the ones that change actual behavior (not just ports):

| Variable | Effect when set |
|---|---|
| `ANTHROPIC_API_KEY` | Switches the Evidence Fusion Engine's explanations and the AI Purchase Copilot from the mock template provider to real Claude output (ADR-010). Zero code changes. |
| `TRUSTBUY_S3_BUCKET` + `AWS_REGION` | Switches community-report attachments and PDF report exports from local disk to S3 (ADR-012). Zero code changes. Requires real AWS credentials reachable by the container (IAM role in production; `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` env vars locally). |
| `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` | In production, point these at files sourced from AWS Secrets Manager (mounted or fetched at container start), not the auto-generated dev keypair. |

## 5. AWS deployment guide (target architecture, not yet automated)

This is the manual bridge to the target state in [ARCHITECTURE.md](ARCHITECTURE.md) §8. **No Terraform/CloudFormation has been written yet** (see [PROJECT_REPORT.md](PROJECT_REPORT.md) §8, limitation #8) - this section is the deployment *plan*, to be automated in Phase 6.

### 5.1 Prerequisites
- An AWS account with an isolated VPC (per environment: dev/staging/production - docs/SECURITY.md §3).
- ECR repositories for each of the 6 images (`auth-service`, `gateway`, `catalog-service`, `community-service`, `web`, plus any future service).
- RDS PostgreSQL (Multi-AZ for production), ElastiCache Redis, an S3 bucket for file storage, ACM certificate for HTTPS.
- Secrets Manager entries for: DB credentials, JWT signing keypair (generate once with a real CSPRNG, `openssl genrsa`, never the dev-boot auto-generator), `ANTHROPIC_API_KEY`.

### 5.2 Build and push images

```bash
AWS_ACCOUNT_ID=<your-account-id>
AWS_REGION=<your-region>
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

for svc in auth-service gateway catalog-service community-service; do
  docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/trustbuy-$svc:latest \
    -f services/$svc/Dockerfile .
  docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/trustbuy-$svc:latest
done

docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/trustbuy-web:latest \
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.trustbuy.ai/api/v1 apps/web
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/trustbuy-web:latest
```

### 5.3 ECS task definitions (per ADR-002's phased grouping)

- **core-api** (Fargate service): gateway + auth-service + community-service containers in one task definition (or separate tasks behind the same target group, either works - ADR-002 leaves the exact grouping to whoever automates this).
- **catalog-api** (Fargate service): catalog-service - this is the one most likely to need independent scaling first (it does the actual extraction + agent work), so give it its own task definition and autoscaling policy from the start even if grouped with others initially.
- **web** (Fargate service): the Next.js app, behind CloudFront.

Environment variables for every task definition come from Secrets Manager (`valueFrom`), never plaintext task-definition JSON.

### 5.4 Networking

- ALB in public subnets, terminating TLS (ACM cert), forwarding to the gateway's target group on the private-subnet ECS tasks.
- CloudFront in front of the ALB for the web app's static assets (per ARCHITECTURE.md §8).
- Security groups: ALB → gateway (port 8000 only), gateway → core/catalog services (port 8000 only, VPC-internal), all services → RDS (5432) and ElastiCache (6379) only from their own security group.

### 5.5 Database migrations in production

Run as a one-off ECS task (not baked into the running service's boot sequence in production - the dev `entrypoint.sh` auto-migrate-on-boot pattern is fine for local dev but risks two replicas racing a migration in production):

```bash
aws ecs run-task --cluster trustbuy-production --task-definition trustbuy-migrate \
  --overrides '{"containerOverrides":[{"name":"migrate","command":["sh","-c","cd /app/libs/trustbuy_db && alembic upgrade head"]}]}'
```

### 5.6 Rollout checklist before first production traffic

1. All items in [docs/SECURITY.md](docs/SECURITY.md) checklist reviewed.
2. `ANTHROPIC_API_KEY` and `TRUSTBUY_S3_BUCKET` set (Known Limitation #10/#4 in [PROJECT_REPORT.md](PROJECT_REPORT.md) resolved).
3. Load testing performed (not yet done - Known Limitation, [PROJECT_REPORT.md](PROJECT_REPORT.md) §7).
4. Orchestrator swapped to the queue-based design (ADR-011) if agent count/volume justifies it before launch.
5. CI pipeline verified against a real GitHub Actions run (not yet done).
