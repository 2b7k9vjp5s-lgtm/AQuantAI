# Issue #66 — v0.6C Catalyst And Risk Assessment Snapshots

## State

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#66`
- Branch: `feat/v06c-catalyst-risk-assessments`
- Draft PR: create `[v0.6C] Add evidence-backed catalyst and risk assessments`
- Required base and ancestor: `571fa9396a9318f2e6c409e1d8b7a25ec2120b2f`
- Version must remain `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #66, this task and the Draft PR before editing. The Issue is authoritative.

Keep Issue #66 Open and the PR Draft/Open/unmerged. Do not release/tag, change version, begin v0.6D/v0.7, rebase/force-push reviewed history, or modify PR #38.

## Objective

Implement the smallest reviewed Stage 2 slice after v0.6B: local append-only, cutoff-aware catalyst and company-risk assessment snapshots. These are immutable research judgments over exact accepted upstream revisions, not monitoring tasks, alerts, scores, recommendations, timing outputs or trades.

## Required domain boundary

Create stable catalyst-assessment and risk-assessment identities attached to one `Stage2CompanyResearch` identity and canonical keys. Add immutable sequential revisions with supersedes chains.

Catalyst revisions must contain bounded explicit fields for:

- catalyst category and subject;
- expected observation window;
- assessment status and confidence;
- trigger/observation criteria;
- evidence-based rationale and uncertainty;
- information cutoff and timezone-aware UTC recorded timestamp.

Risk revisions must contain bounded explicit fields for:

- risk category and subject;
- downside path;
- thesis-invalidation condition;
- mitigants;
- assessment status and confidence;
- evidence-based rationale and uncertainty;
- information cutoff and timezone-aware UTC recorded timestamp.

Use strict reviewed enums and bounded text. Do not add numeric scoring, likelihood/impact points, weights, ranks, expected-loss calculations, risk-reward ratios, price conclusions or final recommendation fields.

## Exact frozen handoff

Every catalyst/risk revision must freeze:

1. one exact accepted v0.6A company-research revision from its own company-research identity;
2. the selected exact financial-transmission hypothesis revisions accepted by that research boundary;
3. at least one exact relevant v0.6B expectation or valuation revision from the same company-research identity;
4. exact v0.5A claim revisions and exact visible claim-evidence links supporting the material assertion.

Fail closed on cross-research links, invisible revisions, later links, incomplete handoff, backdating or mismatched identity ownership. Later research, hypothesis, expectation, valuation, claim/evidence or price additions must not rewrite the frozen snapshot.

## Evidence/status rules

- `supported` requires at least one bound claim revision that is itself `supported`, has visible A/B/C supporting evidence at the frozen claim boundary, and has no visible contradiction.
- D-only evidence cannot independently support a catalyst or risk revision.
- `disputed` requires a disputed claim revision or visible contradiction.
- Missing public evidence remains explicit as `尚未获得可靠公开证据`; confidence wording cannot upgrade it.
- Keep fact/inference labels and uncertainty visible.

Do not fabricate customers, orders, certification, capacity, policy effects, event dates, financial outcomes, mitigants or invalidation signals.

## Persistence and append-only rules

- Add exactly one migration after `20260719_0009`; expected revision is `20260719_0010`.
- Reuse the existing SQLAlchemy Base/session/repository conventions and append-only guards.
- Accepted identities, revisions and frozen link rows must reject ordinary ORM update/delete operations.
- Corrections append deterministic revisions and preserve exact supersedes chains.
- Multi-row create/append commands must be one transaction and fully rollback on all validation, evidence, chronology, uniqueness and cross-research failures.
- PostgreSQL revision numbering must remain deterministic under concurrency.

## Query and HTTP boundary

Add deterministic strict-JSON query contracts and read-only routes under `/industry-alpha` for:

- catalyst-assessment list/detail;
- risk-assessment list/detail;
- optional `as_of_cutoff=YYYY-MM-DD` using both information-date and UTC recorded-date visibility.

No POST, PUT, PATCH or DELETE HTTP routes and no browser editing UI.

## Deterministic fixture/demo

Add one no-network fixture/demo containing:

- exact accepted v0.6A research/hypothesis revisions;
- exact v0.6B expectation and valuation revisions;
- one supported A/B/C-backed catalyst with explicit observation criteria;
- one disputed or explicit-missing-evidence catalyst;
- one supported company risk with bounded downside path and thesis-invalidation condition;
- one disputed or explicit-missing-evidence risk;
- later upstream revisions/evidence additions that are visible currently but excluded from earlier cutoff views.

All returned IDs and collection order must be deterministic across clean SQLite and PostgreSQL databases. Payloads must be strict JSON safe and contain no non-finite values.

## Tests

Add focused SQLite and PostgreSQL coverage for:

- migration `20260719_0010`, clean `base -> head`, down/up round trip and Alembic check;
- exact v0.6A/v0.6B handoff and same-research enforcement;
- stable identities, sequential revisions and supersedes chains;
- strict enum/text/date/time validation;
- supported, disputed, D-only and missing-evidence behavior;
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

Keep implementation focused around new `stage2_assessments` model/contract/command/repository/query/fixture modules, one migration, read-only route registration, one demo, focused tests and directly relevant documentation. Reuse accepted v0.6A/v0.6B boundary helpers where safe rather than duplicating incompatible semantics.

Do not change dependencies, Docker, CI, launchers, authentication, version metadata or unrelated modules.

## Explicit exclusions

No good-industry/good-company/good-price/good-timing conclusion, crowding model, Market Cockpit timing model, expected return, target/fair-value price, upside/downside percentage, score, weight, rank, investment-priority field, final research-conclusion status, automated monitoring, alerts, reminders, task owners, due dates, verification-task lifecycle, watchlists, Quant Core automatic scoring, provider collection, scraping, live network, LLM execution, portfolios, brokers, orders or trading.

## Validation

Run and report exact results for:

- focused SQLite v0.6C tests;
- focused PostgreSQL v0.6C tests;
- full offline suite;
- full PostgreSQL persistence/Industry Alpha suite when available;
- clean PostgreSQL Alembic `base -> head`;
- `20260719_0010 -> 20260719_0009 -> 20260719_0010`;
- `python -m alembic check`;
- all offline demos;
- explicit no-network coverage;
- `python -m compileall -q backend industry_alpha scripts tests`;
- `git diff --check`.

## Delivery

Update Draft PR #67 and Issue #66 with:

- base and final Head SHA;
- architecture and data-contract decisions;
- exact changed files;
- exact test/pass/skip/warning counts;
- migration and demo results;
- known limitations and exclusions.

Keep PR #67 Draft and Issue #66 Open. Stop for ChatGPT review. Do not merge or start another slice.