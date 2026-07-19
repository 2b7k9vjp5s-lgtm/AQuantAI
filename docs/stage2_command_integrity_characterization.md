# Stage 2 Command Integrity Translation Characterization

## Status

Issue #96 / PR #97 characterized v0.6A-v0.6D command-side SQLAlchemy integrity translation. Issue #98 / PR #99 implemented the accepted neutral helper.

- Accepted characterization base: `03756aa7009c738e4c183845fbb8eb9e09906663`.
- Accepted implementation head: `b0dc58b2adb27e9a6ec6f1a2dce3699bd2bab9ff`.
- Accepted implementation baseline: `a2688b6e244743ef5e3bdcaedfc6c6717d7a7d8c`.
- Released version remains `0.2.0`; capability stage remains v0.6D.
- Migration decision: no migration.

## Reviewed scope

The review compared:

- `industry_alpha/stage2_commands.py`;
- `industry_alpha/stage2_expectations_commands.py`;
- `industry_alpha/stage2_assessments_commands.py`;
- `industry_alpha/stage2_judgments_commands.py`;
- corresponding SQLite atomicity tests;
- corresponding PostgreSQL concurrency and rollback tests.

Revision locking and allocation were inspected only to preserve their boundary. They were not changed by PR #99.

## Accepted behavior

All four command modules keep this nesting:

```text
integrity translator
  -> session_factory.begin()
       -> validation, identity/revision/link writes and flushes
```

The transaction context exits first. SQLAlchemy therefore rolls back a database integrity failure before the outer translator maps the exception.

`industry_alpha.stage2_integrity.translate_integrity(message)` now owns exactly this contract:

1. enter without changing transaction or session state;
2. allow successful execution to return normally;
3. catch only `sqlalchemy.exc.IntegrityError`;
4. raise `EvidenceLedgerConflictError` with the caller-provided message;
5. retain the original `IntegrityError` through `raise ... from exc`;
6. propagate all other exception types unchanged;
7. perform no explicit commit, rollback, retry, logging or constraint inspection.

## Caller-owned policy

Conflict wording remains command and operation specific, including duplicate identity keys, revision conflicts and verification-item conflicts.

The neutral helper accepts the exact message as an argument. It does not infer operation names, parse constraint names, normalize text or branch by database backend.

The existing broad mapping of any `IntegrityError` inside the bounded transaction is preserved.

## Transaction and rollback ownership

`session_factory.begin()` remains the sole owner of:

- opening and closing the session;
- commit on success;
- rollback on validation or database failure;
- expiring/closing transaction state.

The neutral helper remains outside the transaction context at every call site. It does not receive a session, call `rollback()`, retry work or suppress an exception.

Existing SQLite tests remain the evidence for atomic rollback. Existing PostgreSQL tests remain the evidence for deterministic concurrent revision allocation where the required database environment is available; they are not helper responsibilities.

## Options evaluated

### Keep four local helpers

Safe but unnecessarily duplicated. The prior bodies encoded no domain policy beyond a caller-supplied string.

### One neutral context manager

Accepted and implemented in PR #99 as the smallest safe slice.

### Constraint-aware conflict classification

Rejected. Constraint names and driver payloads differ across SQLite and PostgreSQL and would change the current compatibility boundary.

### Combine translation with revision locks or retries

Rejected. Process-local `RLock`, database row locks, revision-number allocation, supersession and retry policy have separate concurrency semantics and require independent characterization.

## Implementation acceptance

PR #99 changed exactly:

- `.codex/tasks/issue-98-stage2-integrity-translation.md`;
- `industry_alpha/stage2_integrity.py`;
- the four Stage 2 command modules;
- `tests/test_stage2_integrity.py`.

Independent fixed-head review confirmed exact caller messages, original-cause chaining, same-object non-integrity passthrough and unchanged transaction/lock/allocation behavior. Actions `29687524781`, full tests and the fixture demo succeeded. PostgreSQL-focused tests were reported as skipped when the required test URL was unavailable; no unsupported success claim was made.

## Responsibilities that remain local

The command modules continue to own:

- operation-specific conflict text;
- transaction boundaries and session factories;
- validation and chronology;
- identity, revision and link writes;
- `SELECT ... FOR UPDATE` usage;
- process-local revision locks;
- revision-number and supersession allocation;
- domain exceptions other than database integrity translation;
- exact atomic unit of work;
- any future retry policy.

## Compatibility

The implementation is source-only. It requires no schema migration, downgrade, data repair, dependency, API, fixture, provider, CI, version or release change.

## Next gate

Integrity translation is completed and does not authorize broader command-lifecycle changes.

The next independent characterization may review revision allocation and lock strategy. It must treat process-local locks, row locks, latest-revision selection, revision-number allocation, supersession, SQLite limitations, PostgreSQL concurrency and lifecycle/cleanup as one compatibility-sensitive boundary. No implementation is authorized by this record.