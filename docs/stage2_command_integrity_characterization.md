# Stage 2 Command Integrity Translation Characterization

## Status

Issue #96 reviews the v0.6A-v0.6D command-side SQLAlchemy integrity translation at accepted `main` commit `03756aa7009c738e4c183845fbb8eb9e09906663`.

This is characterization only. Released version remains `0.2.0`, capability stage remains v0.6D, and no migration is required.

## Reviewed scope

The review compared:

- `industry_alpha/stage2_commands.py`;
- `industry_alpha/stage2_expectations_commands.py`;
- `industry_alpha/stage2_assessments_commands.py`;
- `industry_alpha/stage2_judgments_commands.py`;
- the corresponding SQLite atomicity tests;
- the corresponding PostgreSQL concurrency and rollback tests.

Revision locking and allocation were inspected only to preserve their boundary. They are not authorized for change by this report.

## Existing behavior

All four command modules wrap their transaction context with an integrity translator:

```text
integrity translator
  -> session_factory.begin()
       -> validation, identity/revision/link writes and flushes
```

The transaction context exits first. Therefore a database integrity failure is rolled back by SQLAlchemy before the outer translator maps the exception.

Every implementation currently has the same semantic contract:

1. enter without changing transaction or session state;
2. allow successful execution to return normally;
3. catch only `sqlalchemy.exc.IntegrityError`;
4. raise `EvidenceLedgerConflictError` with the caller-provided message;
5. retain the original `IntegrityError` through `raise ... from exc`;
6. return or propagate all other exception types unchanged;
7. perform no explicit commit, rollback, retry, logging or constraint inspection.

## Current implementation forms

### v0.6A and v0.6B

Each service defines a nested `_IntegrityTranslation` context-manager class plus a `_translate_integrity(message)` constructor method.

### v0.6C and v0.6D

Each service defines an equivalent `@contextmanager` method named `_integrity(message)`.

The difference is syntactic. There is no accepted domain-specific behavior in the helper bodies.

## Caller-owned policy

Conflict wording remains command and operation specific. Examples include:

- duplicate company-research membership;
- duplicate hypothesis, expectation, valuation, catalyst, risk or judgment keys;
- research, hypothesis, expectation, valuation, assessment and judgment revision conflicts;
- verification-item conflicts.

A neutral helper must accept the exact message as an argument and must not infer operation names, parse constraint names or normalize text.

The current broad mapping of any `IntegrityError` inside the bounded transaction is also preserved. A first extraction must not introduce backend-specific constraint-name branching.

## Transaction and rollback ownership

`session_factory.begin()` remains the sole owner of:

- opening and closing the session;
- commit on success;
- rollback on validation or database failure;
- expiring/closing transaction state.

The neutral helper must remain outside the transaction context at every call site. It must not receive a session, call `rollback()`, retry work or suppress an exception.

Existing SQLite tests verify atomic rollback for invalid commands. Existing PostgreSQL tests verify deterministic concurrent revision allocation and rollback of invalid state. Those tests remain integration evidence; they do not become helper responsibilities.

## Options evaluated

### Option A: keep four local helpers

Safe but unnecessarily duplicated. The four bodies encode no domain policy beyond a caller-supplied string, and two different implementation styles obscure that their behavior must remain identical.

### Option B: one neutral context manager

Accepted as the smallest safe slice.

A module such as `industry_alpha.stage2_integrity` may expose one function equivalent to:

```python
@contextmanager
def translate_integrity(message: str) -> Iterator[None]:
    try:
        yield
    except IntegrityError as exc:
        raise EvidenceLedgerConflictError(message) from exc
```

Each command module may import it under its current private name or use one private alias. Call-site messages and nesting remain unchanged.

### Option C: constraint-aware conflict classification

Rejected. Constraint names and driver payloads differ across SQLite and PostgreSQL. Classification would add backend coupling and could change current public errors.

### Option D: combine translation with revision locks or retries

Rejected. Process-local `RLock`, database row locks, revision-number allocation and retry policy have separate concurrency semantics and require their own characterization.

## Accepted neutral contract

A later implementation may add one stateless context manager with these requirements:

1. accept a caller-provided message without modification;
2. translate only `IntegrityError`;
3. raise `EvidenceLedgerConflictError(message)` from the original exception;
4. pass non-integrity exceptions through unchanged;
5. perform no session or transaction operation;
6. perform no retry, logging, constraint inspection or backend branching;
7. preserve the existing outer-helper/inner-transaction nesting at every command call site.

## First implementation candidate

A separate implementation Issue may authorize only:

1. add `industry_alpha/stage2_integrity.py`;
2. replace the four local translator implementations with imports/private aliases;
3. keep all conflict message strings at their current call sites;
4. add direct helper tests for success, exact translation/cause and non-integrity passthrough;
5. run existing v0.6A-v0.6D SQLite tests, available PostgreSQL tests, the full offline workflow and fixture demo.

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
- exact atomic unit of work.

## Test requirements

Direct neutral-helper tests must prove:

- successful entry/exit performs no transformation;
- an `IntegrityError` becomes the exact conflict message;
- `__cause__` is the original `IntegrityError` object;
- a representative non-integrity exception is the same object after propagation.

Existing command tests remain the proof that application validation and rollback behavior is unchanged. Existing PostgreSQL concurrency tests remain the proof that revision locks and row locking are unaffected.

## Migration and compatibility

The candidate is source-only. It requires no schema migration, downgrade, data repair, dependency, API, fixture, provider, CI, version or release change.

## Definition of Ready conclusion

The neutral integrity translator reaches Definition of Ready for a separate minimal implementation Issue.

The contract, ownership, exact exception behavior, test surface, no-migration decision and stop conditions are explicit. This conclusion does not authorize revision-lock, revision-allocation, retry or constraint-classification work.
