# Issue #278 — Today Market Ordinary-User Runtime/UI Integration v1

## Authority

Project-owner implementation authorization received on 2026-07-31:

```text
进行下一步开发，完成后给出下一步开发简短指令
```

This instruction authorizes implementation of the already-frozen Slice C scope in Issue #278. It does not authorize Ready, merge, Issue closure, live Provider/network activation, schema/migration, recommendation, portfolio, trading, release/tag/version work, or modification of PR #241.

## Exact start state

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
default_branch = main
exact_main_at_start = c21ce253087927c8233837fe067ececc14fbb51d
issue = #278
accepted_architecture = #270 / merged PR #271
slice_a = #273 / merged PR #275
slice_b = #276 / merged PR #277
branch = feat/today-market-ordinary-user-runtime-ui-integration-v1
risk_tier = Strict Implementation
```

Before branch creation, `main` was re-read and confirmed identical to `c21ce253087927c8233837fe067ececc14fbb51d`.

## Objective

Implement the source-neutral ordinary-user Today Market read/projection layer and Chinese-first page using only existing accepted owners:

```text
last valid local snapshot
+ exact runtime status
+ deterministic Slice B results when exact inputs are available
+ explicit fail-closed/unavailable reasons when exact inputs are unavailable
  -> TodayMarketReadModelV1
  -> ordinary-user Today Market page
```

The browser renders backend-owned deterministic results. It must not reproduce Market Overview, Sector Hotspot, or Stock Anomaly thresholds.

## Frozen read model

```text
TodayMarketReadModelV1 = {
  snapshot_id,
  data_date,
  data_status,
  source_summary,
  coverage,
  refresh_state,
  market_state,
  core_indices,
  market_overview,
  sector_groups,
  stock_anomalies,
  research_link_summary,
  warnings,
  technical_details,
  read_model_fingerprint
}
```

The projection is deterministic for the same authoritative snapshot/runtime inputs. Presentation-only request timestamps must not alter the canonical read-model fingerprint.

## Ordinary-user behavior

1. Prior complete snapshot remains visible before any runtime command and through refresh/failure/cancellation.
2. First-screen order is frozen:
   1. one-sentence market state + latest complete session + refresh state;
   2. core indices / advances-declines / breadth / activity;
   3. strengthening / new / spreading / persistent-strong sectors;
   4. high-level-divergence / cooling sectors;
   5. meaningful stock anomalies;
   6. coverage and source explanation;
   7. folded technical details.
3. Exactly one visually dominant action may be offered for the current runtime state.
4. Source-neutral refresh states are limited to:

```text
current
checking
refresh_required
refreshing
refreshed
not_initialized
manual_catchup_required
blocked_source_contract
failed_retained_prior
cancelled_retained_prior
```

5. Current default production configuration has no authorized live source. It must remain zero-network and show `blocked_source_contract` while retaining local snapshot content.
6. Synthetic Mock is test/demo only and must remain explicitly synthetic.
7. No recommendation, target price, expected return, position size, portfolio action, or trading language.

## Exact implementation allowlist

Only these paths may change:

```text
.codex/tasks/issue-278-today-market-ordinary-user-runtime-ui-integration-v1.md
backend/api/today_market.py
backend/today_market_refresh/read_model.py
today_market/static/today_market.html
today_market/static/today_market.js
today_market/static/today_market.css
tests/test_today_market_runtime_integration.py
tests/test_today_market_ordinary_user_runtime_ui.py
scripts/demo_today_market_runtime_integration.py
.github/workflows/local-tests.yml
```

No other file is authorized.

Explicitly unchanged unless a later owner-approved allowlist amendment is granted:

```text
backend/database/**
migrations/**
datasource/**
backend/today_market_refresh/port.py
backend/today_market_refresh/runtime.py
market_cockpit/today_market_rule_contracts.py
market_cockpit/today_market_rules.py
market_cockpit existing calculators/repositories/services
backend/main.py
recommendation/**
portfolio/**
trading/**
accepted research/evidence mutation paths
release/tag/version files
PR #241
```

If exact Slice B inputs cannot be assembled through the authorized read/projection boundary, STOP and preserve an explicit unavailable result. Do not widen ownership.

## Fail-closed boundaries

```text
new database/schema owner = prohibited
new Provider/source adapter = prohibited
live Provider/network activation = prohibited
runtime fallback provider = disabled
cross-provider row mixing = prohibited
AI/LLM calculation/state ownership = prohibited
recommendation/portfolio/trading mutation = prohibited
current constituents as historical membership substitute = prohibited
raw close as adjustment/reference-close substitute = prohibited
localStorage runtime scope/status identity = prohibited
browser polling/background retry = prohibited
```

Missing exact dated membership blocks constituent-confirmed hotspot/sector-relative anomaly projection. Missing exact analysis-price/reference-close semantics blocks affected cross-session calculations. Those gaps remain visible as unavailable reasons rather than being guessed.

## Implementation approach

- Add `backend/today_market_refresh/read_model.py` as a pure source-neutral projection module.
- Reuse existing `backend/api/today_market.py` authoritative local snapshot and runtime-status boundaries.
- Reuse merged Slice B pure rule functions without changing their contracts or thresholds.
- Assemble only rule inputs that are provably exact from existing snapshot content; otherwise expose unavailable diagnostics.
- Keep GET paths read-only and zero-acquisition.
- Keep runtime status identity server-owned.
- Update Chinese-first HTML/JS/CSS to render the read model without duplicating formulas.

## Required validation

Positive:

- prior snapshot is rendered before any runtime command;
- exact `TodayMarketReadModelV1` shape;
- deterministic fingerprint/replay;
- exact Slice B projection when exact inputs are supplied;
- Chinese-first labels and first-screen order;
- one dominant action by state;
- Mock-only zero-network test/demo path;
- retained prior snapshot on failure/cancellation;
- runtime status fingerprint conflict/replay remains intact.

Negative:

- default production path remains zero-network and exposes blocked-source state;
- GET snapshot/status performs zero acquisition/write;
- missing dated membership cannot produce constituent-confirmed hotspot state;
- missing adjustment/reference-close semantics cannot produce affected anomaly/metric;
- browser contains no deterministic threshold calculations;
- runtime identity is not written to localStorage;
- no polling/scheduler/background retry;
- no recommendation/portfolio/trading/research mutation path;
- new read-model module has no Provider/schema/migration/network/write imports.

Normal CI/demos remain zero-network and synthetic/schema-reachable only.

## Fixed-head gate

Before merge consideration:

1. Base remains exact `c21ce253087927c8233837fe067ececc14fbb51d` and behind = 0.
2. Base→HEAD contains only the exact allowlist above.
3. Focused Slice C tests, full pytest and every configured offline demo succeed on one immutable HEAD.
4. unresolved review threads = 0.
5. Fresh fixed-head implementation review records exactly:

```text
AUTHORIZED TODAY MARKET ORDINARY-USER RUNTIME/UI INTEGRATION V1 IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

6. Any new commit invalidates previous fixed-head CI/review evidence.
7. Project owner separately authorizes Ready/merge.
8. Keep the PR Draft through implementation.