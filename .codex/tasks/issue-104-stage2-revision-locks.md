# Issue #104 - Stage 2 Revision Locks

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #104
- Accepted characterization: Issue #102 / PR #103
- Base and required ancestor: `6c4bb86964a248502c5f1003fb977a6ae393a4ed`
- Branch: `refactor/stage2-revision-locks`
- Work type: behavior-preserving consolidation implementation
- Released version remains `0.2.0`; merged capability stage remains v0.6D.
- Migration decision: no migration.

## Objective

Extract only the repeated process-local keyed `RLock` registry used by v0.6A-v0.6D append commands without changing database locking, revision allocation, supersession or command nesting.

## Authorized files

- `.codex/tasks/issue-104-stage2-revision-locks.md`
- `industry_alpha/stage2_revision_locks.py`
- `industry_alpha/stage2_commands.py`
- `industry_alpha/stage2_expectations_commands.py`
- `industry_alpha/stage2_assessments_commands.py`
- `industry_alpha/stage2_judgments_commands.py`
- `tests/test_stage2_revision_locks.py`

## Required implementation

1. Add `revision_lock(kind, identity)` backed by a guarded process-local `dict[tuple[str, UUID], RLock]`.
2. Key exactly by `(kind, identity)` and return the same `RLock` object for the same key.
3. Preserve different-key isolation and reentrancy.
4. Import the helper under the existing private `_revision_lock` name in all four command modules.
5. Preserve all kind labels: `research`, `hypothesis`, `expectation`, `valuation`, `catalyst`, `risk`, `industry`, `company`.
6. Preserve every existing lock → integrity translator → `session_factory.begin()` nesting.
7. Remove only the now-unused local `Lock`/`RLock` imports, guards, registries and factory definitions.
8. Add direct tests for same/different keys, reentrancy and two-thread same-key exclusion.

## Validation

- `python -m pytest tests/test_stage2_revision_locks.py -q`
- `python -m pytest tests/test_stage2_company_research.py tests/test_stage2_expectations_valuation.py tests/test_stage2_catalyst_risk_assessments.py tests/test_stage2_quality_judgments.py -q`
- Run PostgreSQL Stage 2 concurrency tests when `TEST_DATABASE_URL` is available; otherwise report skips honestly.
- `python -m pytest -q`
- `python -m scripts.demo_research_flow`
- `git diff --check`

## Locked exclusions

No row-lock or lock-order change, latest-revision query change, revision-number/supersession allocation change, registry cleanup/eviction, retry, constraint parsing, transaction/integrity-message change, fixture, API, model, schema, migration, provider, dependency, CI, release/version, v0.6E, v0.7 or PR #38 work.

## Stop gate

Push the exact seven-file implementation to this branch and keep the linked PR Draft/Open/unmerged for independent fixed-head review.
