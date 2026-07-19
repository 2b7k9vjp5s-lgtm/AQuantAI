# Stage 2 Ordered Repository Row-Loading Characterization

## Status

This is the accepted design and implementation record for ordered Stage 2 repository row loading.

- Characterization: Issue #80 / PR #81.
- Implementation: Issue #82 / PR #83.
- Accepted application/consolidation implementation baseline: `e424fa3a95e35b20f5fe8d8ada211821d9661efd`.
- Released software version remains `0.2.0`.
- Merged capability stage remains v0.6D.
- Migration decision: no migration.

The record does not authorize another implementation.

## Accepted neutral primitive

The smallest repeated mechanic is implemented in:

```text
industry_alpha/stage2_repository_rows.py
```

with:

```python
load_ordered_rows(session, model, field, ids, *order_fields)
```

Its complete responsibility is:

1. return `()` when the supplied ID collection is empty;
2. otherwise execute:

```python
select(model).where(field.in_(ids)).order_by(*order_fields)
```

3. materialize `session.scalars(...)` as a tuple.

The helper does not filter `None`, sort or deduplicate IDs, validate complete membership, infer fields or ordering, preserve input-ID order, load graphs, control transactions or translate exceptions.

## Reviewed repository ownership

| Slice | Repository wrapper | Local behavior retained |
| --- | --- | --- |
| v0.6A | `Stage2CompanyResearchRepository._rows` | Stage 1/Stage 2 graph assembly, required-parent checks, handoff and evidence aggregation |
| v0.6B | `Stage2ExpectationRepository._rows` | filters optional `None` IDs before delegation; expectation/valuation graph assembly and price provenance |
| v0.6C | `_rows` and `_linked` | caller-provided owning revision field, catalyst/risk graph and semantics |
| v0.6D | `_rows` and `_linked` | fixed `judgment_revision_id`, industry/company judgment graph and semantics |

No public repository method or return type changed.

## Preserved behavior

- Empty input returns `()` without executing a row-select query.
- Caller-supplied SQLAlchemy ordering remains exact.
- Duplicate requested IDs do not duplicate table rows.
- Missing IDs are omitted without a new exception.
- v0.6B optional `None` IDs are removed only by its local wrapper.
- Sessions, transactions, autoflush behavior and database exceptions remain owned by existing callers and SQLAlchemy.
- Repository-specific missing-parent and aggregate-level `None` behavior remains unchanged.
- SQLite and PostgreSQL execute the same existing SQLAlchemy expression.

## Direct compatibility evidence

`tests/test_stage2_repository_rows.py` verifies:

1. empty IDs return `()` without a select;
2. explicit ordering is independent of input ID order;
3. duplicate and missing IDs retain SQL `IN` semantics;
4. the helper does not commit caller changes;
5. the v0.6B wrapper keeps `None` filtering local.

Existing v0.6A-v0.6D SQLite and PostgreSQL suites remain the integration proof that graph assembly, query payloads and public behavior are unchanged.

GitHub Actions run `29684076479` completed successfully, including the full test step, local fixture demo and container cleanup.

## Explicit non-responsibilities

The accepted implementation does not:

- create a repository base class or mixin;
- create a generic Stage 2 graph loader;
- rewrite inline revision queries for uniformity;
- add eager loading, joins, subqueries, batching or caching;
- introduce missing-row validation or input-position semantics;
- centralize ID normalization;
- change aggregate dataclasses, queries, commands, models or fixtures;
- change APIs, notices, payload ordering, schemas or migrations;
- introduce v0.6E, v0.7, UI, release or deployment work;
- modify PR #38.

## No-migration decision

The implementation changes only Python ownership of an existing read mechanic. It changes no table, column, constraint, index, foreign key, persisted value, relationship, migration registration or API schema.

## Completion evidence

PR #83 was reviewed at head `080a7202815b1d9bacab11dce16f1f2095bcb5fb` and squash-merged as `e424fa3a95e35b20f5fe8d8ada211821d9661efd`.

Issue #82 closed completed after exact seven-file verification, direct compatibility tests and full workflow success.

## Next gate

Ordered repository row loading is complete and is no longer a prospective candidate.

The next possible activity is a separate characterization of pure query visibility/date/UTC/UUID formatting. That characterization must prove identical visibility, chronology, formatting, ordering, missing-data and database behavior before any implementation Issue is created.

No query implementation is authorized by this record.
