# TrustBuy AI — API Documentation

Related: [ARCHITECTURE.md](ARCHITECTURE.md) · [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) · [docs/SECURITY.md](docs/SECURITY.md)

Base URL: `https://api.trustbuy.ai/api/v1` in production; `http://localhost:8090/api/v1` for local dev (gateway; internal services are not publicly reachable). See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for exact local ports.

**As-built note (2026-08-07)**: every endpoint below marked in the running system is real and curl/browser-verified this session (see [PROJECT_REPORT.md](PROJECT_REPORT.md) §7). Two deltas from the original design: `POST /investigations/{id}/report` returns the PDF directly in the response body (no separate `GET /reports-export/{export_id}` indirection was built - simpler, and the artifact is still durably stored via the pluggable `StorageProvider` for a stable URL). Admin routes (§7) are split across three services by resource ownership rather than one Report Generation/Admin service, per ADR-002. Endpoints for pagination cursors, `verify-email`, `password/forgot`/`password/reset`, and Fraud Network are documented below as originally designed but **not implemented** - see [PROJECT_REPORT.md](PROJECT_REPORT.md) §5/§8 for the complete honest list.

## Conventions

- **Auth**: `Authorization: Bearer <access_token>` on every authenticated route. Anonymous investigations are allowed on a subset of routes (rate-limited harder).
- **Pagination**: cursor-based — `?limit=20&cursor=<opaque>`; responses include `next_cursor`.
- **Errors**: uniform envelope —
  ```json
  { "error": { "code": "INVESTIGATION_NOT_FOUND", "message": "...", "request_id": "..." } }
  ```
- **Versioning**: URL-prefixed (`/api/v1`); breaking changes ship as `/api/v2` with a documented deprecation window.
- **Idempotency**: mutating POSTs accept an `Idempotency-Key` header (dedupe window: 24h) — important for report submission and investigation creation from flaky mobile networks.
- **Realtime**: investigation progress is delivered over `WSS /api/v1/investigations/{id}/stream` (falls back to polling `GET` if WebSocket unavailable).

---

## 1. Authentication Service

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/auth/signup` | Create account (email, password, display_name) | Public |
| POST | `/auth/login` | Returns access + refresh token | Public |
| POST | `/auth/refresh` | Rotate refresh token → new access token | Refresh cookie |
| POST | `/auth/logout` | Revoke current refresh token | User |
| POST | `/auth/verify-email` | Confirm email via token | Public |
| POST | `/auth/password/forgot` | Send reset email | Public |
| POST | `/auth/password/reset` | Reset via token | Public |
| GET | `/auth/me` | Current user profile + reputation | User |
| GET | `/auth/sessions` | List active devices/sessions | User |
| DELETE | `/auth/sessions/{id}` | Revoke a specific session | User |

`POST /auth/login` response:
```json
{
  "access_token": "eyJ...",
  "expires_in": 900,
  "user": { "id": "...", "display_name": "...", "reputation_level": "shopper", "trust_points": 0 }
}
```
(refresh token set as httpOnly `Secure` cookie, not returned in body)

---

## 2. Product Extraction & Investigations

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/investigations` | Submit a product URL or search query; source platform is auto-detected and routed to the matching adapter (Amazon India, Flipkart, Myntra, Meesho, Shopify, brand-direct, Instagram shopping, Facebook Marketplace, ad landing page — see [ARCHITECTURE.md](ARCHITECTURE.md) §4.1) | Public (rate-limited) / User |
| GET | `/investigations/{id}` | Get investigation status + recommendation if ready | Public / User |
| GET | `/investigations/{id}/evidence` | Full evidence timeline | Public / User |
| GET | `/investigations/{id}/agents` | Per-agent run detail (evidence, confidence, reasoning) | Public / User |
| GET | `/investigations/{id}/alternatives` | Alternative trusted sellers | Public / User |
| GET | `/investigations/{id}/regret-prediction` | Purchase regret probability | Public / User |
| WSS | `/investigations/{id}/stream` | Live progress events | Public / User |
| GET | `/users/me/investigations` | History of past investigations | User |

`POST /investigations` request:
```json
{ "url": "https://marketplace.example/item/123", "force_refresh": false }
```
`202 Accepted` response:
```json
{
  "investigation_id": "6f2c...",
  "status": "processing",
  "detected_platform": "flipkart",
  "detection_confidence": 0.97,
  "estimated_seconds": 25
}
```

`GET /investigations/{id}` (completed) response:
```json
{
  "investigation_id": "6f2c...",
  "status": "completed",
  "product": { "id": "...", "title": "...", "price": 24.99, "currency": "USD" },
  "seller": { "id": "...", "display_name": "...", "marketplace": "example.com" },
  "recommendation": {
    "verdict": "buy_with_caution",
    "confidence": 0.62,
    "explanation": "3 of 9 agents flagged concerns: review authenticity (0.41) and price manipulation (0.55)...",
    "model_version": "fusion-2026.02"
  },
  "agent_summary": [
    { "agent": "review_intelligence", "verdict_signal": "supports_caution", "confidence": 0.41 },
    { "agent": "seller_intelligence", "verdict_signal": "supports_buy", "confidence": 0.78 }
  ]
}
```

---

## 3. Recommendation Engine / AI Purchase Copilot

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/copilot/conversations` | Start a Copilot conversation scoped to an investigation | User |
| POST | `/copilot/conversations/{id}/messages` | Ask a question | User |
| GET | `/copilot/conversations/{id}` | Full conversation history | User |
| GET | `/investigations/{id}/seller-dna` | Seller DNA Profile | Public / User |
| GET | `/investigations/{id}/fraud-network` | Fraud network graph (nodes/edges) for this seller | User |

`POST /copilot/conversations/{id}/messages` request:
```json
{ "message": "Which reviews look fake?" }
```
response:
```json
{
  "reply": "4 reviews show templated phrasing posted within a 2-hour burst on Mar 3. Two reviewer accounts were created the same day.",
  "cited_evidence_ids": ["ev_a1", "ev_b2"],
  "intent_matched": "explain_review_authenticity"
}
```
Out-of-scope example:
```json
{ "reply": "I can only help with purchase decisions on TrustBuy investigations — try asking about this seller, product, or reviews.", "intent_matched": "out_of_scope" }
```

---

## 4. Community Intelligence Service

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/reports` | File a report (fake seller, counterfeit, scam, refund dispute, genuine confirmation) | User |
| POST | `/reports/{id}/attachments` | Upload invoice/delivery image/refund chat (multipart) | User |
| GET | `/reports/{id}` | Report detail | Public / User |
| GET | `/reports?product_id=&seller_id=&status=` | List/filter reports | Public / User |
| POST | `/reports/{id}/vote` | Upvote/downvote a report | User |
| POST | `/reports/{id}/verify` | Confirm or dispute a report (requires min. reputation level) | User (Investigator+) |
| GET | `/users/me/badges` | Earned badges | User |
| GET | `/users/{id}/reputation` | Public reputation summary | Public |
| GET | `/leaderboard` | Top contributors | Public |

`POST /reports` request:
```json
{
  "report_type": "counterfeit_product",
  "product_id": "...",
  "description": "Received item with misspelled brand logo, packaging differs from official photos.",
  "attachment_ids": []
}
```
`202` response includes `duplicate_of_id` if a near-duplicate was detected (simhash + embedding similarity) so the client can prompt "did you mean to upvote this existing report instead?"

---

## 5. Report Generation Service

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/investigations/{id}/report` | Generate a shareable PDF/HTML evidence report | User |
| GET | `/reports-export/{export_id}` | Download generated report | User (owner) |

---

## 6. Notification Service

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/notifications` | List notifications | User |
| POST | `/notifications/{id}/read` | Mark read | User |
| PUT | `/notifications/preferences` | Set channel preferences (in-app/email/push) | User |

---

## 7. Admin API (separate router, `is_admin`/`is_moderator` only)

| Method | Path | Description |
|---|---|---|
| GET | `/admin/reports/queue` | Moderation queue, oldest-first, spam-filtered |
| POST | `/admin/reports/{id}/resolve` | Resolve with outcome + notes |
| GET | `/admin/investigations/failures` | Investigations with agent failures (ops triage) |
| GET | `/admin/fraud-network/review-queue` | Newly-formed high-confidence fraud clusters for human review |
| PUT | `/admin/agents/{agent_name}/weights` | Adjust/publish a new versioned agent weight table |
| GET | `/admin/metrics/overview` | Platform health dashboard data |
| POST | `/admin/users/{id}/suspend` | Suspend abusive account |

---

## 8. Internal-only APIs (VPC-internal, not on the gateway)

Each agent exposes a minimal internal contract consumed by the orchestrator, standardized via `trustbuy_agent_sdk`:

```
POST /internal/run
{ "investigation_id": "...", "context": { ...extracted entities... } }

→ 200
{
  "agent": "review_intelligence",
  "status": "completed",
  "verdict_signal": "supports_caution",
  "confidence": 0.41,
  "evidence": [ { "polarity": "contradicts", "weight": 0.6, "summary": "...", "detail": {...} } ],
  "reasoning": "...",
  "duration_ms": 1840
}
```

This uniform contract is what lets the Evidence Fusion Engine treat all 9 agents identically regardless of their internal ML approach.
