# Issue #98 - Stage 2 Integrity Translation

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #98
- Accepted characterization: Issue #96 / PR #97
- Base and required ancestor: `99efcbf0f5f7b8bd7652bd1dd3aef072543a2057`
- Branch: `refactor/stage2-integrity-translation`
- Work type: behavior-preserving consolidation implementation
- Released version remains `0.2.0`; merged capability stage remains v0.6D.
- Migration decision: no migration.

## Objective

Extract one neutral Stage 2 context manager that translates SQLAlchemy `IntegrityError` into `EvidenceLedgerConflictError` without changing caller messages, exception chaining, non-integrity propagation, transaction rollback, revision allocation or concurrency behavior.

## Authorized files

- `.codex/tasks/issue-98-stage2-integrity-translation.md`
- `industry_alpha/stage2_integrity.py`
- `industry_alpha/stage2_commands.py`
- `industry_alpha/stage2_expectations_commands.py`
- `industry_alpha/stage2_assessments_commands.py`
- `industry_alpha/stage2_judgments_commands.py`
- `tests/test_stage2_integrity.py`

## Required implementation

1. Add a stateless `translate_integrity(message)` context manager.
2. Catch only `sqlalchemy.exc.IntegrityError`.
3. Raise `EvidenceLedgerConflictError(message)` from the original exception.
4. Delegate all four command modules through a private alias or equivalent minimal wrapper.
5. Keep every existing conflict message byte-for-byte unchanged.
6. Keep the translator outside `session_factory.begin()` at every call site.
7. Remove only translator-specific imports/classes/methods that become unused.
8. Add direct tests for success, exact message/cause and same-object non-integrity passthrough.

## Validation

- `python -m pytest tests/test_stage2_integrity.py -q`
- `python -m pytest tests/test_stage2_company_research.py tests/test_stage2_expectations_valuation.py tests/test_stage2_catalyst_risk_assessments.py tests/test_stage2_quality_judgments.py -q`
- Run PostgreSQL Stage 2 tests when their required test URL is available; otherwise report them as skipped/not run without claiming success.
- `python -m pytest -q`
- `python -m scripts.demo_research_flow`
- `git diff --check`

## Locked exclusions

No conflict-message change, session/transaction ownership change, explicit rollback/commit, retry, logging, constraint-name parsing, backend branching, revision lock/allocation change, row-lock change, fixture, API, contract, repository, query, model, schema, migration, provider, dependency, CI, UI, release/version change, v0.6E, v0.7 or PR #38 work.

## Stop gate

Push the exact seven-file implementation to this branch and keep the linked PR Draft/Open/unmerged for independent review at a fixed head.
