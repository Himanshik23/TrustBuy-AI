# TrustBuy AI — Architecture Decision Records (ADRs)

Format: each ADR has **Status** (Proposed / Accepted / Superseded), **Context**, **Decision**, **Consequences**. New entries are appended, never rewritten — if a decision changes, a new ADR supersedes it and both stay in the log.

---

## ADR-001 — Evidence-first, no bare trust score

**Status**: Accepted

**Context**: The obvious, easy design is a single 0–100 "trust score," like every competitor. It's also the least defensible legally, the least explainable, and the least differentiated.

**Decision**: The platform never surfaces a bare numeric score as the primary output. The primary output is always `{ verdict, evidence[], confidence, explanation }`. A confidence number may be *shown alongside* the verdict, but it is never the headline element in the UI.

**Consequences**: Every service contract (agents, Fusion Engine, API) is shaped around evidence objects, not scores (see [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) §2.3). Harder to build than a score dashboard; that difficulty is the moat.

---

## ADR-002 — Logical microservices, phased physical deployment

**Status**: Accepted — confirmed by product owner 2026-08-07

**Context**: The requested architecture specifies 16 distinct microservices/agents. Deploying all 16 as separately-scaled, separately-deployed services from day one is real startup practice for companies past product-market fit (large teams, high traffic) — but for a pre-launch product built by a small team, it multiplies operational overhead (16 CI pipelines, 16 sets of alarms, 16 deploy surfaces) without a traffic justification yet. Linear, Stripe, and Vercel-caliber companies did not ship their v1 as 16 independently-scaled services.

**Decision**: Keep the **logical** boundaries exactly as specified in [ARCHITECTURE.md](ARCHITECTURE.md) §4 — each service is its own Python package with its own database ownership and its own REST contract, so the target architecture is fully realized in code from day one. **Physically**, group them into fewer deployable ECS services during Phases 1–5:
- **Deployable unit A**: Gateway + Auth + Community + Notification + Report Generation ("core-api")
- **Deployable unit B**: Product Extraction + Recommendation Engine ("catalog-api")
- **Deployable unit C**: all 9 intelligence agents + Evidence Fusion Engine, run as async workers behind the same queue ("agent-workers")

Each logical service still gets its own Docker image and can be split into its own ECS service the moment its load profile demands independent scaling (agent workers are the most likely first split, since they're the most compute-bursty — see [ROADMAP.md](ROADMAP.md) future scope).

**Consequences**: Faster Phase 1–3 velocity, lower AWS bill pre-launch, zero rework needed to split later (module boundaries are already service boundaries).

**Implementation note (Phase 1, added 2026-08-07)**: the "3 deployable units" grouping is an *AWS ECS task-definition* concern, which doesn't exist yet — Terraform/ECS is Phase 6 ([ROADMAP.md](ROADMAP.md)). Locally, `infra/docker/docker-compose.yml` runs `gateway` and `auth-service` as separate containers, because that costs nothing extra in dev and keeps the logical service boundary visible. When Phase 6 builds the real AWS deployment, that's where core-api's services get bundled into one ECS service per ADR-002 — not before.

---

## ADR-008 — Marketplace-agnostic pluggable adapter architecture

**Status**: Accepted — set by product owner 2026-08-07, supersedes the single-marketplace MVP assumption in the original Phase 2 draft of [ROADMAP.md](ROADMAP.md)

**Context**: TrustBuy AI must never be tied to one shopping source. The product owner requires day-one support, architecturally, for a heterogeneous set of source types that don't share a data shape: classic marketplaces (**Amazon India, Flipkart, Myntra, Meesho**), storefront platforms (**Shopify stores**), owned properties (**official brand websites**), and social/ad-driven commerce (**Instagram shopping links, Facebook Marketplace, advertisement landing pages**). These differ not just in HTML structure but in *what a "seller" and "listing" even mean* — a Shopify store's operator is unambiguous; an Instagram shopping post's "seller" may be a tagged brand account with no stable product ID; an ad landing page may have no marketplace context at all.

**Decision**: The Product Extraction Service is built around a **Marketplace Adapter Architecture**:
- A `SourceAdapter` interface (in `trustbuy_agent_sdk` or a new `trustbuy_extraction_sdk`) defines the contract every adapter implements: `detect(url, page_content) -> confidence`, `extract(url, page_content) -> RawExtraction { product, seller, marketplace, reviews[], ads[] }`.
- A **Platform Detection Dispatcher** runs `detect()` across all registered adapters (URL pattern + DOM/content heuristics, not URL matching alone — an Instagram link and a Shopify-on-custom-domain link can look similar) and routes to the highest-confidence adapter.
- Adapters are **registered via a plugin registry**, not an `if/elif` chain in core application code — adding a new source means adding a new adapter package and registering it, never editing `product-extraction-service`'s core logic. This is a hard rule (see Consequences): a code review that finds marketplace-specific `if domain == "..."` branching outside an adapter package is a defect, not a style nit.
- Sources that don't cleanly fit the `marketplaces` → `sellers` → `products` relational shape (Instagram shopping, Facebook Marketplace, ad landing pages) still normalize into that shape at the adapter boundary: e.g. an Instagram shopping post's tagged brand account maps to a `sellers` row with `marketplace.platform_type = 'instagram_shopping'` and `sellers.external_seller_id` set to the account handle rather than a marketplace-issued ID. See schema changes in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) §2.2.

**Consequences**: More upfront design work in Phase 2 than a single-adapter MVP (see revised [ROADMAP.md](ROADMAP.md) Phase 2 sequencing: framework + 2 pilot adapters first, remaining adapters roll out incrementally as a backlog rather than all 9 blocking MVP). In exchange, every subsequent marketplace/source is additive, not a refactor, and the "never hardcode marketplace-specific logic" constraint is enforced structurally, not just by convention.

---

## ADR-003 — PostgreSQL as source of truth, ChromaDB as a derived index

**Status**: Accepted

**Context**: Both Postgres (with `pgvector`) and a dedicated vector DB (ChromaDB, as specified) can serve embeddings.

**Decision**: Use ChromaDB for all embedding/similarity search (products, reviews, evidence, reports) as specified, but treat it as a **derived, rebuildable index** — every Chroma record carries a back-reference to its Postgres row, and Postgres is authoritative. A nightly reconciliation job detects drift.

**Consequences**: Slightly more moving parts than `pgvector`-only, but matches the requested stack and keeps vector search infrastructure independently scalable from the relational store.

---

## ADR-004 — Agents never guess: `insufficient_data` is a first-class status

**Status**: Accepted

**Context**: New listings, new sellers, or blocked external sources create genuine data gaps. A naive agent implementation would default to a neutral/middling confidence, which visually looks identical to "we checked and it's borderline" — a dangerous conflation (see [docs/RISK_ANALYSIS.md](docs/RISK_ANALYSIS.md) §2 cold-start risk).

**Decision**: Every agent contract includes an explicit `INSUFFICIENT_DATA` status distinct from a low-confidence negative finding. The Fusion Engine and UI treat these differently — an investigation with mostly `INSUFFICIENT_DATA` agents is shown as "limited evidence available" rather than folded into a false-confidence verdict.

**Consequences**: More UI states to design ([docs/UI_UX_WIREFRAMES.md](docs/UI_UX_WIREFRAMES.md)), but materially reduces both false-negative harm (missed scams) and false-positive legal exposure (confidently wrong AVOID verdicts).

---

## ADR-005 — Community evidence is reputation-weighted, never single-source-decisive

**Status**: Accepted

**Context**: A single unverified report driving an AVOID PURCHASE verdict is the platform's single biggest defamation and manipulation risk (see [docs/RISK_ANALYSIS.md](docs/RISK_ANALYSIS.md) §1, §3).

**Decision**: Community report weight in the Fusion Engine is always a function of reputation, corroboration count, and recency (formula in [docs/USER_FLOWS.md](docs/USER_FLOWS.md) §5.3), with an enforced minimum-evidence floor before community signal alone can move a verdict to AVOID.

**Consequences**: Slower for a single early report to "matter," which is the intended trade-off — protects both consumers and sellers from a single bad-faith or mistaken report.

---

## ADR-006 — JWT access + rotating refresh, not server sessions

**Status**: Accepted

**Context**: Needed a stateless-friendly auth model that still supports revocation (log out all devices, admin-forced logout).

**Decision**: Short-lived (15 min) stateless JWT access tokens for authorization checks, paired with rotating, Redis-tracked refresh tokens (httpOnly cookie) for revocability. Full detail in [docs/SECURITY.md](docs/SECURITY.md) §1–2.

**Consequences**: Gateway can authorize requests without a DB round-trip on the hot path; revocation still works via the refresh-token layer.

---

## ADR-007 — LLM calls are retrieval-grounded, never free-generating

**Status**: Accepted

**Context**: Both the Copilot and the Fusion Engine's natural-language explanation step use an LLM. Free generation risks hallucinated "evidence" that doesn't exist — a serious credibility and legal problem for a platform whose entire value proposition is trustworthy evidence.

**Decision**: Every LLM call in the product is grounded in retrieved, stored evidence (ChromaDB + Postgres), with citation IDs required in the output schema and validated before the response is returned to a user.

**Consequences**: More engineering than a naive chatbot wrapper; directly supports ADR-001's explainability principle.

---

## ADR-009 — Phase 1 implementation-scope notes

**Status**: Accepted (implementation record, not a design debate)

**Context**: A handful of small, contained choices got made while actually building Phase 1 that are worth recording once here instead of only in scattered code comments, so a future reader doesn't have to reverse-engineer "why is it like this."

**Decisions:**
- **Tailwind CSS v3, not v4**, for the frontend. Both satisfy "Tailwind CSS" in the approved stack; v3's config surface is better-documented and lower-risk for a first build. Revisit at a natural major-version bump, not urgently.
- **Access tokens live in memory only** on the frontend (`lib/api/token-store.ts`), never in `localStorage`/`sessionStorage` (XSS exfiltration risk) - lost on full page reload by design, and silently re-derived via `POST /auth/refresh` (httpOnly cookie) on app boot (`hooks/use-auth.tsx`). This is the concrete frontend half of ADR-006.
- ~~**Rate limiter is fixed-window, not token-bucket**, in Phase 1~~ - **superseded, pre-launch hardening pass**: `services/gateway/app/rate_limit.py` now implements the token-bucket design docs/SECURITY.md §5 always specified as the target, via a single atomic Redis Lua script (`EVAL`) per request so concurrent requests from the same client can't race the read-modify-write. Kept the original fixed-window note above for the record rather than deleting it.
- **`verify-email` and `password/forgot`/`password/reset`** (listed in API_DOCUMENTATION.md §1) are **not implemented** in Phase 1 - they need the Notification Service (SES), which isn't built yet. Signup succeeds without email verification for now (`email_verified_at` stays null). Not a silent gap - tracked here and in `services/auth-service/app/routes.py`'s module docstring.
- **`device_label` truncated to 120 chars** server-side (`_device_label()` in `routes.py`) - real browser User-Agent strings routinely exceed the `VARCHAR(120)` column from DATABASE_SCHEMA.md §2.1; truncating client-supplied data to fit the approved schema was judged better than either rejecting real signups or changing the schema for cosmetic data.

**Consequences**: None of these block Phase 2. Each is called out explicitly so "temporary Phase 1 shortcut" never gets mistaken for "permanent architecture."

**Phase 2 addendum (2026-08-07)**: browser end-to-end testing of the investigation UI surfaced a real bug - `useInvestigation`'s polling (`hooks/use-investigation.ts`) silently stopped refetching while the tab wasn't the active/foreground one, leaving a completed investigation stuck showing a stale "processing" UI forever. Fixed with `refetchIntervalInBackground: true` - a user who tabs away while their investigation runs should see it finished when they come back, not a stale snapshot. Verified via a fresh end-to-end browser run after the fix.

---

## ADR-011 — Investigation pipeline runs in-process (asyncio background task), not a Celery/queue worker fleet, in Phase 2

**Status**: Accepted (implementation scoping decision, made autonomously per your Phase 2 instruction)

**Context**: ARCHITECTURE.md's target design has 9 independent agent workers consuming from a message bus (Redis Streams/Celery), publishing `agent.completed` events the Evidence Fusion Engine subscribes to. Standing up that infrastructure (broker, worker pool, retry/dead-letter handling, event contracts) is real, valuable work - but it's orthogonal to whether the *agent logic and data contracts* are correct, and building it first would mean Phase 2 ships zero working agents while the queue plumbing gets debugged.

**Decision**: `services/catalog-service/app/orchestrator.py` runs the full pipeline (extract → run all agents concurrently-enough via sequential `await` with per-agent timeouts → fuse → persist) as a single `asyncio` background task per investigation, kicked off from the `POST /investigations` request handler, in the same process. Every agent still implements the exact `AgentResult` contract from `trustbuy_agent_sdk` ([ARCHITECTURE.md](ARCHITECTURE.md) §5) and every run is still persisted to `agent_runs`/`evidence_items` exactly as designed - **only the transport changes** (in-process await vs. queue message), not the data model, not the agent contract, not the Fusion Engine's input shape.

**Consequences**: Investigations complete synchronously-ish within the request's background task (typically single-digit seconds for Phase 2's 4 lightweight agents) rather than being fanned out across a worker fleet. This will not scale to 9 heavier agents (OCR, image forensics, embeddings) under real concurrent load - that's exactly when this gets swapped for the queue-based design, and because the contract never changed, swapping the transport touches `orchestrator.py` only, not any agent or the Fusion Engine. Tracked as a required upgrade before Phase 6 production launch in [ROADMAP.md](ROADMAP.md).

---

## ADR-012 — File storage: local disk by default, S3 behind the same clean-provider pattern

**Status**: Accepted

**Context**: Community reports need to accept invoice/delivery-photo/screenshot uploads (docs/USER_FLOWS.md §5). Real AWS S3 access isn't available in this environment - the same "unavailable external API" situation as the LLM provider (ADR-010).

**Decision**: `trustbuy_common/storage.py` defines a `StorageProvider` protocol with `LocalDiskStorageProvider` (real, fully working, writes to a Docker volume, served back via a FastAPI `StaticFiles` mount) and `S3StorageProvider` (real `boto3` implementation, lazily imported). `get_storage_provider()` picks S3 automatically the moment `TRUSTBUY_S3_BUCKET` is set - zero code changes anywhere that calls it (`services/community-service/app/routes.py`'s attachment endpoint never branches on which provider is active).

**Consequences**: Report attachments work end-to-end today via local disk. Moving to S3 for a real multi-instance deployment (local disk doesn't survive/share across container replicas) is a config change, not a code change - and is required before Phase 6 production launch, tracked in ROADMAP.md.

**Bug found and fixed during end-to-end testing (2026-08-07)**: a reporter could vote on (and earn `vote_useful` points from) their own report - `cast_vote` didn't block self-voting the way `create_verification` already blocked self-verification. Fixed by adding the same check.

---

## Open decisions awaiting your input

1. ~~ADR-002 physical deployment grouping~~ — **Resolved 2026-08-07**: phased grouping confirmed.
2. ~~First marketplace adapter~~ — **Resolved 2026-08-07**: superseded by ADR-008, marketplace-agnostic pluggable adapter architecture with the 9 initial sources listed there.
3. ~~LLM provider~~ — **Resolved 2026-08-07 (ADR-010)**: see below. No further open items block Phase 2.

---

## ADR-010 — LLM provider: Claude (Anthropic), behind a mock-first provider interface

**Status**: Accepted (default chosen by implementation, per your instruction to make defensible calls autonomously rather than block on them)

**Context**: You explicitly deferred this in the Phase 1 conversation ("I'll decide later / have my own preference") and later instructed Phase 2+ work to proceed without waiting for approval on non-architectural decisions, with an explicit fallback rule: *"If a feature depends on an unavailable external API, implement a clean provider interface and a mock provider that can later be replaced without changing business logic."* That rule applies exactly here.

**Decision**: `libs/trustbuy_agent_sdk/trustbuy_agent_sdk/llm.py` defines an `LLMProvider` protocol with two implementations:
- `MockLLMProvider` - zero-dependency, always available, returns clearly-labeled (`[mock-llm]`-prefixed) template text. This is what actually runs in this environment right now, since no API key is configured here.
- `AnthropicLLMProvider` - real implementation using the `anthropic` SDK (installed only as an optional extra, imported lazily), activated automatically the moment `ANTHROPIC_API_KEY` is set in the environment - **no code change required to switch from mock to real.**

`get_llm_provider()` is the one factory function every caller (Evidence Fusion Engine explanation generation, AI Purchase Copilot) uses - nothing calls an LLM SDK directly.

**Why Claude/Anthropic as the real default** (not GPT/Gemini/other): no functional reason ties the architecture to one vendor - the whole point of the provider interface is that it doesn't matter. Anthropic was picked because it needs no further justification to be a reasonable default and the interface makes changing it a one-file edit, not a design discussion.

**Consequences**: Every LLM-touching feature in this implementation pass runs end-to-end today using the mock provider - explanations and Copilot replies are real, tested, honest about being template-based, and clearly labeled as such in both the API response and the feature checklist. Set `ANTHROPIC_API_KEY` in `.env` at any point to upgrade to real model output with zero code changes. This is deliberately not "faked" - it's a working deterministic fallback per your own instruction, not a placeholder.
