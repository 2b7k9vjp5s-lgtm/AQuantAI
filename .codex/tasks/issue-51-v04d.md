# Issue #51 — v0.4D Liquidity Distribution And Trading Concentration Context

## Task identity

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#51 [v0.4D] Liquidity distribution and trading concentration context`
- Branch: `feat/v04d-liquidity-context`
- Draft PR: `[v0.4D] Add liquidity distribution context`
- Required ancestor: v0.4C squash merge `98aed74f069a2e9751e2ed8e8dc529b0fe5bc435`
- Project version remains `0.2.0`

Read `.codex/WORKFLOW.md`, Issue #51, this task, `docs/implementation_plan.md`, `docs/product_architecture.md`, `docs/market_cockpit.md`, the accepted v0.4A calculator/contracts/repository/service/API/page, and the v0.4B/v0.4C optional-context integrations before editing.

Keep the PR Draft. Do not merge, close Issue #51, release, tag, change version, begin v0.5, or modify PR #38.

## Product boundary

Implement one additive, deterministic, read-only Market Cockpit liquidity-distribution slice from the already persisted selected-equity snapshot.

This task is:

- local-first and personal-use;
- selected-scope rather than full-market;
- provider-attributed and cutoff-aware;
- descriptive rather than predictive;
- calculation-only over one physical accepted equity snapshot;
- network-free during imports, startup, tests, CI, demos, and page use.

Trading concentration is a distribution statistic. It must never be labeled or interpreted by the product as proof of crowding, a regime, a signal, a recommendation, or investment attractiveness.

## Authorized data

Use only data already present in `PersistedMarketDataSnapshot` and its canonical series:

- exact selected `stock_codes`;
- `daily_price.trade_date`, `stock_code`, `close`, `volume`, `amount`, `adjust_type`, and `source`;
- persisted `trade_calendar` open sessions;
- stock-basic identity/status metadata;
- provider, requested date range, information cutoff, adjustment policy, provenance, completeness, and existing effective-session logic.

Do not add:

- provider endpoints or network calls;
- ingestion commands or provider metadata;
- database tables or migrations;
- a separately selected liquidity series or second calendar;
- shares outstanding, free float, market capitalization, turnover-rate inference, order-book data, margin data, northbound flow, fund holdings, sentiment, or valuation fields.

Never stitch rows across ingestion runs or canonical series.

## Effective session and row eligibility

Reuse the existing Market Cockpit effective session and expected open-session sequence exactly. Do not independently choose a liquidity date.

A liquidity observation for one stock/session is eligible only when:

1. the row belongs to the exact selected code and canonical adjustment policy;
2. the session is an eligible persisted open session at or before the effective session;
3. duplicate stock/session rows have already been excluded by the accepted fail-closed behavior;
4. the accepted traded-record semantics are satisfied;
5. `amount` is finite and strictly positive.

Missing, duplicate, future, out-of-calendar, wrong-scope, wrong-adjustment, non-finite, negative, zero, or no-trade observations are unavailable. They must never be filled, interpolated, forward-filled, shortened, or converted to zero.

## Required contracts

Add explicit typed contracts for a nested additive liquidity context. Names may follow repository conventions, but the public meaning must include:

- effective session;
- requested stock count;
- latest eligible/unavailable counts;
- latest total amount;
- latest median amount;
- top-5 concentration share and member count;
- top-decile concentration share and member count;
- exact 5-session activity window result;
- exact 20-session activity window result;
- latest-above-20-session-baseline count/share;
- structured diagnostics and warnings;
- calculation status such as complete/partial/unavailable using existing naming conventions where practical.

Keep existing v0.4A public fields unchanged. The new field must be additive and JSON-safe. Existing API consumers that ignore it must remain compatible.

## Exact formulas

Let `t` be the existing effective equity session and `A(i,s)` be the eligible positive trading amount for stock `i` on expected session `s`.

### Latest distribution

Let `E_t` be selected codes with eligible `A(i,t)`.

```text
latest_total_amount(t) = sum(A(i,t), i in E_t)
latest_median_amount(t) = median(A(i,t), i in E_t)
```

If `E_t` is empty, both metrics and both concentration shares are `null`, eligible count is zero, and status is unavailable.

For concentration, sort eligible stocks by amount descending and stable stock code ascending for ties.

```text
top5_count = min(5, len(E_t))
top5_share = sum(top top5_count amounts) / latest_total_amount

top_decile_count = max(1, ceil(0.10 * len(E_t)))
top_decile_share = sum(top top_decile_count amounts) / latest_total_amount
```

The small-universe rule above is mandatory and must be documented. Do not silently use floor, round, five names, or a full-universe denominator for the top-decile metric.

### Exact aggregate activity windows

For window `w` in `{5, 20}`, require exactly `w` prior expected sessions plus `t`. The candidate sessions are `S_w = [t-w, ..., t-1, t]` in the persisted expected-session sequence.

Define the matched cohort `E_w` as selected codes having eligible positive amount on every session in `S_w`.

For each session `s` in `S_w`:

```text
matched_total_w(s) = sum(A(i,s), i in E_w)
```

Then:

```text
baseline_total_w(t) = median(matched_total_w(s), s in the exact w prior sessions)
activity_ratio_w(t) = matched_total_w(t) / baseline_total_w(t)
```

Return the matched cohort count and sorted unavailable codes. If the expected-session history is shorter than `w + 1`, `E_w` is empty, or the baseline is not finite and strictly positive, the baseline and ratio are `null` with a deterministic diagnostic. Never substitute a partial window or a changing per-session cohort.

### Above-baseline participation

For every stock in `E_20`:

```text
stock_baseline_20(i,t) = median(A(i,s), s in the exact 20 prior sessions)
above_20(i,t) = A(i,t) > stock_baseline_20(i,t)
```

```text
above_20_count = sum(above_20(i,t), i in E_20)
above_20_share = above_20_count / len(E_20)
```

Use a strict greater-than comparison. Equality is not above baseline. If `E_20` is empty, count is zero and share is `null`.

## Diagnostics

Provide deterministic diagnostics covering at least:

- missing latest row;
- no-trade or zero-amount latest row;
- invalid/non-finite/negative latest amount;
- incomplete 5-session window;
- incomplete 20-session window;
- duplicate, future, out-of-calendar, wrong-scope, and wrong-adjustment exclusions already detected by the accepted calculator path;
- insufficient persisted open-session history.

Keep diagnostics bounded and stable. Counts must remain exact. Code lists must be sorted and must not expose provider raw payloads, local paths, credentials, or arbitrary metadata.

## Integration

1. Extend the existing deterministic calculator rather than adding an LLM or provider dependency.
2. Prefer a focused liquidity calculator/module if that keeps contracts and tests clearer, but it must consume the same single `PersistedMarketDataSnapshot` and effective-session sequence.
3. Extend `MarketCockpitService` and snapshot contracts additively.
4. Extend `/market-cockpit/snapshot` without a new selector parameter.
5. Add a read-only page section that clearly labels the scope as selected-universe and trading concentration as descriptive.
6. Render unavailable values safely; no `NaN`, `Infinity`, misleading zero, broken percentage, or unsafe DOM output.
7. Preserve optional benchmark and sector behavior when their series keys are absent or present.

## Compatibility requirements

Prove that:

- accepted v0.4A breadth, participation, risk, provenance, diagnostics, and cutoff behavior are unchanged;
- accepted v0.4B benchmark context remains unchanged;
- accepted v0.4C sector context remains unchanged;
- existing API calls without any new client behavior continue returning HTTP 200 and their prior fields;
- no database schema or migration changes are introduced;
- project version stays `0.2.0`;
- PR #38 is untouched.

## Tests

Add deterministic tests for at least:

1. complete latest distribution with exact total, median, top-5 share, and top-decile share;
2. tie ordering by amount then stock code;
3. top-decile behavior for universes smaller than 10 and larger than 10;
4. exact 5-session matched-cohort baseline and ratio;
5. exact 20-session matched-cohort baseline and ratio;
6. latest-above-20 baseline count/share with strict greater-than behavior;
7. one missing or invalid row excluding that stock from the entire matched cohort rather than changing the cohort by session;
8. insufficient 6-session and 21-session history producing null metrics;
9. zero, negative, non-finite, no-trade, duplicate, future, out-of-calendar, wrong-scope, and wrong-adjustment behavior;
10. all-latest-unavailable behavior;
11. partial latest coverage with correct denominators;
12. JSON serialization containing no `NaN` or `Infinity`;
13. API backward compatibility with and without benchmark/sector keys;
14. read-only page rendering and unavailable-value safety;
15. no-network import/startup/page behavior;
16. regression coverage for existing v0.4A/v0.4B/v0.4C outputs.

Use fixtures only. Do not perform live provider calls.

## Documentation

Update the narrow relevant documentation to state:

- exact formulas and matched-cohort semantics;
- selected-scope and provider-attributed limitations;
- amount units remain provider-attributed and are not normalized into currency advice;
- concentration is descriptive and not a crowding conclusion;
- missing-data and small-universe rules;
- no new provider, persistence, migration, or automatic collection capability;
- style, valuation, and v0.5 remain unsupported.

## Expected files

Keep the change bounded to files such as:

- `market_cockpit/contracts.py`;
- `market_cockpit/calculator.py` or one focused liquidity calculator;
- `market_cockpit/service.py`;
- `backend/api/market_cockpit.py` only if contract wiring requires it;
- `market_cockpit/static/market_cockpit.html`;
- `market_cockpit/static/market_cockpit.js`;
- focused calculator/API/page tests;
- `docs/market_cockpit.md`, `docs/implementation_plan.md`, and `docs/product_architecture.md` where current-state wording must be updated.

Do not change datasource adapters, persistence models, migrations, dependencies, Docker/Compose, CI, launcher behavior, version files, or unrelated research modules.

## Required validation

Run and report exact results for:

1. `python -m pytest -q`;
2. focused liquidity calculator/contract tests;
3. focused Market Cockpit service/API/page tests;
4. focused v0.4A breadth/risk regression tests;
5. focused v0.4B benchmark regression tests;
6. focused v0.4C sector regression tests;
7. PostgreSQL persistence and migration regression tests showing no schema change;
8. no-network import/startup/page tests;
9. `python -m alembic check`;
10. `python -m scripts.demo_research_flow`;
11. existing persisted Market Cockpit current/historical demos;
12. benchmark and sector current/historical demos;
13. a deterministic liquidity fixture demonstration;
14. `python -m compileall -q backend datasource market_cockpit scripts`;
15. `git diff --check`;
16. GitHub Actions for the final implementation Head.

All validation must remain offline.

## GitHub handoff

After implementation:

1. Update the Draft PR body with base/head SHA, exact files, formulas, contracts, diagnostics, compatibility results, validation counts, and exclusions.
2. Add a concise PR comment and Issue #51 comment with the same implementation record.
3. Keep the PR Draft.
4. Stop for ChatGPT review.

Do not mark Ready, merge, close Issue #51, create a release/tag, change version, start v0.5, or modify PR #38.