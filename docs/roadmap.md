# Roadmap

`docs/architecture_baseline.md` is authoritative. This file summarizes sequencing and does not authorize work.

## Current state

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D.
- Accepted application/consolidation implementation baseline: `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured.
- Active application, consolidation implementation or migration authorization: none.

Docs-only commits may advance `main` without changing these axes.

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
- PR #77 extracted shared frozen-boundary mechanics.
- PRs #81/#83 characterized and implemented ordered scalar row loading.
- PRs #87/#89 characterized and implemented v0.6A-v0.6C pure query values.
- PR #93 characterized v0.6B-v0.6D evidence read serialization and accepted the decision to keep the serializers local.
- PRs #97/#99 characterized and implemented neutral Stage 2 SQLAlchemy integrity translation.
- PRs #103/#105 characterized and implemented the neutral process-local Stage 2 revision-lock registry.

The neutral integrity helper catches only `IntegrityError`, preserves the exact caller-owned message and original cause, and performs no transaction, rollback, retry or constraint-classification work. The neutral revision-lock helper owns only the guarded process-local `(kind, UUID) -> RLock` registry. It preserves all eight kind labels and lock -> integrity translator -> transaction nesting, adds no cross-process or cross-host guarantee, and has no cleanup or eviction policy. Command modules still own transaction boundaries, conflict wording, row locks, latest-revision reads, revision-number allocation, supersession and retry.

No schema, migration, public API, fixture, domain-semantic or released-version change resulted from these consolidation reviews.

## Superseded path

Issue #70 and PR #71 for v0.6E price judgment remain superseded and closed without merge. Canonical price measurement ownership, comparison eligibility, realistic provider parity and sufficient consolidation must be resolved separately before reconsideration.

No v0.6E implementation or migration is authorized.

## Remaining Stage 2 consolidation candidates

1. append-only listener registration and dynamic link-model construction.

The next gate is only an independent ORM lifecycle characterization of item 1. Dynamic model factories and append-only listeners remain deferred until mapper/event registration, import-order behavior and test isolation are reviewed. No implementation is authorized by this status sync.

Evidence read serializer implementation is not a remaining candidate unless a documented re-evaluation trigger from PR #93 occurs. Integrity translation and the process-local lock registry are completed and do not authorize changes to row locks, allocation, supersession, cleanup/eviction or retry behavior.

## Prospective sequence

1. characterize ORM lifecycle concerns;
2. implement only if a smaller neutral contract preserves mapper/event behavior and reaches Definition of Ready;
3. decide whether canonical market-price evidence has independent user value;
4. decide whether valuation observations need comparison-eligibility semantics;
5. re-evaluate whether price judgment needs persisted state or a deterministic read model;
6. only then reconsider v0.7 Watchlist and later portfolio work.

Every item requires separate Architecture Preflight and GitHub authorization.

## Not authorized

- evidence serializer extraction or projection DTOs;
- row-lock, latest-revision, revision-allocation, supersession, cleanup/eviction or retry refactoring without accepted characterization;
- append-only-listener or dynamic model-factory refactoring;
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
