# Stage 2 Ordered Repository Row-Loading Characterization

## Status

This is the architecture characterization required by Issue #80. It reviews the v0.6A-v0.6D Stage 2 repositories on `main` at `b1c0755acee8f18a618da517217ed401775f1b5a`.

It does not authorize implementation. Released version remains `0.2.0`; merged capability stage remains v0.6D. No migration, schema, API, fixture, query contract or application behavior is changed by this report.

## Executive decision

One neutral primitive is justified for the smallest repeated mechanic:

```text
execute an ordered scalar SELECT for rows whose one mapped field is in an explicit ID collection
```

The primitive must remain deliberately narrow. It must not know about Stage 2 graph structure, identity/revision semantics, required parents, evidence meaning, missing-parent policy, link ownership, cutoff visibility or domain status.

A future first implementation may introduce a neutral Python module, provisionally:

```text
industry_alpha/stage2_repository_rows.py
```

with one operation equivalent to:

```python
load_ordered_rows(session, model, field, ids, *order_fields) -> tuple[Model, ...]
```

The operation must preserve the existing SQLAlchemy shape:

```python
select(model).where(field.in_(ids)).order_by(*order_fields)
```

It returns `()` for an empty collection and otherwise returns `tuple(session.scalars(statement))`.

The helper must not filter `None`, deduplicate IDs, validate missing rows, infer ordering, commit, flush, lock, expire, refresh or open a transaction. Repository-local wrappers retain those decisions.

## Reviewed repositories

| Slice | Repository | Repeated primitive | Local behavior that must remain local |
| --- | --- | --- | --- |
| v0.6A | `stage2_repository.py` | `_rows(model, field, ids, *order)` | large Stage 1/Stage 2 graph assembly, required-parent check, exact handoff and evidence aggregation |
| v0.6B | `stage2_expectations_repository.py` | `_rows(model, field, ids, *order)` | filters `None` IDs before SQL; expectation/valuation graph assembly; optional price provenance |
| v0.6C | `stage2_assessments_repository.py` | `_rows(...)` and `_linked(...)` | catalyst/risk model selection, owning revision field name, assessment graph shape |
| v0.6D | `stage2_judgments_repository.py` | `_rows(...)` and `_linked(...)` | industry/company model selection, fixed `judgment_revision_id`, judgment graph shape |

## Exact shared mechanics

Across the four repository families, the common behavior is:

1. receive an existing SQLAlchemy `Session`;
2. receive one mapped model class;
3. receive one mapped filter field and an explicit collection of IDs;
4. return `()` when the collection presented to the primitive is empty;
5. otherwise execute one scalar `SELECT` using `field.in_(ids)`;
6. apply caller-supplied `ORDER BY` expressions exactly as supplied;
7. materialize results as a tuple;
8. leave transaction and session lifecycle ownership to the caller.

No repository currently raises when an individual requested ID is absent. SQL `IN` semantics omit missing rows. Duplicate requested IDs do not duplicate result rows because the predicate selects table rows, not input positions.

## Important differences

### v0.6B `None` normalization

`Stage2ExpectationRepository._rows` removes `None` values before the empty check and SQL execution. This supports optional `daily_price_id` provenance.

That filtering is repository-local input normalization, not part of the neutral ordered-row primitive. A future implementation must preserve the existing wrapper:

```python
ids = [item for item in ids if item is not None]
return load_ordered_rows(session, model, field, ids, *order)
```

Moving `None` filtering into the neutral helper would silently change the contract for every other caller and obscure why v0.6B needs it.

### Link-field ownership

v0.6C resolves a caller-provided revision-field name and orders by that field plus `model.id`.

v0.6D uses the fixed `model.judgment_revision_id` field and orders by that field plus `model.id`.

The neutral helper may execute those mapped-field expressions, but it must not choose or infer them. Each repository wrapper remains responsible for the correct owning field and ordering.

### Revision and graph loading

Some revision queries are written inline rather than through `_rows`. This report does not require every `SELECT` to use the helper. The first implementation should change only the already repeated private `_rows` and `_linked` mechanics. It must not rewrite repository graph assembly for stylistic consistency.

### Missing required parents

v0.6A and v0.6B perform repository-specific required-parent checks and may return `None` when an identity or required parent is unavailable. v0.6C and v0.6D return `None` when the requested aggregate identity is absent.

The neutral helper must not convert missing rows into exceptions, placeholders or aggregate-level `None` results.

## Contract boundaries

### Inputs

- an existing `Session`;
- a mapped model class;
- an explicit mapped field;
- a concrete ID collection supplied by the repository;
- explicit SQLAlchemy order expressions.

### Output

- a tuple of mapped rows in database order defined by the supplied `ORDER BY` expressions;
- `()` for an empty input collection.

### Non-responsibilities

The primitive does not:

- create or close sessions;
- begin, commit or roll back transactions;
- call `flush`, `expire`, `refresh`, `unique` or `populate_existing`;
- normalize, sort, filter or deduplicate IDs;
- validate complete membership;
- preserve the input ID sequence;
- infer model primary keys or link fields;
- load relationships or graphs;
- apply eager-loading options;
- interpret evidence, status, cutoff or revision semantics;
- translate SQLAlchemy exceptions;
- change repository return types.

## SQL, ordering and database compatibility

The first implementation must retain the exact SQLAlchemy construction already used by the repositories:

```python
select(model).where(field.in_(ids)).order_by(*order_fields)
```

This expression is already exercised on SQLite and PostgreSQL through the existing Stage 2 suites. The neutral helper is a Python source-organization change around the same SQLAlchemy expression.

The helper must require explicit ordering. It must not fall back to primary-key order because deterministic order is part of each repository's read contract and differs by row type.

The helper must not transform IDs into a `set`; doing so would make statement parameter order less inspectable and would add normalization not present in v0.6A, v0.6C or v0.6D.

## First implementation slice

A separate implementation Issue may authorize only:

1. add `industry_alpha/stage2_repository_rows.py` with one neutral `load_ordered_rows` operation;
2. keep all existing repository classes and public methods;
3. change each private `_rows` wrapper to delegate to the neutral operation;
4. change v0.6C and v0.6D private `_linked` wrappers to delegate while retaining local field selection and ordering;
5. retain v0.6B `None` filtering in its private wrapper before delegation;
6. add focused direct compatibility tests for the neutral primitive;
7. run the existing v0.6A-v0.6D SQLite and PostgreSQL suites plus the full offline Actions workflow.

The wrappers should remain so the neutral function is not spread through graph-assembly call sites. This keeps repository ownership visible and minimizes the diff.

## Direct compatibility tests

A focused test module should verify:

1. empty IDs return `()` without issuing a row-select statement;
2. rows are returned in the exact caller-supplied order, independent of input ID order;
3. duplicate IDs do not duplicate rows;
4. missing IDs are omitted without an exception;
5. the helper does not commit or mutate session state;
6. a repository-local wrapper can filter `None` before delegation without putting that policy in the neutral helper.

Existing integration tests remain the main proof that API payloads and graph assembly are unchanged. Existing PostgreSQL Stage 2 tests provide cross-database regression coverage; the direct helper test does not need to duplicate the full graph matrix.

## Golden path

1. a repository owns an open session;
2. it computes exact IDs from already loaded aggregate rows;
3. its local wrapper performs any authorized input normalization, such as v0.6B `None` filtering;
4. it supplies the mapped filter field and deterministic order expressions;
5. the neutral helper executes one scalar ordered query;
6. the repository continues assembling its existing typed graph result;
7. the query service produces an unchanged read-only payload.

## Failure and edge paths

- Empty IDs: return `()`.
- Some IDs absent: return existing rows only.
- Duplicate IDs: each matching table row appears once.
- `None` in v0.6B optional provenance IDs: removed by the existing local wrapper.
- Database error: propagates unchanged; the helper does not translate it.
- Closed or invalid session: existing SQLAlchemy behavior propagates unchanged.

## Explicit exclusions

The first implementation must not:

- create a repository base class or mixin;
- create a generic Stage 2 graph loader;
- change aggregate dataclasses or public repository methods;
- rewrite inline revision queries merely for uniformity;
- add eager loading, joins, subqueries, batching or caching;
- introduce missing-row validation;
- alter required-parent behavior;
- alter ordering expressions;
- filter or deduplicate IDs centrally;
- change evidence serialization or query services;
- change commands, locks, integrity translation or append-only behavior;
- change models, schemas, constraints, migrations or fixtures;
- change APIs, notices or payload ordering;
- introduce v0.6E, v0.7, UI, release or deployment work;
- modify PR #38.

## Migration decision

**No migration.**

The proposed slice changes only Python ownership of an existing read helper. It changes no table, column, constraint, index, foreign key, persisted value, relationship, migration registration or API schema.

## Definition of Ready conclusion

A minimal implementation is ready for a separate Issue because:

- the maintenance problem is bounded;
- the shared mechanic and local policies are distinguished;
- input/output behavior is explicit;
- SQLite/PostgreSQL reachability already exists;
- the golden path and edge behavior are defined;
- no migration is required;
- the implementation can remain one infrastructure change with no domain capability.

This conclusion authorizes only creation and review of a separate implementation Issue. It does not authorize code from Issue #80 itself.
