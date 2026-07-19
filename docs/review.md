# Review Log

GitHub Issues and pull-request reviews are authoritative. `docs/architecture_baseline.md` owns the current architecture interpretation.

## Current status

- Review date: 2026-07-19
- Released software version: `0.2.0`
- Merged capability stage: v0.6D
- Accepted application/consolidation implementation baseline: `782b2362e1252aa87b21f7aa58f764837f5adb71`
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured
- Most recent architecture synchronization: Issue #94 and its linked synchronization PR
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

## Evidence read characterization acceptance

Issue #92 / PR #93 compared the v0.6B-v0.6D private evidence payload builders.

Independent review confirmed that the serializers share evidence-item fields, contradiction projection, A-D grade counts and deterministic sorting, but also have material differences:

- v0.6B emits a reduced nested claim shape;
- v0.6B uses domain-specific missing-evidence wording;
- owner revision fields and source-link container names differ;
- v0.6D retains a separate timestamp-null/error policy;
- a whole serializer would require reflection, callbacks or adapter objects;
- neutral projection DTOs would add conversion code without an accepted neutral claim contract.

The accepted decision is to keep the serializers local. Evidence serializer implementation does not reach Definition of Ready, and no implementation Issue follows from PR #93.

PR #93 was squash-merged as `e97762eba916e64299965a33b574870b1dad46e0`. Issue #92 closed completed. Actions tests, fixture demo and cleanup passed; no migration or runtime change occurred.

## Current review conclusion

Neutral ownership exists for:

- shared Stage 2 frozen-boundary mechanics;
- ordered scalar repository row loading;
- v0.6A-v0.6C pure query-value mechanics.

Evidence read serialization intentionally remains domain-local. Remaining consolidation risk is command conflict/integrity and rollback compatibility, revision allocation/locking, and ORM event complexity.

## Locked exclusions

- no evidence serializer extraction or projection DTOs without a re-evaluation trigger and new preflight;
- no command conflict/integrity implementation without accepted characterization;
- no revision-lock, model-factory or append-only-listener refactor;
- no application/provider behavior change or migration;
- no v0.6E price or timing judgment;
- no v0.7 Watchlist or verification-task behavior;
- no portfolio, broker, order, recommendation or automated trading behavior;
- no release/tag/version change;
- no modification of PR #38.

## Next development gate

The next candidate is a separate characterization of command conflict/integrity behavior. It must inventory repeated `IntegrityError` handling, rollback ownership, domain exception translation, exact messages, revision/link atomicity and SQLite/PostgreSQL differences.

Characterization may conclude that conflict handling should remain local. It does not authorize implementation. No Codex application implementation command is active after this synchronization.