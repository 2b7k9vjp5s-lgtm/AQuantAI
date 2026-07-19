# Roadmap

`docs/architecture_baseline.md` is authoritative. This file summarizes sequencing and does not authorize work.

## Current state

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D.
- Accepted application/consolidation implementation baseline: `782b2362e1252aa87b21f7aa58f764837f5adb71`.
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured.
- Active application, consolidation implementation or migration authorization: none.

Merged capability and consolidation work does not automatically publish a release. Docs-only commits may advance `main` without changing these axes.

## Completed product foundations

- Phase 0-6 and stabilization: setup, provider boundaries, deterministic factor/scoring and backtest foundations, ML/research-report contracts, Dashboard contracts and local fixture demo.
- v0.3: PostgreSQL market-data persistence, immutable ingestion attempts, complete-snapshot reconciliation, canonical series, controlled AKShare ingestion and cutoff-aware reads.
- v0.4A-v0.4E: read-only selected-scope Market Cockpit breadth/risk, context, liquidity and descriptive price behavior.
- v0.5A-v0.5C: evidence ledger, industry-chain maps, beneficiary classifications and candidate-pool handoff.
- v0.6A-v0.6D: company research, expectations/valuation observations, catalyst/risk assessments and independent quality judgments.

These capabilities remain research-only, cutoff-aware and non-advisory. They do not provide target prices, expected returns, rankings, recommendations, Watchlist state, portfolio actions or trading behavior.

## Completed architecture and consolidation work

- PR #73 established the unified architecture baseline and delivery gates.
- PR #75 characterized Stage 2 duplication and safe extraction order.
- PR #77 extracted shared frozen-boundary mechanics into `industry_alpha.stage2_boundary`.
- Issue #78 / PR #79 synchronized that result.
- PR #81 characterized repeated ordered row loading; PR #83 added `industry_alpha.stage2_repository_rows.load_ordered_rows`.
- Issue #84 and its linked PR synchronized the row-loader result.
- PR #87 characterized pure query-value mechanics and the v0.6D edge difference.
- PR #89 added `industry_alpha.stage2_query_values` and delegated only v0.6A-v0.6C required UTC, date-granular visibility and timestamp/date/UUID formatting.
- v0.6D query-value behavior, evidence serialization, link selection, payload ordering, notices and aggregate errors remain domain-local.
- No schema, migration, public API, fixture, domain-semantic or released-version change resulted from these consolidation slices.

## Superseded path

Issue #70 and PR #71 for v0.6E price judgment remain superseded and closed without merge. Canonical price measurement ownership, comparison eligibility, realistic provider parity and sufficient consolidation must be resolved separately before reconsideration.

No v0.6E implementation or migration is authorized.

## Remaining Stage 2 consolidation candidates

1. a neutral evidence read-serialization contract;
2. command conflict/integrity primitives;
3. revision allocation and lock strategy;
4. append-only listener registration and dynamic link-model construction.

The next candidate is only an independent characterization of item 1. It must inventory the v0.6B-v0.6D evidence serializers, prove which fields and ordering are truly invariant, preserve domain-specific missing-evidence text and boundaries, and allow a decision to keep the serializers local.

## Prospective sequence

1. characterize a neutral evidence read-serialization contract;
2. implement only the smallest serializer boundary if characterization is accepted;
3. separately characterize command integrity/conflict handling, revision allocation/locks and ORM lifecycle concerns;
4. decide whether canonical market-price evidence has independent user value;
5. decide whether valuation observations need comparison-eligibility semantics;
6. re-evaluate whether price judgment needs persisted state or a deterministic read model;
7. only then reconsider v0.7 Watchlist and later portfolio work.

Every item requires separate Architecture Preflight and GitHub authorization.

## Not authorized

- evidence serializer implementation without accepted characterization;
- command integrity, revision-lock or append-only-listener refactoring;
- v0.6D query-value policy changes;
- v0.6E price or timing judgment;
- v0.7 Watchlist or verification-task behavior;
- portfolio, broker, order, recommendation or automated trading behavior;
- new migrations, releases, tags or version changes;
- modification of PR #38.

## Delivery rule

```text
Architecture Preflight
  -> Definition of Ready
  -> authoritative Issue
  -> task synchronization/planning review
  -> implementation review
  -> merge authorization
  -> architecture/status synchronization
```

Green CI is necessary but not sufficient. Scope, ownership, reachability, semantics and compatibility must also be accepted.