# Stage 2 Revision Lock and Allocation Characterization

## Status

Issue #102 reviews Stage 2 revision locking and allocation at current `main` commit `46ee0f78908cbdff3a611ed158f43cb17fa28f8d`.

This is characterization only. Released version remains `0.2.0`, capability stage remains v0.6D, and no migration is required.

## Reviewed scope

The review compared:

- `industry_alpha/stage2_commands.py`;
- `industry_alpha/stage2_expectations_commands.py`;
- `industry_alpha/stage2_assessments_commands.py`;
- `industry_alpha/stage2_judgments_commands.py`;
- the corresponding revision models and uniqueness constraints;
- SQLite command/atomicity tests;
- PostgreSQL concurrent append tests for v0.6A-v0.6D.

The accepted neutral integrity translator is preserved and is not part of this decision.

## Current append protocol

Every append path follows the same outer shape:

```text
process-local keyed RLock
  -> integrity translator
       -> session_factory.begin()
            -> lock identity row with SELECT ... FOR UPDATE
            -> lock or validate company-research boundary
            -> read latest revision
            -> allocate revision_no = latest + 1
            -> set supersedes_revision_id = latest.id
            -> insert revision and frozen links
            -> flush and commit
```

The layers have different ownership and guarantees. They must not be treated as one interchangeable helper.

## Process-local lock inventory

All four command modules currently define the same mechanics:

```python
_LOCKS_GUARD = Lock()
_LOCKS: dict[tuple[str, UUID], RLock] = {}

def _revision_lock(kind: str, identity: UUID) -> RLock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault((kind, identity), RLock())
```

The exact kind labels are:

| Module | Labels |
| --- | --- |
| v0.6A company research | `research`, `hypothesis` |
| v0.6B expectations/valuation | `expectation`, `valuation` |
| v0.6C assessments | `catalyst`, `risk` |
| v0.6D judgments | `industry`, `company` |

The eight labels are disjoint. A neutral registry keyed by the unchanged `(kind, identity)` tuple therefore does not introduce cross-domain lock coalescing.

## What the process lock guarantees

The `RLock`:

- serializes same-key append calls only inside one Python process;
- is reentrant for the owning thread;
- performs no database or transaction operation;
- does not protect different keys;
- does not coordinate separate processes or hosts;
- remains held around integrity translation and the complete transaction;
- keeps each created lock in a module-level registry for the process lifetime.

The current registries have no cleanup, weak-reference or eviction policy. A first extraction must preserve that behavior rather than claim to solve registry lifetime.

## Database row locking

Append methods lock the domain identity row with `SELECT ... FOR UPDATE`; most paths also lock the owning company-research row directly or through `stage2_boundary.lock_company_research`.

On PostgreSQL this provides the cross-transaction serialization needed before reading the latest revision. On SQLite, `FOR UPDATE` does not provide equivalent row-level locking, so the process-local lock remains part of same-process behavior.

A neutral process-lock helper must not absorb row locking, accept a session or infer a model. Domain-specific not-found messages and lock order remain command-local.

## Revision allocation and constraints

Each revision table has a unique constraint on its identity foreign key plus `revision_no`. Application code reads the latest row ordered by descending revision number, allocates `1` or `latest + 1`, and points `supersedes_revision_id` to that latest row.

The database constraints reject duplicate revision numbers, but they do not independently prove that `supersedes_revision_id` is the immediately preceding accepted row. That chain depends on the command transaction, identity row lock, latest-row selection, chronology validation and domain-specific insert flow.

Therefore revision allocation is not a pure arithmetic helper. Extracting `latest + 1` or a generic allocator would separate the visible result from the concurrency and chronology conditions that make it valid.

## Cross-database evidence

Existing PostgreSQL tests concurrently append two revisions for:

- company research and hypotheses;
- expectations and valuation snapshots;
- catalysts and risks;
- industry and company judgments.

They verify consecutive revision numbers and, where asserted, the supersession chain. These tests are integration evidence for the current combined protocol.

Existing SQLite tests verify atomic rollback and domain semantics but do not establish cross-process SQLite revision allocation. This characterization does not expand the supported concurrency claim.

## Options evaluated

### Option A: keep four local process-lock registries

Safe, but duplicates the exact same stateless key-to-`RLock` factory and guard mechanics.

### Option B: extract one neutral keyed `RLock` registry

Accepted as the smallest safe implementation candidate.

A module such as `industry_alpha.stage2_revision_locks` may expose a function equivalent to:

```python
def revision_lock(kind: str, identity: UUID) -> RLock:
    key = (kind, identity)
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, RLock())
```

Each command module may import it under the existing private `_revision_lock` alias. All call sites, kind strings and nesting remain unchanged.

The helper must not validate labels, normalize UUIDs, expose registry mutation, add cleanup, replace `RLock` with `Lock`, or make async/multiprocess guarantees.

### Option C: extract a generic database row-lock helper

Rejected for this slice. Model choice, lock order, owning research boundaries and exact not-found messages differ. Some company-research locking is already neutralized in `stage2_boundary`; the remaining identity locks are domain-owned.

### Option D: extract revision-number/supersession allocation

Rejected. The latest-row query, chronology checks, domain validation, row locks and insert/link atomicity are inseparable from correct allocation.

### Option E: add retry or constraint-aware recovery

Rejected. Retry semantics and database error classification are not currently accepted behavior and differ across SQLite and PostgreSQL.

## Accepted neutral contract

A later implementation may add one process-local keyed `RLock` factory with these requirements:

1. accept the existing caller-provided `kind` string and UUID identity unchanged;
2. key exactly by `(kind, identity)`;
3. return the same `RLock` object for the same key within the process;
4. return different locks for different kind or identity values;
5. remain thread-safe when first creating a lock;
6. preserve reentrancy;
7. perform no transaction, database, retry, logging, validation or cleanup operation;
8. preserve every existing command call site and outer lock/integrity/transaction nesting.

## Direct test requirements

Direct helper tests must prove:

- the same key returns the same object;
- a different kind with the same UUID returns a different object;
- the same kind with a different UUID returns a different object;
- the returned lock is reentrant for the owning thread;
- two threads using the same key do not enter the protected section concurrently.

Existing v0.6A-v0.6D command tests and PostgreSQL concurrency tests remain integration evidence that command behavior, row locking and allocation are unchanged.

## First implementation candidate

A separate implementation Issue may authorize only:

1. add `industry_alpha/stage2_revision_locks.py`;
2. replace the four local lock registries/factories with imports under the existing private alias;
3. keep all eight kind strings and every `with` nesting unchanged;
4. add direct helper tests;
5. run focused Stage 2 command tests, available PostgreSQL concurrency tests, the full workflow and fixture demo.

No model, constraint, row-lock, transaction, integrity-message, revision-number, supersession, retry or lifecycle policy change belongs in that implementation.

## Definition of Ready conclusions

The neutral process-local keyed `RLock` factory reaches Definition of Ready for a separate minimal implementation Issue.

Generic database row locking, revision allocation, supersession, cleanup and retry do not reach Definition of Ready and remain local. This report does not authorize their implementation or redesign.
