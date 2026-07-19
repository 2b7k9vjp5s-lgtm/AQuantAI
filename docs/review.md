# Review Log

GitHub Issues and pull-request reviews are the authoritative review record. This file is a concise local mirror of the current architecture status and major reset decisions.

See `docs/architecture_baseline.md` for the authoritative capability matrix, dependency direction, field ownership, invariants, architecture debt and delivery gates.

## Current status

- Review date: 2026-07-19
- Released software version: `0.2.0`
- Merged capability stage: v0.6D
- Accepted `main` commit: `9cc5a0e5dda97efa6b9c7b3a43eb3b5c4ead91ec`
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured
- Active architecture work: Issue #72, docs-only unified architecture baseline reset
- Application implementation authorization: none

## Architecture reset decision

Issue #70 and Draft PR #71 attempted to plan a v0.6E price-observation judgment slice. The path was paused and withdrawn before application implementation.

PR #71 was closed without merge and Issue #70 was closed as `not_planned`. Their branch, task and review history remain preserved.

The path was superseded because review exposed project-level problems rather than a single task defect:

1. README, roadmap, review log and prospective architecture used incompatible descriptions of the current state.
2. Canonical market-price measurement, unit and currency did not have a single accepted domain owner.
3. Generic v0.6B valuation `observed_value` did not have structured price-comparison eligibility.
4. Fixture-only data could make a success path appear reachable when the reviewed production adapter could not supply the same fields.
5. v0.6A-v0.6D repeated identity, revision, frozen-link, repository, query, fixture and cross-database test patterns without an intervening consolidation review.
6. The planning process exceeded the new reset threshold after repeated foundational blockers.

No v0.6E model, migration, command, API, fixture, test implementation or runtime behavior was merged.

## Current review conclusion

The repository still has a reliable auditable foundation:

- deterministic local market-data persistence and explicit snapshot-series selection;
- read-only Market Cockpit context;
- append-only v0.5 evidence ledger and Stage 1 handoff;
- append-only v0.6A-v0.6D Stage 2 research records;
- exact revision/provenance links;
- cutoff plus UTC chronology;
- SQLite/PostgreSQL validation;
- no-network fixture and demo discipline.

The immediate risk is architecture governance and duplication growth, not an uncontrolled code branch. The safe action is to align the architecture baseline before adding another domain.

## Active required changes — Issue #72

The docs-only architecture reset must:

- introduce the three-axis current-state model: release version, merged capability stage and runtime surface;
- record the capability matrix through v0.6D;
- mark v0.6E superseded and v0.7+ unauthorized;
- define the implemented domain dependency direction;
- establish field/domain ownership, especially market-price and valuation semantics;
- centralize shared architecture invariants;
- record architecture debt;
- add Architecture Preflight, Definition of Ready, golden-path-first, reset and consolidation gates;
- keep version `0.2.0` and avoid all application behavior.

## Locked exclusions

Until a later explicit authorization is accepted:

- no application code or provider behavior change;
- no migration;
- no v0.6E price judgment;
- no timing judgment;
- no v0.7 Watchlist or verification-task behavior;
- no portfolio, broker, order, recommendation or automated trading behavior;
- no release/tag or version change;
- no modification of PR #38.

## Next review gate

Issue #72 and its Draft PR must remain Open/Draft/unmerged after documentation synchronization. Review will verify:

- only authorized documentation/task files changed;
- project status is consistent across documents;
- the architecture baseline has one unambiguous ownership model;
- future work remains prospective and unauthorized;
- unchanged regression tests, fixture demo and Actions are green.

No Codex application implementation command is issued from this reset.