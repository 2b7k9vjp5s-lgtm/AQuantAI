# Stage 2 ORM Lifecycle Characterization

## Status and authority

- Issue: #116.
- Characterization base: `e6ffd6a9c94afacdbe0a5475108b6521e30762d6`.
- Work type: documentation-only consolidation characterization.
- Released version remains `0.2.0`; merged capability remains v0.6D.
- This report authorizes no ORM, listener, mapped-class factory, import, test,
  schema, migration, dependency, API, or runtime implementation.
- Migration decision: no migration.
- Decision: **no implementation currently reaches Definition of Ready**.

The current behavior is stable for ordinary cached imports and the supported
application/test paths. Explicit module reload is not a supported lifecycle and
is observably unsafe. The evidence is therefore sufficient to document the
boundary, but not to authorize consolidation.

## Environment

The bounded diagnostics ran on Windows with Python `3.13.0` and SQLAlchemy
`2.0.51`. `DATABASE_URL` was unset and the Docker daemon was unavailable, so no
new PostgreSQL diagnostic was run. Existing PostgreSQL tests and their scope are
inventoried below; environment-gated skips are reported by the full test run.

All diagnostics were supplied to `python -` or `python -c` and ran against an
in-memory SQLite database or interpreter state. No diagnostic source, snapshot,
database, or generated artifact was written to the repository.

## Module and import-path matrix

| Stage | Model module | Registration path | Models/tables |
| --- | --- | --- | ---: |
| v0.6A | `industry_alpha.stage2_models` | command, repository, fixture, API service, test, demo, and Alembic imports | 11 |
| v0.6B | `industry_alpha.stage2_expectations_models` | expectation command/repository/fixture/query, API, test, demo, and Alembic imports | 10 |
| v0.6C | `industry_alpha.stage2_assessments_models` | assessment command/repository/fixture/query, API, test, demo, and Alembic imports | 14 |
| v0.6D | `industry_alpha.stage2_judgments_models` | judgment command/repository/fixture/query, API, test, demo, and Alembic imports | 18 |

All four modules import the same `Base` declared in
`backend.database.models`. `backend.database.engine.build_session_factory()`
uses SQLAlchemy's global `Session` class with `expire_on_commit=False`.

`industry_alpha/__init__.py` eagerly imports Stage 2 command and query services.
Importing any `industry_alpha.<submodule>` first executes that package file, so
the supported package path transitively registers all four Stage 2 model modules.
This means a source-level request for one model module is not a genuinely partial
runtime registration experiment.

`migrations/env.py` imports the shared `Base`, then v0.5A, v0.5B, v0.5C, v0.6A,
v0.6B, v0.6C, and v0.6D modules before assigning `target_metadata = Base.metadata`.
The declared Stage 2 migration chain is:

1. `20260719_0008` - v0.6A, 11 tables;
2. `20260719_0009` - v0.6B, 10 tables;
3. `20260719_0010` - v0.6C, 14 tables;
4. `20260719_0011` - v0.6D, 18 tables and current Alembic head.

The model tuple counts and migration table counts both total 53 Stage 2 tables.
The diagnostic metadata contained exactly 53 `stage2_` tables after any one of
the four model modules was requested first in a clean process.

## Listener matrix

Each listener is decorated at module execution with
`@event.listens_for(Session, "before_flush")`. The target is the global
`sqlalchemy.orm.Session`, not one configured sessionmaker instance.

| Stage | Function | Model tuple | Tuple size | Current direct tests |
| --- | --- | --- | ---: | --- |
| v0.6A | `reject_stage2_mutation` | `STAGE2_MODELS` | 11 | SQLite delete guard over tuple; PostgreSQL update/delete guard |
| v0.6B | `reject_stage2_expectation_mutation` | `STAGE2_EXPECTATION_MODELS` | 10 | SQLite delete guard over tuple |
| v0.6C | `reject_stage2_assessment_mutation` | `STAGE2_ASSESSMENT_MODELS` | 14 | SQLite material update and delete |
| v0.6D | `reject_stage2_judgment_mutation` | `STAGE2_JUDGMENT_MODELS` | 18 | SQLite material update and delete |

Exact v0.6A tuple:

`Stage2CompanyResearch`, `Stage2HandoffAssertionLink`,
`Stage2HandoffClaimLink`, `Stage2HandoffEvidenceLink`,
`Stage2CompanyResearchRevision`, `Stage2FinancialHypothesis`,
`Stage2FinancialHypothesisRevision`, `Stage2HypothesisClaimLink`,
`Stage2HypothesisEvidenceLink`, `Stage2ResearchHypothesisLink`, and
`Stage2VerificationItem`.

Exact v0.6B tuple:

`Stage2MarketExpectation`, `Stage2MarketExpectationRevision`,
`Stage2ExpectationHypothesisLink`, `Stage2ExpectationClaimLink`,
`Stage2ExpectationEvidenceLink`, `Stage2ValuationSnapshot`,
`Stage2ValuationSnapshotRevision`, `Stage2ValuationHypothesisLink`,
`Stage2ValuationClaimLink`, and `Stage2ValuationEvidenceLink`.

Exact v0.6C tuple:

`Stage2CatalystAssessment`, `Stage2CatalystAssessmentRevision`, the four
generated catalyst hypothesis/expectation/valuation/claim links,
`Stage2CatalystEvidenceLink`, `Stage2RiskAssessment`,
`Stage2RiskAssessmentRevision`, the four generated risk
hypothesis/expectation/valuation/claim links, and `Stage2RiskEvidenceLink`.

Exact v0.6D tuple:

`Stage2IndustryJudgment`, `Stage2IndustryJudgmentRevision`,
`Stage2CompanyJudgment`, `Stage2CompanyJudgmentRevision`, twelve generated
industry/company hypothesis/expectation/valuation/catalyst/risk/claim links,
`Stage2IndustryJudgmentEvidenceLink`, and
`Stage2CompanyJudgmentEvidenceLink`.

All four listeners have the same ordered behavior:

1. inspect `session.deleted` first;
2. for a tuple member, raise the exact `EvidenceLedgerImmutableError` class with
   `<ClassName> rows are append-only and cannot be deleted.`;
3. inspect `session.dirty` second;
4. reject only when `session.is_modified(row, include_collections=False)` is
   true, using `<ClassName> rows are append-only and cannot be updated.`.

Pending objects in `session.new` are not rejected. Dirty-but-unmodified objects
are allowed. Materially dirty and deleted tuple members fail during
`session.flush()` before their ordinary ORM DML can complete. The exception is
`industry_alpha.errors.EvidenceLedgerImmutableError`, a subclass of
`EvidenceLedgerError` and `ValueError`.

The guard is an ORM unit-of-work contract, not a database immutability
constraint. A bounded SQLite diagnostic confirmed that a direct SQLAlchemy Core
`update()` bypasses `Session.before_flush`. That bypass is existing behavior and
is not changed or approved by this report.

## Dynamic mapped-class matrix

### v0.6C factory

`industry_alpha.stage2_assessments_models._link_model` creates eight classes and
assigns each result to an explicit owning module global. Every class uses the
shared `Base`, UUID primary key `id`, two non-null `RESTRICT` foreign keys,
`recorded_at_utc`, one named two-column unique constraint, and one named index.

| Class | Table | Unique constraint | Index | Foreign-key targets |
| --- | --- | --- | --- | --- |
| `Stage2CatalystClaimLink` | `stage2_catalyst_claim_links` | `uq_stage2_catalyst_claim_links` | `ix_stage2_catalyst_claim` | catalyst revision; claim revision |
| `Stage2CatalystExpectationLink` | `stage2_catalyst_expectation_links` | `uq_stage2_catalyst_expectation_links` | `ix_stage2_catalyst_expectation` | catalyst revision; expectation revision |
| `Stage2CatalystHypothesisLink` | `stage2_catalyst_hypothesis_links` | `uq_stage2_catalyst_hypothesis_links` | `ix_stage2_catalyst_hypothesis` | catalyst revision; hypothesis revision |
| `Stage2CatalystValuationLink` | `stage2_catalyst_valuation_links` | `uq_stage2_catalyst_valuation_links` | `ix_stage2_catalyst_valuation` | catalyst revision; valuation revision |
| `Stage2RiskClaimLink` | `stage2_risk_claim_links` | `uq_stage2_risk_claim_links` | `ix_stage2_risk_claim` | risk revision; claim revision |
| `Stage2RiskExpectationLink` | `stage2_risk_expectation_links` | `uq_stage2_risk_expectation_links` | `ix_stage2_risk_expectation` | risk revision; expectation revision |
| `Stage2RiskHypothesisLink` | `stage2_risk_hypothesis_links` | `uq_stage2_risk_hypothesis_links` | `ix_stage2_risk_hypothesis` | risk revision; hypothesis revision |
| `Stage2RiskValuationLink` | `stage2_risk_valuation_links` | `uq_stage2_risk_valuation_links` | `ix_stage2_risk_valuation` | risk revision; valuation revision |

The revision targets are respectively
`stage2_catalyst_assessment_revisions.id` or
`stage2_risk_assessment_revisions.id`. Upstream targets are
`claim_revisions.id`, `stage2_market_expectation_revisions.id`,
`stage2_financial_hypothesis_revisions.id`, or
`stage2_valuation_snapshot_revisions.id`.

### v0.6D factory

`industry_alpha.stage2_judgments_models._link_model` runs over two kinds and six
upstreams, then assigns twelve results through `globals()`. Every generated class
has the same UUID/timestamp/unique/index pattern as v0.6C.

| Class/global | Table | Unique constraint | Index | Upstream FK target |
| --- | --- | --- | --- | --- |
| `Stage2IndustryJudgmentHypothesisLink` | `stage2_industry_judgment_hypothesis_links` | `uq_stage2_industry_judgment_hypothesis_links` | `ix_stage2_industry_judgment_hypothesis` | `stage2_financial_hypothesis_revisions.id` |
| `Stage2IndustryJudgmentExpectationLink` | `stage2_industry_judgment_expectation_links` | `uq_stage2_industry_judgment_expectation_links` | `ix_stage2_industry_judgment_expectation` | `stage2_market_expectation_revisions.id` |
| `Stage2IndustryJudgmentValuationLink` | `stage2_industry_judgment_valuation_links` | `uq_stage2_industry_judgment_valuation_links` | `ix_stage2_industry_judgment_valuation` | `stage2_valuation_snapshot_revisions.id` |
| `Stage2IndustryJudgmentCatalystLink` | `stage2_industry_judgment_catalyst_links` | `uq_stage2_industry_judgment_catalyst_links` | `ix_stage2_industry_judgment_catalyst` | `stage2_catalyst_assessment_revisions.id` |
| `Stage2IndustryJudgmentRiskLink` | `stage2_industry_judgment_risk_links` | `uq_stage2_industry_judgment_risk_links` | `ix_stage2_industry_judgment_risk` | `stage2_risk_assessment_revisions.id` |
| `Stage2IndustryJudgmentClaimLink` | `stage2_industry_judgment_claim_links` | `uq_stage2_industry_judgment_claim_links` | `ix_stage2_industry_judgment_claim` | `claim_revisions.id` |
| `Stage2CompanyJudgmentHypothesisLink` | `stage2_company_judgment_hypothesis_links` | `uq_stage2_company_judgment_hypothesis_links` | `ix_stage2_company_judgment_hypothesis` | `stage2_financial_hypothesis_revisions.id` |
| `Stage2CompanyJudgmentExpectationLink` | `stage2_company_judgment_expectation_links` | `uq_stage2_company_judgment_expectation_links` | `ix_stage2_company_judgment_expectation` | `stage2_market_expectation_revisions.id` |
| `Stage2CompanyJudgmentValuationLink` | `stage2_company_judgment_valuation_links` | `uq_stage2_company_judgment_valuation_links` | `ix_stage2_company_judgment_valuation` | `stage2_valuation_snapshot_revisions.id` |
| `Stage2CompanyJudgmentCatalystLink` | `stage2_company_judgment_catalyst_links` | `uq_stage2_company_judgment_catalyst_links` | `ix_stage2_company_judgment_catalyst` | `stage2_catalyst_assessment_revisions.id` |
| `Stage2CompanyJudgmentRiskLink` | `stage2_company_judgment_risk_links` | `uq_stage2_company_judgment_risk_links` | `ix_stage2_company_judgment_risk` | `stage2_risk_assessment_revisions.id` |
| `Stage2CompanyJudgmentClaimLink` | `stage2_company_judgment_claim_links` | `uq_stage2_company_judgment_claim_links` | `ix_stage2_company_judgment_claim` | `claim_revisions.id` |

Each class is installed under the exact class name shown as an owning module
global. `judgment_revision_id` targets either
`stage2_industry_judgment_revisions.id` or
`stage2_company_judgment_revisions.id`; the unique constraint and index pair it
with the upstream revision column. Each row links that column to one of:

- `stage2_financial_hypothesis_revisions.id`;
- `stage2_market_expectation_revisions.id`;
- `stage2_valuation_snapshot_revisions.id`;
- `stage2_catalyst_assessment_revisions.id`;
- `stage2_risk_assessment_revisions.id`;
- `claim_revisions.id`.

All generated foreign keys use `ondelete="RESTRICT"`.

The owning module globals and tuple membership are part of repository, command,
fixture, query, and test imports. They are therefore observable mapped-class
identity, not disposable code-generation details.

## Bounded diagnostic evidence

The diagnostics used fresh interpreter processes. Representative invocations
were `python -c "..."` for short probes and a PowerShell here-string piped to
`python -` for multi-step probes. No diagnostic file was created.

### Registration and ordinary import

An `event.contains(Session, "before_flush", function)` probe returned `true`
for all four Stage 2 listener function objects. SQLAlchemy's diagnostic dispatch
registry contained seven global Industry Alpha `before_flush` functions in
total: v0.5A, v0.5B, v0.5C, and the four Stage 2 functions. Re-requesting each
Stage 2 module three times through `importlib.import_module()` left the total at
seven and the Stage 2 count at four.

An ephemeral Python call profiler observed a dirty-but-unmodified flush before
and after those repeated imports. Each of the four Stage 2 listener functions
was invoked exactly once per flush in both observations; no duplicate invocation
was observed on the supported ordinary-import path.

Ordinary repeated imports preserved all four module objects, listener function
objects, mapped-class objects, table objects, and `Base.metadata`. The four model
tuple sizes were `11`, `10`, `14`, and `18`. All tuple classes referenced the
same `Base.metadata` object.

### Requested import order

Four separate processes requested each Stage 2 model module first. In every
process, package initialization loaded all four modules, produced 53 Stage 2
tables, and produced the same sorted table-set SHA-256:

`cb0852d0ea59dc6be71b0b70e49ca6ce3e7571503f5a4b99d3d0379a88db508d`.

This proves deterministic supported package imports. It does not prove that
manually bypassing package initialization, deleting entries from `sys.modules`,
or executing source under another module name is supported.

### Explicit reload sensitivity

`importlib.reload()` was attempted once for each model module in one disposable
process. All four attempts emitted SQLAlchemy warnings that the declarative base
already contained the same class/module name. Each then failed on its first
static table with `InvalidRequestError`:

- v0.6A: duplicate `stage2_company_research`;
- v0.6B: duplicate `stage2_market_expectations`;
- v0.6C: duplicate `stage2_catalyst_assessments`;
- v0.6D: duplicate `stage2_industry_judgments`.

The error text required `extend_existing=True` to redefine the existing table.
The old listener remained registered and the old table remained in metadata, but
the warning demonstrates that declarative class lookup may already have been
touched before failure. No state after a failed explicit reload is treated as a
supported runtime state.

### Session and mutation behavior

An in-memory SQLite fixture exercised the current `build_session_factory()` and
a custom `Session` subclass factory:

- assigning the existing scalar value made the object dirty but
  `is_modified(..., include_collections=False)` returned false; flush succeeded;
- a material scalar update raised exactly
  `EvidenceLedgerImmutableError: Stage2CompanyResearchRevision rows are append-only and cannot be updated.`;
- deletion raised exactly
  `EvidenceLedgerImmutableError: Stage2CompanyResearchRevision rows are append-only and cannot be deleted.`;
- rollback preserved the original row and value after both failures;
- the custom `Session` subclass received the global listener and raised the same
  exact update exception;
- fixture construction proved accepted pending inserts remain allowed;
- a direct Core `update()` bypassed `before_flush`, confirming the ORM-only
  boundary.

## Existing test evidence

### SQLite and offline tests

- `tests/test_stage2_company_research.py` parameterizes deletion across
  `STAGE2_MODELS`; command validation tests verify atomic rollback.
- `tests/test_stage2_expectations_valuation.py` deletes every
  `STAGE2_EXPECTATION_MODELS` member and rolls back after each rejection.
- `tests/test_stage2_catalyst_risk_assessments.py` verifies material identity
  update and revision deletion rejection plus atomic validation rollback.
- `tests/test_stage2_quality_judgments.py` verifies material identity update and
  revision deletion rejection plus atomic validation rollback.
- All four test families build isolated SQLite engines with the shared global
  metadata. Clean database repetition tests database state determinism, not a
  fresh mapper/event registry.

### PostgreSQL tests

- `tests/test_stage2_company_research_postgres.py` directly verifies v0.6A
  material update and delete rejection, migration from `20260719_0007`, and
  concurrent revision allocation.
- `tests/test_stage2_expectations_valuation_postgres.py` verifies v0.6B migration,
  concurrency, fixture determinism, and rollback, but has no direct append-only
  listener test over its ten-model tuple.
- `tests/test_stage2_catalyst_risk_assessments_postgres.py` verifies v0.6C
  migration, concurrency, and clean-database fixture semantics, but has no direct
  listener identity/invocation test.
- `tests/test_stage2_quality_judgments_postgres.py` verifies v0.6D migration,
  concurrency, and cross-database fixture semantics, but has no direct listener
  identity/invocation test.

The local environment could not add PostgreSQL evidence because `DATABASE_URL`
was unset and the Docker daemon was unavailable. PostgreSQL skips must therefore
remain explicit rather than being interpreted as passes.

## Lifecycle findings

1. **Shared metadata:** all 53 Stage 2 mapped classes use one `Base.metadata`.
2. **Normal imports:** Python's module cache makes registration idempotent by
   avoiding re-execution; there is no explicit application-level registration
   idempotency mechanism.
3. **Import order:** supported package imports are deterministic but eager. The
   package initializer masks genuinely partial model registration.
4. **Explicit reload:** unsupported and unsafe; it warns and fails before a
   replacement module can complete.
5. **Listener identity:** four distinct domain listener functions remain
   registered on global `Session`; ordinary re-import preserves identity.
6. **Mapper identity:** 20 dynamic link classes and 33 static Stage 2 classes are
   stable only while their defining modules are cached normally.
7. **Duplicate risk:** ordinary imports do not duplicate listeners. Any future
   registration helper, source re-execution, test module unloading, or manual
   event registration could duplicate invocation unless identity and removal
   rules are explicit.
8. **Session reach:** the global target covers the configured factory and tested
   custom `Session` subclasses. It is broader than one application sessionmaker.
9. **Test isolation:** database engines are often isolated, while metadata,
   mappers, and event registrations are process-global. Existing clean-database
   tests do not reset the ORM registry.
10. **Failure timing:** ordinary ORM updates/deletes fail at flush; pending rows
    are allowed; dirty-but-unmodified scalar rows are allowed; direct Core DML is
    outside the guard.

## Candidate classification

| Candidate | Classification | Reason |
| --- | --- | --- |
| Move all four decorated listeners into one module | Deferred because ORM/event compatibility risk is too high | Changes registration trigger, function identity, import reach, and possibly error timing; no committed identity/idempotency matrix exists |
| Extract only the repeated mutation scan into a pure helper while retaining four local decorators and tuples | Shareable only after an explicit neutral contract | Mechanically bounded, but custom-Session reach, event count, exact timing, and PostgreSQL coverage are not yet committed compatibility tests |
| Consolidate the v0.6C and v0.6D `_link_model` factories | Deferred because ORM/event/schema compatibility risk is too high | Would move mapped-class ownership and can change `__module__`, globals, mapper identity, import timing, table registration, and Alembic metadata behavior |
| Keep model tuples, evidence-link mixins, and domain class globals local | Domain-specific and required to remain local | They define exact accepted domain membership and public import identity |

No candidate is classified as safe to extract now.

## Decision: no implementation DoR

No later implementation reaches Definition of Ready from this evidence. The
blocking gaps are concrete:

- registration idempotency currently depends on Python's import cache rather
  than an explicit neutral owner or contract;
- explicit reload is unsafe and perturbs declarative lookup before failing;
- no committed test fixes the four listener identities/counts, custom-Session
  reach, supported import behavior, or mapper/table identity;
- PostgreSQL directly tests append-only behavior only for v0.6A, and PostgreSQL
  was unavailable for this characterization;
- moving either dynamic factory would change observable class ownership unless a
  separate compatibility contract first proves otherwise.

A future review may reconsider only the smaller pure mutation-scan helper after
separate authorization adds a committed compatibility matrix. That prerequisite
is not an implementation authorization, and this task creates no implementation
Issue.

## Migration, dependency, and rollback decisions

- Migration: none; persisted schema and Alembic revisions remain unchanged.
- Dependency: none; SQLAlchemy remains the existing dependency.
- Runtime/import changes: none.
- Rollback for this characterization: revert this documentation only; no data
  repair or schema action is required.
- A future source-only candidate, if independently authorized, must remain
  reversible by source reversion with no data repair.

## Diagnostic limitations

- No live PostgreSQL diagnostic ran locally.
- Private SQLAlchemy dispatch registry inspection was used only as ephemeral
  evidence; production code must not depend on that private API.
- The import-order probes used supported Python package imports. They did not
  bypass `industry_alpha/__init__.py` or manually manipulate `sys.modules`.
- Failed reload observations are diagnostic only; behavior after such a failure
  is not guaranteed or supported.
- No multi-process or `pytest-xdist` mapper/listener experiment was run.
- No persistent database or user data was mutated.

## Explicit non-goals

This report does not authorize listener consolidation, mapped-class factory
consolidation, model or import rewiring, database-level append-only triggers,
bulk-DML interception, schema or migration changes, dependency changes, API or
runtime behavior, provider work, canonical-price work, v0.6E, v0.7, release or
version changes, or any change to PR #38.
