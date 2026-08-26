# TrustBuy AI

**"Know Before You Buy."**

TrustBuy AI is an **AI Purchase Intelligence Platform**. It does not answer "is this website safe?" — that question belongs to ScamAdviser, VirusTotal, and Norton Safe Web. TrustBuy AI answers a harder, more useful question:

> **"Should I buy THIS product from THIS seller RIGHT NOW?"**

Every analysis fuses evidence from the product, the seller, the marketplace, the business behind it, its reviews, its advertisements, historical reputation, community reports, and known fraud networks into one explainable recommendation:

- 🟢 **BUY**
- 🟡 **BUY WITH CAUTION**
- 🔴 **AVOID PURCHASE**

Every recommendation ships with the evidence and reasoning behind it. There is no opaque "trust score" — the score, if shown at all, is a summary of evidence, never the product itself.

---

## Why TrustBuy AI is different

| | ScamAdviser / VirusTotal / Norton | TrustBuy AI |
|---|---|---|
| Unit of analysis | Website / domain | Product + Seller + Marketplace + Business, together |
| Output | A score (0–100) | A recommendation + evidence timeline |
| Reasoning | Hidden heuristics | Explainable, per-agent, cited evidence |
| Community | None / passive | Active reputation economy (Trust Points, badges, verification) |
| Time dimension | Point-in-time | Historical pattern learning, price manipulation detection |
| Fraud detection | Domain blacklists | Fraud network graph across sellers/products/accounts |

## Documentation map

This repository is documentation-first. No implementation begins until the architecture below is reviewed and approved. See [WORKFLOW](#workflow--project-management) at the bottom.

| Document | Contents |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, microservice architecture, AI agent architecture, folder structure, deployment architecture |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | ER diagram, full relational schema, vector store design |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | REST API design per microservice, auth flow, conventions |
| [docs/SRS.md](docs/SRS.md) | Software Requirements Specification (functional & non-functional) |
| [docs/USER_FLOWS.md](docs/USER_FLOWS.md) | End-user flow, admin flow, community reputation system |
| [docs/UI_UX_WIREFRAMES.md](docs/UI_UX_WIREFRAMES.md) | Wireframes, design system, layout of every core screen |
| [docs/SECURITY.md](docs/SECURITY.md) | Security architecture, threat model, abuse prevention |
| [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | Test pyramid, AI evaluation strategy, CI gates |
| [docs/RISK_ANALYSIS.md](docs/RISK_ANALYSIS.md) | Technical, legal, AI, and business risk register |
| [ROADMAP.md](ROADMAP.md) | Phased development roadmap, timeline, future scope |
| [DECISIONS.md](DECISIONS.md) | Architecture Decision Records (ADRs) |
| [CHANGELOG.md](CHANGELOG.md) | Dated log of what changed |
| [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) | Live phase-by-phase status tracker |
| [PROJECT_REPORT.md](PROJECT_REPORT.md) | **Final project report — the honest, itemized status of every feature below** |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Windows/Docker run commands, AWS deployment guide |

## Core product surface

The list below is the full product vision from Phase 0. **For which of these are actually built, tested, and running today vs. still planned, see [PROJECT_REPORT.md](PROJECT_REPORT.md) §5 "Feature Checklist"** — don't assume everything here is live.

- **AI Purchase Copilot** ✅ — a shopping-only AI assistant that explains *why* a recommendation was made and points at weak evidence.
- **Seller DNA Profile** 🟡 — signals exist (complaint history, prior-investigation track record); no dedicated profile UI yet.
- **Fraud Network Visualization** ❌ — not built.
- **Evidence Timeline** ✅ — live in the investigation UI.
- **Review Authenticity Analysis** ✅ — sentiment-mismatch and near-duplicate detection.
- **Counterfeit Detection** ❌ — not built (needs image forensics).
- **Advertisement Analysis** ❌ — not built.
- **Price Manipulation Detection** ✅ — live, via historical price-observation volatility.
- **Alternative Trusted Sellers** ❌ — schema exists, unpopulated.
- **Purchase Regret Prediction** ❌ — not built.
- **Community Intelligence** ✅ — reports, votes, verification quorum, Trust Points, badges, leaderboard, all live.
- **Shopping Memory** ❌ — not built.

## Tech stack

**Frontend** — Next.js 15, React, TypeScript, Tailwind CSS, shadcn/ui, Framer Motion, React Hook Form, TanStack Query, Axios, Lucide Icons, Recharts, next-themes.

**Backend** — FastAPI (Python 3.12), JWT auth, PostgreSQL, Redis, SQLAlchemy 2.0, Alembic.

**AI / ML** — Sentence Transformers, spaCy, scikit-learn, OpenCV, OCR (Tesseract/PaddleOCR), ChromaDB (vector store), an LLM provider for the multi-agent reasoning and copilot layer.

**Platform** — Docker, AWS (ECS/EKS, RDS, ElastiCache, S3, CloudFront), GitHub Actions CI/CD.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system, service, and deployment diagrams.

## Workflow & project management

This project is built phase by phase, never all at once:

1. **Phase 0 — Architecture** (this repository, currently in progress): SRS, system/microservice/AI-agent architecture, DB schema, API design, UX wireframes, security & risk analysis, roadmap. No application code is written until this is reviewed.
2. **Phase 1+** — implementation, one phase at a time, per [ROADMAP.md](ROADMAP.md). [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) is updated after every phase; [CHANGELOG.md](CHANGELOG.md) and [DECISIONS.md](DECISIONS.md) are updated whenever something changes or a non-obvious choice is made.

Existing work is always reused; nothing is rewritten without a documented reason (see [DECISIONS.md](DECISIONS.md)).

## Run it locally

Requires Docker Desktop (with Compose v2) and, optionally, Node 20+ if you want to run the frontend outside Docker. Everything else (Python, Postgres, Redis) runs inside containers - nothing else to install.

```bash
git clone <this-repo> && cd TrustBuy   # or just cd into your existing clone
cp .env.example .env
docker compose --env-file .env -f infra/docker/docker-compose.yml up --build
```

First run takes a few minutes (image builds + `npm install` inside the frontend build stage). When it's ready:

| Service | URL |
|---|---|
| **Web app** | http://localhost:3010 |
| API Gateway | http://localhost:8090/api/v1 (e.g. `GET /health`) |
| Auth Service (direct, for debugging) | http://localhost:8091 |
| Catalog Service (direct, for debugging) | http://localhost:8092 |
| Community Service (direct, for debugging) | http://localhost:8093 |
| Postgres | `localhost:5433` (user/db `trustbuy`, password in `.env`) |
| Redis | `localhost:6380` |
| ChromaDB | http://localhost:8010 |

Open **http://localhost:3010** and paste a real product URL (a Shopify store product page works best today - see [PROJECT_REPORT.md](PROJECT_REPORT.md) §4) to run a real investigation, or click **Get Started** to sign up first and unlock community reporting, the Copilot, and the dashboard. Database migrations run automatically on the auth-service container's first boot; a dev RSA keypair for JWT signing is generated automatically into a Docker volume the first time too - nothing to configure by hand.

**Stop the stack:**
```bash
docker compose -f infra/docker/docker-compose.yml down
```
Add `-v` to also delete the Postgres/Chroma/keys volumes (full reset).

**Ports were deliberately chosen** (5433, 6380, 8010, 8090, 8091, 3010 instead of the usual 5432/6379/8000/3000) to avoid colliding with anything else already running on your machine - see [DECISIONS.md](DECISIONS.md) ADR-002's implementation note if you ever need to change them (edit `.env`).

**Running the frontend outside Docker** (faster iteration while working on UI):
```bash
cd apps/web
cp .env.local.example .env.local
npm install
npm run dev
```
Requires the backend half of the stack (`postgres`, `redis`, `chroma`, `auth-service`, `catalog-service`, `community-service`, `gateway`) still running via `docker compose up`.

**Running backend tests** (any service - auth-service, gateway, catalog-service, community-service):
```bash
docker compose -f infra/docker/docker-compose.yml exec catalog-service sh -c "pip install pytest pytest-asyncio -q && python -m pytest -q"
```
Full command reference: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) §2.

**Linting:**
```bash
pip install ruff && ruff check libs services   # Python
cd apps/web && npm run lint && npm run type-check   # TypeScript
```

## Status

🚧 **Phases 1, 2, and 4 complete and verified; Phases 3, 5, and 6 partially complete.** Read **[PROJECT_REPORT.md](PROJECT_REPORT.md)** for the full, honest, itemized status of every feature (23 ✅ fully working, 5 🟡 partial, 15 ❌ missing, out of 43 discrete capabilities in the original brief) - it does not round up. [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) has the phase-by-phase tracker; [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) has exact run commands.
