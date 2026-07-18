# Issue #45 — v0.4A Market Cockpit Review Task

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#45 [v0.4A] Database-backed Market Cockpit breadth and risk foundation`
- Draft PR: `#46 [v0.4A] Add database-backed Market Cockpit foundation`
- Branch: `feat/v04a-market-cockpit-foundation`
- Required main ancestor: `b1e6ee59a2e26b0989e205353f63ed56dacdf137`
- Reviewed implementation head: `bec8fc83ec78d1b1c5d1214889ae758ab1da7487`
- Blocking review: `4728172324`
- Accepted pre-review CI run: `29637868999`

The commits after the reviewed implementation head that only add `.codex/WORKFLOW.md` and this task file are authorized task-synchronization commits. Any other unexpected commit must be reported before editing.

Read `.codex/WORKFLOW.md`, Issue #45, PR #46, and review `4728172324` before changing code.

## Objective

Revise the existing v0.4A implementation so that it remains a local, read-only, database-backed monitor for one explicit persisted snapshot series while accurately representing scope confidence, immutable collection provenance, and stale/no-trade data.

Preserve the accepted architecture:

- one explicit `series_key` or complete canonical selector;
- one selected successful complete ingestion run;
- no provider-only selection;
- no cross-run or cross-series history stitching;
- persisted trade-calendar session windows;
- deterministic point-in-time calculations;
- lazy and injectable database construction;
- read-only FastAPI endpoint and local static page;
- existing fixture Dashboard routes and payloads unchanged;
- all automated validation offline.

## Required revisions

### 1. Separate calculation readiness from scope coverage confidence

The current three-stock fixture is internally complete but is incorrectly reported as overall `ready`. Issue #45 requires small or incomplete scopes to remain visibly limited.

Implement explicit coverage-aware semantics without claiming market representation and without inventing an unsupported “representative A-share” threshold.

Required contract behavior:

- Add a calculation/data status that describes whether the requested metrics are internally complete for the exact selected universe.
- Add a scope coverage status, with an explicit value such as `unverified_selected_scope`, because v0.4A has no reviewed market-wide coverage policy.
- Keep the existing overall `completeness_status` as the conservative user-facing status.
- The overall status must be `partial` when scope coverage is unverified or explicitly small, even when every calculation is available.
- `insufficient_data` remains required when no core latest return can be calculated.
- The API and page must state that internally ready calculations do not imply representative A-share or full-market coverage.
- Do not use `全市场`, `A股市场宽度`, `market-wide breadth`, or equivalent claims.

Do not introduce an arbitrary stock-count threshold and call it market representativeness. A numeric diagnostic such as scope count may be shown, but the confidence decision must remain tied to the absence of a reviewed coverage policy.

Update the current three-stock fixture expectations: calculations may be internally ready, but the overall completeness status must remain `partial` with a visible scope warning.

Add tests for:

- internally complete three-stock scope;
- incomplete latest-return coverage;
- no core latest returns;
- coverage fields serialized in API and rendered on the page;
- forbidden full-market wording remains absent.

### 2. Carry sanitized immutable ingestion provenance into the view

The selected `ingestion_runs` row already stores immutable provenance. Extend the repository snapshot and public provenance contract with an explicit allowlist.

Expose at minimum:

- ingestion `imported_at` in UTC;
- ingestion `completed_at` in UTC;
- `collection_timestamp_utc` when present in provider request metadata;
- `effective_information_cutoff_date` when present;
- installed `akshare_package_version` when present;
- endpoint identifiers and adapter compatibility version from canonical `compatibility_parameters`;
- the request's `as_of_cutoff` as a separate nullable field;
- selected run information cutoff;
- effective as-of trading session;
- view `generated_at_utc`, clearly labeled as generation time.

Rules:

- Never serialize the complete opaque `provider_request_metadata` object directly.
- Use a fixed explicit allowlist.
- Never expose keys containing or representing secrets, tokens, passwords, API keys, credentials, connection strings, or cookies.
- Missing optional provenance values must be `null` or an explicit unavailable state, not fabricated strings.
- Normalize timestamps to timezone-aware UTC ISO-8601 values.
- Backfilled or fixture runs without live collection metadata must remain valid and visibly identify unavailable optional fields.
- Do not modify persisted ingestion history or migrations for this view-only requirement unless a demonstrated schema defect requires separate authorization.

Update API/page labels so users can distinguish:

- when source data was collected/imported;
- what information cutoff it claims;
- what historical cutoff the user requested;
- which trading session was actually calculated;
- when the view was generated.

Add tests for:

- live-style allowed metadata fields;
- fixture/backfilled missing optional metadata;
- endpoint and adapter compatibility provenance;
- requested `as_of_cutoff` echo;
- sensitive and unknown metadata keys excluded;
- timestamp normalization;
- page provenance labels.

### 3. Define deterministic stale and no-trade handling

The current code treats any positive close pair as a valid return and permits current zero participation values. This can classify a carried-forward no-trade row as a valid unchanged observation.

Implement a conservative policy using only existing normalized fields.

Required rules:

- A stock missing a row on the effective session is unavailable for latest breadth.
- For each affected stock, derive and report the last valid available session at or before the effective session and the number of persisted open-session gaps.
- A stock-session row with both `volume == 0` and `amount == 0` is a deterministic `no_trade` observation.
- A `no_trade` observation is unavailable for latest-session breadth and participation.
- A no-trade carried-forward close must not be counted as `unchanged`.
- Do not claim a confirmed suspension. Use wording such as `potentially suspended or no-trade`.
- A genuinely unchanged close with positive trading activity remains a valid unchanged return.
- Negative, non-finite, or otherwise invalid volume/amount remains unavailable under existing validation rules.
- Rolling close metrics and risk must document and consistently apply the no-trade policy. Prefer excluding the affected stock/window rather than silently treating a no-trade close as a traded observation.

Extend contracts with auditable aggregate diagnostics, at minimum:

- stale or missing latest count;
- no-trade latest count;
- optionally structured affected-stock details containing code, reason, last available session, and open-session gap.

Keep the response bounded and deterministic. Do not add an unbounded raw-row dump.

Add tests for:

- missing latest row with last-session/gap detail;
- zero volume and zero amount with unchanged close;
- genuinely unchanged close with positive volume/amount;
- no-trade exclusion from advance/decline/unchanged and participation;
- rolling/risk coverage behavior under a no-trade session;
- deterministic warning/detail ordering.

## Retained metric and point-in-time requirements

Do not regress the existing reviewed formulas:

- latest close-to-close mean and median returns;
- advancing, declining, unchanged, unavailable counts;
- advance ratio and breadth balance;
- population cross-sectional dispersion;
- 20/60-session close SMA breadth;
- 20/60-session closing-price new highs and lows;
- current volume/amount versus each stock's prior-20-session median;
- equal-weight daily universe returns, 20-return sample volatility annualized by `sqrt(252)`, and compounded-wealth maximum drawdown;
- `null` plus warning for insufficient windows, never fabricated zero.

Point-in-time rules remain mandatory:

- select no snapshot after requested `as_of_cutoff`;
- use no calendar or price row after the effective session;
- use one physical ingestion run only;
- never substitute adjustment policy, scope, date range, or compatibility series;
- keep the future-price trap test;
- keep current and historical cutoff repository/PostgreSQL tests.

## API and page requirements

Retain:

- `GET /market-cockpit/snapshot?series_key=...&as_of_cutoff=YYYYMMDD`;
- `GET /market-cockpit`;
- local CSS and vanilla JavaScript;
- DOM and `textContent` rendering only;
- no form, trading control, recommendation language, framework, CDN, or automatic refresh;
- 422 for invalid/missing selector or cutoff;
- 404 for no eligible complete snapshot;
- 503 for unavailable database configuration or query failure;
- no fixture fallback disguised as persisted data.

The page must render the new scope coverage, collection provenance, stale/no-trade diagnostics, warnings, formulas, and unsupported sections.

Database construction must remain lazy. Imports, FastAPI startup, static page serving, tests, CI, fixture demos, and existing Dashboard routes must not create an engine, migrate, collect data, or access a provider/network.

## Required validation

Run and report exact results for:

1. `python -m pytest -q`
2. focused Market Cockpit contract/calculation/repository/API/page tests
3. PostgreSQL Market Cockpit and current/as-of cutoff tests
4. existing PostgreSQL persistence/migration tests
5. clean Alembic `base -> head`
6. `python -m alembic check`
7. `python -m scripts.demo_research_flow`
8. `python -m scripts.demo_market_cockpit`
9. `python -m compileall -q backend market_cockpit scripts`
10. import/startup/page no-network regression tests

The deterministic Market Cockpit demo must show:

- current and historical selected ingestion runs;
- internally ready calculation status where applicable;
- conservative overall partial status for the unverified three-stock scope;
- immutable collection/import/view timestamps as available;
- no-trade/stale diagnostics;
- read-only true;
- network access false.

## GitHub synchronization

After implementing and pushing:

1. Update PR #46 body with:
   - new head SHA;
   - final calculation, coverage, and overall status semantics;
   - provenance allowlist;
   - stale/no-trade policy;
   - contracts and page changes;
   - changed files;
   - exact validation results;
   - current/historical demo output;
   - known limitations.
2. Add an Issue #45 comment with the same concise completion record.
3. Keep PR #46 Draft.
4. Stop and wait for ChatGPT review.

## Exclusions and stop conditions

Do not:

- merge PR #46;
- close Issue #45;
- create a release or tag;
- change version `0.2.0`;
- add migrations without a separately justified schema defect;
- add provider endpoints or external datasets;
- add official indices, industry/sector rotation, style, valuation, market cap, or crowding;
- persist derived cockpit snapshots;
- add scheduling, background collection, or automatic refresh;
- begin v0.4B or v0.5;
- add Industry Alpha, Stock Research, Watchlist, paper portfolios, LLM execution, authentication, deployment, broker, order, or trading behavior;
- modify, close, rebase, or merge unrelated PR #38.
