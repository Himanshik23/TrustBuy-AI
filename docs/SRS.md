# TrustBuy AI — Software Requirements Specification (SRS)

Related: [../ARCHITECTURE.md](../ARCHITECTURE.md) · [../ROADMAP.md](../ROADMAP.md)

## 1. Purpose

Define the functional and non-functional requirements for TrustBuy AI, an AI purchase-intelligence platform that produces an explainable BUY / BUY WITH CAUTION / AVOID PURCHASE recommendation for a specific product-seller pair, backed by multi-agent evidence and community intelligence.

## 2. Scope

In scope: product/seller/marketplace/business/review/ad analysis, community reporting & reputation, AI Purchase Copilot, fraud network detection, report generation, notifications, admin moderation.

Out of scope (v1): native mobile apps, browser extension (documented as future scope), payment processing, direct marketplace integrations requiring partner agreements, non-English content analysis (English-first, i18n architected but not fully localized).

## 3. Stakeholders

- **Shoppers** — primary users seeking a purchase decision.
- **Community contributors** — Investigators/Fraud Hunters/Trust Guardians/Trust Ambassadors filing and verifying reports.
- **Moderators/Admins** — resolve disputes, tune agent weights, manage abuse.
- **Sellers/Marketplaces** (indirect) — subject of analysis; dispute/appeal path required for fairness and legal defensibility (see [RISK_ANALYSIS.md](RISK_ANALYSIS.md)).

## 4. Functional requirements

### FR-1 Investigation
- FR-1.1 A user (authenticated or anonymous) can submit a product URL or search query.
- FR-1.2 The system extracts product, seller, marketplace, and business entities from the source.
- FR-1.3 The system runs all applicable intelligence agents asynchronously and reports partial progress.
- FR-1.4 The system produces one of exactly three verdicts: BUY, BUY WITH CAUTION, AVOID PURCHASE, each with a confidence score and natural-language explanation.
- FR-1.5 The system never returns a verdict without at least one supporting evidence item; if no agent could gather evidence, status is `insufficient_data`, not a fabricated verdict.
- FR-1.6 A user can view the full evidence timeline behind any recommendation.
- FR-1.7 Repeated investigations of the same product within a configurable TTL return the cached result unless `force_refresh` is set.

### FR-2 AI Purchase Copilot
- FR-2.1 A logged-in user can open a chat scoped to a specific investigation.
- FR-2.2 The Copilot answers only shopping/evidence-related questions about that investigation; out-of-scope questions are declined with a redirect.
- FR-2.3 Every Copilot answer that references evidence must cite the specific evidence item(s).

### FR-3 Community reporting
- FR-3.1 A logged-in user can file a report (fake seller, counterfeit product, scam, refund dispute, genuine-purchase confirmation) with optional attachments (invoice, delivery image, refund conversation).
- FR-3.2 The system detects likely-duplicate reports (content hash + embedding similarity) before final submission and offers to merge/upvote instead.
- FR-3.3 Users above a minimum reputation level can verify (confirm/dispute) others' reports.
- FR-3.4 Users can upvote/downvote reports.
- FR-3.5 Verified reports contribute weighted evidence to future investigations of the same product/seller.

### FR-4 Reputation & gamification
- FR-4.1 Users earn/lose Trust Points for actions (filing a report that gets verified, false reports, useful votes, spam penalties).
- FR-4.2 Reputation levels: Shopper → Investigator → Fraud Hunter → Trust Guardian → Trust Ambassador, each unlocking new abilities (see [USER_FLOWS.md](USER_FLOWS.md)).
- FR-4.3 Users earn badges for specific milestones/behaviors.
- FR-4.4 Report and verification weight in the Fusion Engine scales with the submitter's reputation.

### FR-5 Fraud network
- FR-5.1 The system links sellers/accounts/products sharing fraud signals (payment handles, addresses, images, co-reported patterns) into a graph.
- FR-5.2 A user can view an interactive fraud network visualization for a flagged seller.
- FR-5.3 New high-confidence clusters are queued for moderator review before being surfaced as a strong negative signal.

### FR-6 Reports & sharing
- FR-6.1 A user can export an investigation as a shareable PDF/HTML evidence report.

### FR-7 Admin
- FR-7.1 Admins/moderators can view and resolve the report moderation queue.
- FR-7.2 Admins can adjust and publish versioned agent-weight tables.
- FR-7.3 Admins can suspend abusive accounts and see platform health metrics.
- FR-7.4 Sellers/marketplaces can submit a dispute/appeal against a recommendation (routed to the moderation queue) — required for fairness and legal defensibility.

## 5. Non-functional requirements

| Category | Requirement |
|---|---|
| **Performance** | p50 investigation completion ≤ 15s, p95 ≤ 45s for a previously-unseen product. Cached lookups ≤ 300ms. |
| **Scalability** | Agent workers scale horizontally on queue depth; target 10,000 concurrent investigations at launch scale, architecture supports 1M+ MAU without redesign (see [../ARCHITECTURE.md](../ARCHITECTURE.md) §8). |
| **Availability** | 99.5% uptime target for the gateway/web app; individual agent failures degrade gracefully to `partial` recommendations, never a hard failure. |
| **Explainability** | Every verdict must be traceable to evidence; no black-box score without justification (product principle, not just a requirement). |
| **Accessibility** | WCAG 2.1 AA across the web app. |
| **Internationalization** | UI string externalization from day one; content analysis is English-first with an documented path to add languages. |
| **Security** | See [SECURITY.md](SECURITY.md) in full. |
| **Data quality** | Agents must report `insufficient_data` rather than guess; community reports require reputation-weighted corroboration before strongly influencing a verdict. |
| **Auditability** | Every recommendation stores the exact agent-weight snapshot and model version used, for reproducibility and dispute resolution. |
| **Legal defensibility** | AVOID PURCHASE verdicts require a minimum evidence threshold and are never based on a single unverified report (see [RISK_ANALYSIS.md](RISK_ANALYSIS.md) — defamation risk). |

## 6. Constraints

- Must run within a single AWS VPC per environment; no direct database access across service boundaries.
- LLM calls (Copilot, Fusion explanation generation) must be retrieval-grounded against stored evidence, not free-generated, to bound hallucination risk.
- Anonymous users can request investigations but cannot file reports, use the Copilot, or earn reputation.

## 7. Assumptions

- Target marketplaces expose product/review/seller data through public listing pages that can be legally and technically extracted (rate-limited, respecting robots.txt/ToS on a per-marketplace allowlist basis — a compliance review precedes adding any new marketplace source).
- v1 focuses on e-commerce marketplaces (not classifieds/P2P marketplaces like Craigslist-style listings) — future scope in [../ROADMAP.md](../ROADMAP.md).
