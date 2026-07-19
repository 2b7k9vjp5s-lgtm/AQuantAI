# Stage 2 Consolidation Characterization

## Status

This report is the design record for Stage 2 consolidation.

- Architecture characterization: accepted in PR #75.
- First implementation slice: accepted in PR #77.
- Accepted `main` commit after implementation: `4b6377169fabb8eef5f1b421e8f008a11582f8a9`.
- Migration decision: no migration.

The report records completed work and remaining candidates. It does not authorize another implementation.

## Accepted dependency correction

Before PR #77, v0.6D quality-judgment commands imported shared private mechanics from the v0.6C catalyst/risk command module.

The accepted direction is now:

```text
industry_alpha.stage2_boundary
  <- v0.6C catalyst/risk commands
  <- v0.6D quality-judgment commands
```

`industry_alpha.stage2_boundary` owns the exact v0.6A/v0.6B base-boundary mechanics shared by v0.6C and v0.6D.

## Implemented neutral contract

```python
@dataclass(frozen=True)
class Stage2BaseBoundary:
    research_revision: Stage2CompanyResearchRevision
    hypotheses: tuple[Stage2FinancialHypothesisRevision, ...]
    expectations: tuple[Stage2MarketExpectationRevision, ...]
    valuations: tuple[Stage2ValuationSnapshotRevision, ...]
    claims: tuple[ClaimRevision, ...]
    evidence: tuple[tuple[ClaimRevision, ClaimEvidenceLink, EvidenceItem], ...]
```

The neutral module now owns:

- exact unique revision loading;
- company-research row locking;
- stored UTC normalization;
- cutoff and recorded-time visibility checks;
- command time-boundary validation;
- exact v0.6A/v0.6B boundary construction.

The implementation preserved SQL locking, transaction boundaries, deterministic ordering, exception classes and validation messages, exact claim/evidence membership, cutoff chronology, command signatures, payload contracts, fixtures and Alembic metadata.

## Responsibilities that remain local

v0.6C continues to own:

- catalyst/risk categories and status semantics;
- assessment revision construction;
- assessment chronology and evidence rules;
- assessment links, revision locks and conflict translation.

v0.6D continues to own:

- judgment kinds, outcomes, evidence states and confidence rules;
- the exact catalyst/risk extension boundary;
- judgment revision construction;
- judgment links, revision locks and conflict translation.

No repository, query, model, listener, fixture, API or schema was consolidated in PR #77.

## Remaining structural repetition

### Repository loading

All four Stage 2 repository families contain ordered `SELECT ... WHERE ... IN (...)` loading patterns. v0.6C and v0.6D also contain linked-row helpers.

A small ordered-row primitive may be shareable. A generic Stage 2 graph loader is not justified because each stage loads a different graph and provenance boundary.

This is the next characterization candidate. Before implementation, review must establish identical SQL shape, ordering, duplicate and missing-row behavior, session behavior, and SQLite/PostgreSQL compatibility.

### Query visibility and serialization

Query modules repeat stored-UTC normalization, recorded visibility, dual cutoff/revision visibility, date/UTC formatting and UUID sorting.

Those pure functions may be later candidates. Evidence payload assembly remains domain-sensitive and needs an explicit neutral read contract before extraction.

### Command lifecycle and concurrency

v0.6B-v0.6D repeat process-local revision locks and integrity-error translation. These mechanisms affect concurrency, rollback and error compatibility and remain deferred.

### Models and append-only listeners

v0.6C and v0.6D repeat frozen-link model construction and `Session.before_flush` append-only listeners.

Centralization can affect mapper import order, event registration, metadata and error behavior. This is high risk and may remain duplicated.

### Fixtures and tests

Each slice has deterministic fixtures and SQLite/PostgreSQL coverage. Future consolidation should reuse existing golden paths and separate shared invariant tests from domain-semantic tests.

## Current classification

| Mechanism | Current decision |
| --- | --- |
| Shared v0.6A/v0.6B frozen boundary | Completed in PR #77 |
| UTC and visibility helpers required by that boundary | Completed in PR #77 |
| v0.6C and v0.6D domain semantics | Remain local |
| Ordered repository row loading | Next characterization candidate |
| Generic evidence graph repository | Not justified |
| Query date/UTC/UUID formatting | Later characterization candidate |
| Evidence read serialization | Requires a neutral contract |
| Integrity translation | Deferred |
| Revision allocation and lock strategy | Deferred |
| Dynamic model factories | Deferred, ORM-sensitive |
| Append-only listener registration | Deferred, ORM-sensitive |
| Schema and migrations | No change required |

## First-slice acceptance evidence

Issue #76 and PR #77 established:

- one immutable boundary type used by v0.6C and v0.6D;
- removal of the v0.6D import dependency on v0.6C private command helpers;
- unchanged public command behavior and domain validation;
- unchanged repository, query, model, API, fixture and migration boundaries;
- focused compatibility tests;
- successful full GitHub Actions test and local fixture-demo workflow.

The implementation can be reverted as a source-only change. It requires no database downgrade or data repair.

## Remaining candidates

Separate reviewed work may later consider:

1. ordered repository row-loading primitives;
2. cutoff/UTC/date/UUID query formatting;
3. a neutral evidence read contract;
4. conflict and integrity primitives;
5. revision allocation and lock strategy;
6. append-only listener registration.

Completion of PR #77 is not blanket authorization for these items.

## Next gate

Issue #78 is documentation synchronization only. The next code candidate begins with a separate characterization of ordered repository row loading. Implementation requires a later accepted Issue with exact scope, compatibility evidence and stop conditions.

v0.6E, v0.7 and new migrations remain unauthorized.
