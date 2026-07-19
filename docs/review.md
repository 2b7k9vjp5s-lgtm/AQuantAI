# Review Log

GitHub Issues and pull-request reviews are authoritative. `docs/architecture_baseline.md` owns the current architecture interpretation.

## Current status

- Review date: 2026-07-19
- Released software version: `0.2.0`
- Merged capability stage: v0.6D
- Accepted application/consolidation implementation baseline: `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured
- Most recent accepted consolidation implementation: Issues #102/#104 and PRs #103/#105
- Active application or consolidation implementation authorization: none
- New migration authorization: none

Docs-only commits may advance `main` without changing release, capability or runtime state.

## Accepted architecture decisions

- Issue #70 / PR #71 for v0.6E price judgment were closed without merge.
- Issue #72 / PR #73 established the unified baseline and delivery gates.
- Issue #74 / PR #75 characterized Stage 2 infrastructure.
- Issue #76 / PR #77 extracted the neutral frozen boundary.
- Issues #80/#82 and PRs #81/#83 characterized and implemented ordered scalar row loading.
- Issues #86/#88 and PRs #87/#89 characterized and implemented v0.6A-v0.6C pure query values.
- Issue #92 / PR #93 kept evidence read serializers domain-local because no neutral claim projection reached Definition of Ready.
- Issues #96/#98 and PRs #97/#99 characterized and implemented neutral command integrity translation.
- Issues #102/#104 and PRs #103/#105 characterized and implemented the neutral process-local revision-lock registry.

## Command integrity implementation acceptance

PR #99 was accepted at fixed head `b0dc58b2adb27e9a6ec6f1a2dce3699bd2bab9ff` and squash-merged as `a2688b6e244743ef5e3bdcaedfc6c6717d7a7d8c`.

Independent review confirmed:

- the base-to-head diff contained exactly the seven Issue #98 files;
- `stage2_integrity.translate_integrity(message)` catches only SQLAlchemy `IntegrityError`;
- it raises `EvidenceLedgerConflictError` with the exact caller message and chains from the original exception;
- non-integrity exceptions propagate as the same object;
- all four command modules preserve outer-translator/inner-`session_factory.begin()` nesting;
- conflict messages, transaction-owned rollback, process-local locks, database row locks, revision allocation and supersession are unchanged;
- Actions `29687524781`, full tests and the fixture demo succeeded;
- PostgreSQL-focused tests were honestly reported as skipped where the required database URL was unavailable.

No migration, API, schema, fixture, dependency, release, version, v0.6E, v0.7 or PR #38 change occurred.

## Revision-lock implementation acceptance

PR #105 was accepted at fixed head `d1266de8369906af90f481d3727f08fb5552e8fa` and merged as `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.

Independent review confirmed:

- `industry_alpha.stage2_revision_locks` owns only one guarded process-local `(kind, UUID) -> RLock` registry;
- all eight labels (`research`, `hypothesis`, `expectation`, `valuation`, `catalyst`, `risk`, `industry`, `company`) are unchanged;
- lock -> integrity translator -> transaction nesting is unchanged;
- same-key identity, different-key isolation, reentrancy and same-key thread exclusion are covered directly;
- row locks, latest-revision reads, revision-number allocation, supersession, cleanup/eviction and retry remain command-local;
- no cross-process or cross-host guarantee was added, and SQLite/PostgreSQL concurrency limitations remain unchanged;
- Actions `29688711474`, full tests and the fixture demo succeeded.

No migration, runtime-surface, API, schema, release, version, v0.6E, v0.7 or PR #38 change occurred.

## Current review conclusion

Neutral ownership exists for:

- shared Stage 2 frozen-boundary mechanics;
- ordered scalar repository row loading;
- v0.6A-v0.6C pure query-value mechanics;
- SQLAlchemy integrity-error translation;
- the process-local keyed revision-lock registry.

Evidence read serialization intentionally remains domain-local. Command modules continue to own exact conflict text, transaction boundaries, row locks, latest-revision reads, revision-number allocation, supersession, cleanup/eviction and retry. The next consolidation gate is ORM lifecycle characterization.

## Locked exclusions

- no evidence serializer extraction or projection DTOs without a re-evaluation trigger and new preflight;
- no row-lock, latest-revision, revision-allocation, supersession, cleanup/eviction or retry refactor without accepted characterization;
- no model-factory or append-only-listener refactor;
- no application/provider behavior change or migration;
- no v0.6E price or timing judgment;
- no v0.7 Watchlist or verification-task behavior;
- no portfolio, broker, order, recommendation or automated trading behavior;
- no release/tag/version change;
- no modification of PR #38.

## Next development gate

The next gate is a separate ORM lifecycle characterization of dynamic link-model factories and append-only listener registration. It must inventory mapper/event registration, import-order and test-isolation behavior before any implementation decision.

Dynamic model factories and append-only listeners remain deferred. Characterization may conclude that they should remain local. It does not authorize implementation. No Codex application implementation command is active after this synchronization.
