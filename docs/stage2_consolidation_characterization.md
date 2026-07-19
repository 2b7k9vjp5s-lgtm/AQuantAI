# Stage 2 Consolidation Characterization

## Status

This is the design record for accepted Stage 2 consolidation work.

- Initial characterization: Issue #74 / PR #75.
- Neutral frozen-boundary implementation: Issue #76 / PR #77.
- Ordered repository row-loading characterization: Issue #80 / PR #81.
- Neutral ordered row-loader implementation: Issue #82 / PR #83.
- Accepted application/consolidation implementation baseline: `e424fa3a95e35b20f5fe8d8ada211821d9661efd`.
- Migration decision for both implementations: no migration.

The report records completed work and remaining candidates. It does not authorize another implementation.

## Completed dependency correction

Before PR #77, v0.6D quality-judgment commands imported shared private mechanics from the v0.6C catalyst/risk command module.

The accepted direction is:

```text
industry_alpha.stage2_boundary
  <- v0.6C catalyst/risk commands
  <- v0.6D quality-judgment commands
```

`industry_alpha.stage2_boundary` owns exact shared v0.6A/v0.6B base-boundary loading, UTC/cutoff visibility and company-research locking. Catalyst/risk and judgment semantics, revision locks and conflict translation remain local.

## Completed repository mechanic

PR #83 added:

```text
industry_alpha.stage2_repository_rows.load_ordered_rows
```

The neutral primitive owns only:

```python
select(model).where(field.in_(ids)).order_by(*order_fields)
```

It returns `()` for empty IDs and otherwise materializes the caller-owned ordered scalar query as a tuple.

Repository-local responsibilities remain unchanged:

- v0.6B filters optional `None` IDs before delegation;
- v0.6C selects its caller-provided owning revision field;
- v0.6D selects `judgment_revision_id`;
- every repository owns graph assembly, required-parent and missing-row policy;
- sessions, transactions, exceptions and public repository methods remain local.

The extraction did not introduce a repository base class, generic graph loader, eager loading, joins, caching or input-order semantics.

## Acceptance evidence

### Frozen-boundary slice

PR #77 established:

- one immutable `Stage2BaseBoundary` used by v0.6C and v0.6D;
- removal of the v0.6D dependency on v0.6C private command helpers;
- unchanged command behavior, validation, APIs, fixtures and Alembic metadata;
- successful full Actions tests and local fixture demo.

### Ordered-row slice

PR #83 established:

- one stateless `load_ordered_rows` helper;
- existing private v0.6A-v0.6D wrappers retained;
- unchanged SQL shape and ordering expressions;
- direct tests for empty input, duplicate IDs, missing IDs, explicit ordering, transaction ownership and local `None` filtering;
- unchanged graph assembly, public repository methods and read payloads;
- successful full Actions tests, PostgreSQL regressions and local fixture demo.

Both slices are source-only and require no database downgrade or data repair.

## Current classification

| Mechanism | Current decision |
| --- | --- |
| Shared v0.6A/v0.6B frozen boundary | Completed in PR #77 |
| UTC and visibility helpers required by that boundary | Completed in PR #77 |
| Ordered scalar repository row loading | Completed in PR #83 |
| Repository graph assembly and missing-parent semantics | Remain local |
| v0.6B optional-ID normalization | Remains local |
| v0.6C and v0.6D domain semantics | Remain local |
| Generic evidence graph repository | Not justified |
| Pure query visibility/date/UTC/UUID formatting | Next characterization candidate |
| Evidence read serialization | Requires a neutral contract |
| Integrity translation | Deferred |
| Revision allocation and lock strategy | Deferred |
| Dynamic model factories | Deferred, ORM-sensitive |
| Append-only listener registration | Deferred, ORM-sensitive |
| Schema and migrations | No change required |

## Remaining candidates

Separate reviewed work may later consider:

1. pure query cutoff/recorded visibility and date/UTC/UUID formatting;
2. a neutral evidence read contract;
3. conflict and integrity primitives;
4. revision allocation and lock strategy;
5. append-only listener registration and dynamic model construction.

A characterization may conclude that a candidate should remain duplicated. Completion of PR #77 or PR #83 is not blanket authorization for any remaining item.

## Next gate

The next candidate begins with a separate characterization Issue for pure query visibility/date/UTC/UUID formatting. It must inventory exact existing functions and prove identical chronology, formatting, ordering, missing-data and cross-database behavior.

No query implementation, v0.6E, v0.7 or new migration is authorized by this record.
