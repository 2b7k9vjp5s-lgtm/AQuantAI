# Review Log

GitHub Issues and pull-request reviews are authoritative. `docs/architecture_baseline.md` owns the current architecture interpretation.

## Current status

- Review date: 2026-07-19
- Released software version: `0.2.0`
- Merged capability stage: v0.6D
- Accepted application/consolidation implementation baseline: `782b2362e1252aa87b21f7aa58f764837f5adb71`
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured
- Most recent architecture synchronization: Issue #90 and its linked synchronization PR
- Active application or consolidation implementation authorization: none
- New migration authorization: none

Docs-only commits may advance `main` without changing release, capability or runtime state.

## Accepted architecture decisions

- Issue #70 / PR #71 for v0.6E price judgment were closed without merge.
- Issue #72 / PR #73 established the unified baseline, ownership, invariants, debt register and delivery gates.
- Issue #74 / PR #75 characterized Stage 2 infrastructure.
- Issue #76 / PR #77 moved shared frozen-boundary mechanics to `industry_alpha.stage2_boundary` and removed the v0.6D dependency on v0.6C private helpers.
- Issue #78 / PR #79 synchronized that first consolidation result.
- Issue #80 / PR #81 characterized repeated ordered scalar row loading.
- Issue #82 / PR #83 implemented `industry_alpha.stage2_repository_rows.load_ordered_rows`; Issue #84 and its linked PR synchronized the result.

## Query-value acceptance

Issue #86 / PR #87 characterized pure Stage 2 query-value mechanics.

The accepted design established that v0.6A-v0.6C share identical behavior for:

- required UTC normalization, including the exact missing-timestamp visibility error;
- naive and aware datetime conversion to UTC;
- date-granular recorded and information-date visibility;
- trailing-`Z` timestamp formatting;
- optional date and UUID text formatting.

v0.6D remains local because its required non-null helper has different malformed-input behavior.

Issue #88 / PR #89 implemented `industry_alpha.stage2_query_values` and delegated only those mechanics from v0.6A-v0.6C. Independent review confirmed:

- exact six-file inventory;
- unchanged evidence payload construction, link selection, sorting, notices, aggregate errors and public contracts;
- unchanged `stage2_judgments_query.py`;
- direct tests for exact error text, UTC conversion, formatting and cutoff boundaries;
- successful GitHub Actions tests, local fixture demo and cleanup;
- PostgreSQL-focused cases were not falsely reported as executed when the required URL was unavailable;
- no model, schema, migration, fixture, API, repository, command, dependency, CI, UI, release or version change.

PR #89 was squash-merged as `782b2362e1252aa87b21f7aa58f764837f5adb71`. Issue #88 closed completed.

## Current review conclusion

The repository retains deterministic persistence, exact revision/provenance links, cutoff plus UTC chronology, read-only Stage 1/Stage 2 surfaces and no-network fixture discipline.

Neutral ownership now exists for:

- shared Stage 2 frozen-boundary mechanics;
- ordered scalar repository row loading;
- v0.6A-v0.6C pure query-value mechanics.

Remaining risk is evidence read-serialization duplication, command lifecycle/concurrency repetition and ORM event complexity.

## Locked exclusions

- no evidence serializer implementation without accepted characterization;
- no v0.6D query-value policy change;
- no command integrity, revision-lock, model-factory or append-only-listener refactor;
- no application/provider behavior change or migration;
- no v0.6E price or timing judgment;
- no v0.7 Watchlist or verification-task behavior;
- no portfolio, broker, order, recommendation or automated trading behavior;
- no release/tag/version change;
- no modification of PR #38.

## Next development gate

The next candidate is a separate characterization of a neutral evidence read-serialization contract across the v0.6B-v0.6D query modules. It must identify truly invariant claim/evidence fields and ordering while preserving domain-specific boundaries, missing-evidence text, conflicts, collection types and public payloads.

Characterization may conclude that serializers should remain local. It does not authorize implementation. No Codex application implementation command is active after this synchronization.