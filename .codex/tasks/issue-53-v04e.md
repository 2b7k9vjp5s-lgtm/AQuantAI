# Issue #53 — v0.4E Price-Behavior Context

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#53 [v0.4E] Price-behavior style proxy and risk-appetite context`
- Branch: `feat/v04e-price-behavior-context`
- Draft PR title: `[v0.4E] Add price-behavior context`
- Required ancestor: v0.4D squash merge `02a53f1032c9fa5f60243dec3a053b4ba8ae5c9b`
- Project version must remain `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #53, this task, the merged v0.4A-v0.4D Market Cockpit implementation, and current CI before editing.

Keep the PR Draft. Do not merge, close Issue #53, create a release/tag, change version, begin v0.5, or modify PR #38.

## Product boundary

Implement one narrow, local, deterministic, selected-universe, read-only context built only from price behavior already present in the selected persisted equity snapshot.

The feature must be named and presented as a **price-behavior proxy**, not a canonical institutional style model. Do not claim size, value, growth, quality, profitability, market-cap, valuation, beta, alpha, factor exposure, or a market regime.

The context is descriptive research evidence only. It must not produce a score, signal, recommendation, attractiveness ranking, risk-on/risk-off conclusion, crowding conclusion, portfolio action, or trading behavior.

## Authorized inputs and architecture

Reuse exactly the v0.4A-v0.4D selected equity path:

- the same physical `PersistedMarketDataSnapshot` selected by the existing repository/service;
- the same accepted effective session;
- the same filtered stock-code scope and price lookup;
- the same persisted point-in-time open-session sequence;
- the same selected ingestion run, series key, cutoff, requested date range, adjustment, provider, and provenance.

Use only persisted `daily_price.close` plus existing traded-row validity rules.

Do not add:

- another selector, repository, series, ingestion run, calendar, or cross-run stitching;
- a provider endpoint, network call, ingestion script, scheduler, or automatic refresh;
- a table, migration, derived-snapshot persistence, dependency, Docker/Compose, CI, or launcher change;
- inferred market cap, free float, fundamentals, valuation, sector constituents, or company mappings.

No database migration is expected. Stop and report before adding one.

## Exact calculations

All sessions below are the selected snapshot's persisted open sessions ending at the accepted effective session `t`. All returns are decimal values.

### 1. Exact 20-session momentum

Require exactly 21 persisted open sessions: `t-20 ... t`.

A stock is eligible only when every required session has one accepted traded observation with a finite positive close.

```text
return_20(i,t) = close(i,t) / close(i,t-20) - 1
```

Do not shorten the window, bridge a missing session, use only the endpoints when an intermediate required observation is invalid, fill, interpolate, or substitute zero.

### 2. Exact 60-session momentum

Require exactly 61 persisted open sessions: `t-60 ... t`, with the same complete-window eligibility rule.

```text
return_60(i,t) = close(i,t) / close(i,t-60) - 1
```

### 3. Exact 20-return realized volatility per stock

Require exactly 21 persisted open sessions and all 20 valid close-to-close returns.

```text
r(i,s) = close(i,s) / close(i,s-1) - 1
volatility_20(i,t) = sample_std(last 20 r(i,s), ddof=1) * sqrt(252)
```

Reject non-finite intermediate returns and non-finite aggregate results. Do not clip or partially calculate.

### 4. Independent cross-sectional summaries

For each metric, preserve its exact independent eligible cohort and report:

- requested stock count;
- eligible count;
- unavailable count;
- median value, or `null` when no eligible finite value exists.

For 20-session and 60-session momentum also report:

- positive count where return is strictly greater than zero;
- non-positive count where return is less than or equal to zero;
- positive share using the eligible cohort as denominator;
- `null` share when eligible count is zero.

All medians, ratios, and aggregate outputs must be finite or `null`. Use fail-closed helpers rather than emitting `NaN` or `Infinity`.

### 5. Fixed matched descriptive quadrant

Create one fixed matched cohort containing only stocks eligible for all three metrics: return-20, return-60, and volatility-20.

Calculate the median volatility over that full matched cohort. Ties belong to the `<= median` side.

Report exact count and share for exactly four buckets:

1. `positive_momentum_lower_or_equal_volatility`
   - `return_60 > 0`
   - `volatility_20 <= matched median volatility`
2. `positive_momentum_higher_volatility`
   - `return_60 > 0`
   - `volatility_20 > matched median volatility`
3. `non_positive_momentum_lower_or_equal_volatility`
   - `return_60 <= 0`
   - `volatility_20 <= matched median volatility`
4. `non_positive_momentum_higher_volatility`
   - `return_60 <= 0`
   - `volatility_20 > matched median volatility`

Required invariants when the matched cohort is non-empty:

```text
sum(bucket counts) == matched_cohort_count
sum(bucket shares) == 1 within reviewed floating tolerance
```

When the matched cohort is empty:

- matched cohort count is zero;
- matched median volatility is `null`;
- every bucket count is zero;
- every bucket share is `null`;
- status/reason explicitly reports the empty or unavailable cohort.

This quadrant is a transparent selected-universe distribution. Do not label it risk-on, risk-off, defensive, aggressive, leadership, style rotation, or investment attractiveness.

## Contracts and naming

Add a backward-compatible nested context named `price_behavior_context` unless a clearly superior reviewed name is already established in the codebase.

Use typed contracts for:

- metric status/reason;
- exact window metadata;
- independent summary counts and values;
- matched cohort and four buckets;
- diagnostics and bounded identifier samples;
- warnings, interpretation, formula reference, scope label, and `read_only=true`.

The context must always be present for a successfully selected equity snapshot. Insufficient history returns a typed unavailable context with factual counts/nulls; do not remove the field.

## Diagnostics

Define one reviewed identifier sample limit, preferably reusing the existing Market Cockpit bounded diagnostic convention when compatible.

Diagnostics must distinguish at least:

- insufficient persisted open-session history;
- missing required stock/session row;
- no-trade required row;
- invalid, non-positive, or non-finite close;
- duplicate or excluded accepted-path rows where the existing filtered lookup exposes them;
- non-finite calculation or aggregate;
- empty matched cohort.

Every growing stock-code list must expose:

- exact count;
- deterministic stock-code-ascending bounded sample;
- truncation flag;
- omitted count.

Warnings must use bounded samples and `(+N more)` style suffixes. Truncation affects presentation only and must never change eligibility, medians, bucket counts, shares, or status.

Do not expose raw provider payloads, arbitrary request metadata, local paths, credentials, headers, or secrets.

## Service, API, and page integration

- Calculate the context from the already accepted snapshot, effective session, expected sessions, filtered lookup, and validity predicates.
- Do not query the database or select data again inside the new calculator.
- Preserve all existing v0.4A breadth/risk, v0.4B benchmark, v0.4C sector, and v0.4D liquidity fields and calculations.
- Preserve existing selectors, API routes, query parameters, status mappings, and optional benchmark/sector behavior.
- Add one clearly bounded read-only page section labelled as selected-universe price-behavior proxies.
- Render unavailable values as `Unavailable` and use DOM-safe `textContent`/element construction only.
- Do not add forms, buttons, automatic refresh, network calls, or trading controls.

## Documentation

Update only the relevant narrow documentation:

- `docs/market_cockpit.md` with exact formulas, complete-window rules, matched-cohort quadrant, statuses, diagnostics, and explicit non-style/non-advisory limits;
- `docs/implementation_plan.md` with a short v0.4E authorized-slice paragraph;
- `docs/product_architecture.md` to mark v0.4D merged and v0.4E in review without claiming canonical style, valuation, or crowding support;
- local usage/demo documentation only if a new offline demo command is added.

Do not rewrite unrelated roadmap stages.

## Expected implementation surface

Expected files are limited to a narrow additive surface, such as:

- `market_cockpit/price_behavior_contracts.py`;
- `market_cockpit/price_behavior_calculator.py`;
- existing Market Cockpit contracts/calculator/service integration files only where necessary;
- existing API serialization path only where necessary;
- Market Cockpit HTML/JS and minimal CSS only where necessary;
- focused tests;
- a deterministic offline fixture/demo only if useful;
- the narrow documentation listed above.

Do not change datasource adapters, persistence models/services, migrations, dependencies, Docker/Compose, CI, launcher behavior, version files, Quant Core modules, Industry Alpha modules, or PR #38.

## Required tests

Add deterministic tests for at least:

1. exact 20-session momentum ordinary values;
2. exact 60-session momentum ordinary values;
3. exact 20-return annualized volatility with `ddof=1`;
4. strictly positive versus zero/non-positive momentum boundary;
5. volatility median tie goes to `<= median`;
6. all four quadrant buckets and sum invariants;
7. small universes, including one-stock and two-stock cohorts;
8. insufficient 21-session and 61-session calendars;
9. missing intermediate rows, proving endpoints alone are insufficient;
10. no-trade and invalid/non-finite closes;
11. empty independent and matched cohorts;
12. bounded deterministic diagnostics with exact counts/truncation/omitted counts;
13. truncation does not change full-cohort calculations;
14. repeated calculations are identical;
15. strict `json.dumps(..., allow_nan=False)`;
16. FastAPI JSON returns finite values or `null` only;
17. page renders nulls safely and contains no unsafe HTML construction;
18. v0.4A breadth/risk regression;
19. v0.4B benchmark regression;
20. v0.4C sector regression;
21. v0.4D liquidity regression;
22. no-network import/startup/page regression.

## Validation

Run and report exact results for:

- focused price-behavior contracts/calculator tests;
- focused service/API/page tests;
- v0.4A-v0.4D compatibility suites;
- complete offline test suite;
- PostgreSQL-enabled full suite using an isolated temporary database;
- persistence/migration regressions proving no schema change;
- clean Alembic `base -> head` and `python -m alembic check`;
- all existing current/historical Market Cockpit, benchmark, sector, liquidity, and research demos;
- any new price-behavior demo in current and insufficient-history modes;
- no-network tests;
- `python -m compileall -q backend datasource market_cockpit scripts`;
- `git diff --check`;
- final GitHub Actions for the implementation Head.

All tests and demos must remain offline. Do not make a live AKShare call.

## GitHub handoff

After implementation:

1. Update Draft PR #54 with final Head, exact files, formulas, statuses, diagnostics, boundaries, validation counts, and CI.
2. Add concise PR #54 and Issue #53 comments with the same final handoff.
3. Keep PR #54 Draft, open, and unmerged.
4. Keep Issue #53 open.
5. Stop for ChatGPT review.

Do not mark Ready, merge, close Issue #53, create a release/tag, change version `0.2.0`, begin v0.5, or modify PR #38.