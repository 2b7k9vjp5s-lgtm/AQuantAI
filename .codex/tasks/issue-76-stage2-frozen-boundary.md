# Issue #76 - Extract Neutral Stage 2 Frozen Boundary

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#76`
- Work type: consolidation/refactoring implementation
- Base and required ancestor: `3119f44052a1250cfaced00509c85559bb101ed6`
- Branch: `refactor/stage2-frozen-boundary`
- Draft PR: `[Consolidation] Extract neutral Stage 2 frozen boundary`
- Released version remains `0.2.0`.

## Objective

Move the exact v0.6A/v0.6B frozen-boundary mechanics currently owned by v0.6C into a neutral Stage 2 module, then make v0.6C and v0.6D consume that same contract without changing behavior.

## Authorized files

- `.codex/tasks/issue-76-stage2-frozen-boundary.md`
- `industry_alpha/stage2_boundary.py`
- `industry_alpha/stage2_assessments_commands.py`
- `industry_alpha/stage2_judgments_commands.py`
- `tests/test_stage2_boundary.py`

## Required implementation

- Add immutable `Stage2BaseBoundary`.
- Extract exact unique upstream loading, company-research locking, stored UTC normalization, cutoff visibility, command time boundary, required text validation, and v0.6A/v0.6B boundary construction.
- Preserve the existing validation messages and SQL locking shape.
- Keep a v0.6C `_Boundary` compatibility alias for existing internal tests.
- Remove every v0.6D import from `stage2_assessments_commands.py`.
- Keep catalyst/risk and judgment semantics local.

## Locked exclusions

No model, schema, migration, repository, query, API, contract, fixture, demo, provider, dependency, Docker, CI, UI, version, v0.6E, v0.7, PR #38, revision-lock, revision-allocation, or append-only-listener change.

## Validation

- focused neutral-boundary tests;
- existing v0.6C/v0.6D SQLite and PostgreSQL suites;
- full `python -m pytest -q`;
- `python -m scripts.demo_research_flow`;
- exact five-file diff;
- no Alembic or metadata change;
- GitHub Actions success.

## Stop gate

Open a Draft PR, synchronize evidence, and stop for separate implementation review. Do not merge from this task.
