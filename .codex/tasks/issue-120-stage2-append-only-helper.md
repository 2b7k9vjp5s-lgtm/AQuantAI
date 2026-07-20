# Issue #120 - Stage 2 Append-Only Mutation Helper

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #120
- Base and required ancestor: `e0644de3ea7c3afaeba8da483fef800c2c90f197`
- Branch: `refactor/stage2-append-only-helper`
- Work type: source-only consolidation implementation
- Released version remains `0.2.0`; merged capability remains v0.6D.
- Accepted application/consolidation implementation baseline remains `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.
- Migration, schema, dependency and data-repair decision: no change.

## Objective

Extract only the repeated Stage 2 append-only mutation scan into a neutral pure helper after the accepted Issue #118 / PR #119 lifecycle compatibility matrix.

Keep every event decorator, listener function identity, registration module, model tuple, mapped class and dynamic factory in its current domain module.

## Exact authorized files

1. `.codex/tasks/issue-120-stage2-append-only-helper.md`
2. `industry_alpha/orm_append_only.py`
3. `industry_alpha/stage2_models.py`
4. `industry_alpha/stage2_expectations_models.py`
5. `industry_alpha/stage2_assessments_models.py`
6. `industry_alpha/stage2_judgments_models.py`
7. `tests/test_stage2_orm_lifecycle_contract.py`

Do not modify any other path.

## Helper contract

Create `industry_alpha/orm_append_only.py` with one public function:

```python
reject_append_only_mutation(session, model_types) -> None
```

The function must:

1. iterate `session.deleted` before `session.dirty`;
2. use `isinstance(row, model_types)`;
3. raise the existing `EvidenceLedgerImmutableError` directly for matching deleted rows with:
   `<ClassName> rows are append-only and cannot be deleted.`;
4. for matching dirty rows, call `session.is_modified(row, include_collections=False)`;
5. raise the same exact error class directly for material updates with:
   `<ClassName> rows are append-only and cannot be updated.`;
6. return `None` when no prohibited mutation is present.

The helper must not register events, import a Stage 2 model module, own a model tuple, create or own an engine/sessionmaker/mapper/metadata/registry, catch or wrap the immutable error, or inspect Core DML.

## Domain listener changes

For each of the four Stage 2 model modules:

- preserve the current `@event.listens_for(Session, "before_flush")` decorator;
- preserve the current listener function name, module and signature;
- preserve the local tuple object and order exactly;
- replace only the repeated delete/dirty loops with one call to `reject_append_only_mutation(session, LOCAL_TUPLE)`;
- remove only imports made unused by that body replacement;
- make no mapped-class, table, constraint, index, FK, factory or generated-global change.

## Focused tests

Extend only `tests/test_stage2_orm_lifecycle_contract.py` to prove the neutral helper itself:

- returns `None` for no matching mutation and for a dirty-but-unmodified row;
- raises the exact class and exact class-derived update/delete messages;
- inspects deletion before dirty state when both contain matching rows;
- has no SQLAlchemy event-registration side effect;
- imports no Stage 2 model module and owns no model tuple.

Do not weaken or replace the existing lifecycle matrix.

## Validation

Report honestly:

- exact seven-file base-to-head diff;
- focused lifecycle/helper tests;
- `python -m pytest -q`;
- `python -m scripts.demo_research_flow`;
- `git diff --check` or equivalent whitespace inspection;
- GitHub Actions on the fixed head with PostgreSQL service;
- warnings and skips without reclassification.

## Rollback

Source revert only: restore the four previous local loop bodies and remove the neutral helper/imports. No schema or data repair is required.

## Locked exclusions

No listener relocation/rename, decorator/event-target change, tuple relocation/change, dynamic factory or generated-global change, database trigger, Core-DML interception, existing fixture edit, schema/migration/Alembic revision, dependency, API/runtime behavior, provider/Hithink/AKShare, canonical-price work, release/version, v0.6E, v0.7 or PR #38 work.

## Stop gate

Push exactly the seven authorized files to a linked Draft PR. Keep it Draft/Open/unmerged for independent fixed-head review. Do not start another work item in the same PR.
