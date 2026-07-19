# Issue #82 - Stage 2 Ordered Repository Row Loader

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#82`
- Work type: behavior-preserving consolidation implementation
- Accepted characterization: Issue #80 / PR #81
- Base and required ancestor: `25546f7c40b4db1d80229cafef61beb41aaa4345`
- Branch: `refactor/stage2-repository-row-loader`
- Released version remains `0.2.0`.

## Objective

Extract one neutral ordered scalar row-loading primitive while preserving the Stage 2 repositories' existing private wrappers, SQLAlchemy statement shape, deterministic ordering, graph ownership, missing-row behavior and session/transaction ownership.

## Authorized files

- `.codex/tasks/issue-82-stage2-repository-row-loader.md`
- `industry_alpha/stage2_repository_rows.py`
- `industry_alpha/stage2_repository.py`
- `industry_alpha/stage2_expectations_repository.py`
- `industry_alpha/stage2_assessments_repository.py`
- `industry_alpha/stage2_judgments_repository.py`
- `tests/test_stage2_repository_rows.py`

## Required behavior

- `load_ordered_rows(session, model, field, ids, *order_fields)` returns `()` for empty IDs.
- Non-empty IDs use `select(model).where(field.in_(ids)).order_by(*order_fields)`.
- The neutral helper does not sort, filter, normalize or deduplicate IDs.
- Existing private wrapper signatures remain unchanged.
- v0.6B filters `None` locally before delegation.
- v0.6C and v0.6D keep link-field choice and ordering local.
- No commit, rollback, flush, locking, graph assembly or missing-row validation is added.

## Validation

- Direct helper tests cover empty input, caller-supplied ordering, duplicate IDs, missing IDs, transaction ownership and v0.6B local `None` filtering.
- Existing v0.6A-v0.6D SQLite and PostgreSQL coverage remains green.
- Full GitHub Actions tests and local fixture demo succeed.
- No migration.

## Locked exclusions

No repository base class, generic graph loader, public repository contract change, graph rewrite, eager loading, joins, subqueries, batching, caching, central ID normalization, query/command/model/schema/fixture/API/provider/dependency/CI/UI/release change, v0.6E, v0.7 or PR #38 work.

## Stop gate

Open a Draft PR and keep it Open/Draft/unmerged until independent implementation review. Do not start another consolidation candidate from this task.
