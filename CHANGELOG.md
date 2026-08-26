# Changelog

All notable changes to TrustBuy AI are logged here, most recent first. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed — 2026-08-15 (pre-launch Tier-1 hardening pass)
- **Copilot/Advisor "same answer every time" bug**: with no `ANTHROPIC_API_KEY` configured (this deployment's current state), `answer_question()` returned the deterministic template string byte-for-byte identical on every call for the same intent - a rephrased or repeated question read back exactly the same text. `app/copilot/templates.py` now rotates 2-3 honest phrasing variants per handler by `turn_index` (assistant-message count in the conversation, threaded through from `app/copilot/service.py`); the underlying verdict/confidence/evidence never change, only how they're introduced. Verified with a standalone script asserting non-identical output across 6 turns of the same question.
- **Rate limiter upgraded fixed-window → token-bucket** (`services/gateway/app/rate_limit.py`, DECISIONS.md ADR-009 addendum): now a single atomic Redis Lua script per request (capacity + continuous refill), matching docs/SECURITY.md §5's original target and removing the fixed-window's edge-of-window double-burst.
- **Business registration (GSTIN/CIN) now actually parsed** when a seller discloses one on the page (`app/adapters/generic.py`'s `_detect_business_registration`, real regex against real Indian GSTIN/CIN formats - never looked up against an external registry, never guessed). Wired into `app/seller_intelligence/service.py`'s trust/transparency scoring for Official Brand Website and Independent Store source types. Previously always reported `Data unavailable`.
- Core-flow review (orchestrator, safe_fetch, routes, community self-vote guard, frontend Copilot double-submit guard) - no additional bugs found; confirmed the Phase 2/4 fixes are still intact.

### Added — 2026-08-07 (Phase 2, 4, partial 5 & 6 — same-day continuation)
- **Marketplace Adapter Architecture** (ADR-008): Platform Detection Dispatcher, real Shopify adapter (verified against a live store's `.json` endpoint), real Generic Structured-Data adapter (JSON-LD/OpenGraph), 6 domain-matched adapters (Amazon India, Flipkart, Myntra, Meesho, Instagram Shopping, Facebook Marketplace) that correctly identify their platform and delegate to the generic parser.
- **Catalog Service** (new): Product Extraction + investigation orchestration, running the pipeline as an in-process `asyncio` background task (ADR-011, a documented simplification of the target queue-based design).
- **4 real intelligence agents**: Platform Verification (live TLS handshake), Seller Intelligence (community + prior-investigation signals), Review Intelligence (VADER sentiment + near-duplicate detection), Historical Learning (price-manipulation detection).
- **Evidence Fusion Engine v1**: deterministic, versioned, unit-tested weighted-evidence algorithm; LLM only narrates the already-fixed verdict, never computes it.
- **SSRF-safe outbound fetcher** (`safe_fetch.py`): verified against both the AWS metadata endpoint and localhost.
- **LLM provider abstraction** (ADR-010): `MockLLMProvider` (real, working, clearly labeled) + `AnthropicLLMProvider` (real, activates on `ANTHROPIC_API_KEY` with zero code changes).
- **Investigation frontend**: URL submission, live per-agent progress polling, verdict/evidence-timeline display - browser-verified end to end, including finding and fixing a real polling bug (`refetchIntervalInBackground`).
- **Community Service** (new): reports (5 types, duplicate detection via content hashing), voting (self-vote blocked - a real bug found and fixed this session), 3-verifier quorum resolution, Trust Points ledger, automatic reputation-level computation, 3 seeded badges, leaderboard, moderation queue.
- **File storage abstraction** (ADR-012): `LocalDiskStorageProvider` (real, working) + `S3StorageProvider` (real, activates on `TRUSTBUY_S3_BUCKET`), used by report attachments and PDF exports.
- **Real OCR** (Tesseract) on report-attachment images.
- **AI Purchase Copilot**: two-layer scope enforcement (deterministic intent classifier + grounded LLM prompt), verified both accepting an in-scope question and declining an off-topic one in the same conversation.
- **PDF evidence report export**: real `reportlab` rendering, verified as a valid PDF from real investigation data.
- **Admin Dashboard**: metrics overview, moderation queue with resolve actions, failed-investigations list, user suspension - all RBAC-gated (admin/moderator only) and verified, including that a suspended user genuinely cannot log back in.
- **Full documentation closeout**: [PROJECT_REPORT.md](PROJECT_REPORT.md) (final report, AI agent summary, marketplace adapter summary, honest 43-item feature checklist, Principal-Engineer self-review, testing report, known limitations, maintenance guide) and [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) (Windows/Docker run commands, AWS deployment guide).
- Verification: 24 backend tests across 4 services (all passing), frontend lint/type-check/build (clean), `ruff check` (clean), a from-scratch `docker compose down -v && up --build` rebuild, and an 11-point live end-to-end smoke test against real network traffic - 11/11 passed on the final run.

### Added — 2026-08-07 (Phase 1)
- **Phase 1 - Foundation complete.** Monorepo scaffold, Docker Compose dev stack (Postgres, Redis, Chroma, auth-service, gateway, web), shared libraries (`trustbuy_common`, `trustbuy_db`, `trustbuy_auth`, `trustbuy_agent_sdk`), Authentication Service (signup/login/refresh/logout/me/sessions, Argon2id + RS256 JWT), API Gateway (reverse proxy, Redis rate limiting, CORS), Alembic baseline migration (`users`, `refresh_tokens`, `audit_logs`), Next.js 15 frontend (landing/login/signup/dashboard, dark/light theme, TanStack Query, in-memory-token auth), GitHub Actions CI (`.github/workflows/ci.yml`).
- All of it built and smoke-tested end to end: `docker compose build/up`, full auth flow via curl and a real browser session, backend `pytest` suites, frontend `npm run build`/`lint`, `ruff check`. Details and exact repro steps in [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) "Phase 1 completion record".
- Fixed one real bug surfaced during verification: `device_label` truncation for real browser User-Agent strings exceeding `VARCHAR(120)` (DECISIONS.md ADR-009).
- Recorded ADR-009 (Phase 1 implementation-scope notes: Tailwind v3, in-memory access tokens, fixed-window rate limiter, deferred email verification, `device_label` truncation) and a Phase-1 implementation clarification on ADR-002 (local dev runs services as separate containers; the "3 deployable units" grouping is an AWS ECS concern that starts in Phase 6).
- Reviewed (read-only) three pre-existing `trustbuy-ai*` project folders in `Downloads/` per your instruction; left untouched, used only to inform a few implementation patterns (see prior conversation turn).

### Changed — 2026-08-07 (later same day)
- **ADR-002 confirmed**: phased microservice deployment (3 grouped ECS units for Phases 1–5) accepted.
- **ADR-008 added and accepted**: TrustBuy AI is marketplace-agnostic by architecture — a pluggable `SourceAdapter` framework with auto-detection, no hardcoded marketplace logic in core services. Initial 9 target sources: Amazon India, Flipkart, Myntra, Meesho, Shopify stores, official brand websites, Instagram shopping links, Facebook Marketplace, advertisement landing pages.
- Updated [ARCHITECTURE.md](ARCHITECTURE.md) §4.1 (new adapter architecture diagram + contract), [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) `marketplaces` table (`platform_type`, `source_identifier`, `adapter_version`), [ROADMAP.md](ROADMAP.md) Phase 2 (re-sequenced: framework + 2 pilot adapters, remaining 7 as incremental backlog), [API_DOCUMENTATION.md](API_DOCUMENTATION.md) (`detected_platform` in investigation response), and [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md).
- LLM provider decision explicitly deferred by product owner; remains the only open item, and only blocks Phase 2 agent work, not Phase 1.

### Added — 2026-08-07
- Phase 0 architecture complete: [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md), [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md), [API_DOCUMENTATION.md](API_DOCUMENTATION.md), [ROADMAP.md](ROADMAP.md), [DECISIONS.md](DECISIONS.md), and `docs/` (SRS, User Flows, UI/UX Wireframes, Security, Testing Strategy, Risk Analysis).
- Recorded 7 initial ADRs in [DECISIONS.md](DECISIONS.md), including the open recommendation on phased microservice deployment (ADR-002) awaiting sign-off.
- No application code yet — by design, per project workflow (see [README.md](README.md#workflow--project-management)).
