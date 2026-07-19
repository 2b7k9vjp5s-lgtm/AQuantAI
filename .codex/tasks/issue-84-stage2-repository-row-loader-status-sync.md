# Issue #84 - Stage 2 Repository Row-Loader Status Sync

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#84`
- Work type: docs-only architecture/status synchronization
- Base and required ancestor: `e424fa3a95e35b20f5fe8d8ada211821d9661efd`
- Branch: `docs/stage2-repository-row-loader-status-sync`
- Released version remains `0.2.0`.
- Merged capability stage remains v0.6D.

## Objective

Synchronize the architecture record after Issue #80 / PR #81 characterized ordered Stage 2 repository row loading and Issue #82 / PR #83 merged the neutral `load_ordered_rows` implementation.

Remove stale statements that describe ordered repository row loading as prospective or unimplemented.

## Authorized files

- `.codex/tasks/issue-84-stage2-repository-row-loader-status-sync.md`
- `docs/architecture_baseline.md`
- `docs/roadmap.md`
- `docs/review.md`
- `docs/stage2_consolidation_characterization.md`
- `docs/stage2_repository_row_loading_characterization.md`

## Required updates

- Record PR #81 and PR #83 as completed.
- Record accepted application/consolidation implementation baseline `e424fa3a95e35b20f5fe8d8ada211821d9661efd`.
- Mark neutral ordered scalar row loading complete.
- Preserve repository-local `None` normalization, link-field selection, graph assembly and missing-parent semantics.
- Distinguish completed repository mechanics from remaining query, evidence-serialization, command/concurrency and ORM candidates.
- Identify pure query visibility/date/UTC/UUID formatting as the next separately reviewed characterization candidate.
- Keep v0.6E, v0.7, migrations, release and application behavior changes unauthorized.

## Locked exclusions

No application code, tests, fixtures, APIs, contracts, models, repositories, queries, commands, migrations, providers, dependencies, Docker, CI, UI, release metadata, v0.6E, v0.7 or PR #38 changes.

This task does not authorize query utility implementation.

## Validation and stop gate

- Exact six-file inventory.
- No application, test or migration diff.
- Internal status consistency after Issue #84 closes.
- Existing GitHub Actions test and fixture-demo workflow succeeds.
- Open a Draft PR and keep it Open/Draft/unmerged until separate documentation review.
