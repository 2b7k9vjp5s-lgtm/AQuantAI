# Review Log

GitHub Issues and pull-request reviews are authoritative. `docs/architecture_baseline.md` owns the current architecture interpretation.

## Current status

- Review date: 2026-07-19
- Released software version: `0.2.0`
- Merged capability stage: v0.6D
- Accepted application/consolidation implementation baseline: `e424fa3a95e35b20f5fe8d8ada211821d9661efd`
- Runtime surfaces: local fixture-backed read-only Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured
- Most recent architecture synchronization: Issue #84 and its linked synchronization PR
- Active application or consolidation implementation authorization: none
- New migration authorization: none

Docs-only commits may advance `main` without changing release, capability or runtime state.

## Accepted architecture decisions

- Issue #70 and PR #71 for v0.6E price judgment were closed without merge. No price-judgment model, migration, API or runtime behavior exists.
- Issue #72 and PR #73 established the unified baseline, ownership, invariants, architecture debt and delivery gates.
- Issue #74 and PR #75 characterized Stage 2 infrastructure.
- Issue #76 and PR #77 moved shared exact v0.6A/v0.6B frozen-boundary mechanics to `industry_alpha.stage2_boundary` and removed the v0.6D dependency on v0.6C private helpers.
- Issue #78 and PR #79 synchronized that first consolidation result.

## Ordered repository row-loader acceptance

Issue #80 and PR #81 characterized repeated ordered scalar row loading across v0.6A-v0.6D repositories.

The accepted design shares only:

```text
select(model).where(field.in_(ids)).order_by(*order_fields)
```

Repository-local ownership remains for:

- v0.6B optional-ID `None` filtering;
- v0.6C/v0.6D link-field selection;
- graph assembly and required-parent behavior;
- missing-row policy;
- session and transaction lifecycle.

Issue #82 and PR #83 implemented `industry_alpha.stage2_repository_rows.load_ordered_rows`.

Independent review confirmed:

- exact seven-file inventory;
- unchanged public repository methods, graph results and ordering expressions;
- direct coverage for empty input, duplicate IDs, missing IDs, explicit ordering, transaction ownership and local `None` filtering;
- successful full Actions tests, PostgreSQL regressions and local fixture demo;
- no model, schema, migration, fixture, API, query, command, dependency, CI, UI or release change.

PR #83 was squash-merged as `e424fa3a95e35b20f5fe8d8ada211821d9661efd`. Issue #82 closed completed.

## Current review conclusion

The repository retains deterministic persistence, exact revision/provenance links, cutoff plus UTC chronology, read-only Stage 1/Stage 2 surfaces, SQLite/PostgreSQL validation and no-network fixture discipline.

Neutral ownership now exists for:

- shared Stage 2 frozen-boundary mechanics;
- ordered scalar repository row loading.

Remaining risk is query/read serialization duplication, command lifecycle/concurrency repetition and ORM event complexity.

## Locked exclusions

- no query utility implementation without accepted characterization;
- no evidence serializer unification;
- no command integrity, revision-lock, model-factory or append-only-listener refactor;
- no application/provider behavior change or migration;
- no v0.6E price or timing judgment;
- no v0.7 Watchlist or verification-task behavior;
- no portfolio, broker, order, recommendation or automated trading behavior;
- no release/tag/version change;
- no modification of PR #38.

## Next development gate

The next candidate is a separate characterization of pure query visibility/date/UTC/UUID formatting. It must prove identical cutoff and recorded visibility, datetime normalization, output formatting, UUID/payload ordering, missing-data behavior and SQLite/PostgreSQL compatibility.

Characterization does not authorize implementation. No Codex application implementation command is active after this synchronization.
