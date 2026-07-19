# Roadmap

`docs/architecture_baseline.md` is authoritative. This file summarizes sequencing and does not authorize work.

## Current state

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D.
- Accepted application/consolidation implementation baseline: `782b2362e1252aa87b21f7aa58f764837f5adb71`.
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

The serializer decision is not unfinished implementation work. It records that no neutral claim projection reaches Definition of Ready, domain missing-evidence wording must remain visible, and v0.6D timestamp error behavior remains independent.

No schema, migration, public API, fixture, domain-semantic or released-version change resulted from these consolidation reviews.

## Superseded path

Issue #70 and PR #71 for v0.6E price judgment remain superseded and closed without merge. Canonical price measurement ownership, comparison eligibility, realistic provider parity and sufficient consolidation must be resolved separately before reconsideration.

No v0.6E implementation or migration is authorized.

## Remaining Stage 2 consolidation candidates

1. command conflict/integrity primitives and error compatibility;
2. revision allocation and lock strategy;
3. append-only listener registration and dynamic link-model construction.

The next candidate is only an independent characterization of item 1. It must inventory repeated database conflict handling, rollback boundaries, exception classes/messages and cross-database behavior before any implementation decision.

Evidence read serializer implementation is not a remaining candidate unless a documented re-evaluation trigger from PR #93 occurs.

## Prospective sequence

1. characterize command conflict/integrity handling;
2. implement only a minimal primitive if exact rollback and error compatibility are proven;
3. separately characterize revision allocation/locks and ORM lifecycle concerns;
4. decide whether canonical market-price evidence has independent user value;
5. decide whether valuation observations need comparison-eligibility semantics;
6. re-evaluate whether price judgment needs persisted state or a deterministic read model;
7. only then reconsider v0.7 Watchlist and later portfolio work.

Every item requires separate Architecture Preflight and GitHub authorization.

## Not authorized

- evidence serializer extraction or projection DTOs;
- command conflict/integrity implementation without accepted characterization;
- revision-lock or append-only-listener refactoring;
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