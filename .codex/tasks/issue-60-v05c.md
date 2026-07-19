# Issue #60 — v0.5C Evidence-Backed Stage 1 Beneficiary Classification

## State

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#60`
- Branch: `feat/v05c-stage1-beneficiaries`
- Draft PR: `[v0.5C] Add evidence-backed Stage 1 beneficiary classifications`
- Required base and ancestor: `61c13b5f88c0eea8208a2c9031adf322789e1c42`
- Version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #60, merged v0.5A/v0.5B models, migrations, docs, tests and current CI before editing.

Keep the PR Draft/Open/unmerged and Issue #60 Open. Do not modify PR #38, create a release/tag, change version, or begin v0.6.

## Objective

Implement one bounded, local, append-only and cutoff-aware Stage 1 beneficiary-classification foundation. Connect exact v0.5B frozen map assertions to exact persisted company snapshot identities and exact v0.5A claim revisions, then freeze eligible supported classifications into a Stage 2 candidate-pool handoff.

This slice creates research records only. It does not perform company deep dives, financial-transmission analysis, valuation, ranking, recommendations or trading.

## Required domain

Add stable identities and immutable revisions for:

1. A beneficiary identity belonging to one research case and one industry map, keyed by canonical `source` + `stock_code`.
2. Beneficiary revisions with sequential revision number, `beneficiary_kind`, `assessment_status`, bounded rationale summary, information cutoff, recorded UTC timestamp and supersedes pointer.
3. Exact links from each beneficiary revision to at least one v0.5B node, relationship or observation revision.
4. Exact links from each beneficiary revision to at least one v0.5A claim revision.
5. A candidate-pool identity belonging to the same research case/map.
6. Candidate-pool revisions with title/scope, cutoff, recorded timestamp and supersedes pointer.
7. Candidate-pool memberships freezing exact beneficiary revisions.

Reviewed beneficiary kinds:

- `direct`
- `secondary`
- `potential`

Reviewed assessment statuses:

- `draft`
- `supported`
- `disputed`
- `rejected`

Use the existing `stock_basic` persistence. A beneficiary revision must record or link the exact visible `StockBasicRecord` used for company name, exchange and listing metadata. Do not introduce a second market-data/company master or a new provider.

## Evidence and map boundary

- Every beneficiary revision must link exact v0.5A claim revisions from the same research case.
- Every beneficiary revision must reference exact v0.5B assertion revisions contained in the selected map revision.
- `supported` requires at least one visible supported A/B/C-backed claim, no visible contradiction at the beneficiary revision timestamp, and at least one exact frozen map assertion.
- D-only evidence cannot independently support a beneficiary classification.
- `disputed` requires a disputed claim or visible contradiction.
- Missing evidence, conflicts and rejected/draft states remain explicit in read contracts.
- Do not infer customers, orders, capacity, revenue exposure, market share, certification, financial transmission or beneficiary purity from names, sectors or D-grade leads.

## Candidate-pool rules

- Only exact beneficiary revisions with `assessment_status=supported` and kind `direct`, `secondary` or `potential` may be frozen into a candidate-pool revision.
- A pool revision may include at most one revision of a beneficiary identity.
- All memberships must share the same research case, industry map and selected map revision boundary.
- Candidate pools have no score, weight, rank, target price or recommendation semantics.
- Read ordering must be deterministic, such as beneficiary kind then source/stock code and stable identifier. Do not imply investment priority.

## Append-only, chronology and transactions

- Corrections append revisions; accepted identities, revisions, links and memberships cannot be updated or deleted through ordinary ORM sessions.
- Use exact timezone-aware UTC chronology.
- Beneficiary identities/revisions cannot predate the case, map, selected map revision, company snapshot, linked assertions, claims, evidence or prior revision.
- Candidate-pool revisions cannot predate the pool identity, selected map revision, beneficiary revisions, links or prior pool revision.
- Later company, assertion, claim, evidence or membership records must not rewrite earlier cutoff/frozen views.
- Multi-row commands are single transactions and fully rollback on validation, uniqueness, chronology, cross-case/map or evidence failure.
- Revision numbering must be concurrency-safe on PostgreSQL using repository conventions.

## Persistence

Add exactly one focused Alembic migration after `20260719_0006`. Reuse the existing SQLAlchemy Base, engine and session conventions. Add only the tables/indexes/constraints needed for beneficiary identities/revisions, exact map-assertion and claim bindings, candidate-pool identities/revisions and exact memberships.

Downgrade must remove only v0.5C objects in dependency-safe order. Update migration imports/tests that enumerate domain models.

## Commands and repository boundaries

Provide deterministic command services for tests and offline fixtures only. Reuse v0.5A/v0.5B validation helpers where safe, but avoid circular imports and do not weaken existing append-only or freeze protections.

All command inputs must validate strict enums, text bounds, duplicate IDs, exact ownership, cutoff visibility and UTC chronology. Translate persistence conflicts to existing domain error types and leave no partial rows after failure.

## Query and API

Provide deterministic cutoff-aware reads for:

- beneficiary list for an industry map;
- beneficiary detail with exact company snapshot, map assertions, claims, evidence, conflicts and missing-evidence summary;
- candidate-pool list;
- candidate-pool detail with frozen exact beneficiary revisions.

Expose read-only GET routes under `/industry-alpha`, preferably map-scoped beneficiary routes plus candidate-pool list/detail routes. Support optional `as_of_cutoff=YYYY-MM-DD` using dual information-date and UTC recorded-date visibility.

No POST, PUT, PATCH or DELETE HTTP routes. No browser editing UI.

Notices must state that outputs are local research classifications, not scores, rankings, recommendations or investment advice.

## Offline fixture/demo

Add one deterministic no-network fixture/demo with:

- one accepted v0.5B map snapshot;
- at least three company identities using exact local `stock_basic` rows;
- one supported direct classification;
- one supported secondary or potential classification;
- one D-only draft classification;
- one disputed classification with visible contradiction;
- one frozen candidate-pool revision containing only eligible supported revisions;
- a later revision/link excluded from an earlier cutoff view;
- strict JSON output and deterministic ordering.

The demo must use an isolated local database and must not call providers, the network or an LLM.

## Tests and validation

Cover at minimum:

- clean base-to-head, `20260719_0006 -> head`, downgrade/upgrade and `python -m alembic check`;
- stable identities, revision numbers and supersedes chains;
- exact `stock_basic` snapshot identity and visibility;
- strict beneficiary kind/status enums and text bounds;
- same-case/map enforcement and exact map-membership validation;
- exact claim and assertion bindings;
- A/B/C-supported, D-only, disputed, conflict and missing-evidence behavior;
- candidate-pool eligibility and one-revision-per-identity rules;
- chronology and historical cutoff non-leakage, including later link/evidence protection;
- append-only update/delete rejection;
- atomic rollback on every failed multi-row command;
- PostgreSQL concurrent revision numbering;
- deterministic ordering and strict JSON;
- read-only API and no mutation routes;
- no-network startup/import/test/demo behavior;
- all existing v0.2-v0.5B regressions and demos;
- `python -m compileall` for changed Python packages;
- `git diff --check`.

Run the full offline suite and the PostgreSQL suite when `TEST_DATABASE_URL` is available. Record exact pass/skip/warning counts and environment limitations in the PR and Issue.

## Documentation

Update the conceptual data model, implementation plan, product architecture and local usage docs to mark v0.5B merged and describe the exact v0.5C boundary. Add a focused beneficiary/candidate-pool document covering identities, evidence/map bindings, cutoff semantics, eligibility and exclusions.

## Exclusions

Do not add numeric scores, weights, rankings, investment-attractiveness conclusions, financial-transmission models, revenue/customer/order/capacity assumptions, Stage 2 deep dives, valuation, catalysts/risks judgments, watchlists, portfolios, recommendations, signals, LLM/provider execution, scraping, ingestion automation, brokers, orders or trading.

Do not change dependencies, Docker/Compose, CI, launchers, project version, release/tag state or PR #38.

## Delivery

1. Implement only Issue #60 on `feat/v05c-stage1-beneficiaries`.
2. Keep the PR Draft throughout implementation.
3. Update the Draft PR and Issue with base/head SHA, exact changed files, schema, evidence/map rules, cutoff semantics, demo and validation results.
4. Stop for ChatGPT review. Do not merge, close Issue #60 or begin v0.6 without explicit owner authorization.