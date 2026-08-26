# TrustBuy AI — Risk Analysis

Related: [docs/SECURITY.md](SECURITY.md) · [../DECISIONS.md](../DECISIONS.md) · [../ROADMAP.md](../ROADMAP.md)

Risk = Likelihood × Impact, rated Low/Medium/High. This register is reviewed every phase (see [PROJECT_PROGRESS.md](../PROJECT_PROGRESS.md)) and new risks are logged as ADR-adjacent entries, not silently absorbed.

## 1. Legal & reputational risk

| Risk | L | I | Mitigation |
|---|---|---|---|
| **Defamation exposure from AVOID PURCHASE verdicts** — naming a real seller as fraudulent/counterfeit is a legal statement, not just a UX label. | Med | **High** | Minimum evidence threshold before AVOID is reachable; never based on a single unverified report; every verdict traceable to cited evidence; mandatory, visible dispute/appeal path for sellers (FR-7.4); explanation language is evidence-descriptive ("3 reports of counterfeit packaging, unverified") rather than accusatory ("this seller is a scammer"); legal review of verdict copy before launch. |
| **Marketplace ToS / scraping legality** for Product Extraction Service. | Med | High | Per-marketplace allowlist with compliance review before onboarding a source; respect robots.txt and rate limits; prefer official APIs/affiliate feeds where available over scraping; legal counsel review before adding any new marketplace. |
| **Liability for a bad recommendation leading to a loss** (user buys despite AVOID, or avoids despite BUY, and loses money). | Low | Med | Clear ToS disclaimer: TrustBuy provides evidence-based guidance, not a guarantee; confidence is always shown, never hidden; "insufficient_data" states are surfaced honestly rather than forced into a confident verdict. |
| **Regulatory (consumer protection / FTC-style "unfair practices" scrutiny)** if verdicts are perceived as unaccountable automated decisions. | Low | Med | Explainability is architectural (not bolted on); human moderation queue for disputes; documented, versioned agent-weight governance. |

## 2. AI / model risk

| Risk | L | I | Mitigation |
|---|---|---|---|
| **Hallucinated evidence** in Copilot or Fusion explanations. | Med | High | Retrieval-grounded generation only (ChromaDB), schema-validated outputs, citation requirement enforced in code, not just prompt (see [docs/SECURITY.md](SECURITY.md) §7). |
| **Prompt injection via scraped content** (malicious listing/review text instructing the AI). | Med | High | Untrusted-content isolation, intent classifier gate, adversarial test suite ([docs/TESTING_STRATEGY.md](TESTING_STRATEGY.md) §4). |
| **Model/weight drift silently changing outcomes** over time. | Med | Med | Versioned, published weight tables; every recommendation stores the snapshot used; regression gate on golden fixture sets before any weight change ships. |
| **Cold-start / new-product blind spot** — a brand-new listing with no history looks identical to an evidence gap, not necessarily risk. | High | Med | Agents explicitly distinguish `insufficient_data` from `negative_evidence`; UI never conflates "we don't know yet" with "this is risky." |
| **Adversarial sellers gaming the system** (review-bombing competitors, coordinated fake "genuine purchase" confirmations). | High | Med | Reputation-weighted evidence, Sybil-resistance signals, fraud-network cross-checks on the reporting accounts themselves, moderator review queue for anomalous spikes. |

## 3. Data quality & community risk

| Risk | L | I | Mitigation |
|---|---|---|---|
| **Low initial community density** → weak community-intelligence signal at launch (cold-start for the reputation system itself). | High | Med | Product must be independently useful from agent evidence alone, pre-community-scale (see [ROADMAP.md](../ROADMAP.md) MVP scope); seed moderation team seeds initial verified reports. |
| **Duplicate/spam reports drowning genuine signal.** | Med | Med | Duplicate detection pipeline, rate limits, reputation-weighted moderation queue prioritization ([docs/USER_FLOWS.md](USER_FLOWS.md) §5.4). |
| **Reputation gaming** (farm points via low-effort verified reports, then abuse elevated weight). | Med | Med | Corroboration-factor weighting, penalty ledger, anomaly detection on point-accrual velocity. |

## 4. Technical risk

| Risk | L | I | Mitigation |
|---|---|---|---|
| **External data source instability** (marketplaces change DOM/structure, block scraping). | High | Med | Extraction adapters isolated per marketplace, contract tests against fixture snapshots catch breakage fast, graceful `insufficient_data` fallback rather than pipeline crash. |
| **Agent pipeline latency spikes under load.** | Med | Med | Queue-depth autoscaling, per-agent timeout + circuit breaker, cached results for repeat investigations. |
| **Vector store / relational store drift** (Chroma record orphaned from Postgres row). | Low | Low | Chroma is never source of truth; nightly reconciliation job; `chroma_id` foreign-key-style integrity check. |
| **Single LLM provider dependency.** | Med | Med | Provider-abstraction layer in `trustbuy_agent_sdk`; fallback provider configured for the Copilot and explanation generation. |

## 5. Business risk

| Risk | L | I | Mitigation |
|---|---|---|---|
| **Chicken-and-egg**: no users without good data, no data without users. | High | High | Launch with strong agent-only evidence (no community dependency) in high-fraud categories (electronics, fashion knockoffs) where public signal (reviews, price history, WHOIS) is already rich enough to be useful solo. |
| **High cost of AI inference per investigation** at scale. | Med | Med | Aggressive caching of repeat-product investigations, tiered agent execution (cheap heuristic agents run first and can short-circuit expensive ones when confidence is already high), cost dashboards from day one. |
| **Competitive response** from incumbent review/trust sites. | Low | Low | Differentiation is architectural (explainability, multi-entity fusion, community economy) — not easily copy-pasted; documented as the core moat in [README.md](../README.md). |

## 6. Risk review cadence

This register is revisited at the end of every roadmap phase; new or escalated risks are logged with the phase they were identified in, in [PROJECT_PROGRESS.md](../PROJECT_PROGRESS.md).
