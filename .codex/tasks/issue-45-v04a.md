# Issue #45 — v0.4A Market Cockpit Final Diagnostic Revision

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#45 [v0.4A] Database-backed Market Cockpit breadth and risk foundation`
- Draft PR: `#46 [v0.4A] Add database-backed Market Cockpit foundation`
- Branch: `feat/v04a-market-cockpit-foundation`
- Required main ancestor: `b1e6ee59a2e26b0989e205353f63ed56dacdf137`
- Previously reviewed implementation head: `867879b1ccbcf722935a259fa80ee1fb57078411`
- Passing CI for that head: `29638648101`
- Blocking re-review: `4728218845`

Read `.codex/WORKFLOW.md`, Issue #45, PR #46, review `4728218845`, and this file before editing.

The original three review areas are accepted in principle and must not regress:

- calculation readiness, scope coverage, and conservative overall status are separate;
- immutable ingestion provenance is exposed only through a fixed allowlist;
- current-session missing, invalid, and no-trade observations are excluded from calculations;
- rolling metrics and risk apply the no-trade policy;
- one explicit snapshot series and one physical ingestion run are used;
- all calculations remain deterministic and point-in-time safe;
- API/page behavior remains read-only, local-first, offline in automated validation, and non-advisory.

## Objective

Close the remaining auditability inconsistency between the latest-return metric and structured diagnostics.

A latest return requires valid traded rows on both:

1. the effective as-of session; and
2. the immediately preceding persisted open session.

At reviewed head `867879b1ccbcf722935a259fa80ee1fb57078411`, `_latest_metrics()` correctly makes the stock unavailable when either row is unusable, but `_latest_data_diagnostics()` inspects only the effective-session row. A valid current row with a missing, invalid, or no-trade previous row therefore increments `metrics.latest_session.unavailable_count` while structured diagnostic counts and details can remain empty.

The final response and page must never show an unavailable latest return without a corresponding deterministic structured reason.

## Required contract and calculation revision

### 1. One structured issue for every unavailable latest return

Implement and enforce this invariant:

```text
latest_return_unavailable_count == metrics.latest_session.unavailable_count
len(latest_return_issues) == metrics.latest_session.unavailable_count
```

There must be exactly one issue per unavailable stock code, sorted deterministically by stock code.

A stock with a valid latest return must not appear in this issue list.

### 2. Distinguish current-session and previous-session causes

Use explicit reason values that distinguish at least:

- missing effective-session row;
- invalid effective-session row;
- no-trade effective-session row;
- missing previous-session row;
- invalid previous-session row;
- no-trade previous-session row.

Names may follow the existing contract style, but must be stable, documented, and tested.

Use deterministic precedence when more than one row is unusable:

1. effective-session cause first;
2. otherwise previous-session cause.

This prevents duplicate details for one stock and keeps the count invariant exact.

### 3. Make session-gap fields meaningful for the blocking row

Each issue must expose enough bounded information to audit why the return is unavailable. Include at minimum:

- `stock_code`;
- `reason`;
- the session whose missing/invalid/no-trade row blocks the return;
- the last valid traded session before that blocking session, or `null`;
- the persisted open-session gap from the last valid traded session to the blocking session, or `null`.

Do not report the valid current session as the “last available” answer for a previous-session failure. The reference point must be the blocking session.

Do not emit raw price rows or an unbounded history dump.

### 4. Preserve useful current-session aggregates without contradiction

The existing current-session aggregates may remain:

- `stale_or_missing_latest_count`;
- `no_trade_latest_count`.

Add a separate latest-return unavailable aggregate and issue list, or broaden/rename the diagnostic contract cleanly. Whichever design is used:

- the API meaning must be explicit;
- the page must distinguish current-row health from latest-return eligibility;
- an unavailable latest return must never coexist with an empty diagnostic message claiming no relevant issue;
- warnings and structured details must agree.

### 5. Reuse one eligibility classification path

Avoid separate logic drifting between `_latest_metrics()` and diagnostics.

Prefer a shared deterministic classifier that evaluates, per stock:

- current record eligibility;
- previous record eligibility;
- selected reason and blocking session;
- latest return value when eligible.

Metrics and diagnostics should consume the same classification result so their counts cannot diverge.

Do not change the reviewed return formula or epsilon semantics.

## Required tests

Add focused tests for all of the following:

1. valid current row plus missing previous row;
2. valid current row plus previous row with both volume and amount zero;
3. valid current row plus invalid/non-finite previous activity or price;
4. effective-session issue precedence when both current and previous rows are unusable;
5. genuinely unchanged, positively traded current and previous rows remain a valid unchanged return;
6. exact equality between structured latest-return unavailable count, issue-list length, and `metrics.latest_session.unavailable_count`;
7. one deterministic issue per affected stock with stock-code ordering;
8. correct blocking-session, last-valid-session, and gap values;
9. API serialization of all reason variants used by tests;
10. page rendering of previous-session failures;
11. the page does not display an empty “no issue” message while latest unavailable count is non-zero;
12. existing current-session no-trade, rolling-window, risk, scope, provenance, cutoff, and future-row tests continue to pass.

Add a regression test that would fail on reviewed head `867879b1ccbcf722935a259fa80ee1fb57078411`: keep the effective-session row valid, remove or zero both activity fields on the preceding open-session row, and assert the structured issue is present.

## Retained architecture and behavior

Do not regress or redesign the accepted implementation:

- explicit `series_key` or complete canonical selector;
- no provider-only selection;
- one selected successful complete ingestion run;
- no cross-run or cross-series stitching;
- no row after the effective cutoff/session;
- exact stock scope, requested date range, adjustment policy, and compatibility series;
- persisted trade-calendar windows;
- calculation status `ready|partial|insufficient_data` for the exact universe;
- scope coverage `unverified_selected_scope` in v0.4A;
- conservative overall status `partial` when calculations exist, otherwise `insufficient_data`;
- immutable provenance allowlist and sensitive/unknown metadata exclusion;
- lazy and injectable database construction;
- existing Dashboard routes and fixture payloads unchanged;
- local HTML/CSS/vanilla JavaScript using DOM/`textContent` only;
- no form, trading control, recommendation language, CDN, framework, or automatic refresh;
- 422/404/503 API error behavior;
- no fixture fallback disguised as persisted data;
- no network access during import, startup, tests, CI, page use, or fixture demonstrations.

## Documentation and page

Update `docs/market_cockpit.md` and any directly affected local usage text to define:

- latest-return eligibility requires two valid traded sessions;
- current-session diagnostics versus latest-return diagnostics;
- all structured reason values;
- blocking-session and gap semantics;
- deterministic precedence and ordering;
- the count invariant.

Update the page to render the revised bounded diagnostics. Preserve source/cutoff/scope/provenance/formula/unsupported-section presentation and forbidden-market-coverage wording protections.

## Required validation

Run and report exact results for:

1. `python -m pytest -q`
2. focused Market Cockpit contract/calculation/repository/API/page tests
3. PostgreSQL Market Cockpit current/as-of cutoff tests
4. existing PostgreSQL persistence and migration tests
5. clean Alembic `base -> head`
6. `python -m alembic check`
7. `python -m scripts.demo_research_flow`
8. `python -m scripts.demo_market_cockpit`
9. `python -m compileall -q backend market_cockpit scripts`
10. import/startup/page no-network regression tests
11. `git diff --check`

No migration is expected. Do not add one unless a demonstrated schema defect is reported and separately authorized.

## GitHub synchronization

After implementing and pushing:

1. Update PR #46 body with:
   - new head SHA;
   - the shared latest-return eligibility/classification design;
   - reason values and precedence;
   - blocking-session and gap semantics;
   - count invariants;
   - changed files;
   - exact validation results;
   - demo output and known limitations.
2. Add an Issue #45 comment with the same concise completion record.
3. Keep PR #46 Draft.
4. Stop and wait for ChatGPT re-review.

## Exclusions and stop conditions

Do not:

- merge PR #46;
- close Issue #45;
- create a release or tag;
- change version `0.2.0`;
- add migrations without separate authorization;
- add provider endpoints or external datasets;
- add official indices, sectors, style, valuation, market cap, or crowding;
- persist derived cockpit snapshots;
- add schedulers, background collection, or automatic refresh;
- begin v0.4B or v0.5;
- add Industry Alpha, Stock Research, Watchlist, paper portfolios, LLM execution, authentication, deployment, broker, order, recommendation, or trading behavior;
- modify, close, rebase, or merge unrelated PR #38.
