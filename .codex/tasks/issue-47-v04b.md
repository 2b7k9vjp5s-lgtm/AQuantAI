# Issue #47 — v0.4B Benchmark Session Integrity And Alignment Revision

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#47 [v0.4B] Benchmark index persistence and Market Cockpit context`
- Draft PR: `#48 [v0.4B] Add benchmark index context`
- Branch: `feat/v04b-benchmark-index-context`
- Required base/task ancestor: `5420da2e28b52e9410ca1216c1b8feb7652978ce`
- Reviewed implementation head: `6402762f1af6723b7a473a779edf9587598dcd91`
- Passing GitHub Actions run for reviewed head: `29640571746`
- Blocking COMMENT review: `4728315417`
- Project version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #47, PR #48, review `4728315417`, `docs/benchmark_context.md`, the selected-equity Market Cockpit calendar/cutoff implementation, and this file before editing.

Keep PR #48 Draft. This is a bounded correctness and auditability revision; do not redesign accepted persistence, provider, or product boundaries.

## Accepted implementation that must not regress

The following areas are accepted in principle:

- dedicated `benchmark_index_daily` normalized contract and Alembic `20260718_0003`;
- restrictive ingestion-run relationship, natural key, validation, rollback, idempotency, and downgrade/upgrade coverage;
- separate benchmark and equity complete-snapshot series identities;
- one explicit AKShare `index_zh_a_hist` endpoint with no silent fallback;
- maximum 20 explicit codes, explicit network authorization, finite timeout/retries, live-cutoff discipline, offline fixture, and database-free dry run;
- explicit benchmark `series_key` or complete selector, one physical successful run, and no cross-run/series/provider/endpoint stitching;
- optional `benchmark_series_key` while preserving equity-only v0.4A API behavior;
- separate provenance and provider-attributed, non-official, non-full-market wording;
- lazy injectable database construction and 422/404/503 behavior;
- local semantic HTML/CSS/vanilla JavaScript using DOM/`textContent` only;
- no import, startup, page, test, CI, fixture-demo, or dry-run network side effect;
- no relative performance, alpha, beta, signals, recommendations, brokers, orders, or trading.

## Objective

Close two remaining correctness gaps:

1. benchmark metrics must use exact consecutive point-in-time open-session windows rather than merely the latest N stored rows;
2. benchmark alignment must never report `aligned` when exact code coverage is incomplete, per-code sessions disagree, or the documented cutoff-alignment condition is not satisfied.

## 1. Establish one explicit expected-session sequence

For Market Cockpit benchmark context, derive the expected A-share open-session sequence from the already selected equity snapshot's persisted trade calendar.

Requirements:

- use only persisted open sessions at or before the equity effective as-of session;
- honor the requested `as_of_cutoff`, equity cutoff, benchmark cutoff, equity effective session, and benchmark requested end date;
- never query a live calendar or infer weekdays;
- never use rows from another equity or benchmark run;
- pass the exact ordered expected-session sequence into the benchmark calculation boundary explicitly;
- keep benchmark and equity data rows separate even though the equity calendar defines session eligibility;
- fail or return an actionable non-success result if the required persisted calendar is unavailable or internally contradictory; do not silently fall back to row order alone.

Document why the selected equity trade calendar is the v0.4B session reference for A-share benchmark context.

## 2. Exact per-code window eligibility

For each exact benchmark code, classify row availability against the expected session sequence before calculating metrics.

### Latest close

- The latest available valid close at or before the permitted bound may still be exposed with its actual session.
- A stale or missing latest row must affect alignment and warnings.

### Latest return

Calculate `close(t) / close(t-1) - 1` only when:

- both rows are valid and finite;
- `t` is the code's latest available session;
- `t-1` is the immediately preceding expected open session.

Do not calculate a multi-session move and label it as a latest-session return. A missing immediately preceding expected session returns `null` with a bounded warning.

### SMA20 and SMA60

Calculate only when every one of the exact 20 or 60 expected open sessions ending at the code's latest session is present exactly once with a valid close.

- no shortened window;
- no sparse-row substitution;
- no forward fill;
- no substitution from another code;
- a gap outside a metric's required window must not invalidate that metric.

### Realized volatility and maximum drawdown

Calculate only from exactly 21 consecutive expected open sessions ending at the code's latest session.

- derive exactly 20 adjacent one-session returns;
- use sample standard deviation `ddof=1` and annualize by `sqrt(252)`;
- build drawdown from initial wealth `1.0` and the same 20 returns;
- any missing session inside the 21-session window returns both metrics as `null` plus a warning.

### Output and diagnostics

Keep outputs bounded and deterministic. Expose enough information to explain every null metric. Use either explicit per-window fields or an equally auditable structure containing at least:

- required session count;
- present valid session count within that exact window;
- window start/end session when definable;
- bounded missing session list or missing count;
- stable reason such as `insufficient_history`, `missing_expected_session`, or `invalid_close`.

A total historical `available_session_count` alone is not sufficient when a metric is null despite total rows exceeding its required count.

Sort code outputs and any missing-session details deterministically.

## 3. Deterministic alignment and coverage semantics

Revise benchmark context alignment so it accounts for exact requested-code coverage, per-code latest sessions, equity session, and cutoff policy.

At minimum expose bounded audit fields equivalent to:

- requested code count;
- available code count;
- aligned code count;
- exact missing code list;
- per-code latest session through existing metrics;
- equity information cutoff;
- benchmark information cutoff;
- equity effective session;
- effective benchmark session;
- session-alignment status;
- cutoff-alignment status, or one combined status with equally explicit semantics.

Required rules:

- `aligned` is permitted only when every exact requested code has an available latest row at the equity effective session and the documented cutoff-alignment condition is satisfied;
- if any requested code has no eligible row, status is `partial` and the code is listed;
- if code latest sessions differ, status is `partial`;
- if all available requested codes share one earlier session, status is a clear non-aligned value such as `different_session`;
- equal effective sessions with different information cutoffs must not remain silently `aligned` if documentation states cutoff differences are non-aligned; model cutoff alignment separately or use a documented combined non-aligned status;
- warnings, counts, status, provenance, and per-code metrics must not contradict one another.

Do not redefine selected benchmark codes as full-market coverage.

## 4. Documentation and page

Update only directly affected documentation and presentation:

- `docs/benchmark_context.md` must define the expected-session source, exact-window rules, gap behavior, coverage counts, and alignment/cutoff states;
- page formula wording must say exact consecutive persisted open-session windows, not merely N closes;
- the page must display coverage/alignment counts and missing codes without unsafe HTML;
- page empty states must not claim alignment or completeness when a requested code is unavailable;
- retain provider-attributed, non-official, non-advisory wording and all unsupported-section boundaries.

## 5. Required regression tests

Add deterministic tests for all of the following:

1. remove the immediately previous expected open session for one code: latest return is `null` with an explicit broken-window reason;
2. remove one middle expected session inside the last 20/21-session window: SMA20, volatility, and drawdown are `null` as applicable;
3. remove the same middle expected session from every selected code: the gap is still detected even though all code date sets match;
4. remove a session that is inside the 60-session window but outside the 20/21-session windows: SMA60 is null while shorter valid metrics remain available;
5. a gap strictly before all required ending windows does not invalidate current metrics;
6. one requested code has no row under the selected historical cutoff: available/aligned counts and status are partial, never aligned;
7. mixed per-code latest sessions produce partial status;
8. all requested codes share one earlier latest session: status is different-session/non-aligned;
9. equity and benchmark effective sessions match but information cutoffs differ: cutoff status is explicit and overall alignment is not misleadingly aligned;
10. fully complete exact windows preserve the accepted formulas and aligned result;
11. current/historical cutoff and future-row traps remain point-in-time safe;
12. API serialization and page rendering expose the revised bounded fields safely;
13. equity-only requests remain byte/semantic compatible except for already authorized optional defaults;
14. all existing migration, persistence, ingestion, v0.4A, Dashboard, and no-network tests continue to pass.

Use fixtures that would fail at reviewed head `6402762f1af6723b7a473a779edf9587598dcd91`.

## 6. Required validation

Run and report exact results for:

1. `python -m pytest -q` with the PostgreSQL test URL;
2. focused benchmark calculation/alignment/API/page regressions;
3. focused benchmark contract/persistence/provider/repository tests;
4. PostgreSQL benchmark and Market Cockpit current/as-of tests;
5. PostgreSQL persistence and migration suite;
6. clean Alembic `base -> head`;
7. `20260718_0003 -> 20260718_0002 -> 20260718_0003` downgrade/upgrade path;
8. `python -m alembic check`;
9. `python -m scripts.demo_research_flow`;
10. existing persisted equity current/historical demo;
11. revised persisted benchmark current/historical-cutoff demo including alignment counts/status;
12. offline benchmark dry run and repeated idempotent persistence;
13. `python -m compileall -q backend datasource market_cockpit scripts`;
14. import/startup/page/dry-run no-network regressions;
15. `git diff --check`.

Automated validation must remain offline. No new migration is expected for this revision.

## 7. GitHub synchronization

After implementing and pushing:

1. Update PR #48 body with:
   - new head SHA;
   - expected-session source and clipping rules;
   - exact per-window eligibility design;
   - gap reasons/counts;
   - final alignment and cutoff semantics;
   - changed files;
   - exact validation results;
   - revised current/historical demos and known limitations.
2. Add a concise Issue #47 completion comment with the same record.
3. Keep PR #48 Draft.
4. Stop for ChatGPT re-review.

## Exclusions and stop conditions

Do not:

- merge PR #48;
- close Issue #47;
- create a release or tag;
- change project version `0.2.0`;
- rewrite, squash, rebase, amend, or force-push the reviewed implementation commit;
- add a migration unless a separate schema defect is demonstrated and authorized;
- change the reviewed AKShare endpoint or add fallback endpoints;
- add sector/industry classification or rotation;
- add size/value/growth style, valuation, market-cap breadth, or crowding;
- add beta, correlation, alpha, excess return, relative-strength ranking, signals, or recommendations;
- persist derived Market Cockpit snapshots;
- add schedulers, background collection, page-triggered collection, or automatic refresh;
- begin v0.5 or any later stage;
- add Stock Research, Watchlist, paper portfolios, LLM execution, authentication, deployment, brokers, orders, or trading;
- modify, close, rebase, or merge unrelated PR #38.

Stop and report instead of improvising if exact expected-session continuity cannot be established from the selected persisted equity calendar without breaking accepted v0.4A behavior.