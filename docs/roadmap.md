# Roadmap

`docs/architecture_baseline.md` is authoritative. This file summarizes sequencing and does not authorize work.

## Current state

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D.
- Provider-status synchronization base: `ca2a9fa0ca4daea6b7318a50851272b74c4dc115`.
- Accepted application/consolidation implementation baseline: `7705b7caf210d606473db6f24c5fadfad4918646`.
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
- PR #117 characterized Stage 2 ORM lifecycle behavior.
- PR #119 committed and accepted the SQLite/subprocess/PostgreSQL lifecycle compatibility matrix.
- PR #121 implemented the neutral Stage 2 append-only mutation scan and merged as `7705b7caf210d606473db6f24c5fadfad4918646`.

The neutral integrity helper catches only `IntegrityError`, preserves the exact caller-owned message and original cause, and performs no transaction, rollback, retry or constraint-classification work. The neutral revision-lock helper owns only the guarded process-local `(kind, UUID) -> RLock` registry. The neutral append-only helper owns only delete-before-dirty scanning, tuple membership, material-dirty detection and exact immutable messages. All four decorators, listeners, tuples, dynamic factories and generated globals remain domain-local. Command modules still own transaction boundaries, conflict wording, row locks, latest-revision reads, revision-number allocation, supersession and retry.

No schema, migration, public API, fixture, domain-semantic or released-version change resulted from these consolidation reviews.

## Accepted future provider direction

Issue #108 / PR #109 records Hithink as the preferred future A-share provider candidate. It is not implemented and is not the active default. AKShare remains an explicit separate alternative, and existing AKShare ingestion history and canonical series remain preserved.

Every ingestion run and canonical series contains exactly one provider. Silent fallback, provider relabeling and row-level provider mixing are prohibited. Explicit alternatives create separate provider-specific runs and series.

Canonical ingestion may later use reviewed REST or a separately reviewed market-dump importer. MCP and LLM-mediated calls are excluded from canonical ingestion. No production Hithink implementation has reached Definition of Ready.

Issue #112 / Draft PR #113 produced a technically reviewed seven-file contract probe at fixed head `b09fcd8e68f4d280407b483a7d114aa0b0e8a015`; Actions `29691380530` succeeded. The account owner deferred integration, so Issue #112 closed as `not planned` and PR #113 closed without merge. No live probe ran, no API key was used, and no live contract, permission or data-use acceptance exists.

No Hithink code, dependency, provider default, runtime behavior, database/schema change or migration reached `main`. Hithink remains a deferred future candidate that requires new Architecture Preflight and explicit authorization. AKShare remains the implemented controlled provider path.

## Superseded path

Issue #70 and PR #71 for v0.6E price judgment remain superseded and closed without merge. Canonical price measurement ownership, comparison eligibility, realistic provider parity and sufficient consolidation must be resolved separately before reconsideration.

No v0.6E implementation or migration is authorized.

## Deferred Stage 2 ORM work

Listener/decorator/tuple relocation and v0.6C/v0.6D dynamic link-model factory consolidation have no current Definition of Ready. Explicit reload support, database triggers and Core-DML interception also remain unauthorized. The accepted helper does not change event registration, mapper identity or domain ownership.

Evidence read serializer implementation is not a remaining candidate unless a documented re-evaluation trigger from PR #93 occurs. Integrity translation, the process-local lock registry and the pure append-only scan are completed and do not authorize changes to row locks, allocation, supersession, cleanup/eviction, retry, event registration or mapped-class ownership.

## Prospective sequence

1. characterize whether canonical market-price evidence has independent user value and define value normalization, measurement, provenance, chronology, adjustment, comparison and missing-data semantics;
2. decide whether valuation observations need comparison-eligibility semantics;
3. re-evaluate whether price judgment needs persisted state or a deterministic read model;
4. only then reconsider v0.7 Watchlist and later portfolio work;
5. reconsider Hithink only through a new Architecture Preflight and explicit authorization.

Every item requires separate Architecture Preflight and GitHub authorization.

## Not authorized

- evidence serializer extraction or projection DTOs;
- row-lock, latest-revision, revision-allocation, supersession, cleanup/eviction or retry refactoring without accepted characterization;
- listener/decorator/tuple relocation, dynamic model-factory consolidation, explicit reload support, database triggers or Core-DML interception;
- provider implementation, live request, secret, dependency, ingestion script, fixture or default-provider change;
- silent provider fallback, relabeling, row-level mixing or MCP/LLM canonical ingestion;
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
