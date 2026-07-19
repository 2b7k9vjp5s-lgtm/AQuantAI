# Stage 2 Consolidation Characterization

## Status

This report characterizes merged v0.6A-v0.6D infrastructure on `main` after architecture-baseline merge `09c33f6b2da2432ec18e0dd104931a5879d2f5d6`.

It is a design and risk assessment. It does not authorize refactoring or feature work.

## Executive decision

The first safe consolidation slice should be narrowly limited to extracting the neutral v0.6A/v0.6B frozen-boundary mechanics currently shared by v0.6C and v0.6D.

The immediate problem is not simply duplicated code. `industry_alpha/stage2_judgments_commands.py` imports a typed boundary and several underscore-prefixed implementation helpers directly from `industry_alpha/stage2_assessments_commands.py`. This creates an incorrect dependency direction:

```text
v0.6D quality judgments
  -> private implementation inside v0.6C catalyst/risk commands
```

The intended direction is:

```text
neutral Stage 2 frozen-boundary mechanics
  <- v0.6C catalyst/risk commands
  <- v0.6D quality-judgment commands
```

The first implementation must not also consolidate repositories, query serializers, model factories, SQLAlchemy append-only listeners, revision locks, schemas or migrations.

## Reviewed implementation families

| Stage | Primary domain | Models | Commands | Repository | Query | Main tests |
| --- | --- | --- | --- | --- | --- | --- |
| v0.6A | company research and financial hypotheses | `stage2_models.py` | `stage2_commands.py` | `stage2_repository.py` | `stage2_query.py` | `test_stage2_company_research.py`, PostgreSQL counterpart |
| v0.6B | expectations and valuation observations | `stage2_expectations_models.py` | `stage2_expectations_commands.py` | `stage2_expectations_repository.py` | `stage2_expectations_query.py` | `test_stage2_expectations_valuation.py`, PostgreSQL counterpart |
| v0.6C | catalyst and risk assessments | `stage2_assessments_models.py` | `stage2_assessments_commands.py` | `stage2_assessments_repository.py` | `stage2_assessments_query.py` | `test_stage2_catalyst_risk_assessments.py`, PostgreSQL counterpart |
| v0.6D | industry and company quality judgments | `stage2_judgments_models.py` | `stage2_judgments_commands.py` | `stage2_judgments_repository.py` | `stage2_judgments_query.py` | `test_stage2_quality_judgments.py`, PostgreSQL counterpart |

Each slice also has a fixture module, contracts, an offline demo or research-flow participation, API routes and migration-registration changes.

## Observed structural repetition

### 1. Identity and revision lifecycle

The command families repeatedly implement this transaction shape:

1. normalize recorded time and information cutoff;
2. lock or load the company-research identity;
3. create or lock a domain identity;
4. validate an exact frozen upstream boundary;
5. find the prior revision;
6. allocate `revision_no` and `supersedes_revision_id`;
7. insert the revision;
8. insert exact frozen links;
9. flush and commit atomically;
10. translate integrity failures to evidence-ledger conflicts.

This repetition is partly mechanical and partly domain-specific. The transaction shell is similar, but the allowed upstream states, required links and semantic fields differ materially.

### 2. Revision locks and integrity translation

v0.6B, v0.6C and v0.6D each maintain a process-local lock registry keyed by domain kind and identity UUID. They also translate `IntegrityError` into domain conflict errors.

These mechanisms look shareable, but they participate in concurrency behavior and error compatibility. They are deferred from the first slice.

### 3. Frozen upstream boundary validation

v0.6C introduces a typed `_Boundary` containing:

- exact v0.6A company-research revision;
- exact accepted hypothesis revisions;
- exact v0.6B expectation revisions;
- exact v0.6B valuation revisions;
- exact claim revisions;
- exact claim/evidence-link/evidence tuples.

Its `_frozen_boundary` routine also validates company ownership, exact revision membership, status eligibility, cutoff visibility, UTC chronology and exact claim/evidence provenance.

v0.6D needs the same v0.6A/v0.6B base boundary before adding exact v0.6C catalyst/risk revisions. Instead of depending on a neutral module, it imports these private v0.6C command symbols:

- `_Boundary`;
- `_frozen_boundary`;
- `_load_unique`;
- `_locked_research`;
- `_required_text`;
- `_stored_utc`;
- `_time_boundary`;
- `_visible_upstream`.

This is the highest-priority coupling to remove.

### 4. Repository row loading

All four repository families implement ordered `SELECT ... WHERE field IN (...)` helpers. v0.6C and v0.6D also implement generic linked-row loaders. v0.6B has a repeated evidence graph loader, while v0.6A performs a larger handoff graph load.

Representative differences matter:

- v0.6A loads Stage 1 candidate-pool, beneficiary, industry-map and ingestion provenance;
- v0.6B additionally loads optional local daily-price and ingestion-run context;
- v0.6C loads one assessment graph with hypothesis/expectation/valuation/claim/evidence links;
- v0.6D loads a larger judgment graph including catalyst and risk links.

A small ordered-row helper is mechanically common. A generic “load any Stage 2 graph” abstraction is not yet justified.

Repository consolidation is not part of the first slice.

### 5. Query visibility and evidence serialization

The query modules repeatedly implement:

- stored-UTC normalization;
- recorded-at visibility;
- dual cutoff/revision visibility;
- ISO date and UTC timestamp formatting;
- UUID list sorting;
- claim/evidence payload assembly;
- grade counts;
- conflicts and missing-evidence lists;
- list/detail history selection.

The v0.6B and v0.6D evidence serializers are structurally similar but not identical. v0.6D exposes claim-kind and inference provenance added by later acceptance work, while missing-evidence wording and notices are domain-specific.

Shared pure formatting and visibility helpers are plausible later candidates. A shared evidence payload builder needs an explicit contract before extraction.

Query consolidation is not part of the first slice.

### 6. Model factories and append-only listeners

v0.6C and v0.6D both dynamically construct multiple frozen-link model classes and register separate `Session.before_flush` listeners to reject updates and deletes.

The persisted table names, foreign keys, check constraints and model registration are already stable. Centralizing these factories or listeners can affect SQLAlchemy mapper import order, event registration, migration metadata and exception behavior.

Model and listener consolidation is deferred.

### 7. Fixtures and tests

Each Stage 2 slice adds deterministic fixture identities and dedicated SQLite/PostgreSQL tests. Later slices also run earlier PostgreSQL tests as migration and compatibility regression coverage.

The test structure provides strong behavior protection, but it also expands the cross-product matrix. The first extraction should rely on existing v0.6C/v0.6D suites plus a small direct unit test for the new neutral boundary module. It should not rewrite the fixture architecture.

## Classification matrix

| Mechanism | Classification | Decision |
| --- | --- | --- |
| Stored UTC normalization and upstream visibility checks | Safe pure extraction | Include only as needed by the neutral boundary module |
| Exact unique upstream revision loading | Safe pure extraction | Include in first slice with unchanged validation/error behavior |
| Company-research row locking | Safe pure extraction with SQL statement preserved | Include in first slice |
| Typed v0.6A/v0.6B base boundary | Shareable after neutral contract | Make this the central first-slice contract |
| Base-boundary construction | Shareable after neutral contract | Move from v0.6C ownership to neutral Stage 2 ownership |
| Required non-empty bounded text validation | General validation concern | Prefer existing `industry_alpha.validation` or a tiny neutral helper; do not leave v0.6D importing it from v0.6C |
| v0.6C assessment status validation | Domain-specific | Keep in `stage2_assessments_commands.py` |
| v0.6D outcome/evidence-state validation | Domain-specific | Keep in `stage2_judgments_commands.py` |
| v0.6D catalyst/risk extension boundary | Domain-specific | Keep in v0.6D |
| Revision lock registry | Deferred concurrency-sensitive infrastructure | Do not move in first slice |
| Latest revision allocation | Deferred concurrency-sensitive infrastructure | Do not move in first slice |
| Integrity translation context manager | Potentially shareable | Defer until command lifecycle contract is reviewed |
| Repository `_rows`/`_linked` helpers | Safe but lower priority | Defer to a later read-infrastructure slice |
| Evidence graph repository loader | Requires neutral contract | Defer |
| Query date/time/UUID formatting | Safe but lower priority | Defer |
| Evidence read serialization | Requires neutral contract | Defer |
| Dynamic link model factories | ORM/schema-sensitive | Defer |
| Append-only `before_flush` listeners | ORM event-sensitive | Defer |
| Database schemas and migrations | Not needed | No change |
| Domain contracts and API notices | Domain-specific | Keep local |

## Proposed neutral boundary contract

The first later implementation should introduce one neutral module, provisionally:

```text
industry_alpha/stage2_boundary.py
```

The exact exported names should be reviewed in the implementation Issue, but the responsibilities should remain bounded.

### Neutral typed value

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

This is the exact v0.6A/v0.6B boundary consumed by both v0.6C and v0.6D. It does not include catalyst, risk or judgment semantics.

### Neutral operations

The module may expose reviewed operations equivalent to the current behavior:

- lock and return one `Stage2CompanyResearch` row;
- load a deduplicated exact tuple of requested revision IDs;
- normalize stored datetimes to UTC;
- validate upstream information-cutoff and recorded-time visibility;
- construct `Stage2BaseBoundary` from exact IDs and existing frozen links.

The extraction must preserve:

- exact SQL locking behavior;
- ID deduplication and ordering behavior;
- all current validation messages unless an Issue explicitly authorizes message changes;
- accepted `supported`/`disputed` upstream requirements currently shared by v0.6C/v0.6D;
- exact claim, evidence-link and evidence membership;
- cutoff and UTC anti-leakage checks.

### Responsibilities that remain outside the neutral module

`stage2_assessments_commands.py` retains:

- catalyst/risk categories;
- assessment status semantics;
- catalyst/risk revision construction;
- assessment-specific chronology labels;
- assessment link insertion;
- assessment status/evidence validation;
- assessment revision locking and conflict translation.

`stage2_judgments_commands.py` retains:

- industry/company judgment kinds;
- outcome, evidence-state and confidence rules;
- catalyst/risk exact-extension validation;
- judgment-specific chronology;
- judgment revision construction and link insertion;
- judgment revision locking and conflict translation.

v0.6A and v0.6B commands remain unchanged in the first slice. Their boundary semantics should not be retrofitted merely to increase reuse.

## First implementation slice

### Scope

A later implementation Issue should authorize only:

1. add the neutral Stage 2 boundary module;
2. move or reproduce the reviewed shared mechanics without semantic change;
3. update v0.6C to consume the neutral module;
4. update v0.6D to consume the neutral module and eliminate all imports from `stage2_assessments_commands.py` that represent shared base-boundary mechanics;
5. add focused direct tests for the neutral boundary contract;
6. run all existing v0.6C/v0.6D SQLite and PostgreSQL tests and the full offline suite.

### Explicit exclusions

The first implementation must not:

- change any SQLAlchemy model or table;
- add a migration;
- rewrite persisted rows;
- change API contracts or payload ordering;
- alter fixture IDs or contents;
- consolidate repositories or query services;
- consolidate model factories or append-only listeners;
- change revision locks or revision-number allocation;
- change status, outcome, evidence-state or eligibility semantics;
- introduce v0.6E, price evidence, valuation comparison, v0.7 or UI work.

## No-migration decision

The first extraction is Python source organization only.

Required migration decision: **no migration**.

There is no table, column, constraint, index, foreign key, enum-like check, persisted value, revision number or API schema change.

## Golden path for the later implementation

A production-realistic offline success path already exists through the accepted deterministic Stage 2 fixture:

1. exact v0.6A company-research revision;
2. exact supported/disputed hypotheses frozen by that revision;
3. exact v0.6B expectation/valuation revisions accepted by the same research boundary;
4. exact claims and evidence frozen by those v0.6B revisions;
5. v0.6C creates a catalyst or risk assessment;
6. v0.6D uses the same neutral base boundary and adds exact accepted v0.6C revisions;
7. current and historical read payloads remain byte-for-byte structurally equivalent after strict JSON serialization.

The refactor is accepted only when this path and existing rejection paths behave unchanged.

## Compatibility proof required

The later implementation must prove:

- v0.6D no longer imports shared mechanics from `stage2_assessments_commands.py`;
- v0.6C and v0.6D use the same neutral typed base-boundary contract;
- existing command method signatures are unchanged;
- existing exception classes and messages are unchanged unless explicitly documented;
- no table metadata or Alembic head changes;
- SQLite and PostgreSQL revision allocation/concurrency tests remain green;
- transaction rollback leaves zero partial rows on every existing failure path;
- existing list/detail payloads, histories, conflicts, missing-evidence output and ordering remain unchanged;
- full no-network behavior remains unchanged.

## Rollback strategy

Rollback is a pure source reversion:

1. restore the shared functions and boundary dataclass to `stage2_assessments_commands.py`;
2. restore the prior imports in `stage2_judgments_commands.py`;
3. remove the neutral module and its focused tests.

No database downgrade, data repair, fixture regeneration or API migration is required.

## Later candidates, not yet authorized

After the boundary extraction is accepted, separate characterization or implementation Issues may consider:

1. shared ordered repository row-loading primitives;
2. shared cutoff/UTC/date/UUID query formatting;
3. a neutral evidence read-serialization contract;
4. command conflict/integrity primitives;
5. revision allocation and lock strategy;
6. append-only listener registration.

Each must be independently justified. The current report does not authorize them.

## Stop condition

This report completes characterization only. Do not create `stage2_boundary.py`, update application imports or begin any refactor until this report is reviewed, accepted and followed by a separate implementation Issue.