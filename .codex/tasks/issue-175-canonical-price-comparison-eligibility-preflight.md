# Issue 175 — Canonical Price and Comparison Eligibility v1 Architecture Preflight

## Authority

- GitHub Issue: #175
- Required base: `22c1951ba23c495cc6070b948149f4118a86ab6d`
- Branch: `docs/canonical-price-comparison-eligibility-preflight`
- Risk tier: **Strict**
- Owner authorization: `审核完成，继续` on 2026-07-22
- Roadmap: Issue #137, parallel market-price infrastructure track

## Objective

Define an implementable, local-first contract for:

1. explicit listed-instrument, market, exchange and currency identity;
2. deterministic promotion of one exact Provider-normalized daily-price observation into one accepted canonical-price revision;
3. versioned Comparison Eligibility that states whether exact canonical-price revisions may participate in one named downstream comparison purpose;
4. cutoff, recorded-UTC, provenance, conflict, missing and historical-freeze behavior;
5. future schema, command, API, migration and test boundaries.

This task does not authorize runtime code, migrations, Provider changes, external requests, comparison calculations, rankings or recommendations.

## Existing state that must remain unchanged

- `backend.database.models.DailyPriceRecord` is a Provider-normalized L1 source observation.
- `IngestionRun` owns Provider, dataset, series identity, status and source cutoff.
- `StockBasicRecord.exchange` is Provider-normalized text and is not an accepted exchange identity.
- existing Stage 2 valuation observations may optionally link one `DailyPriceRecord`, but that link is not Canonical Price or Comparison Eligibility.
- Company Research Comparison Matrix v1 is merged through PR #174 at main commit `22c1951ba23c495cc6070b948149f4118a86ab6d` and remains component-only.
- no existing row may be relabeled, backfilled or silently rebound.

## Required architecture decisions

### Instrument identity

- stable identity and append-only revisions;
- exact market, exchange, currency, source-code alias and listing chronology;
- accepted values must be recorded explicitly, never inferred from code prefixes, names, Provider identity or UI context;
- one source alias may map to only one cutoff-visible listing revision inside an accepted alias contract;
- ambiguous aliases fail closed.

### Price semantics

- exact L0/L1/L2/L3 transition;
- v1 canonical price kind and adjustment basis;
- exact unit, currency, decimal scale and deterministic rounding;
- one exact source observation and one exact succeeded ingestion run;
- no Provider mixing, fallback or newest-looking-row selection;
- source binary-float limitations must remain visible in provenance.

### Canonical price history

- stable canonical series identity;
- append-only observation/revision model;
- exact trade date, price kind, adjustment basis, currency, unit and source link;
- explicit information cutoff and recorded UTC;
- expected-latest conflict protection;
- no automatic repair or relinking.

### Comparison Eligibility

- separate D2 rule-owned state from price value;
- named comparison purpose and rule version;
- exact canonical-price revision inputs;
- explicit `eligible`, `ineligible`, `missing`, `stale`, `conflicting`, `not_applicable` states and reason codes;
- no score, ordering, valuation attractiveness or recommendation meaning;
- exact cutoff and recorded-UTC visibility.

### Migration and downgrade

- additive tables only;
- no modification or backfill of existing market-data or Stage 2 tables;
- populated downgrade refusal before any drop;
- atomic migration;
- deterministic PostgreSQL and supported SQLite behavior.

### Commands and reads

- explicit local write commands only;
- read-only API candidates with exact IDs and both as-of boundaries;
- no network in imports, startup, tests, CI, fixtures or ordinary reads;
- no automatic downstream relinking.

## Golden path

Use production-reachable, offline data:

1. one succeeded `IngestionRun` with one explicit series identity;
2. one exact `StockBasicRecord` and one exact `DailyPriceRecord`;
3. one explicit listed-instrument revision recording market, exchange and currency;
4. one explicit canonical-price series contract binding Provider, dataset, source code, price kind, adjustment basis, decimal conversion and scale;
5. one accepted canonical-price revision linked to the exact source row and run;
6. one Comparison Eligibility revision over exact canonical-price revision inputs;
7. deterministic readback at explicit `as_of_cutoff` and `as_of_recorded_at_utc`.

## Primary failure path

Fail closed before any canonical-price or eligibility write when:

- listing identity is missing or ambiguous;
- exchange or currency is absent;
- source run is not succeeded;
- source series identity does not match the accepted contract;
- duplicate source rows exist for the same accepted natural key;
- adjustment basis or price kind is incompatible;
- source value is non-finite or cannot be converted under the exact decimal rule;
- a later revision is accidentally selected outside either as-of boundary;
- the expected latest revision has changed.

## Stop conditions

Return to architecture work and do not authorize implementation when:

- market/exchange/currency ownership is unresolved;
- existing Provider-normalized fields are treated as canonical without an explicit contract;
- binary-float conversion and rounding are not deterministic and visible;
- Comparison Eligibility meaning or purpose remains ambiguous;
- implementation would require Provider, ingestion or external-network changes;
- implementation would mutate or backfill existing rows;
- downstream scope expands into valuation, expected return, ranking or recommendation.

## Authorized files

- `.codex/tasks/issue-175-canonical-price-comparison-eligibility-preflight.md`
- `docs/canonical_price_comparison_eligibility_preflight.md`
- `docs/architecture_baseline.md`

## Validation

- verify all three documents agree on base, scope, ownership and exclusions;
- verify candidate schema is additive and no backfill is proposed;
- verify one production-reachable offline golden path and one fail-closed path;
- verify no hidden inference, Provider fallback, network, score, valuation or recommendation semantics;
- verify the complete base-to-head inventory contains only the three authorized files.

## Completion gate

- Draft architecture PR only;
- documentation and repository checks pass;
- author-side fixed-head review is recorded;
- one independent fixed-head architecture approval is required;
- no implementation Issue is opened before architecture merge.
