# Stage 2 ORM Lifecycle Characterization

## Status and authority

- Original characterization: Issue #116 / PR #117.
- Accepted characterization merge: `2fb24eadf7285000fdb0c2ef7ebc1d84f87c8908`.
- Compatibility-matrix follow-up: Issue #118 / PR #119.
- Work type: test-only consolidation prerequisite plus documentation decision.
- Released version remains `0.2.0`; merged capability remains v0.6D.
- Accepted application/consolidation implementation baseline remains
  `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.
- Migration, dependency, schema, API and runtime decisions: no change.

Issue #116 established that current behavior is stable on supported cached-import
paths but had no committed lifecycle compatibility matrix. Issue #118 adds that
matrix without changing production ORM code.

The post-matrix architecture decision is deliberately narrow:

- a pure mutation-scan helper reaches Definition of Ready as one later,
  independently authorized source-only candidate;
- all four listener decorators, listener function identities, model tuples,
  dynamic mapped-class factories and generated class globals remain local to
  their current domain modules;
- no implementation is authorized by this report or by PR #119.

## Current module and registration matrix

All four modules use the single `backend.database.models.Base` and register one
listener on the global SQLAlchemy `Session.before_flush` event.

| Stage | Model module | Listener | Model tuple | Size |
| --- | --- | --- | --- | ---: |
| v0.6A | `industry_alpha.stage2_models` | `reject_stage2_mutation` | `STAGE2_MODELS` | 11 |
| v0.6B | `industry_alpha.stage2_expectations_models` | `reject_stage2_expectation_mutation` | `STAGE2_EXPECTATION_MODELS` | 10 |
| v0.6C | `industry_alpha.stage2_assessments_models` | `reject_stage2_assessment_mutation` | `STAGE2_ASSESSMENT_MODELS` | 14 |
| v0.6D | `industry_alpha.stage2_judgments_models` | `reject_stage2_judgment_mutation` | `STAGE2_JUDGMENT_MODELS` | 18 |

The supported package path eagerly imports the four Stage 2 modules. Alembic
imports v0.6A through v0.6D in order before exposing `Base.metadata`. The Stage 2
migration chain remains:

1. `20260719_0008` - v0.6A;
2. `20260719_0009` - v0.6B;
3. `20260719_0010` - v0.6C;
4. `20260719_0011` - v0.6D and current Alembic head.

The four tuples and the Alembic model set contain exactly 53 `stage2_` tables.

## Append-only behavior contract

Each current listener has the same ordered behavior while retaining a distinct
module-local function object and tuple:

1. inspect `session.deleted` first;
2. when a deleted row belongs to the local tuple, raise the exact
   `EvidenceLedgerImmutableError` class with
   `<ClassName> rows are append-only and cannot be deleted.`;
3. inspect `session.dirty` second;
4. call `session.is_modified(row, include_collections=False)`;
5. when a materially modified row belongs to the local tuple, raise the exact
   error class with
   `<ClassName> rows are append-only and cannot be updated.`.

The accepted timing and reach are:

- errors occur during ordinary ORM `flush()`;
- pending inserts are allowed;
- dirty-but-materially-unmodified scalar assignments are allowed;
- rollback preserves the original persisted row and value;
- the global `Session` target reaches the configured session factory and custom
  `Session` subclasses;
- explicit module reload is unsupported;
- direct Core DML is outside this ORM guard and is not elevated into a desired
  compatibility contract.

## Committed compatibility matrix

PR #119 adds two new files and edits no existing test or production file:

- `tests/test_stage2_orm_lifecycle_contract.py`;
- `tests/test_stage2_orm_lifecycle_contract_postgres.py`.

### Ordinary import, mapper and metadata identity

The non-PostgreSQL contract fixes the following supported behavior:

- `event.contains(Session, "before_flush", listener)` is true for all four
  current listener function objects;
- model tuple sizes remain 11, 10, 14 and 18;
- every tuple member's table uses the single shared `Base.metadata`;
- supported imports expose exactly 53 `stage2_` tables;
- three ordinary `importlib.import_module()` rounds preserve module objects,
  listener objects, tuple objects, mapped-class objects, table objects and the
  metadata object;
- a clean subprocess uses Python's public profiling hook around one
  dirty-but-unmodified flush and observes each Stage 2 listener exactly once;
- no SQLAlchemy private dispatch registry is used by the committed tests;
- no explicit reload test is committed because a failed reload can perturb
  process-global declarative state.

### Dynamic mapped classes

The matrix fixes the existing v0.6C generated globals and table identities:

| Class | Table |
| --- | --- |
| `Stage2CatalystHypothesisLink` | `stage2_catalyst_hypothesis_links` |
| `Stage2CatalystExpectationLink` | `stage2_catalyst_expectation_links` |
| `Stage2CatalystValuationLink` | `stage2_catalyst_valuation_links` |
| `Stage2CatalystClaimLink` | `stage2_catalyst_claim_links` |
| `Stage2RiskHypothesisLink` | `stage2_risk_hypothesis_links` |
| `Stage2RiskExpectationLink` | `stage2_risk_expectation_links` |
| `Stage2RiskValuationLink` | `stage2_risk_valuation_links` |
| `Stage2RiskClaimLink` | `stage2_risk_claim_links` |

It also fixes the twelve v0.6D globals generated for both `Industry` and
`Company` judgment kinds over these six upstreams:

- `Hypothesis`;
- `Expectation`;
- `Valuation`;
- `Catalyst`;
- `Risk`;
- `Claim`.

Each generated global must continue to resolve to the same mapped class and the
matching table named
`stage2_<industry|company>_judgment_<upstream>_links` within one normally cached
process. This is a keep-local identity contract, not permission to consolidate
the two factories.

### SQLite session and mutation behavior

The committed SQLite matrix builds the existing deterministic v0.6D fixture,
which transitively builds v0.6A through v0.6C, using the current shared metadata
and session factory. It verifies:

- a dirty-but-unmodified `Stage2CompanyResearch` flush succeeds;
- a new pending `Stage2VerificationItem` flush succeeds;
- representative updates and deletes from v0.6A, v0.6B, v0.6C and v0.6D fail
  with the exact class-specific message;
- each failed mutation rolls back and the original row/value remains;
- a custom `Session` subclass receives the same global listener behavior.

Representative identity rows are intentionally simple domain roots:

| Stage | Representative model | Mutated field |
| --- | --- | --- |
| v0.6A | `Stage2CompanyResearch` | `stock_code` |
| v0.6B | `Stage2MarketExpectation` | `expectation_key` |
| v0.6C | `Stage2CatalystAssessment` | `catalyst_key` |
| v0.6D | `Stage2IndustryJudgment` | `judgment_key` |

The full existing tuple-level and command-level tests continue to provide wider
domain coverage; this matrix fixes lifecycle compatibility rather than replacing
those tests.

### PostgreSQL behavior

The PostgreSQL contract uses the existing `TEST_DATABASE_URL` safety rule:

- absence of `TEST_DATABASE_URL` is an honest skip;
- the database name must contain `test`;
- Alembic downgrades to base and upgrades to head for the module;
- cleanup truncates only the existing test database roots with `CASCADE`;
- the existing deterministic v0.6D fixture supplies representative rows for all
  four Stage 2 families;
- material updates and deletes for v0.6A through v0.6D raise the exact immutable
  error class and message at flush;
- rollback preserves each row and original value.

The fixed-head GitHub Actions validation record is maintained on PR #119. It
uses PostgreSQL 16 and must complete the full test step, fixture demo and cleanup
successfully. Exact run identifiers and any available counts belong in that PR
record; unavailable counts must not be guessed in this architecture document.

## Import and lifecycle findings

1. Ordinary import idempotency continues to rely on Python's module cache; the
   committed matrix now fixes that supported path.
2. Explicit reload remains unsupported and outside the matrix.
3. Listener decorators and function objects remain domain-local and registered
   exactly once per normal process import.
4. Global `Session` reach is observable and intentionally preserved.
5. All mapped classes, tables and metadata remain process-global under the
   current declarative base.
6. The dynamic v0.6C/v0.6D class globals are observable public repository
   identities and cannot be treated as disposable factory output.
7. The append-only guard remains an ORM unit-of-work boundary, not a database
   trigger or general Core-DML interceptor.

## Candidate classification after the matrix

| Candidate | Decision | Reason |
| --- | --- | --- |
| Move all four decorated listeners to one module | Deferred | Would change registration trigger, function identity and import reach |
| Extract only the repeated mutation scan into a pure helper | Bounded later implementation candidate | Preserves local decorators, tuples, order, messages and flush timing while removing only duplicated loops |
| Consolidate v0.6C/v0.6D `_link_model` factories | Deferred | Would change mapped-class ownership, globals, import timing and possibly mapper/table identity |
| Move model tuples or evidence-link mixins | Keep domain-local | They define exact accepted domain membership and import identity |
| Add database triggers or Core-DML interception | Not authorized | This would create a different persistence contract and require separate characterization |

## Definition of Ready decision

One and only one source-only candidate reaches Definition of Ready: a pure
append-only mutation-scan helper.

### Exact neutral owner and contract

A later independently authorized implementation may introduce one neutral module,
provisionally `industry_alpha/orm_append_only.py`, containing a function with the
following bounded responsibility:

```python
reject_append_only_mutation(session, model_types)
```

Its contract must be limited to the current repeated algorithm:

- accept the active SQLAlchemy `Session` and an explicit domain-owned tuple of
  mapped classes;
- scan `session.deleted` before `session.dirty`;
- use `isinstance(row, model_types)`;
- use `session.is_modified(row, include_collections=False)` for dirty rows;
- raise the existing `EvidenceLedgerImmutableError` with the exact current
  class-derived delete/update messages;
- return `None` when no rejected mutation is present.

The helper must not:

- register or remove SQLAlchemy events;
- import any Stage 2 model module or own any model tuple;
- own a sessionmaker, engine, mapper, metadata or declarative registry;
- change insert, dirty-but-unmodified, rollback or exception timing behavior;
- inspect or intercept Core DML;
- catch, translate or wrap the immutable error.

### Required later file family

A later implementation Issue may authorize only a bounded source-and-test family:

1. one new neutral helper module;
2. the four current Stage 2 model modules, changing only each listener body to
   delegate with its existing local tuple;
3. the committed non-PostgreSQL lifecycle contract test;
4. the committed PostgreSQL lifecycle contract test;
5. this characterization document if a status update is required.

The four decorated listener function names, decorator locations and tuples must
remain in their current modules. Dynamic factories and generated globals are not
part of that implementation candidate.

### Rollback and migration

- Migration: none.
- Persisted schema: unchanged.
- Dependency: unchanged.
- Data repair: none.
- Rollback: source reversion to the four current local loop bodies.

## Validation gate for PR #119

Acceptance requires all of the following on one fixed head:

- exactly the four Issue #118 authorized files;
- focused lifecycle tests;
- full `python -m pytest -q`;
- `python -m scripts.demo_research_flow`;
- `git diff --check` or equivalent whitespace-error inspection;
- GitHub Actions success with its PostgreSQL service;
- no hidden warning or skip reclassification;
- no production, fixture, dependency, schema, migration or runtime change.

## Explicit non-goals

This work does not authorize listener relocation, dynamic factory consolidation,
model/global/tuple relocation, explicit reload support, database append-only
triggers, Core-DML interception, schema or migration changes, dependency changes,
API or runtime behavior, provider work, canonical-price work, release/version
changes, v0.6E, v0.7 or any change to PR #38.
