# Issue #70 - v0.6E Evidence-Backed Price Observation Judgments Plan

## Authorization state

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#70`
- Branch: `feat/v06e-price-observation-judgments`
- Draft PR: `[v0.6E] Plan evidence-backed price observation judgments`
- Required base and ancestor: `9cc5a0e5dda97efa6b9c7b3a43eb3b5c4ead91ec`
- Version must remain `0.2.0`
- This task snapshot and Draft PR setup are the only authorized changes.

Read `.codex/WORKFLOW.md`, Issue #70, this task file, the Draft PR, its latest review, and latest CI before any later implementation work. Issue #70 is authoritative.

Keep Issue #70 Open and the PR Draft/Open/unmerged. Do not implement application code until ChatGPT separately accepts this plan and synchronizes explicit implementation authorization. Do not release/tag, change version, begin timing judgments or v0.7, add page/UI work, rebase/force-push reviewed history, or modify PR #38.

## Objective

Plan the smallest local, append-only, cutoff-aware manual price-observation judgment slice for one accepted v0.6A company-research identity. The proposed record preserves exact price, valuation, quality-judgment, claim, and evidence provenance while remaining a descriptive research observation.

This slice must not become a target-price, fair-value, expected-return, recommendation, good-price, good-timing, alert, portfolio, order, or trading system. No application behavior is authorized by this planning PR.

## Proposed domain boundary

Create a stable `price_observation_judgments` identity attached to one `Stage2CompanyResearch` identity and a canonical non-editable key. Add immutable, sequential `price_observation_judgment_revisions` with exact supersedes chains.

Each proposed revision contains bounded manual research fields:

- one strict `observation_context` value from the proposed vocabulary below;
- one existing-style `evidence_state` value;
- an explicit comparison basis that names what the observed price is being compared with, without computing value or return;
- evidence-based rationale;
- uncertainty;
- a bounded immutable `后续验证清单`;
- information cutoff date;
- timezone-aware UTC recorded timestamp.

The observation is descriptive and manually asserted. The system must not derive, upgrade, score, rank, recommend, or translate it into timing or trading language.

## Exact frozen boundary

Every proposed revision must freeze all of the following:

1. one exact accepted v0.6A `Stage2CompanyResearchRevision` from its own stable company-research identity;
2. exact relevant v0.6B market-expectation and valuation-snapshot revisions from that same company-research identity;
3. one exact local `daily_price` row from one successful ingestion run whenever price context is present;
4. one exact accepted v0.6D company-quality judgment revision from that same company-research identity;
5. exact material v0.5A claim revisions and exact visible claim-evidence links;
6. exact stock code, trade date, adjustment mode, series key, ingestion-run identity, provider, adapter/contract provenance, information cutoff, imported UTC timestamp, and completed UTC timestamp associated with the frozen price row;
7. the revision information cutoff and timezone-aware UTC recorded timestamp.

The price row is optional only for an explicitly unavailable or not-assessed observation. A revision that makes a comparative price observation must freeze exactly one visible local row. It must not select by provider alone, combine series, substitute a different adjustment mode, or silently use a later row.

Later prices, ingestion attempts, expectations, valuations, company-quality judgments, research revisions, claims, evidence, or links must not rewrite an accepted revision. Historical reads must evaluate both information-date visibility and actual UTC recorded/imported/completed visibility.

## Proposed categorical vocabulary

The following vocabulary is proposed for review and must not be implemented until accepted:

### `observation_context`

- `below_recorded_comparison`: the exact observed close is manually documented as below the explicitly named frozen comparison context;
- `within_recorded_comparison`: the exact observed close is manually documented as within the explicitly named frozen comparison context;
- `above_recorded_comparison`: the exact observed close is manually documented as above the explicitly named frozen comparison context;
- `not_comparable`: the frozen materials do not provide a valid like-for-like comparison;
- `not_assessed`: no reliable comparison has been made.

These labels describe only the relationship to a recorded comparison basis. They must never be exposed as cheap/expensive, attractive/unattractive, favorable/unfavorable, buy/sell/hold, upside/downside, good-price, good-timing, or a recommendation.

### `evidence_state`

Reuse the reviewed vocabulary:

- `supported`;
- `disputed`;
- `insufficient_evidence`.

No confidence field may upgrade disputed or missing evidence. If inference confidence is exposed through frozen claims, it remains claim provenance rather than a price score.

## Proposed validation rules

- Comparative contexts require exactly one frozen daily-price row, at least one exact v0.6B expectation revision, at least one exact v0.6B valuation revision, and one exact accepted v0.6D company-quality judgment revision.
- `supported` requires at least one bound supported claim revision with visible A/B/C supporting evidence and no visible contradiction.
- D-only evidence cannot independently produce `supported`.
- `disputed` requires a disputed claim revision or visible contradiction and must preserve the conflicting evidence in reads.
- `insufficient_evidence` must preserve explicit missing-evidence reasons.
- `not_comparable` requires a non-empty incompatibility reason and cannot use `supported`.
- `not_assessed` requires `insufficient_evidence`, explicit `尚未获得可靠公开证据` wording, and no comparative conclusion.
- Facts must retain null inference confidence/basis; inferences require the existing valid confidence vocabulary and a non-empty basis.
- Comparison basis, rationale, uncertainty, and verification notes accept only strings (or explicitly allowed `None`), enforce reviewed length bounds, reject blank values where required, and never coerce non-strings with `str()`.
- All dates, identifiers, enum values, prices, and provenance must be valid and finite. Strict JSON output must reject `NaN` and `Infinity`.
- The frozen price stock code must equal the company-research stock code and belong to the exact selected stock scope.
- The price row must come from a successful ingestion run and the exact canonical series/adjustment boundary. Its trade date must be on or before the revision information cutoff.
- The ingestion run must satisfy `imported_at_utc <= completed_at_utc <= revision.recorded_at_utc`; every frozen upstream record/link must be visible by both information cutoff and recorded UTC time.
- Cross-company, cross-case, cross-research, cross-series, later, invisible, incomplete, superseded-in-place, or backdated boundaries fail closed.
- Identity creation, revision append, and all frozen links occur in one transaction. Any validation, chronology, uniqueness, or concurrency failure rolls back every row.
- Accepted identities, revisions, and frozen links reject ordinary ORM update/delete. Corrections append a new revision.
- Revision numbers are deterministic and contiguous per identity. PostgreSQL allocation uses the established row-lock/concurrency pattern and preserves an exact supersedes chain.

## Proposed persistence plan

If a later review authorizes implementation, add exactly one forward Alembic migration after `20260719_0011`. The reviewed migration identifier must be chosen in that authorization; this planning task does not reserve or create one.

Proposed tables:

- `price_observation_judgments`: stable identity, company-research identity, canonical key, creation cutoff and UTC timestamp;
- `price_observation_judgment_revisions`: immutable revision number, supersedes link, proposed enums, bounded text, information cutoff and UTC timestamp;
- frozen links for the exact company-research revision;
- frozen links for exact expectation and valuation revisions;
- one optional frozen daily-price natural-key/provenance boundary;
- one frozen company-quality judgment revision link;
- frozen exact claim-revision and claim-evidence-link memberships.

Prefer explicit foreign keys and uniqueness constraints matching established v0.5/v0.6 append-only conventions. Do not duplicate daily-price data or introduce a new price series, provider, calendar, cache, queue, ORM, database, ingestion path, or mutable snapshot.

Downgrade must be safe and scoped to the new tables only. It must not delete, rewrite, merge, or reinterpret existing v0.3-v0.6D audit history.

## Proposed read-only API

If later authorized, add deterministic strict-JSON list/detail routes under `/industry-alpha`:

- `GET /industry-alpha/price-observation-judgments`;
- `GET /industry-alpha/price-observation-judgments/{judgment_id}`;
- optional `as_of_cutoff=YYYY-MM-DD` on both routes.

The read model must expose the stable identity, selected revision, exact supersedes chain, observation/evidence states, rationale, uncertainty, bounded `后续验证清单`, exact upstream IDs, complete price and ingestion provenance, claim fact/inference fields, evidence grades/relations, contradictions, missing-evidence diagnostics, information cutoff, and UTC timestamps.

Ordering must be explicit and deterministic. Current and historical reads must fail closed when the selector or frozen boundary is absent, ambiguous, later, or inconsistent. The API must use the existing fixed generic 503 configuration-error message and must never reveal database URLs, credentials, paths, or raw exceptions.

No POST, PUT, PATCH, or DELETE route and no browser editing or presentation page is authorized.

## Proposed deterministic fixture and demo

If later authorized, add one completely offline fixture/demo that reuses the accepted nested v0.5/v0.6A-v0.6D fixture boundary and contains:

- one supported comparative observation with exact A/B/C evidence and a frozen successful daily-price row;
- one disputed observation that visibly retains contradictory evidence;
- one `not_comparable` or `not_assessed` observation with explicit missing-data semantics;
- fact and inference claim provenance;
- a later price, valuation, company-quality judgment, claim/evidence addition, and later observation revision that remain visible currently but are excluded from an earlier cutoff;
- deterministic fixture-only UUIDv5 IDs across the complete returned payload while normal runtime UUIDv4 behavior remains unchanged.

The fixture must return complete list/detail and historical payloads with stable ordering. Two clean SQLite builds, two clean PostgreSQL builds, and cross-database canonical payload comparison must have identical semantic fields, all exposed IDs, and ordering. Serialization uses `json.dumps(..., allow_nan=False)`.

## Proposed SQLite and PostgreSQL tests

Any later implementation authorization must require focused tests for:

- one new migration, clean `base -> head`, previous-head upgrade, safe down/up round trip, and `python -m alembic check`;
- exact v0.6A research, v0.6B expectation/valuation, daily-price/ingestion, v0.6D quality-judgment, claim, and evidence boundaries;
- same-company, same-case, same-series, exact stock, date, adjustment, and successful-ingestion enforcement;
- stable identities, immutable sequential revisions, deterministic numbering, and supersedes chains;
- all proposed enums and allowed combinations;
- supported, disputed, D-only, contradiction, missing-evidence, not-comparable, and not-assessed behavior;
- chronology across information dates and UTC recorded/imported/completed timestamps;
- current and historical cutoff reads with no later price, valuation, judgment, claim, evidence, or link leakage;
- later upstream records not mutating an already accepted observation;
- append-only update/delete rejection;
- atomic rollback with unchanged row counts for every multi-row failure;
- deterministic PostgreSQL concurrent revision allocation;
- deterministic fixture IDs, complete payload, all returned IDs, collection ordering, and SQLite/PostgreSQL equality;
- strict JSON, invalid cutoff handling, fixed generic 503 behavior, and read-only route inventory;
- imports, FastAPI startup, tests, fixture demo, and API reads performing no network access;
- all existing v0.3-v0.6D regressions and demos.

## Proposed implementation validation gate

The later implementation task must list and report exact results for:

- focused SQLite v0.6E tests;
- focused PostgreSQL v0.6E tests;
- full offline suite;
- full PostgreSQL persistence/Industry Alpha suite when available;
- clean PostgreSQL Alembic `base -> head`;
- previous head -> new head and new head -> previous head -> new head;
- `python -m alembic check`;
- all offline demos;
- explicit no-network coverage;
- `python -m compileall -q backend industry_alpha scripts tests`;
- `git diff --check`;
- final GitHub Actions success on the implementation Head.

This planning PR runs only the current unchanged offline test suite and local fixture demo requested by Issue #70.

## Explicit exclusions

No target price, fair value, intrinsic value, expected return, upside/downside amount or percentage, discount/premium calculation, risk-reward ratio, numeric score, weight, rank, investment priority, buy/sell/hold label, recommendation, automatic conclusion, good-price judgment, good-timing judgment, timing signal, alert/reminder/task lifecycle, Quant Core link or score, provider collection, scraping, live network, LLM execution, page/UI work, watchlist, portfolio, broker, order, or trading behavior.

Do not add or modify application code, models, migrations, APIs, fixtures, demos, tests, documentation outside this task snapshot, dependencies, Docker, Compose, CI, launchers, authentication, or version metadata in this planning slice.

Do not begin timing judgments, v0.7 Watchlist, release/tag work, or any later roadmap phase. Do not modify PR #38.

## Task-sync validation

Run the unchanged repository commands and report exact results:

- `python -m pytest -q`;
- `python -m scripts.demo_research_flow`.

Before commit, verify that the complete branch diff from `9cc5a0e5dda97efa6b9c7b3a43eb3b5c4ead91ec` contains only `.codex/tasks/issue-70-v06e.md` and passes `git diff --check`.

## Delivery and execution gate

1. Commit and push only this task file on `feat/v06e-price-observation-judgments`.
2. Create Draft PR `[v0.6E] Plan evidence-backed price observation judgments`.
3. Record base/head SHA, the single changed file, proposed frozen boundary, enums, validation, API, fixture/test plan, exact test results, exclusions, and known environment limitations in the PR and Issue #70.
4. Keep the PR Draft/Open/unmerged and Issue #70 Open.
5. Stop for ChatGPT review.

No business implementation may begin until a later GitHub-synchronized review explicitly authorizes it.
