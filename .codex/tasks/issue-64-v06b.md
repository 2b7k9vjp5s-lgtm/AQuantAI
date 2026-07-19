# Issue #64 — v0.6B Expectations And Valuation Snapshots

## State

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#64`
- Branch: `feat/v06b-expectations-valuation`
- Draft PR: `[v0.6B] Add evidence-backed expectations and valuation snapshots`
- Required base: `c94c5ecbac66e43c2c369f36ba64c9b7a13655b6`
- Version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #64, merged v0.3/v0.5/v0.6A contracts, `docs/research_workflow.md`, `docs/data_model.md`, and `docs/implementation_plan.md` before editing.

Keep the PR Draft/Open/unmerged and Issue #64 Open. Do not modify PR #38, create release/tag, change version, begin v0.6C, or broaden the feature.

## Objective

Implement a local, append-only, cutoff-aware foundation for market expectations and valuation snapshots attached to exact accepted v0.6A company-research revisions. Preserve evidence, assumptions, uncertainty, price provenance and historical views without generating scores, rankings, target prices, final recommendations or trading actions.

## Required domain model

Add stable identities and immutable revisions for:

1. **Market expectations**
   - one Stage 2 company-research identity plus canonical expectation key;
   - revision number, subject, period/horizon, expectation kind, direction, status, confidence, basis, information cutoff, UTC timestamp and supersedes pointer;
   - exact frozen company-research revision and exact accepted financial-hypothesis revisions;
   - exact claim revisions and exact visible claim-evidence links.

2. **Valuation snapshots**
   - one Stage 2 company-research identity plus canonical valuation key;
   - revision number, valuation method, metric/business context, observed value(s) or explicit missing-data state, unit/currency, comparison basis, assumptions, confidence, information cutoff, UTC timestamp and supersedes pointer;
   - exact frozen company-research revision and exact accepted financial-hypothesis revisions;
   - exact claim revisions and exact visible claim-evidence links;
   - optional exact local `daily_price` row plus its successful ingestion run and series provenance.

Use strict reviewed enums and bounded text. Numeric fields must use finite deterministic decimal semantics; do not store NaN/Infinity or binary-float-dependent values.

## Evidence and status rules

- `supported` requires at least one bound claim revision whose `claim_status` is `supported`, with visible A/B/C `supports` evidence and no visible contradiction at the expectation/valuation revision boundary.
- D-only evidence is insufficient.
- `disputed` requires a disputed claim revision or visible contradiction.
- Missing evidence or metrics remain explicit using `尚未获得可靠公开证据`; do not fabricate consensus, forecasts, guidance, comparables, multiples or operating/financial values.
- Later Stage 2 revisions, hypotheses, claim/evidence links, price rows or ingestion runs must never rewrite accepted historical snapshots.
- A valuation snapshot is a dated research artifact only. Do not infer good price, good timing, expected return or investment priority.

## Exact price-reference boundary

When a price reference is present:

- bind one exact existing local `daily_price` row;
- require its ingestion run to be successful and visible at the valuation cutoff/time;
- require source and stock code to match the frozen Stage 2 company identity;
- expose source, stock code, trade date, adjustment type, close, ingestion run ID, series key, information cutoff and import/completion provenance;
- reject provider-only or implicit latest selection;
- reject price rows after the valuation cutoff or recorded boundary;
- keep the reference immutable after acceptance.

## Append-only, chronology and transactions

- Ordinary ORM update/delete of identities, revisions and frozen link rows must fail.
- Corrections append deterministic revisions and supersedes chains.
- Validate timezone-aware UTC chronology against research identity/revision, hypotheses, claims, evidence, price row/run and prior revisions.
- Cross-case, cross-company, cross-research and incompatible price references fail closed.
- Every command is a single transaction; validation, uniqueness, chronology or evidence failure leaves no partial identities, revisions or links.
- PostgreSQL concurrent revision creation must produce deterministic unique revision numbers or a reviewed domain error without partial rows.

## Persistence and API

- Add exactly one migration after `20260719_0008`; expected revision is `20260719_0009`.
- Reuse the existing Base/session/repository patterns.
- Add read-only GET list/detail routes under `/industry-alpha` for expectations and valuation snapshots.
- Support optional `as_of_cutoff=YYYY-MM-DD` using dual information-date and UTC recorded-date visibility.
- Return deterministic strict JSON with explicit conflicts, missing evidence, exact research/hypothesis/claim/evidence links and optional price provenance.
- Add no HTTP mutation routes and no browser editing UI.

## Offline fixture/demo

Provide a deterministic no-network fixture containing:

- one accepted v0.6A company-research revision with supported financial-transmission hypotheses;
- one supported expectation with A/B/C-backed evidence;
- one draft or disputed expectation with missing evidence or contradiction;
- one valuation snapshot with structured observed metric context and an exact local daily-price reference;
- one valuation snapshot with explicit missing data;
- later research/evidence/price additions excluded from earlier cutoff views.

Add an offline demo script for the new read model and include it in regression validation without changing CI configuration.

## Validation

Run and report exact results for:

- focused SQLite/domain/API tests;
- focused PostgreSQL tests when `TEST_DATABASE_URL` is available;
- full offline suite;
- full PostgreSQL suite when available;
- clean Alembic `base -> head`;
- `20260719_0009 -> 20260719_0008 -> 20260719_0009` round trip;
- `python -m alembic check`;
- all existing offline demos plus the new v0.6B demo;
- explicit no-network coverage;
- `python -m compileall -q backend industry_alpha scripts tests`;
- `git diff --check`.

Cover exact v0.6A handoff, stable identities/revisions, strict enums/text/decimal/date validation, exact price provenance, A/B/C versus D-only rules, conflicts/missing evidence, chronology, cutoff non-leakage, append-only guards, atomic rollback, PostgreSQL concurrency, deterministic JSON and read-only API behavior.

## Exclusions

No automated consensus collection, financial-statement ingestion, scraping, live provider calls, valuation engine, DCF execution, automatic comparable selection, target/fair-value share prices, expected returns, upside/downside percentages, scores, weights, rankings, investment-attractiveness conclusions, final recommendations, catalyst/risk judgment workflow, good-price/good-timing conclusions, Quant Core automatic scoring, watchlists, portfolios, LLM/provider execution, brokers, orders, trading, authentication, SaaS, dependency/Docker/CI/launcher/version/release/tag changes, v0.6C, or PR #38 changes.

## Delivery

1. Implement only Issue #64 on `feat/v06b-expectations-valuation`.
2. Update the Draft PR and Issue with final Head, exact changed files and exact validation results.
3. Keep the PR Draft and Issue Open.
4. Stop for ChatGPT review. Do not merge, close Issue #64, release/tag, change version, start v0.6C or modify PR #38.