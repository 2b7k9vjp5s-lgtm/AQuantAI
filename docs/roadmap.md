# Roadmap

`docs/architecture_baseline.md` is authoritative. This file summarizes sequencing and does not authorize work.

## Current state

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D.
- Accepted application/consolidation implementation baseline: `e424fa3a95e35b20f5fe8d8ada211821d9661efd`.
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured.
- Active application, consolidation implementation or migration authorization: none.

Merged capability and consolidation work does not automatically publish a release. Docs-only commits may advance `main` without changing these axes.

## Completed product foundations

- Phase 0-6 and stabilization: project setup, provider boundaries, deterministic factor/scoring and backtest foundations, ML/research-report contracts, Dashboard contracts and local fixture demo.
- v0.3: PostgreSQL market-data persistence, immutable ingestion attempts, complete-snapshot reconciliation, canonical series, controlled AKShare ingestion and cutoff-aware reads.
- v0.4A-v0.4E: read-only selected-scope Market Cockpit breadth/risk, benchmark/sector context, liquidity and descriptive price behavior.
- v0.5A-v0.5C: evidence ledger, industry-chain maps, beneficiary classifications and candidate-pool handoff.
- v0.6A-v0.6D: company research, expectations/valuation observations, catalyst/risk assessments and independent quality judgments.

These capabilities remain research-only, append-only where applicable, cutoff-aware and non-advisory. They do not provide target prices, expected returns, rankings, recommendations, Watchlist state, portfolio actions or trading behavior.

## Completed architecture and consolidation work

- PR #73 established the unified architecture baseline and delivery gates.
- PR #75 characterized Stage 2 duplication and safe extraction order.
- PR #77 extracted shared v0.6A/v0.6B frozen-boundary mechanics into `industry_alpha.stage2_boundary`.
- Issue #78 and PR #79 synchronized that result.
- PR #81 characterized repeated ordered repository row-loading mechanics.
- PR #83 added `industry_alpha.stage2_repository_rows.load_ordered_rows` and delegated existing v0.6A-v0.6D private wrappers.
- v0.6B `None` filtering, link-field selection, graph assembly, missing-parent behavior and session ownership remain repository-local.
- No schema, migration, API, fixture, query-service or domain-semantic change was made.
- Issue #84 and its linked PR synchronize the completed row-loader result.

## Superseded path

Issue #70 and PR #71 for v0.6E price judgment remain superseded and closed without merge. Canonical price measurement ownership, structured comparison eligibility, realistic provider parity and sufficient consolidation must be resolved separately before reconsideration.

No v0.6E implementation or migration is authorized.

## Remaining Stage 2 consolidation candidates

1. pure query cutoff/recorded visibility and date/UTC/UUID formatting;
2. a neutral evidence read-serialization contract;
3. command conflict/integrity primitives;
4. revision allocation and lock strategy;
5. append-only listener registration and dynamic link-model construction.

The next candidate is only a separate characterization of item 1. It must prove identical visibility, chronology, formatting, ordering and error behavior before implementation. Stable schemas and domain payloads must not be generalized for visual uniformity.

## Prospective sequence

1. characterize safe query visibility/date/UTC/UUID formatting;
2. implement only minimal pure helpers if characterization is accepted;
3. characterize evidence serialization only after defining a neutral contract;
4. decide whether canonical market-price evidence has independent user value;
5. decide whether valuation observations need comparison-eligibility semantics;
6. re-evaluate whether price judgment needs persisted state or a deterministic read model;
7. only then reconsider v0.7 Watchlist and later portfolio work.

Every item requires separate Architecture Preflight and GitHub authorization.

## Not authorized

- query utility implementation without accepted characterization;
- evidence serializer unification;
- command integrity, revision-lock or append-only-listener refactoring;
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
