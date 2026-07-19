# Issue #62 — v0.6A Stage 2 Company Research Foundation

## State

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#62`
- Branch: `feat/v06a-company-research`
- Draft PR: `[v0.6A] Add Stage 2 company research foundation`
- Required base and ancestor: `df6d78299d0761a6911457ca4a3b6959b195eeb4`
- Version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #62, merged v0.5A-v0.5C models, migrations, docs, tests and current CI before editing.

Keep the PR Draft/Open/unmerged and Issue #62 Open. Do not modify PR #38, create a release/tag, change version, begin v0.6B, or add valuation/ranking/recommendation behavior.

## Objective

Implement one bounded, local, append-only and cutoff-aware Stage 2 company-research foundation. Stage 2 may start only from an exact frozen v0.5C candidate-pool membership. Persist company-research file revisions and evidence-backed financial-transmission hypotheses without valuation, scoring, ranking, recommendations or trading.

## Required domain

Add stable identities and immutable revisions for:

1. A Stage 2 company-research identity belonging to one research case, industry map, candidate-pool identity and canonical company key.
2. Research-file revisions with sequential revision number, workflow state, conclusion status, research question, bounded summary, information cutoff, UTC recorded timestamp and supersedes pointer.
3. Financial-transmission hypothesis identities and revisions.
4. Exact links from each hypothesis revision to exact v0.5A claim revisions.
5. Exact membership/freeze references from the Stage 2 identity to one candidate-pool revision, one membership, one beneficiary identity/revision and one exact successful `stock_basic` record.
6. Verification items forming the mandatory `后续验证清单` for completed research-file revisions.

Research-file workflow state and conclusion status must remain separate. Reuse reviewed values from existing research-case conventions where safe; do not invent ambiguous synonyms.

Reviewed hypothesis directions:

- `positive`
- `negative`
- `mixed`
- `uncertain`

Hypothesis revisions are inferences and must include:

- explicit mechanism;
- operating metric;
- financial-statement line;
- expected lag/horizon;
- confidence;
- explicit basis;
- information cutoff and recorded UTC timestamp;
- exact claim-revision bindings.

## Exact Stage 1 handoff

A Stage 2 identity can be created only from an exact visible `stage1_candidate_pool_membership` contained in an exact candidate-pool revision.

Freeze and expose these exact references:

- candidate-pool identity and revision;
- candidate-pool membership;
- Stage 1 beneficiary identity and revision;
- selected v0.5B map revision and exact assertion links frozen by that beneficiary revision;
- exact successful `stock_basic` record and ingestion-run provenance;
- exact Stage 1 claim revisions and evidence visible at the accepted handoff boundary.

All records must share one research case, industry map and company identity. Reject non-member companies, mismatched revisions, cross-case/map references, later snapshots and non-successful ingestion runs.

No later Stage 1 beneficiary revision, membership, claim link, evidence link, assertion revision or company snapshot may rewrite an accepted Stage 2 historical view.

## Evidence rules

- Every hypothesis revision must bind at least one exact claim revision from the same research case.
- The claim/evidence boundary must be visible at both the hypothesis cutoff and hypothesis recorded timestamp.
- `supported` requires at least one visible supported A/B/C-backed claim revision and no visible contradiction.
- D-only evidence cannot independently support a hypothesis or completed Stage 2 conclusion.
- `disputed` requires a disputed claim or visible contradiction.
- Missing evidence, contradictory evidence and unsupported assumptions remain explicit in read contracts.
- Never fabricate customers, orders, capacity, market share, revenue exposure, margins, certification, operating metrics or financial impact.

A completed research-file revision must:

- contain at least one accepted hypothesis revision;
- have no silent missing-evidence state;
- include a non-empty `后续验证清单`;
- keep unresolved conflicts explicit rather than silently claiming support.

## Append-only, chronology and transactions

- Corrections append revisions; accepted identities, revisions, links and verification items cannot be updated or deleted through ordinary ORM sessions.
- Use exact timezone-aware UTC chronology.
- Stage 2 identities/revisions cannot predate the case, map, pool identity/revision, membership, beneficiary identity/revision, company snapshot/import completion, selected map revision, assertions, claims, evidence or prior revision.
- Hypothesis revisions cannot predate their identity, research-file revision boundary, linked claims/evidence or prior hypothesis revision.
- Verification items cannot predate their research-file revision; later accepted items cannot be backdated before existing accepted checklist history.
- Multi-row commands are single transactions and fully rollback on validation, uniqueness, chronology, cross-boundary or evidence failure.
- Revision numbering must be concurrency-safe on PostgreSQL using repository conventions.

## Persistence

Add exactly one focused Alembic migration after `20260719_0007`.

Reuse the existing SQLAlchemy Base, engine and session conventions. Add only the tables, indexes and constraints needed for Stage 2 company-research identities/revisions, hypothesis identities/revisions, exact claim links, exact frozen Stage 1 handoff references and verification items.

Downgrade must remove only v0.6A objects in dependency-safe order. Update migration imports/tests that enumerate domain models.

## Commands and repository boundaries

Provide deterministic command services for tests and offline fixtures only. No HTTP mutation routes.

All command inputs must validate strict strings/enums, text bounds, duplicate IDs, exact ownership, cutoff visibility, UTC chronology and frozen Stage 1 boundaries. Optional text accepts only `str | None`; required text accepts only `str`.

Translate persistence conflicts to existing domain errors and leave no partial rows after failure.

Avoid circular imports. Reuse existing evidence/chronology helpers where safe without weakening v0.5 freeze protections.

## Query and API

Provide deterministic cutoff-aware reads for:

- Stage 2 company-research list, preferably scoped by candidate-pool revision or industry map;
- Stage 2 company-research detail with exact handoff, company snapshot, map assertions, Stage 1 claims/evidence, research-file history, hypotheses, conflicts, missing evidence and verification items.

Expose read-only GET routes under `/industry-alpha`. Support optional `as_of_cutoff=YYYY-MM-DD` using both information-date and UTC recorded-date visibility.

No POST, PUT, PATCH or DELETE routes. No browser editing UI.

Notices must state that outputs are local research hypotheses, not scores, rankings, target prices, recommendations or investment advice.

## Offline fixture/demo

Add one deterministic no-network fixture/demo containing:

- one exact frozen v0.5C candidate-pool revision with at least two exact memberships;
- one supported Stage 2 research file with an A/B/C-backed `positive` or `mixed` financial-transmission hypothesis;
- one draft or disputed research file with missing evidence or visible contradiction;
- one completed research-file revision with a non-empty `后续验证清单`;
- a later research/hypothesis/link/checklist revision excluded from an earlier cutoff view;
- strict JSON output and deterministic ordering.

Use an isolated local database. Do not call providers, the network or an LLM.

## Tests and validation

Cover at minimum:

- clean base-to-head, `20260719_0007 -> head`, downgrade/upgrade and `python -m alembic check`;
- stable identities, revision numbers and supersedes chains;
- exact candidate-pool revision/membership/beneficiary/company handoff;
- rejection of non-members, cross-case/map records and mismatched exact revisions;
- strict workflow, conclusion, direction and hypothesis-field validation;
- hypothesis inference confidence/basis enforcement;
- exact claim/evidence binding and visible A/B/C, D-only, disputed, conflict and missing-evidence behavior;
- completed research checklist enforcement;
- exact chronology and historical cutoff non-leakage, including later Stage 1 links/evidence and later Stage 2 hypothesis/checklist records;
- append-only update/delete rejection;
- atomic rollback on every failed multi-row command;
- PostgreSQL concurrent research-file and hypothesis revision numbering;
- deterministic ordering and strict JSON;
- read-only API and no mutation routes;
- generic database-error responses without raw URLs, paths, credentials or exception text;
- no-network startup/import/test/demo behavior;
- all existing v0.2-v0.5C regressions and demos;
- `python -m compileall` for changed Python packages;
- `git diff --check`.

Run the full offline suite and PostgreSQL suite when `TEST_DATABASE_URL` is available. Record exact pass/skip/warning counts and environment limitations in the PR and Issue.

## Documentation

Update the conceptual data model, implementation plan, product architecture and local usage docs to mark v0.5C merged and describe the exact v0.6A boundary. Add a focused Stage 2 company-research document covering frozen handoff, identities, hypothesis semantics, evidence/cutoff rules, verification checklist and exclusions.

## Exclusions

Do not add valuation models/snapshots, multiples, DCF, numeric scores, weights, ranks, target prices, investment-attractiveness conclusions, final recommendations, catalyst/risk judgment workflow, Quant Core automatic validation, watchlists, portfolios, LLM/provider execution, scraping, ingestion automation, brokers, orders or trading.

Do not change dependencies, Docker/Compose, CI, launchers, project version, release/tag state or PR #38. Do not begin v0.6B.

## Delivery

1. Implement only Issue #62 on `feat/v06a-company-research`.
2. Keep the PR Draft throughout implementation.
3. Update the Draft PR and Issue with base/head SHA, exact changed files, schema, handoff/evidence/cutoff semantics, demo and validation results.
4. Stop for ChatGPT review. Do not merge, close Issue #62 or begin v0.6B without explicit owner authorization.
