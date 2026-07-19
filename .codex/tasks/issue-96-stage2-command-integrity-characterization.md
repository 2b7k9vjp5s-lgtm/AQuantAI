# Issue #96 - Stage 2 Command Integrity Characterization

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #96
- Base and required ancestor: `03756aa7009c738e4c183845fbb8eb9e09906663`
- Branch: `docs/stage2-command-integrity-characterization`
- Work type: architecture characterization only
- Released version remains `0.2.0`; merged capability stage remains v0.6D.

## Objective

Compare v0.6A-v0.6D command-side SQLAlchemy `IntegrityError` translation and decide whether one neutral context manager can remove duplication without changing rollback ownership, caller messages, exception chaining, revision allocation or concurrency behavior.

## Authorized files

- `.codex/tasks/issue-96-stage2-command-integrity-characterization.md`
- `docs/stage2_command_integrity_characterization.md`

## Required analysis

1. Inventory each command helper and call site.
2. Preserve exact caller-owned conflict messages.
3. Preserve the original `IntegrityError` as `__cause__`.
4. Preserve every non-`IntegrityError` unchanged.
5. Keep `session_factory.begin()` responsible for commit and rollback.
6. Keep locks, `SELECT ... FOR UPDATE`, revision allocation and link atomicity local.
7. Define direct helper and existing integration test evidence.
8. State the no-migration decision and whether implementation reaches Definition of Ready.

## Locked exclusions

No application implementation, test edit, fixture, API, contract, repository, query, model, schema, migration, provider, dependency, CI, UI, release/version change, revision-lock refactor, revision allocation change, v0.6E, v0.7 or PR #38 work.

## Stop gate

Open a Draft PR and keep it unmerged until independent characterization review. Characterization does not authorize implementation.
