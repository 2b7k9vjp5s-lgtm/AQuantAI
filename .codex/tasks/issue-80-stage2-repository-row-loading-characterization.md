# Issue #80 - Stage 2 Ordered Repository Row-Loading Characterization

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#80`
- Work type: docs-only consolidation characterization
- Base and required ancestor: `b1c0755acee8f18a618da517217ed401775f1b5a`
- Branch: `docs/stage2-repository-row-loading-characterization`
- Released version remains `0.2.0`.

## Objective

Characterize repeated ordered `SELECT ... WHERE field IN (...) ORDER BY ...` mechanics in the v0.6A-v0.6D Stage 2 repositories and decide whether one neutral primitive can be extracted without changing observable behavior or domain ownership.

## Authorized files

- `.codex/tasks/issue-80-stage2-repository-row-loading-characterization.md`
- `docs/stage2_repository_row_loading_characterization.md`

## Required evidence

Review:

- `industry_alpha/stage2_repository.py`;
- `industry_alpha/stage2_expectations_repository.py`;
- `industry_alpha/stage2_assessments_repository.py`;
- `industry_alpha/stage2_judgments_repository.py`;
- existing SQLite and PostgreSQL Stage 2 repository/query integration tests.

The report must distinguish:

- exact shared SQL mechanics;
- repository-local ID normalization;
- repository-local link-field ownership;
- graph assembly and required-parent semantics;
- missing and duplicate ID behavior;
- deterministic ordering and session behavior.

## Required decision

State whether a neutral helper is justified. If justified, define one bounded first implementation slice, exact exclusions, direct compatibility tests and a no-migration decision.

## Locked exclusions

No application code, tests, fixtures, APIs, models, queries, commands, repository implementation, schemas, migrations, providers, dependencies, CI, UI, release metadata, v0.6E, v0.7 or PR #38 changes.

Do not authorize a repository base class, generic graph loader, ORM model factory or unit-of-work abstraction.

## Validation and stop gate

- Exact two-file inventory.
- Internal consistency with the authoritative architecture baseline.
- Existing GitHub Actions test and fixture-demo workflow succeeds.
- Open a Draft PR and keep it Open/Draft/unmerged for separate characterization review.
- This task does not authorize implementation.
