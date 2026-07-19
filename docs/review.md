# Review Log

GitHub Issues and pull-request reviews are the authoritative review record. This file is a concise local mirror of the current architecture status and major decisions.

See `docs/architecture_baseline.md` for the authoritative capability matrix, dependency direction, field ownership, invariants, architecture debt and delivery gates.

## Current status

- Review date: 2026-07-19
- Released software version: `0.2.0`
- Merged capability stage: v0.6D
- Accepted application/consolidation implementation baseline: `4b6377169fabb8eef5f1b421e8f008a11582f8a9`
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured
- Most recent architecture synchronization: Issue #78 and PR #79
- Active application or consolidation implementation authorization: none
- New migration authorization: none

Docs-only commits after the implementation baseline may advance `main` without changing the released version, merged capability stage or runtime behavior.

## Architecture reset decision

Issue #70 and Draft PR #71 attempted to plan a v0.6E price-observation judgment slice. The path was paused and withdrawn before application implementation.

PR #71 was closed without merge and Issue #70 was closed as `not_planned`. Their branch, task and review history remain preserved.

The path was superseded because review exposed project-level problems rather than a single task defect:

1. project documents used incompatible descriptions of the current state;
2. canonical market-price measurement, unit and currency did not have a single accepted owner;
3. generic v0.6B valuation `observed_value` did not have structured price-comparison eligibility;
4. fixture-only data could make an adapter-unreachable path appear valid;
5. v0.6A-v0.6D repeated identity, revision, frozen-link, repository, query, fixture and cross-database patterns without consolidation;
6. planning exceeded the reset threshold after repeated foundational blockers.

No v0.6E model, migration, command, API, fixture, test implementation or runtime behavior was merged.

## Unified baseline acceptance

Issue #72 and PR #73 established:

- the three-axis current-state model;
- capability and runtime boundaries through v0.6D;
- field and domain ownership;
- shared architecture invariants;
- architecture debt tracking;
- Architecture Preflight and Definition of Ready;
- golden-path-first, reset and consolidation gates.

The baseline was merged without changing release version or application behavior.

## Stage 2 consolidation review

Issue #74 and PR #75 characterized repeated Stage 2 infrastructure and selected one minimal first implementation:

- move exact v0.6A/v0.6B frozen-boundary mechanics to neutral Stage 2 ownership;
- remove the dependency from v0.6D quality judgments on v0.6C private command helpers;
- keep repository, query, model, listener, revision-lock and domain-semantic changes out of the same slice;
- require no migration.

Issue #76 and PR #77 then implemented that accepted slice.

Independent implementation review confirmed:

- exact authorized five-file inventory;
- one immutable `Stage2BaseBoundary` contract used by v0.6C and v0.6D;
- unchanged SQL locking, transaction, revision and validation behavior;
- unchanged API, repository, query, model, fixture and migration boundaries;
- focused compatibility tests and successful full Actions test/demo workflow.

PR #77 was squash-merged as `4b6377169fabb8eef5f1b421e8f008a11582f8a9`. Issue #76 closed as completed.

## Status synchronization acceptance

Issue #78 and PR #79 synchronized the architecture baseline, roadmap, review log and Stage 2 consolidation design record after PRs #75 and #77.

The accepted synchronization:

- records PRs #73, #75 and #77 as completed;
- records `4b6377169fabb8eef5f1b421e8f008a11582f8a9` as the application/consolidation implementation baseline;
- marks neutral boundary extraction complete;
- distinguishes completed boundary consolidation from remaining repository, query, concurrency and ORM candidates;
- identifies ordered repository row-loading primitives as the next separate characterization candidate;
- preserves version `0.2.0` and all feature/migration exclusions;
- changes no application behavior.

## Current review conclusion

The repository has a reliable auditable foundation:

- deterministic local market-data persistence and explicit snapshot-series selection;
- read-only Market Cockpit context;
- append-only v0.5 evidence ledger and Stage 1 handoff;
- append-only v0.6A-v0.6D Stage 2 research records;
- exact revision/provenance links;
- cutoff plus UTC chronology;
- SQLite/PostgreSQL validation;
- no-network fixture and demo discipline;
- neutral ownership of the shared v0.6A/v0.6B Stage 2 frozen boundary.

The highest-priority incorrect dependency direction is resolved. Remaining risk is continued infrastructure duplication and test-matrix growth, not uncontrolled feature work.

## Locked exclusions

Until a later explicit authorization is accepted:

- no repository utility implementation without an accepted characterization Issue;
- no application code or provider behavior change;
- no migration;
- no v0.6E price judgment;
- no timing judgment;
- no v0.7 Watchlist or verification-task behavior;
- no portfolio, broker, order, recommendation or automated trading behavior;
- no release/tag or version change;
- no modification of PR #38.

## Next development gate

The next candidate is a separate characterization Issue for ordered repository row-loading primitives. It must verify:

- exact repeated SQL shapes;
- deterministic ordering and duplicate handling;
- missing-row behavior;
- session and loading semantics;
- SQLite/PostgreSQL compatibility;
- a no-migration decision and explicit implementation exclusions.

Characterization does not authorize implementation. No Codex application implementation command is active after this status synchronization.
