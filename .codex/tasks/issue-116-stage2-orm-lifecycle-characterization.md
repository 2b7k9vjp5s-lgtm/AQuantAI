# Issue #116 - Stage 2 ORM Lifecycle Characterization

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #116
- Base and required ancestor: `e6ffd6a9c94afacdbe0a5475108b6521e30762d6`
- Branch: `docs/stage2-orm-lifecycle-characterization`
- Work type: documentation-only consolidation characterization
- Released version remains `0.2.0`; merged capability remains v0.6D.
- Accepted application/consolidation implementation baseline remains `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.
- Migration decision: no migration.

## Objective

Characterize the SQLAlchemy lifecycle contract around Stage 2 append-only listener registration and dynamic frozen-link mapped-class factories before deciding whether any neutral implementation reaches Definition of Ready.

This task does not authorize ORM, model, listener, factory, import, test, schema or migration changes.

## Exact authorized files

1. `.codex/tasks/issue-116-stage2-orm-lifecycle-characterization.md`
2. `docs/stage2_orm_lifecycle_characterization.md`

Do not modify any other path.

## Required inventory

Inspect, but do not edit:

- `industry_alpha/stage2_models.py`;
- `industry_alpha/stage2_expectations_models.py`;
- `industry_alpha/stage2_assessments_models.py`;
- `industry_alpha/stage2_judgments_models.py`;
- `backend/database/models.py`;
- `migrations/env.py`;
- runtime, fixture and test imports that register these modules;
- SQLite and PostgreSQL Stage 2 tests covering append-only behavior, rollback, metadata and migration compatibility.

Record exact evidence for:

- the four global `Session.before_flush` listeners, their function identities, model tuples and error behavior;
- all dynamically generated v0.6C/v0.6D link classes, exact class/table counts and owning module globals;
- the single shared `Base.metadata` and Alembic v0.6A-to-v0.6D import order;
- normal repeated imports, explicit reload sensitivity, partial/different import order and test-process isolation;
- duplicate listener invocation risk and dynamic mapper/table recreation risk;
- global `Session` target behavior versus configured sessionmaker/custom Session usage;
- dirty-but-unmodified, materially dirty, deleted and pending object handling;
- exact `EvidenceLedgerImmutableError` class, message shape and failure timing;
- SQLite/PostgreSQL behavior and environment limitations;
- resolved SQLAlchemy version in the validation environment when available.

## Bounded diagnostics

Ephemeral Python/pytest diagnostics are allowed only to observe current behavior. Do not commit diagnostic scripts, snapshots, generated files or test changes. Do not mutate persistent user data.

Diagnostics must fail safely and should cover, where practical:

1. `event.contains` or equivalent listener-registration evidence;
2. listener count/invocation behavior under ordinary repeated imports;
3. explicit module reload outcome without suppressing warnings/errors;
4. mapped-class/table identity and `Base.metadata` stability;
5. Alembic metadata completeness under the supported import sequence;
6. append-only insert/update/delete behavior through current session factories.

Do not normalize away or hide warnings. Distinguish supported normal import behavior from unsupported explicit reload experiments.

## Required report

Create `docs/stage2_orm_lifecycle_characterization.md` with:

1. status, base and no-implementation authority statement;
2. module/import-path matrix;
3. listener matrix: target, function, registration trigger, model tuple, message and current tests;
4. dynamic model matrix: factory, generated names/counts, table/constraint/index/FK identity and registration path;
5. existing SQLite/PostgreSQL test evidence;
6. bounded diagnostic commands and exact observed results;
7. import/reload, mapper/metadata and test-isolation findings;
8. classification of each candidate as:
   - safe to extract without schema/behavior change;
   - shareable only after an explicit neutral contract;
   - domain-specific and required to remain local;
   - deferred because ORM/event/schema/compatibility risk is too high;
9. one explicit decision:
   - a single bounded later implementation candidate, or
   - no implementation reaches DoR;
10. exact later-slice contract and file family only if DoR is reached;
11. migration, dependency and rollback decisions;
12. explicit non-goals.

Do not presume that listener consolidation and dynamic model-factory consolidation belong in one implementation slice. A keep-local decision is valid.

## Definition of Ready gate

A later implementation may be proposed only if the report proves:

- one exact neutral owner and bounded public contract;
- listener registration identity/idempotency rules;
- unchanged mapped-class, table and metadata identity;
- unchanged supported import and Alembic registration behavior;
- unchanged exception class, message and timing;
- a bounded SQLite/PostgreSQL compatibility matrix;
- no migration or persisted-schema change;
- rollback by source reversion with no data repair.

If any item is unsupported, ambiguous or dependent on explicit reload behavior, stop with no implementation DoR or propose a smaller characterization/test prerequisite.

## Validation

Run and report:

- exact two-file base-to-head diff;
- `python -m pytest -q`;
- `python -m scripts.demo_research_flow`;
- `git diff --check`;
- GitHub Actions on the fixed head;
- PostgreSQL tests only when the required environment is available, with skips reported honestly.

## Locked exclusions

No ORM/model/listener/factory implementation, import rewiring, test or fixture change, database/schema/migration, Alembic revision, dependency, API/runtime behavior, provider/Hithink/AKShare change, canonical-price work, release/version, v0.6E, v0.7 or PR #38 work.

## Stop gate

Push exactly the two authorized files to a linked Draft PR. Keep it Draft/Open/unmerged for independent fixed-head review. Return the fixed head SHA, exact file list, validation results, diagnostic limitations and the report's DoR/no-DoR decision. Do not create an implementation Issue.