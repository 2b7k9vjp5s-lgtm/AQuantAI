# Issue 177 — Canonical Price and Comparison Eligibility v1 Implementation

## Authority

- GitHub Issue: #177
- Architecture Issue: #175
- Approved architecture PR: #176
- Required base: `aa47ae857bb3a3580efcb5193c0bb0b84751c02d`
- Branch: `feat/canonical-price-comparison-eligibility`
- Risk tier: **Strict**
- Owner authorization: `审核完成，继续` on 2026-07-22

## Objective

Implement the approved local-first Canonical Price and Comparison Eligibility v1 contract without changing Provider acquisition, existing source rows, Stage 2 records, product ranking or advisory boundaries.

## Ownership and boundaries

- Existing `IngestionRun`, `StockBasicRecord` and `DailyPriceRecord` remain Provider-normalized L1 source observations.
- The existing `backend.database` market-data domain owns explicit listed identity, canonical series contracts, L3 canonical-price revisions and D2 eligibility.
- Market, exchange, currency, unit, adjustment and source selection are explicit inputs; no prefix/name/Provider/UI/AI inference.
- Evidence Ingestion, Provider adapters and external network behavior remain unchanged.

## Schema

Migration `20260722_0013` creates exactly nine additive tables:

1. `listed_instruments`
2. `listed_instrument_revisions`
3. `canonical_price_series`
4. `canonical_price_series_revisions`
5. `canonical_prices`
6. `canonical_price_revisions`
7. `comparison_eligibility_assessments`
8. `comparison_eligibility_revisions`
9. `comparison_eligibility_members`

No existing table is altered or backfilled. Populated downgrade must fail before any drop.

## Commands

Local JSON-only commands:

- `scripts.record_listed_instrument`
- `scripts.record_canonical_price_series`
- `scripts.record_canonical_price`
- `scripts.record_price_comparison_eligibility`

Every command supports dry-run, strict fields, expected-latest protection, one atomic transaction and credential-safe failures.

The canonical-price input must explicitly provide both the exact `source_daily_price_id` and its exact `source_ingestion_run_id`; the command must verify the relationship rather than deriving or selecting another run.

## Read surfaces

Exact UUID and mandatory two-boundary reads:

- `/market-data/listed-instruments/{instrument_id}`
- `/market-data/canonical-prices/{canonical_price_id}`
- `/market-data/comparison-eligibility/{assessment_id}`

No symbol/name search, fallback, current-time default, network, valuation, ranking or recommendation fields.

## Golden path

A normal succeeded fixture `IngestionRun` and exact `DailyPriceRecord` are bound to an explicit CN_A / ISO_MIC / XSHE / CNY listed identity and accepted series contract. `float_repr_decimal_v1` produces one accepted L3 official close, then one eligible `company_research_price_context_v1` assessment. All three exact-ID surfaces read the frozen graph under explicit cutoff and recorded-time boundaries.

The source run must have completed no later than the canonical revision's `recorded_at_utc`; source information cutoff and completion time must also remain within both read boundaries.

## Primary failure path

Missing explicit exchange or currency fails as `canonical_identity_incomplete` before any series, price or eligibility write. No inference, source fallback or partial commit is allowed.

## Validation

- focused command/query/model tests;
- exact API tests and GET-only route verification;
- migration upgrade metadata and populated/empty downgrade tests;
- PostgreSQL/full pytest regression through GitHub Actions;
- local fixture demo remains network-free;
- complete base-to-head inventory stays inside Issue #177 authorized file families.

## Locked exclusions

No Provider or ingestion change, external network, FX, corporate-action reconstruction, existing-row mutation/backfill, automatic relinking, arithmetic price comparison, expectation gap, valuation normalization, fair value, target price, expected return, score, ranking, recommendation, alerts, portfolio, trading, release, tag or version change.

## Completion gate

Keep the implementation PR Draft/Open/unmerged until final CI, offline golden path, author-side fixed-head review and one independent fixed-head implementation approval succeed.
