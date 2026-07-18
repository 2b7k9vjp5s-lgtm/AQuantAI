# Issue #55 — v0.5A Research Case And Evidence Ledger Foundation

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#55 [v0.5A] Research case and evidence ledger foundation`
- Branch: `feat/v05a-evidence-ledger`
- Draft PR title: `[v0.5A] Add research evidence ledger`
- Required ancestor: v0.4E squash merge `dcd632040dd91340dbed94a34a5f11a532cf1832`
- Project version must remain `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #55, this task, the accepted product architecture, current persistence conventions, Alembic history, FastAPI route conventions, and current CI before editing.

Keep the PR Draft. Do not merge, close Issue #55, create a release/tag, change the version, implement later v0.5 slices, or modify PR #38.

## Product boundary

Implement the first bounded v0.5 Industry Alpha foundation: a local, append-only, cutoff-aware research-case and evidence ledger.

The ledger records human-entered or deterministic fixture research material. It does not fetch, scrape, summarize, score, recommend, or trade. All normal imports, application startup, tests, demos, and read-only requests must remain network-free.

This slice must not claim that an industry is attractive, that a company benefits, or that a market/industry conclusion is correct. It establishes auditable records and validation rules only.

## Authorized architecture

Add one focused `industry_alpha` domain/application module that follows the existing dependency direction:

```text
FastAPI read routes
  -> Industry Alpha query/application services
  -> repository interface / SQLAlchemy repository
  -> PostgreSQL models
```

Command services may be used by tests and an explicit offline fixture demo. Do not expose browser or public HTTP mutation endpoints in this slice.

Use existing database/session/configuration conventions. Do not add a second ORM, second database, cache, queue, scheduler, provider adapter, vector database, or background worker.

## Required persistence model

Use stable UUID identities and immutable append-only ledger rows. Exact SQLAlchemy names may follow repository conventions, but the relational meaning must be preserved.

### 1. Research case identity

`research_cases` contains only stable identity metadata:

- `id` UUID primary key;
- caller-supplied unique `case_key` suitable for deterministic fixtures;
- `created_at_utc` timezone-aware timestamp;
- optional immutable `origin` enum/string limited to reviewed values such as `manual` and `fixture`.

Do not store mutable title, workflow state, or conclusion state on this identity row.

### 2. Research case revisions

`research_case_revisions` is immutable and append-only:

- UUID primary key;
- `case_id` foreign key;
- `revision_no` positive integer, unique per case;
- `title`;
- `research_question`;
- optional `summary`;
- `workflow_state` enum: `open`, `paused`, `completed`, `archived`;
- `conclusion_status` enum: `unassessed`, `insufficient_evidence`, `supported`, `disputed`, `rejected`;
- `information_cutoff_date` date;
- `recorded_at_utc` timezone-aware timestamp;
- optional `supersedes_revision_id`, which when present must refer to the immediately previous revision of the same case.

Workflow state and conclusion status are separate fields and must never be inferred from each other.

Revision numbers are assigned transactionally as `max(existing revision_no) + 1` under a concurrency-safe per-case strategy. Concurrent appends must not create duplicate revision numbers or silently overwrite one another.

### 3. Evidence items

`evidence_items` is immutable:

- UUID primary key;
- `case_id` foreign key;
- evidence grade enum `A`, `B`, `C`, `D`;
- bounded reviewed `source_kind` enum/string;
- `source_title`;
- optional `publisher_or_author`;
- optional `source_locator` stored only as user-provided text; never fetched automatically;
- `information_date` date;
- `recorded_at_utc` timezone-aware timestamp;
- concise `summary`;
- optional `content_fingerprint` for caller-provided deterministic deduplication;
- optional `supersedes_evidence_id` restricted to evidence in the same case.

If a content fingerprint is supplied, enforce deterministic uniqueness within the case. Do not store raw provider payloads, credentials, headers, local secret paths, or downloaded documents.

Evidence grading semantics:

- `A`: primary official, regulatory, filing, statistical-authority, or directly attributable first-party evidence;
- `B`: reputable attributable secondary research, media, or industry evidence with a discernible method;
- `C`: attributable indirect or tertiary context evidence;
- `D`: unverified lead, rumor, community/social assertion, or concept-stock list.

The system records the user-assigned grade; it does not automatically upgrade or downgrade evidence.

### 4. Claim identities and revisions

`claims` contains stable identity only:

- UUID primary key;
- `case_id` foreign key;
- caller-supplied unique `claim_key` within the case;
- `created_at_utc`.

`claim_revisions` is immutable:

- UUID primary key;
- `claim_id` foreign key;
- `revision_no` positive integer unique per claim;
- `statement`;
- `claim_kind` enum: `fact`, `inference`;
- `claim_status` enum: `draft`, `supported`, `disputed`, `rejected`;
- optional `inference_confidence` enum: `low`, `medium`, `high`;
- optional `inference_basis`;
- `information_cutoff_date` date;
- `recorded_at_utc` timezone-aware timestamp;
- optional `supersedes_revision_id` restricted to the immediately previous revision of the same claim.

Exact validation:

- fact claims must have `inference_confidence = null` and `inference_basis = null`;
- inference claims require non-empty confidence and non-empty basis in every revision;
- `supported` is not valid unless the exact claim revision has at least one visible `supports` link to A/B/C evidence;
- D-only support is never sufficient for `supported`;
- `disputed` requires at least one visible `contradicts` link;
- a claim revision with visible contradictory evidence cannot be promoted to `supported`; append a new revision after the conflict is addressed instead;
- draft claims may exist before evidence is linked;
- corrections append a revision; no statement or status is overwritten.

Because links may be added after a draft revision is created, provide one transactional command that appends a new claim revision and its evidence links atomically when changing status to `supported`, `disputed`, or `rejected`.

### 5. Claim/evidence links

`claim_evidence_links` is immutable:

- UUID primary key;
- `claim_revision_id` foreign key;
- `evidence_id` foreign key;
- relation enum: `supports`, `contradicts`, `context`;
- optional concise `link_note`;
- `recorded_at_utc` timezone-aware timestamp;
- unique `(claim_revision_id, evidence_id, relation)`.

The claim revision and evidence item must belong to the same research case.

Contradictory evidence must remain visible in reads. Do not delete or suppress it because a later claim revision changes status.

### 6. Case revision claim membership

`case_revision_claim_links` freezes the exact claim revisions used by a case revision:

- UUID primary key;
- `case_revision_id` foreign key;
- `claim_revision_id` foreign key;
- role enum: `conclusion`, `context`, `risk`;
- unique `(case_revision_id, claim_revision_id, role)`.

Both revisions must belong to the same research case.

For a case revision with `conclusion_status = supported`:

- at least one linked `conclusion` claim revision is required;
- every linked `conclusion` claim revision must have `claim_status = supported`;
- no linked conclusion claim may contain visible contradictory evidence;
- every supported conclusion claim must have at least one A/B/C supporting evidence link.

For `conclusion_status = disputed`, at least one linked conclusion claim must be disputed or have contradictory evidence.

`unassessed`, `insufficient_evidence`, and `rejected` must remain explicit states; do not derive a recommendation or score from them.

### 7. Follow-up verification checklist

`verification_items` is append-only and belongs to a specific case revision:

- UUID primary key;
- `case_revision_id` foreign key;
- positive deterministic `item_no` unique per case revision;
- non-empty `description`;
- status enum: `open`, `completed`, `deferred`;
- optional `due_date`;
- `recorded_at_utc` timezone-aware timestamp.

A case revision with `workflow_state = completed` must be created atomically with at least one verification item. The read contract must label this collection `后续验证清单` as well as expose a stable English field name.

This slice does not add reminder delivery, automatic notifications, or a general watchlist task system.

## Append-only behavior

Expose no repository or service method that updates or deletes accepted ledger rows. State changes happen through new revisions or new checklist rows.

Add narrow ORM/service guards so an attempted update/delete through the application repository fails clearly and rolls back. Direct database-administrator SQL is outside the product boundary, but ordinary application code must not have a destructive ledger path.

All multi-row commands are transactional. Validation failure, duplicate keys, cross-case links, invalid state promotion, or revision conflict must leave no partial rows.

## Cutoff-aware query semantics

Provide one deterministic query model for a complete case ledger.

For `as_of_cutoff = D`, a row is visible only when both conditions hold:

```text
row.information_cutoff_date or row.information_date <= D
DATE(row.recorded_at_utc in UTC) <= D
```

For rows without a separate information date, use the parent revision/evidence visibility plus their own recorded date.

The query must:

- choose the latest visible case revision by revision number;
- choose the latest visible revision for each visible claim;
- include only evidence visible by both information date and recorded date;
- include only links whose own recorded date and both endpoints are visible;
- include only case-revision claim links and verification items whose recorded dates are visible;
- retain complete visible historical revisions in an explicit history collection;
- never reveal later corrections, links, conflicts, or evidence in an earlier cutoff view.

When `as_of_cutoff` is omitted, use the complete currently recorded ledger. Do not use the current wall-clock date as a hidden information cutoff.

Use deterministic ordering:

- cases by `case_key`, then UUID;
- revisions by revision number;
- claims by `claim_key`, then revision number;
- evidence by information date, recorded timestamp, then UUID;
- links by claim key/revision, relation, evidence UUID;
- verification items by item number.

## Read-only API

Add backward-compatible routes under a focused prefix:

```text
GET /industry-alpha/cases
GET /industry-alpha/cases/{case_id}
```

Supported query parameter:

```text
as_of_cutoff=YYYY-MM-DD
```

The list route returns stable identity, latest visible revision summary, counts, and cutoff metadata. The detail route returns:

- case identity and provenance;
- latest visible case revision;
- visible case revision history;
- current visible claims plus claim histories;
- evidence items and grades;
- claim/evidence relations;
- explicit conflict entries derived from visible `contradicts` links;
- frozen case-revision claim membership;
- `verification_items` and `后续验证清单` label metadata;
- validation/read-only disclaimers.

Use existing FastAPI error/status conventions. A missing case is 404. A syntactically invalid cutoff is 422. A valid cutoff with no visible revision returns a typed unavailable/not-visible response or reviewed 404 behavior consistently; document and test the chosen behavior.

Do not add POST, PUT, PATCH, or DELETE routes in v0.5A. Do not add a browser editing form or trading action.

## Contracts and strict serialization

Use typed Pydantic/dataclass contracts consistent with the repository. All response objects must be strict JSON-safe and deterministic.

Reject or normalize invalid text at command boundaries. Define reviewed maximum lengths for keys, titles, statements, summaries, source locators, notes, and checklist descriptions. Do not return NaN, Infinity, raw SQLAlchemy objects, local paths, secrets, or stack traces.

Expose factual labels explaining:

- evidence grades are user-assigned provenance classifications;
- D-grade evidence cannot independently support a conclusion;
- conflicts and missing evidence remain visible;
- the ledger is research record-keeping, not investment advice.

## Offline fixture/demo

Add a deterministic offline demo that builds or exercises one bounded fixture ledger containing:

- one research case;
- at least two case revisions;
- one fact claim and one inference claim;
- A/B/C support evidence;
- one D-grade lead that cannot independently support a claim;
- one contradictory evidence link;
- one completed case revision with a non-empty `后续验证清单`;
- a current view and an earlier cutoff view proving no later-information leakage.

Follow existing demo conventions. It may use the configured local PostgreSQL test database or a reviewed in-memory repository abstraction, but must never call the network or mutate production-like external systems.

## Migration and compatibility

Add exactly one forward Alembic revision after current head `20260718_0004` unless repository inspection proves a newer accepted head exists. Choose the actual revision identifier according to project convention.

Migration requirements:

- all tables, constraints, indexes, enums/checks, and foreign keys are explicit;
- downgrade removes only v0.5A objects in safe dependency order;
- clean `base -> head`, upgrade from current accepted head, downgrade/upgrade round trip, and `alembic check` pass;
- no change to v0.3-v0.4 market-data tables or semantics.

Preserve all existing APIs, Market Cockpit behavior, Quant Core behavior, launchers, Docker/Compose behavior, and fixture demos.

## Documentation

Update only relevant documents:

- `docs/implementation_plan.md`: add a short v0.5A authorized-slice paragraph;
- `docs/product_architecture.md`: mark v0.4E merged and v0.5A evidence ledger in review;
- add a focused Industry Alpha evidence-ledger document covering tables, lifecycle/conclusion separation, evidence grades, cutoff semantics, conflict visibility, append-only rules, API, and exclusions;
- update local API/demo usage only where needed.

Do not rewrite later v0.5-v0.9 roadmap stages.

## Expected implementation surface

Expected files are limited to a focused additive surface such as:

- new `industry_alpha/` contracts, validation, repository/service, and query modules;
- existing backend/FastAPI route registration only where necessary;
- existing datasource/database model and session registration only where necessary;
- one Alembic migration;
- deterministic fixture/demo;
- focused tests;
- the narrow documentation above.

Do not modify:

- AKShare/provider adapters or ingestion commands;
- Market Cockpit calculations;
- Quant Core factor/ranking/backtest/ML behavior;
- dependencies unless an already-installed dependency cannot meet the reviewed design; stop and report before adding one;
- Docker/Compose, CI, launchers, version files, release/tag configuration;
- PR #38.

## Required tests

Add deterministic tests for at least:

1. case creation and initial revision;
2. separate workflow and conclusion states;
3. deterministic revision numbering;
4. concurrent same-case revision append behavior;
5. immutable update/delete rejection;
6. evidence A/B/C/D validation;
7. deterministic content-fingerprint uniqueness;
8. fact versus inference field validation;
9. inference basis/confidence requirements;
10. D-only support cannot create a supported claim;
11. A/B/C support can create a supported claim;
12. contradictory evidence blocks supported promotion;
13. disputed claim requires contradiction;
14. cross-case claim/evidence link rejection;
15. case revision freezes exact claim revisions;
16. supported case conclusion validation;
17. disputed case conclusion validation;
18. completed workflow requires non-empty verification checklist;
19. deterministic checklist numbering;
20. full transaction rollback for invalid multi-row commands;
21. current ledger deterministic ordering;
22. earlier cutoff excludes later evidence, revisions, links, conflicts, and checklist rows;
23. information date earlier but recorded later does not leak into an earlier cutoff;
24. strict JSON serialization;
25. list and detail API success;
26. invalid cutoff and missing/not-visible case behavior;
27. no mutation HTTP routes;
28. migration base-to-head, current-head upgrade, downgrade/upgrade, and check;
29. PostgreSQL constraints and transaction isolation;
30. all existing v0.2-v0.4 APIs, tests, demos, startup, and no-network behavior.

## Validation

Run and report exact results for:

- focused Industry Alpha domain/service/repository tests;
- focused API/serialization tests;
- focused migration tests;
- complete offline test suite;
- PostgreSQL-enabled complete suite using an isolated temporary database;
- clean Alembic `base -> head`;
- upgrade from accepted `20260718_0004` head to the new revision;
- downgrade/upgrade round trip for the new revision;
- `python -m alembic check`;
- the new evidence-ledger demo in current and historical-cutoff modes;
- all existing research and Market Cockpit demos;
- no-network import/startup/page tests;
- `python -m compileall -q backend datasource market_cockpit industry_alpha scripts`;
- `git diff --check`;
- final GitHub Actions for the implementation Head.

All tests and demos must remain offline. Do not make a live provider or LLM call.

## GitHub handoff

After implementation:

1. Update Draft PR #56 with final Head, exact files, schema, command/query rules, cutoff semantics, validation results, and CI.
2. Add concise PR #56 and Issue #55 comments with the same final handoff.
3. Keep PR #56 Draft, open, and unmerged.
4. Keep Issue #55 open.
5. Stop for ChatGPT review.

Do not mark Ready, merge, close Issue #55, create a release/tag, change version `0.2.0`, begin v0.5B/Stage 1 scoring or mapping, or modify PR #38.