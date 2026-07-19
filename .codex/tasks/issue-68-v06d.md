# Issue #68 — v0.6D Evidence-Backed Industry And Company Judgments

## State

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#68`
- Branch: `feat/v06d-independent-judgments`
- Draft PR: create `[v0.6D] Add evidence-backed industry and company judgments`
- Required base and ancestor: `87c88089b779292c6c30a8ac72c5fad99314a799`
- Version must remain `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #68, this task and the Draft PR before editing. The Issue is authoritative.

Keep Issue #68 Open and the PR Draft/Open/unmerged. Do not release/tag, change version, begin v0.6E/v0.7, rebase/force-push reviewed history, or modify PR #38.

## Objective

Implement the smallest reviewed Stage 2 synthesis slice after merged v0.6C: local, append-only, cutoff-aware independent industry-quality and company-quality judgment snapshots over exact accepted upstream research revisions.

These are manual evidence-backed research judgments. They are not scores, rankings, recommendations, price/timing outputs, watchlist states, verification-task lifecycles or trades.

## Required domain boundary

Create stable industry-judgment and company-judgment identities attached to one `Stage2CompanyResearch` identity and canonical keys. Add immutable sequential revisions with exact supersedes chains.

Each revision must contain bounded explicit fields for:

- outcome: `affirmed`, `not_affirmed`, `uncertain`, or `not_assessed`;
- evidence state: `supported`, `disputed`, or `insufficient_evidence`;
- confidence using the existing reviewed inference-confidence vocabulary where appropriate;
- decision criteria;
- evidence-based rationale;
- uncertainty;
- immutable bounded `后续验证清单` research notes;
- information cutoff date;
- timezone-aware UTC recorded timestamp.

Industry revisions must explicitly cover:

- driver durability;
- value-pool direction;
- chain/bottleneck support.

Company revisions must explicitly cover:

- beneficiary credibility;
- financial-transmission credibility;
- execution risks.

Use strict enums and bounded text. Do not add numeric scores, likelihood/impact points, weights, ranks, expected-loss calculations, price conclusions or recommendations.

## Exact frozen handoff

Every industry/company judgment revision must freeze:

1. one exact accepted v0.6A company-research revision from its own company-research identity;
2. the exact accepted financial-transmission hypothesis revisions selected by that research boundary;
3. exact relevant v0.6B expectation and/or valuation revisions from the same company-research identity;
4. exact relevant v0.6C catalyst and/or risk assessment revisions from the same company-research identity;
5. exact material v0.5A claim revisions and exact visible claim-evidence links.

Industry judgments must remain traceable through the exact v0.6A frozen Stage 1 beneficiary/map/company snapshot boundary.

Company judgments must bind at least one exact v0.6B revision and at least one exact v0.6C revision.

Preserve frozen claim provenance in reads:

- `claim_kind`;
- `inference_confidence`;
- `inference_basis`;
- claim revision cutoff and UTC timestamp;
- exact evidence grades and relations;
- conflicts and explicit missing evidence.

Fail closed on cross-company, cross-case, cross-research, invisible, later, incomplete or backdated boundaries. Later research, hypothesis, expectation, valuation, catalyst, risk, claim or evidence additions must not rewrite an accepted judgment.

## Evidence and outcome rules

- `affirmed` requires evidence state `supported`, at least one bound supported claim with visible A/B/C supporting evidence, and no visible contradiction.
- D-only evidence cannot independently affirm a judgment.
- Evidence state `disputed` requires a disputed claim revision or visible contradiction.
- Outcome `uncertain` must use evidence state `disputed` or `insufficient_evidence` and preserve explicit uncertainty.
- Outcome `not_assessed` must use evidence state `insufficient_evidence` and explicit `尚未获得可靠公开证据` wording.
- Outcome `not_affirmed` is manual. The system must not infer it automatically from missing data. It must preserve the exact claims/evidence used and an explicit rationale.
- Confidence wording cannot upgrade missing or disputed evidence.
- Do not fabricate drivers, value-pool shifts, beneficiary purity, customer/certification progress, financial transmission, execution risks or mitigants.

## Persistence and append-only rules

- Add exactly one migration after `20260719_0010`; expected revision is `20260719_0011`.
- Reuse the existing SQLAlchemy Base/session/repository conventions and append-only guards.
- Accepted identities, revisions and all frozen link rows must reject ordinary ORM update/delete operations.
- Corrections append deterministic revisions and preserve exact supersedes chains.
- Multi-row create/append commands must be one transaction and fully rollback on validation, chronology, evidence, uniqueness and cross-boundary failures.
- UTC chronology must cover identity creation, every frozen upstream revision/link and the prior judgment revision.
- PostgreSQL revision numbering must remain deterministic under concurrency.

## Query and HTTP boundary

Add deterministic strict-JSON read-only list/detail contracts and routes under `/industry-alpha` for:

- industry judgments;
- company judgments;
- optional `as_of_cutoff=YYYY-MM-DD` using both information-date and UTC recorded-date visibility.

No POST, PUT, PATCH or DELETE HTTP routes and no browser editing UI.

## Deterministic fixture/demo

Add one no-network fixture/demo containing:

- exact accepted v0.6A research/hypothesis revisions;
- exact v0.6B expectation/valuation revisions;
- exact v0.6C catalyst/risk revisions;
- one affirmed A/B/C-backed industry judgment;
- one uncertain or not-assessed industry judgment;
- one affirmed A/B/C-backed company judgment;
- one not-affirmed, uncertain or not-assessed company judgment;
- fact and inference claims with preserved provenance;
- later upstream revisions/evidence/judgment additions visible currently but excluded from earlier cutoff views.

All returned IDs and collection order must be deterministic across clean SQLite and PostgreSQL databases. Payloads must be strict JSON safe and contain no non-finite values.

## Tests

Add focused SQLite and PostgreSQL coverage for:

- migration `20260719_0011`, clean `base -> head`, down/up round trip and Alembic check;
- exact v0.6A/v0.6B/v0.6C handoff and same-company enforcement;
- Stage 1 traceability for industry judgments;
- stable identities, sequential revisions and supersedes chains;
- strict enums/text/date/time validation;
- affirmed, not-affirmed, uncertain and not-assessed behavior;
- supported, disputed, D-only and missing-evidence behavior;
- fact/inference provenance visibility;
- chronology and historical non-leakage;
- later upstream revisions/links not mutating accepted snapshots;
- append-only update/delete guards;
- atomic rollback with unchanged row counts;
- deterministic PostgreSQL concurrent revision allocation;
- deterministic fixture IDs/order and strict JSON;
- read-only API behavior and invalid cutoff handling;
- no-network startup/import/demo behavior;
- all existing regressions and demos.

## Expected files

Keep implementation focused around new `stage2_judgments` model/contract/command/repository/query/fixture modules, one migration, read-only route registration, one demo, focused tests and directly relevant documentation. Reuse accepted v0.6A/v0.6B/v0.6C boundary helpers where safe rather than duplicating incompatible semantics.

Do not change dependencies, Docker, CI, launchers, authentication, version metadata or unrelated modules.

## Explicit exclusions

No good-price or good-timing judgment, formal `research_conclusion_status`, case lifecycle/watchlist state, verification-task owner/due date/completion/reminder semantics, Quant Core validation links or automatic scoring, target/fair-value price, expected return, upside/downside, risk-reward ratio, numeric score, weight, rank, investment-priority field, recommendation, automated monitoring, provider collection, scraping, live network, LLM execution, portfolios, brokers, orders or trading.

Do not begin v0.6E/v0.7 and do not modify PR #38.

## Validation

Run and report exact results for:

- focused SQLite v0.6D tests;
- focused PostgreSQL v0.6D tests;
- full offline suite;
- full PostgreSQL persistence/Industry Alpha suite when available;
- clean PostgreSQL Alembic `base -> head`;
- `20260719_0011 -> 20260719_0010 -> 20260719_0011`;
- `python -m alembic check`;
- all offline demos;
- explicit no-network coverage;
- `python -m compileall -q backend industry_alpha scripts tests`;
- `git diff --check`.

## Delivery

Update Draft PR #69 and Issue #68 with:

- base and final Head SHA;
- architecture and data-contract decisions;
- exact changed files;
- exact test/pass/skip/warning counts;
- migration and demo results;
- known limitations and exclusions.

Keep PR #69 Draft and Issue #68 Open. Stop for ChatGPT review. Do not merge or start another slice.
