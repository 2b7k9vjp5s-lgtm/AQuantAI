# Stage 2 Consolidation Characterization

## Status

This is the design record for accepted Stage 2 consolidation work.

- Initial characterization: Issue #74 / PR #75.
- Neutral frozen-boundary implementation: Issue #76 / PR #77.
- Ordered repository row-loading characterization and implementation: Issues #80/#82, PRs #81/#83.
- Query-value characterization and implementation: Issues #86/#88, PRs #87/#89.
- Evidence read-serialization characterization: Issue #92 / PR #93.
- Command integrity characterization and implementation: Issues #96/#98, PRs #97/#99.
- Accepted application/consolidation implementation baseline: `a2688b6e244743ef5e3bdcaedfc6c6717d7a7d8c`.
- Migration decision for all accepted implementation slices: no migration.

This report records completed work and remaining candidates. It does not authorize another implementation.

## Completed neutral boundaries

### Frozen boundary

`industry_alpha.stage2_boundary` owns exact shared v0.6A/v0.6B base-boundary loading, UTC/cutoff visibility and company-research locking used by v0.6C and v0.6D. Domain semantics and revision locks remain local.

### Ordered repository rows

`industry_alpha.stage2_repository_rows.load_ordered_rows` owns only explicit `IN` filtering and caller-owned ordering for scalar row loading. Repository wrappers retain optional-ID normalization, link-field selection, graph assembly, missing-parent policy, sessions and transactions.

### Query values

`industry_alpha.stage2_query_values` owns only the accepted v0.6A-v0.6C required UTC, date-granular visibility and timestamp/date/UUID formatting mechanics. v0.6D query values remain local because malformed-null behavior differs.

### Command integrity translation

`industry_alpha.stage2_integrity.translate_integrity` owns only stateless translation of SQLAlchemy `IntegrityError` into `EvidenceLedgerConflictError` with the exact caller-provided message and the original exception as cause.

The command modules retain conflict-message policy, `session_factory.begin()` transaction ownership, rollback behavior, process-local revision locks, database row locks, latest-revision selection, revision-number/supersession allocation and any future retry policy.

## Reviewed local boundary: evidence read serialization

PR #93 reviewed the v0.6B-v0.6D evidence payload builders. Shared mechanics include evidence-item fields, contradiction projections, A-D grade counts and deterministic sorting. The serializers remain local because:

- v0.6B emits a reduced claim projection and domain-specific missing-evidence text;
- v0.6C/v0.6D currently match more closely, but that equality is not an accepted neutral public contract;
- owner-link fields and source-link container names differ;
- v0.6D preserves independent timestamp-null/error behavior;
- a shared helper would require reflection, callbacks or projection adapters without a demonstrated benefit.

The accepted decision is not deferred implementation. Evidence serializer extraction does not reach Definition of Ready and no implementation Issue follows.

## Acceptance evidence

- PR #77 removed the v0.6D dependency on v0.6C private command helpers.
- PR #83 preserved repository SQL shape, graph behavior and transaction ownership while sharing ordered row loading.
- PR #89 preserved public query payloads and v0.6D edge policy while sharing v0.6A-v0.6C pure query values.
- PR #93 documented the evidence serializer no-extraction decision after comparing exact fields, wording, link ownership and error semantics.
- PR #99 preserved every conflict message, transaction nesting, rollback ownership and lock/allocation behavior while sharing integrity translation.

All accepted implementation slices are source-only and require no database downgrade or data repair. Characterization PRs are docs-only.

## Current classification

| Mechanism | Current decision |
| --- | --- |
| Shared v0.6A/v0.6B frozen boundary | Completed in PR #77 |
| Ordered scalar repository row loading | Completed in PR #83 |
| v0.6A-v0.6C pure query values | Completed in PR #89 |
| SQLAlchemy integrity translation | Completed in PR #99 |
| v0.6D query-value null/error policy | Remains local |
| Repository graph assembly and missing-parent semantics | Remain local |
| Evidence read serialization | Reviewed in PR #93; remains local; no implementation DoR |
| Revision allocation and lock strategy | Next characterization candidate |
| Dynamic model factories | Deferred, ORM-sensitive |
| Append-only listener registration | Deferred, ORM-sensitive |
| Schema and migrations | No change required |

## Remaining candidates

Separate reviewed work may later consider:

1. revision allocation and lock strategy;
2. append-only listener registration and dynamic model construction.

A characterization may conclude that a candidate should remain duplicated. Completed neutral boundaries are not blanket authorization for any remaining item.

Evidence read serialization may be reconsidered only under the triggers recorded in `docs/stage2_evidence_read_characterization.md`.

## Next gate

The next candidate begins with a separate characterization Issue for revision allocation and lock strategy. It must inventory process-local `RLock` registries, database `SELECT ... FOR UPDATE`, latest-revision reads, revision-number and supersession allocation, SQLite behavior, PostgreSQL concurrency evidence, retry policy and lifecycle/cleanup implications before proposing any neutral primitive.

No revision/lock implementation, command retry, evidence serializer extraction, v0.6E, v0.7 or new migration is authorized by this record.