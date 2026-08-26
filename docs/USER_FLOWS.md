# TrustBuy AI — User Flows, Admin Flows & Community Reputation System

Related: [../ARCHITECTURE.md](../ARCHITECTURE.md) · [UI_UX_WIREFRAMES.md](UI_UX_WIREFRAMES.md) · [../DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md)

## 1. Primary user flow — "Should I buy this?"

```mermaid
flowchart TD
    A["Land on TrustBuy\n(paste URL / search / browser share)"] --> B{Logged in?}
    B -- No --> C["Continue as guest\n(investigation allowed, reporting/copilot locked)"]
    B -- Yes --> D["Full access"]
    C --> E
    D --> E["Submit product URL or search"]
    E --> F["Live investigation view\nagents streaming in: ✓ Seller ✓ Product … Reviews…"]
    F --> G["Recommendation revealed:\nBUY / BUY WITH CAUTION / AVOID"]
    G --> H["Evidence Timeline"]
    G --> I["Seller DNA Profile"]
    G --> J["Alternative Trusted Sellers"]
    G --> K{Want to ask more?}
    K -- Yes --> L["AI Purchase Copilot\n(login required)"]
    K -- No --> M["Save to Shopping Memory\n(optional outcome tracking)"]
    G --> N{Spot something wrong or confirm it was accurate?}
    N -- Yes --> O["File a Community Report\n(login required)"]
    O --> P["Attach evidence: invoice / delivery photo / refund chat"]
    P --> Q["Duplicate check → merge or submit"]
    Q --> R["Report enters moderation/verification queue"]
    R --> S["Earns Trust Points once verified"]
```

## 2. Onboarding flow

```mermaid
flowchart LR
    S1["Sign up (email + password)"] --> S2["Verify email"]
    S2 --> S3["Set display name + avatar"]
    S3 --> S4["Starter tour: 1 sample investigation walkthrough"]
    S4 --> S5["Land on dashboard: recent investigations + Shopping Memory"]
```

## 3. Community contribution flow (report lifecycle)

```mermaid
sequenceDiagram
    actor U as Contributor
    participant W as Web App
    participant COMM as Community Service
    participant MOD as Moderator
    participant FUSION as Evidence Fusion Engine

    U->>W: File report + attachments
    W->>COMM: POST /reports
    COMM->>COMM: content-hash + embedding duplicate check
    alt Likely duplicate
        COMM-->>W: suggest existing report
        U->>COMM: Upvote existing instead
    else Unique
        COMM->>COMM: status = pending
        COMM-->>W: Report submitted
        COMM->>MOD: enqueue if spam-risk signals present
        loop Community verification
            actor V as Other Investigators
            V->>COMM: confirm / dispute
        end
        COMM->>COMM: status -> verified (quorum + reputation-weighted majority)
        COMM->>U: +Trust Points, notification
        COMM->>FUSION: evidence available for future investigations of this product/seller
    end
```

## 4. Admin / moderation flow

```mermaid
flowchart TD
    A["Admin dashboard"] --> B["Moderation Queue\n(reports flagged as spam-risk or disputed)"]
    A --> C["Fraud Network Review Queue\n(new high-confidence clusters)"]
    A --> D["Agent Health\n(failures, latency, insufficient_data rate)"]
    A --> E["Agent Weight Console\n(publish new versioned weight table)"]
    A --> F["Seller/Marketplace Disputes\n(appeals against AVOID verdicts)"]
    B --> B1{Decision}
    B1 -- Verify --> B2["Report verified, Trust Points awarded"]
    B1 -- Reject --> B3["Report rejected, reporter reputation penalized if abusive"]
    B1 -- Duplicate --> B4["Merge into existing report"]
    C --> C1{Confirm cluster?}
    C1 -- Yes --> C2["Cluster promoted to active fraud-network evidence"]
    C1 -- No --> C3["Cluster dismissed, signals down-weighted"]
    F --> F1["Review evidence + dispute"]
    F1 --> F2{Uphold or revise?}
    F2 -- Revise --> F3["Trigger re-investigation with corrected data"]
    F2 -- Uphold --> F4["Dispute closed, response sent to appellant"]
```

## 5. Community reputation system

### 5.1 Levels

| Level | Trust Points required | Unlocks |
|---|---|---|
| **Shopper** | 0 (default on signup) | Run investigations, use Copilot, save Shopping Memory |
| **Investigator** | 100 | File reports, vote on reports |
| **Fraud Hunter** | 500 | Verify/dispute others' reports, higher report weight |
| **Trust Guardian** | 2,000 | Flag fraud-network clusters for review, appeal-review visibility |
| **Trust Ambassador** | 8,000 + moderator-invited | Mentor queue, early access to new agents, direct escalation channel to moderators |

Point thresholds and weights live in a config table (`reputation_levels`), not hardcoded, so they can be tuned without a deploy.

### 5.2 Trust Point actions

| Action | Points |
|---|---|
| Report filed and later verified | +25 |
| Report verified by Fraud Hunter+ (bonus) | +10 |
| Useful vote (aligned with eventual consensus) | +2 |
| Report filed and rejected as false/spam | −30 |
| Duplicate/spam report submitted | −10 |
| Verification that matches eventual consensus | +5 |
| Verification that is later overturned | −5 |
| Genuine-purchase confirmation verified | +15 |

### 5.3 Reputation-weighted evidence

A report's contribution to the Evidence Fusion Engine is weighted by:

```
report_weight = base_weight(report_type)
              × reputation_multiplier(reporter.level)
              × corroboration_factor(verification_count, verifier_avg_reputation)
              × recency_decay(report_age)
```

This ensures a single low-reputation, unverified report never single-handedly drives an AVOID PURCHASE verdict (see [RISK_ANALYSIS.md](RISK_ANALYSIS.md) — defamation risk mitigation), while a corroborated pattern from trusted contributors carries real weight.

### 5.4 Spam & abuse prevention

- **Duplicate detection**: simhash of description + perceptual hash of attachments + embedding similarity against recent reports for the same product/seller.
- **Rate limiting**: per-user report submission caps (Redis token bucket), stricter for new accounts.
- **Sybil resistance**: reputation gains taper for accounts with correlated signup patterns (same IP/device fingerprint cluster) pending manual review.
- **Vote manipulation**: votes from accounts younger than a threshold, or from accounts detected in a fraud-network cluster with the reported seller, are down-weighted or excluded.
- **Penalty ledger**: every point change is logged in `trust_points_ledger` with a `reason`, fully auditable.

## 6. Alternate flows

- **Guest → conversion**: a guest who runs an investigation is prompted to sign up specifically to unlock the Copilot and reporting, at the point of highest intent (right after seeing the recommendation) — not at first page load.
- **Failed/partial investigation**: if agents time out, the UI clearly shows a `partial` badge and which agents didn't complete, with an option to retry.
- **Seller dispute**: a seller/marketplace representative can submit a dispute (public form, no login required to file, review requires evidence) routed straight into the Admin Moderation flow (§4).
