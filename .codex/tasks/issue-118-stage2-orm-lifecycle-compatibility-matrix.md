# Issue #118 - Stage 2 ORM Lifecycle Compatibility Matrix

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #118
- Base and required ancestor: `2fb24eadf7285000fdb0c2ef7ebc1d84f87c8908`
- Branch: `tests/stage2-orm-lifecycle-contract`
- Work type: test-only consolidation prerequisite
- Released version remains `0.2.0`; merged capability remains v0.6D.
- Accepted application/consolidation implementation baseline remains `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.
- Migration decision: no migration.

## Objective

Commit the compatibility matrix required by the accepted ORM lifecycle characterization before deciding whether a pure Stage 2 append-only mutation-scan helper reaches Definition of Ready.

This task does not authorize the helper or any production ORM/model/listener/factory/import implementation.

## Exact authorized files

1. `.codex/tasks/issue-118-stage2-orm-lifecycle-compatibility-matrix.md`
2. `tests/test_stage2_orm_lifecycle_contract.py`
3. `tests/test_stage2_orm_lifecycle_contract_postgres.py`
4. `docs/stage2_orm_lifecycle_characterization.md`

Do not modify any other path, including existing tests and fixtures.

## Non-PostgreSQL contract

Create `tests/test_stage2_orm_lifecycle_contract.py` using public SQLAlchemy/Python APIs where possible. Isolate process-global import/invocation probes in clean subprocesses.

The tests must fix these current contracts:

- the four current listener function objects are registered on global `sqlalchemy.orm.Session` through `event.contains`;
- repeated ordinary `importlib.import_module()` preserves module, listener, mapped-class, table and shared `Base.metadata` identity;
- repeated ordinary imports do not cause multiple invocation of any Stage 2 listener during one flush in a clean subprocess;
- exact model tuple sizes remain 11, 10, 14 and 18;
- the supported import path exposes exactly 53 `stage2_` tables;
- the existing eight v0.6C and twelve v0.6D generated link-class globals retain their exact class names, table names and shared metadata identity;
- the configured session factory and a custom `Session` subclass receive append-only behavior;
- accepted pending inserts and dirty-but-materially-unmodified rows remain allowed;
- representative v0.6A-v0.6D material updates/deletes fail at flush with exact `EvidenceLedgerImmutableError` class and current message shape;
- rollback preserves original rows and values.

Use existing deterministic fixture builders. Do not add or modify fixtures.

Do not add an explicit `importlib.reload()` regression test. Reload is unsupported and can perturb process-global declarative state. Do not lock direct Core DML bypass as a desired contract. Production code must not depend on private SQLAlchemy dispatch internals.

## PostgreSQL contract

Create `tests/test_stage2_orm_lifecycle_contract_postgres.py` using the existing `TEST_DATABASE_URL` safety convention and Alembic-managed test schema.

- refuse a database whose name does not contain `test`;
- downgrade/upgrade and cleanup only the authorized test database;
- build accepted deterministic Stage 2 rows through existing fixtures;
- exercise representative v0.6A, v0.6B, v0.6C and v0.6D rows through the current ORM session factory;
- verify material update and delete failures use the exact immutable error class/message and rollback preserves stored rows;
- skip honestly when `TEST_DATABASE_URL` is absent;
- preserve existing migration, fixture and concurrency behavior.

Do not add a migration, schema change, database trigger or production guard.

## Documentation decision

Update `docs/stage2_orm_lifecycle_characterization.md` with:

- accepted PR #117 merge `2fb24eadf7285000fdb0c2ef7ebc1d84f87c8908`;
- the committed compatibility matrix and exact file scope;
- observed local and CI/PostgreSQL results and limitations;
- one explicit decision after the tests exist:
  1. the pure mutation-scan helper reaches Definition of Ready as one later source-only candidate, with exact neutral owner, contract and file family; or
  2. no implementation reaches DoR, with remaining blockers.

Even if DoR is reached, do not implement the helper and do not create its implementation Issue.

Dynamic mapped-class factories, generated class globals, model tuples and all four listener decorators remain domain-local.

## Validation

Run and report:

- exact four-file base-to-head diff;
- `python -m pytest -q`;
- `python -m scripts.demo_research_flow`;
- `git diff --check`;
- GitHub Actions on the fixed head, including PostgreSQL service results;
- all warnings/skips honestly.

## Locked exclusions

No production ORM/model/listener/factory/helper/import code, existing test or fixture edit, database/schema/migration/Alembic revision, dependency, API/runtime behavior, provider/Hithink/AKShare, canonical-price work, release/version, v0.6E, v0.7 or PR #38 work.

## Stop gate

Push exactly the four authorized files to a linked Draft PR. Keep it Draft/Open/unmerged for independent fixed-head review. Return the fixed head SHA, exact file list, local and CI results, PostgreSQL evidence/limitations and the documentation DoR/no-DoR decision. Do not create a production implementation Issue.
