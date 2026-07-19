# Stage 2 Consolidation Characterization

## Status

This is the design record for accepted Stage 2 consolidation work.

- Initial characterization: Issue #74 / PR #75.
- Neutral frozen-boundary implementation: Issue #76 / PR #77.
- Ordered repository row-loading characterization and implementation: Issues #80/#82, PRs #81/#83.
- Query-value characterization and implementation: Issues #86/#88, PRs #87/#89.
- Accepted application/consolidation implementation baseline: `782b2362e1252aa87b21f7aa58f764837f5adb71`.
- Migration decision for all accepted consolidation implementations: no migration.

This report records completed work and remaining candidates. It does not authorize another implementation.

## Completed neutral boundaries

### Frozen boundary

`industry_alpha.stage2_boundary` owns exact shared v0.6A/v0.6B base-boundary loading, UTC/cutoff visibility and company-research locking used by v0.6C and v0.6D. Catalyst/risk and judgment semantics, revision locks and conflict translation remain local.

### Ordered repository rows

`industry_alpha.stage2_repository_rows.load_ordered_rows` owns only explicit `IN` filtering and caller-owned ordering for scalar row loading. Repository wrappers retain optional-ID normalization, link-field selection, graph assembly, missing-parent policy, sessions, transactions and public methods.

### Query values

`industry_alpha.stage2_query_values` owns only the accepted v0.6A-v0.6C pure mechanics:

- required UTC normalization with the exact missing-timestamp visibility error;
- naive/aware datetime conversion to UTC;
- date-granular recorded and information-date visibility;
- trailing-`Z` timestamp text;
- optional date and UUID text.

v0.6B/v0.6C revision collection wrappers remain local. v0.6D query values remain local because malformed-null behavior differs. Evidence payload construction, grade counts, conflicts, missing-evidence text, claim/link selection, ID sorting, notices, aggregate errors and public contracts remain local.

## Acceptance evidence

PR #77 established the neutral frozen boundary and removed the v0.6D dependency on v0.6C private command helpers.

PR #83 established the stateless ordered-row primitive while preserving SQL shape, graph behavior and transaction ownership.

PR #89 established the v0.6A-v0.6C pure query-value module while preserving public query payloads and the v0.6D edge policy. Direct tests cover exact errors, UTC conversion, formatting and cutoff boundaries. GitHub Actions tests and the local fixture demo passed. PostgreSQL-focused cases were not claimed as executed where the required URL was unavailable.

All three slices are source-only and require no database downgrade or data repair.

## Current classification

| Mechanism | Current decision |
| --- | --- |
| Shared v0.6A/v0.6B frozen boundary | Completed in PR #77 |
| Ordered scalar repository row loading | Completed in PR #83 |
| v0.6A-v0.6C pure query values | Completed in PR #89 |
| v0.6D query-value null/error policy | Remains local |
| Repository graph assembly and missing-parent semantics | Remain local |
| Evidence read serialization | Next characterization candidate; requires a neutral contract |
| Generic evidence graph repository | Not justified |
| Command conflict/integrity translation | Deferred |
| Revision allocation and lock strategy | Deferred |
| Dynamic model factories | Deferred, ORM-sensitive |
| Append-only listener registration | Deferred, ORM-sensitive |
| Schema and migrations | No change required |

## Remaining candidates

Separate reviewed work may later consider:

1. a neutral evidence read-serialization contract;
2. command conflict and integrity primitives;
3. revision allocation and lock strategy;
4. append-only listener registration and dynamic model construction.

A characterization may conclude that a candidate should remain duplicated. Completed neutral boundaries are not blanket authorization for any remaining item.

## Next gate

The next candidate begins with a separate characterization Issue for evidence read serialization across v0.6B-v0.6D. It must inventory exact claim/evidence fields, lookup dependencies, ordering, conflict/missing projections, domain-specific text and collection types. It must define whether a neutral input/output contract can exist without weakening domain ownership, and it may conclude that no extraction is safe.

No evidence serializer implementation, v0.6E, v0.7 or new migration is authorized by this record.