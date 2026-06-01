# Startup resource registry

The enumerated resource surface the advisory brain + scouts draw on, by category.
Each entry: what it is, why it's load-bearing, access (free / paid / operator-key).
**Freshness-stamped: 2026-06-01.** Volatile entries (pricing, programs, deadlines)
must be re-verified at use time — flagged ⚠️. This registry is publish-safe: no keys,
no operator secrets (CLAUDE.md rule 13).

> Honesty rail: this lists *where to look*, not vetted advice. Financial/tax/legal
> entries inform; they don't substitute for a CPA/attorney.

## Frameworks & mental models (free)
- **YC Startup Library / Startup School** — canonical idea→PMF→fundraise playbooks. https://www.startupschool.org
- **Lean Startup / build-measure-learn** — validation loop discipline (Ries).
- **Jobs-to-be-Done** — demand framing (Christensen / Traynor's product lens).
- **Sequoia "Writing a Business Plan" / pitch arc** — narrative scaffold.
- **Brian Balfour's "Four Fits"** — market↔model↔channel↔product fit (growth loops). https://brianbalfour.com
- **a16z marketplace + SaaS metrics primers** — benchmark vocabulary. https://a16z.com

## Benchmarks & metrics (free, ⚠️ figures drift)
- **SaaS Capital / OpenView / ChartMogul benchmark reports** — MRR growth, churn, NDR by ARR band. ⚠️ re-pull current year.
- **Bessemer "State of the Cloud" + Cloud Index** — public-comp multiples, efficiency. ⚠️
- **Carta "State of Private Markets"** — valuations, dilution, round sizes by stage. ⚠️

## Market intelligence (free + paid)
- **Hacker News** (RSS, free) — launch + sentiment; `hnrss.org`.
- **Product Hunt** (free web / API key) — launches, categories, what's resonating.
- **X / Twitter** (free web recon default; paid `X_BEARER_TOKEN` for structured recent-search) — **the primary live signal source**; founder pain, VC thesis, launch pulse. See `sources/trend-scout.yaml`.
- **Reddit** (free API) — r/SaaS, r/startups, r/Entrepreneur pain-language.
- **Crunchbase / PitchBook** (⚠️ paid, operator-key) — funding, comps. Gate to budget.
- **Google Trends** (free) — search-intent demand curves.
- **SEC EDGAR** (free API) — S-1s, public-comp economics.

## Legal & structure (inform only — verify with an attorney)
- **Clerky / Stripe Atlas** (⚠️ paid) — Delaware C-corp formation, cap-table hygiene.
- **YC SAFE + post-money SAFE docs** (free) — standard early instruments. https://www.ycombinator.com/documents
- **Cooley GO / Orrick Start-Up Forms** (free templates) — term sheets, option plans.

## Tax (inform only — verify with a CPA; jurisdiction-specific ⚠️)
- **QSBS (§1202)** — qualified small-business-stock gain exclusion; eligibility is fact-specific.
- **R&D tax credit (§41 / §174 capitalization)** — ⚠️ §174 amortization rules shifted recently; confirm current treatment.
- **83(b) election** — 30-day window on restricted stock; missing it is costly.
- **Delaware franchise tax** — assumed-par vs authorized-shares method (big delta).

## Programs & communities (⚠️ deadlines + terms change)
- **Accelerators** — YC, Techstars, a16z START, South Park Commons. ⚠️ batch deadlines.
- **Cloud credits** — AWS Activate, Google for Startups, Azure Founders Hub (⚠️ eligibility caps).
- **Communities** — Indie Hackers, On Deck, r/SaaS, relevant X circles.

## Demand & validation (free)
- **Smoke tests / landing-page + waitlist** — pre-build demand signal.
- **Fake-door / concierge MVP** — manual-first validation (do-things-that-don't-scale).
- **Customer-interview discipline** — *The Mom Test* (Fitzpatrick); ask about past behavior, not hypotheticals.

## Financial modeling (free + templates)
- **Causal / Runway / standard 3-statement + cohort models** — burn, runway, scenarios.
- **Rule of 40, magic number, CAC payback, LTV/CAC, NDR** — the core SaaS health ratios.
- **Dilution / cap-table waterfall** — model each round's founder-ownership impact.

---
*Maintenance: scouts append cited entries to the belief DB; promote durable, broadly
useful ones here with a freshness stamp. Re-verify ⚠️ entries before relying on them.*
