# Roadmap

`docs/architecture_baseline.md` is the authoritative current-state and architecture source. This roadmap summarizes sequencing; it does not authorize work by itself.

## Current state

AQuantAI uses three independent status axes:

- released software version: `0.2.0`;
- merged capability stage on `main`: v0.6D;
- runtime surfaces: the local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured.

Merged capability and consolidation slices do not automatically publish a new release.

The accepted application/consolidation implementation baseline is `4b6377169fabb8eef5f1b421e8f008a11582f8a9`. Later docs-only commits may advance `main` without changing the released version, merged capability stage or runtime behavior.

## Completed foundations

### Phase 0-6 and stabilization

Project initialization, provider boundaries, deterministic factor/scoring utilities, backtest foundations, ML contracts, research-report contracts, Dashboard contracts, local fixture demo and correctness hardening are complete.

### v0.2 baseline

The released `0.2.0` metadata and local fixture-backed Dashboard baseline remain unchanged.

### v0.3 market-data persistence

Completed:

- PostgreSQL market-data persistence and migrations;
- immutable ingestion attempts and complete-snapshot reconciliation;
- canonical snapshot-series identities and exact selectors;
- controlled manual AKShare ingestion with explicit network opt-in;
- cutoff-aware deterministic reads and offline fixtures.

### v0.4A-v0.4E Market Cockpit

Completed reviewed slices:

- selected-universe breadth and risk;
- optional independently selected benchmark context;
- provider-attributed sector context;
- liquidity distribution and concentration context;
- descriptive price-behavior proxies.

These remain selected-scope, descriptive, read-only and non-advisory. They do not provide canonical valuation, regime, crowding, signals or recommendations.

### v0.5A-v0.5C Industry Alpha Stage 1

Completed reviewed slices:

- research-case and evidence ledger;
- evidence-backed industry chain maps;
- Stage 1 company-beneficiary classifications and candidate-pool handoff.

### v0.6A-v0.6D Stage 2

Completed reviewed slices:

- v0.6A company research and financial-transmission hypotheses;
- v0.6B expectations and valuation observations;
- v0.6C catalyst and risk assessments;
- v0.6D independent industry/company quality judgments.

All are append-only, cutoff-aware, evidence-bound and read-only. They do not produce target prices, expected returns, rankings, recommendations, Watchlist state, portfolio actions or trading behavior.

## Completed architecture and consolidation work

- PR #73 established the unified architecture baseline and delivery gates.
- PR #75 characterized Stage 2 duplication, risk and safe extraction order.
- PR #77 extracted the neutral v0.6A/v0.6B frozen-boundary mechanics into `industry_alpha.stage2_boundary`.
- v0.6C and v0.6D now consume one neutral `Stage2BaseBoundary` contract.
- v0.6D no longer imports shared private mechanics from the v0.6C command module.
- No schema, migration, API, fixture or domain-semantic change was made by that extraction.
- Issue #78 and PR #79 synchronized these outcomes into the architecture record without changing application behavior.

## Superseded path

v0.6E price-observation judgment planning in Issue #70 and PR #71 is superseded and closed without merge.

The reset established that a price judgment cannot be implemented until the project separately resolves:

- canonical market-price measurement, unit and currency ownership;
- structured valuation comparison eligibility;
- production-realistic fixture/provider parity;
- sufficient Stage 2 shared-infrastructure consolidation.

No v0.6E implementation or migration is authorized.

## Current authorization state

No application feature, consolidation implementation or migration is currently authorized.

The next candidate is a separate characterization of ordered repository row-loading primitives. Characterization must precede implementation and must prove identical SQL shape, ordering, duplicate and missing-row behavior, session behavior and SQLite/PostgreSQL compatibility.

## Remaining Stage 2 consolidation candidates

The neutral boundary extraction resolved the highest-priority incorrect dependency direction. Remaining candidates must be handled independently:

1. ordered repository row-loading primitives;
2. pure query cutoff/UTC/date/UUID formatting;
3. a neutral evidence read-serialization contract;
4. command conflict/integrity primitives;
5. revision allocation and lock strategy;
6. append-only listener registration.

Stable schemas must not be generalized merely for aesthetic uniformity. A review may conclude that duplication should remain when sharing would weaken domain ownership or ORM stability.

## Prospective sequence

The following sequence requires separate Architecture Preflight and GitHub authorization at every step:

1. characterize ordered repository row-loading primitives;
2. implement only a minimal helper if characterization is accepted;
3. characterize safe query visibility and formatting utilities;
4. decide whether a standalone canonical market-price evidence contract has user value;
5. decide whether valuation observations need structured comparison-eligibility semantics;
6. re-evaluate whether a separate price-judgment aggregate is necessary;
7. only then reconsider v0.7 Watchlist and verification tasks;
8. later consider Paper Portfolio and portfolio analysis.

A deterministic read model may be preferable to a new persisted judgment aggregate when it can reproduce the required relationship without duplicating state.

## Not authorized

Until explicitly approved in a future Issue:

- repository utility implementation beyond an accepted characterization;
- evidence serializer unification;
- revision-lock or append-only-listener refactoring;
- v0.6E price judgment;
- timing judgment;
- v0.7 Watchlist or verification-task runtime behavior;
- v0.8 Paper Portfolio or simulated trades;
- v0.9 portfolio analysis and Quant Core workflow integration;
- new migrations;
- release/tag or version changes;
- broker, order, automated trading, recommendation or production deployment behavior.

## Delivery rule

Development proceeds only through:

```text
Architecture Preflight
  -> Definition of Ready
  -> concise authoritative Issue
  -> task synchronization/planning review
  -> implementation review
  -> merge authorization
  -> architecture/status synchronization
```

Green CI is necessary but not sufficient. A stage must also prove domain ownership, production reachability, fixture parity, explicit semantics and bounded scope.
