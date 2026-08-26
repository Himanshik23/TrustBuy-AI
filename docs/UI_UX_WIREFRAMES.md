# TrustBuy AI — UI/UX Wireframes & Design System

Related: [USER_FLOWS.md](USER_FLOWS.md) · [../ARCHITECTURE.md](../ARCHITECTURE.md)

Visual language: **Linear**'s density and motion, **Stripe**'s typographic confidence and data presentation, **Vercel**'s dark-mode-first minimalism, **Perplexity**'s evidence-citation pattern, **Notion**'s calm content layout, **Arc**'s playful-but-premium accent use. Never cluttered, never a generic "trust score gauge" as the hero element — evidence is the hero.

## 1. Design tokens

- **Type**: Inter (UI), Geist Mono or JetBrains Mono (evidence IDs, technical data). Scale: 12/14/16/20/24/32/48.
- **Color** (semantic, theme-aware via `next-themes`):
  - `--verdict-buy`: green 500/400 (light/dark)
  - `--verdict-caution`: amber 500/400
  - `--verdict-avoid`: red 500/400
  - `--surface`, `--surface-elevated`, `--border-subtle`, `--text-primary`, `--text-secondary` — standard neutral scale, near-black/near-white rather than pure, per Linear/Vercel convention.
  - One accent (indigo/violet) reserved for interactive elements only — never used for verdicts, so verdict color always reads unambiguously.
- **Spacing**: 4px base unit, 8/12/16/24/32/48/64 scale.
- **Radius**: 8px cards, 6px inputs/buttons, 999px pills (badges, verdict chips).
- **Motion**: Framer Motion, 150–250ms ease-out for state changes; investigation progress uses staggered fade/slide-in per agent, not a generic spinner.
- **Elevation**: flat + border-based, one subtle shadow level for popovers/modals only — no heavy drop shadows.

## 2. Landing / Home

```
┌─────────────────────────────────────────────────────────────┐
│  TrustBuy AI                         Sign in   [Get Started] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│              Know Before You Buy.                            │
│   Paste a product link. Get an explainable verdict —         │
│   not just a score.                                          │
│                                                               │
│   ┌───────────────────────────────────────────┐  [Analyze]  │
│   │ Paste a product URL or describe a seller…  │              │
│   └───────────────────────────────────────────┘              │
│                                                               │
│   Trusted signals from 9 AI agents + a community of          │
│   verified shoppers.                                          │
│                                                               │
│   [Recent community catches — live ticker of verified reports]│
└─────────────────────────────────────────────────────────────┘
```

## 3. Investigation — live progress

```
┌─────────────────────────────────────────────────────────────┐
│ ← New investigation                    example.com/item/123 │
├─────────────────────────────────────────────────────────────┤
│  [Product image]   Wireless Earbuds Pro X2        $24.99     │
│                     Sold by: TechDeals_Official               │
│                                                               │
│  Investigating…                                               │
│  ✓ Platform Verification         supports_buy       0.81     │
│  ✓ Seller Intelligence           supports_buy       0.74     │
│  ⏳ Review Intelligence           running…                     │
│  ⏳ Product Intelligence          running…                     │
│  ○ Advertisement Intelligence     queued                      │
│  ○ Historical Learning            queued                      │
│  ○ Fraud Network                  queued                      │
│                                                               │
│  Each row animates in with its confidence bar (Framer Motion) │
└─────────────────────────────────────────────────────────────┘
```

## 4. Recommendation result (core screen)

```
┌─────────────────────────────────────────────────────────────┐
│  🟡 BUY WITH CAUTION                       Confidence: 62%   │
│  "3 of 9 agents flagged concerns — review authenticity and   │
│   a recent price manipulation pattern. Seller and platform   │
│   check out fine."                                            │
│                                                               │
│  [Ask the Copilot ›]           [Export report]  [Save]       │
├─────────────────────────────────────────────────────────────┤
│  Tabs:  Evidence Timeline | Seller DNA | Fraud Network |      │
│         Alternatives | Reviews | Ads                          │
├─────────────────────────────────────────────────────────────┤
│  Evidence Timeline (default tab)                              │
│  ● Mar 3   Review burst detected — 4 reviews in 2 hours  ▼    │
│  ● Feb 28  Price inflated 40% then "discounted" back     ▼    │
│  ● Jan 12  Seller account created, 0 prior complaints    ▼    │
│  ● Jan 12  SSL valid, marketplace registered since 2019  ▼    │
│  (each ▼ expands to source + confidence + raw evidence)       │
└─────────────────────────────────────────────────────────────┘
```

Verdict chip color is the **only** place strong color appears on this screen — evidence rows stay neutral so the eye isn't fighting the verdict for attention.

## 5. Seller DNA Profile

```
┌─────────────────────────────────────────────────────────────┐
│  TechDeals_Official · example.com                            │
│  Account age: 2.1 yrs   Fulfillment: Dropship   Complaints: 3│
├─────────────────────────────────────────────────────────────┤
│  [Radar chart: Reliability / Longevity / Response / Fulfillment /│
│   Review Health / Price Stability]  (Recharts)                │
│                                                                │
│  Linked storefronts (2)            Ownership timeline          │
│  • QuickTech_Store (0.71 conf.)    2023 → registered            │
│  • DealHub99 (0.58 conf.)          2024 → 2 linked storefronts  │
│                                     2026 → current                │
└─────────────────────────────────────────────────────────────┘
```

## 6. Fraud Network Visualization

Interactive force-directed graph (custom Canvas/D3 layer, not Recharts — Recharts handles the standard charts; the graph is its own component). Node color = risk score, node size = connection count, edge thickness = link strength. Hover reveals link type ("shares payment handle", "shares delivery address"). Clicking a node opens its own Seller DNA panel inline, no navigation away.

```
┌─────────────────────────────────────────────────────────────┐
│  Fraud Network — TechDeals_Official                          │
│                                                                │
│         ●───────●  QuickTech_Store                            │
│        ╱ TechDeals  ╲                                          │
│       ●  (this seller) ●──● DealHub99                          │
│        ╲               ╱                                        │
│         ●──────────────●  shared payment handle (0.71)         │
│                                                                │
│  Legend: ● low risk  ● medium  ● high     [Report this cluster]│
└─────────────────────────────────────────────────────────────┘
```

## 7. AI Purchase Copilot (side panel)

```
┌───────────────────────────────┐
│  Copilot · scoped to this      │
│  investigation                 │
├───────────────────────────────┤
│  You: Which reviews look fake? │
│                                 │
│  Copilot: 4 reviews show        │
│  templated phrasing posted in  │
│  a 2-hour burst on Mar 3.       │
│  [View cited evidence →]        │
│                                 │
│  Suggested: "Compare with       │
│  alternative sellers" ›          │
├───────────────────────────────┤
│  Ask about this purchase…  [→] │
└───────────────────────────────┘
```

Slides in from the right on desktop, full-sheet on mobile. Suggested-question chips are always scoped (never a blank "ask anything" box) to reinforce the narrow-purpose framing.

## 8. Community report form

```
┌─────────────────────────────────────────────────────────────┐
│  Report an issue with this listing                            │
│  Type:  ○ Counterfeit  ○ Fake seller  ○ Scam                  │
│         ○ Refund dispute  ○ Confirm genuine purchase            │
│                                                                │
│  Description                                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                                                         │  │
│  └───────────────────────────────────────────────────────┘  │
│  Attach evidence (optional): [+ Invoice] [+ Photo] [+ Chat]   │
│                                                                │
│  ⚠ Similar report exists — upvote instead?  [View] [Continue anyway]│
│                                                                │
│                                       [Cancel]  [Submit report]│
└─────────────────────────────────────────────────────────────┘
```

## 9. Profile / reputation

```
┌─────────────────────────────────────────────────────────────┐
│  @himanshi        Fraud Hunter          1,240 Trust Points    │
│  ████████████░░░░░░  620 to Trust Guardian                    │
│                                                                │
│  Badges: 🛡 First Catch   🔍 10 Verified   🧭 Early Adopter    │
│                                                                │
│  Recent activity: filed 3 reports (2 verified) · 12 votes cast │
└─────────────────────────────────────────────────────────────┘
```

## 10. Admin dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  Overview | Moderation Queue | Fraud Clusters | Agent Health | │
│  Weights | Disputes                                            │
├─────────────────────────────────────────────────────────────┤
│  Investigations today: 4,213     Avg confidence: 0.71          │
│  [Line chart: investigations/day]  [Bar: verdict distribution] │
│  Agent failure rate: 1.2%  ⚠ Business Verification: 4.8% (spike)│
└─────────────────────────────────────────────────────────────┘
```

## 11. Responsive & accessibility notes

- Mobile: bottom-sheet pattern for Copilot, tabs collapse to a horizontal scroll chip row, fraud-network graph gets a simplified list fallback (graph is enhancement, not requirement, on small screens).
- All verdict states carry a text label + icon, never color alone (colorblind-safe).
- Full keyboard navigation on evidence timeline (roving tabindex), focus-visible rings on every interactive element, `aria-live="polite"` region for streaming agent progress.
- Dark mode is the default for the marketing/landing surfaces (Vercel-style); app surfaces respect system preference via `next-themes` with an explicit toggle.
