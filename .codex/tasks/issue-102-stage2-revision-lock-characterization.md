# Issue #102 - Stage 2 Revision Lock Characterization

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #102
- Base and required ancestor: `46ee0f78908cbdff3a611ed158f43cb17fa28f8d`
- Branch: `docs/stage2-revision-lock-characterization`
- Work type: architecture characterization only
- Released version remains `0.2.0`; merged capability stage remains v0.6D.

## Objective

Separate repeated same-process keyed `RLock` mechanics from database row locking and revision allocation, then decide whether a minimal neutral extraction reaches Definition of Ready.

## Authorized files

- `.codex/tasks/issue-102-stage2-revision-lock-characterization.md`
- `docs/stage2_revision_lock_characterization.md`

## Required analysis

1. Inventory each `_revision_lock` implementation and all kind labels.
2. Preserve exact append nesting and caller-owned messages.
3. Inventory identity/research `SELECT ... FOR UPDATE`, latest-revision reads, `revision_no + 1`, supersession and unique constraints.
4. Distinguish same-process `RLock` behavior from PostgreSQL row-lock behavior and SQLite limitations.
5. Assess reentrancy, key collisions, registry lifetime and module isolation.
6. Define bounded direct tests and existing integration evidence.
7. State the no-migration decision and separate DoR conclusions for process locks versus allocation/row locks.

## Locked exclusions

No application implementation, test edit, fixture, API, command, model, schema, migration, dependency, CI, release/version, retry policy, row-lock change, revision-number/supersession change, v0.6E, v0.7 or PR #38 work.

## Stop gate

Open a Draft PR and keep it unmerged until independent characterization review. Characterization does not authorize implementation.
