# Issue #273 Task Snapshot — Today Market Daily Market Acquisition Foundation v1

## Authority

Project-owner implementation authorization on 2026-07-29:

```text
启动 Issue #273 的实现开发，先完成仓库与 schema/migration stop-condition 审计；
确认无需 migration 后，创建只包含精确授权文件的 Draft PR
```

Project-owner M2/M3 authorization on 2026-07-29:

```text
在同一个 Draft PR #274 内继续 M2 请求规划与 M3 响应校验，
所有提交必须限制在任务快照冻结的精确文件清单内
```

Project-owner replacement authorization on 2026-07-29:

```text
冻结并关闭 PR #274 为 superseded；从当前精确 main 创建干净替代分支和 Draft PR，
重建 M1–M3 的最终授权内容，不 cherry-pick #274 提交，不修改 allowlist 外文件；
验证通过后继续 M4–M6
```

## Exact replacement start state

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
exact_base = afc6ae442a440fa9099494d0aa3f6ab12e64fb57
implementation_issue = #273
superseded_pr = #274 / closed / Draft / unmerged / read-only
replacement_branch = feat/today-market-daily-market-acquisition-foundation-v1-clean
risk_tier = Strict Implementation
workflow = .codex/WORKFLOW.md
selected_source = ths-account-structured-provider-v1
```

PR #274 is permanently excluded from merge and fixed-head review because its commit history contains temporary out-of-allowlist files even though its final diff was clean. The replacement branch:

- starts from exact current `main`;
- does not cherry-pick any #274 commit;
- rebuilds only the final authorized M1–M3 tree;
- preserves every existing exclusion and stop condition;
- must keep every replacement commit within the exact allowlist below.

PR #241 remains permanently frozen, closed, Draft and unmerged at
`3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

## Accepted predecessors

```text
Today Market architecture = #270 / merged PR #271
source-contract amendment = #272 / closed / completed
THS Stage C0 offline foundation = #227/#229 + #230/#231
provider-neutral acquisition port = #253/#254
Today Market deterministic Mock = #255/#256
Today Market runtime integration = #259/#260 + #261/#262
```

## Schema/migration audit

The exact-base audit reviewed existing `IngestionRun`, normalized Stock Basic, Daily Price,
Trade Calendar and Benchmark Index Daily owners, THS Stage C0 contracts and the
provider-neutral Today Market acquisition port.

```text
schema_migration_required = false
migration_files_authorized = none
database_model_changes_authorized = none
```

Existing ownership is sufficient for Slice A v1 because:

1. `IngestionRun` records immutable attempt provenance, batch identity, series identity,
   request scope, source metadata, versions and status.
2. Identical successful content converges through existing idempotency constraints.
3. Changed source content can be represented as an additional immutable run.
4. `DailyPriceRecord.adjust_type` separates raw/qfq/hfq series.
5. Trade Calendar, Stock Basic and Benchmark Index Daily already have run-bound owners.
6. Existing persistence services validate scope, dates, identities, OHLC consistency and
   duplicate natural keys before atomic commit.

Locked stop conditions:

```text
standalone adjustment-factor persistence required -> STOP
company-action event persistence required -> STOP
durable historical industry/concept membership required -> STOP
changed facts cannot be represented as a new immutable run -> STOP
new table/column/index/migration/backfill required -> STOP
```

No JSON blob, hidden file, side database or ad-hoc persistence workaround is allowed.

## Project-owner provisional source contract

Issue #272 closed with:

```text
private_local_retention = allowed for project use
private_local_retention_period = indefinite
provider_historical_query_horizon = rolling 10 years
locally persisted valid history may outlive the Provider query window
public Provider-valued repository fixtures = prohibited
unsupported taxonomy/date = fail closed
```

These are project-owner provisional operating assumptions, not Provider legal confirmation.
Later contradictory official terms invalidate live readiness and require a reviewed amendment.

## Exact authorized file inventory

The replacement implementation PR may add or modify only:

```text
.codex/tasks/issue-273-today-market-daily-market-acquisition-foundation-v1.md

datasource/ths_structured_provider/__init__.py
datasource/ths_structured_provider/live_contracts.py
datasource/ths_structured_provider/live_selectors.py
datasource/ths_structured_provider/live_planner.py
datasource/ths_structured_provider/live_schemas.py
datasource/ths_structured_provider/credentials.py
datasource/ths_structured_provider/transport.py
datasource/ths_structured_provider/acquisition.py

backend/today_market_refresh/contracts.py
backend/today_market_refresh/port.py

tests/test_ths_daily_market_acquisition_contracts.py
tests/test_ths_daily_market_acquisition_planning.py
tests/test_ths_daily_market_acquisition_validation.py
tests/test_ths_daily_market_acquisition_persistence.py
tests/test_today_market_live_acquisition_handoff.py

tests/fixtures/ths_daily_market_acquisition/stock_basic_success.synthetic.json
tests/fixtures/ths_daily_market_acquisition/trade_calendar_success.synthetic.json
tests/fixtures/ths_daily_market_acquisition/a_share_daily_success.synthetic.json
tests/fixtures/ths_daily_market_acquisition/benchmark_daily_success.synthetic.json
tests/fixtures/ths_daily_market_acquisition/partial_response.synthetic.json

scripts/demo_ths_daily_market_acquisition.py
.github/workflows/local-tests.yml
```

No additional path is authorized. In particular:

```text
backend/database/** = unchanged
migrations/** = unchanged
docs/architecture_baseline.md = unchanged
backend/api/** = unchanged
today_market/static/** = unchanged
market_cockpit/** = unchanged
release/tag/version files = unchanged
PR #241 = unchanged
```

## Implemented M1–M6 candidate

The replacement branch reconstructs the final authorized M1–M3 content as a new commit whose
only parent is exact `main`. It does not copy or preserve #274 commit ancestry. M4–M6 were then
implemented additively inside the same exact allowlist. The implementation is a candidate until
one exact immutable HEAD passes focused tests, full tests, configured offline demos and GitHub CI.

### M1 — source policy and readiness

Implemented content:

- one THS/iFinD source authority;
- reviewed host family, credential-reference type, QPS and ten-year boundary;
- Provider-public facts separated from project-owner provisional assumptions;
- synthetic-only public fixtures;
- remote execution disabled by default;
- secret-free deterministic contract fingerprints;
- no Provider fallback or source mixing.

### M2 — selectors and request planning

Implemented content:

- closed capability registry;
- explicit instrument identity, exchange and exact requested sessions;
- exact expected natural keys rather than inferred listing/suspension behavior;
- rolling ten-year rejection with no silent truncation;
- one-session and ten-session deterministic planning;
- explicit call/cell/QPS budget revision without account identity;
- no arbitrary host/path/header/query dictionaries;
- request and plan fingerprints exclude credentials and volatile request IDs;
- persisted logical plans remain non-executable; transport execution is a separate explicit M4 boundary.

### M3 — response validation

Implemented content:

- strict envelope/source/capability/schema validation;
- exact selector-to-response identity/date/natural-key agreement;
- OHLC, finite numeric, nonnegative volume/amount and chronology checks;
- duplicate, conflicting, unrequested and partial rows fail closed;
- volatile request IDs excluded from content fingerprints;
- synthetic fixtures only;
- historical block response schema remains unavailable pending exact taxonomy review.

### M4 — credential reference and transport

Implemented candidate content:

- credential reference only; no token value, fragment, length or hash persistence;
- only reviewed THS/iFinD host and operation contracts;
- network disabled by default and no concrete live network client in normal runtime/tests/demos;
- deterministic timeout, authentication, quota, rate-limit and bounded-retry mapping;
- no fallback or source mixing;
- ordinary CI/import/demo remains zero-network.

### M5 — immutable persistence

Implemented candidate content:

- reuse existing market and benchmark persistence services;
- bind source policy, request fingerprint and attempt metadata to `IngestionRun`;
- identical facts replay idempotently;
- changed facts append as a new run;
- partial attempts never become a completed acquisition batch;
- preserve prior valid local history on every failure;
- trigger schema stop condition instead of side storage;
- preserve concrete persistence-owner provenance inside the M5 receipt;
- expose a stable provider-neutral component key on each persisted receipt for the M5→M6 boundary.

### M6 — provider-neutral handoff

Implemented candidate content:

- preserve all existing Mock-only invariants and tests;
- expose acquisition completeness and provenance only;
- consume provider-neutral persisted component identities plus run/batch/series/cutoff provenance;
- do not import or depend on concrete database persistence services;
- do not expose persistence implementation owner names in application component DTOs or summaries;
- mismatched component roles, source, acquisition fingerprint or coverage fail closed;
- do not calculate market, sector, hotspot or anomaly truth;
- do not activate startup/first-entry networking.

Current gate:

```text
M1 = implemented
M2 = implemented
M3 = implemented
M4 = implemented candidate
M5 = implemented candidate
M6 = implemented candidate
implementation_candidate = complete pending exact-head validation
final_fixed_head_gate = pending CI and independent review
```

## Required golden path

```text
exact reviewed source policy
  -> exact requested sessions D1/D2
  -> synthetic production-reachable envelopes
  -> strict validation
  -> existing append-only persistence owners
  -> complete provider-neutral acquisition result
  -> exact IngestionRun/batch provenance
```

A partial D2 response must fail before persistence and preserve prior valid history.

## Locked exclusions

No schema/migration/backfill, standalone adjustment-factor owner, durable historical-membership
owner, startup live wiring, API/UI, Market Overview, sector/hotspot/anomaly calculation, scheduler,
daemon, polling, notification, Tushare/AKShare fallback, mixed sources, news/PDF/OCR, AI-owned
acceptance, recommendation, valuation, portfolio, broker, trading, release, tag or version change.

## Validation and delivery gate

Before merge consideration:

1. Base remains exact implementation start unless later drift is explicitly handled.
2. Every commit and final Base→HEAD inventory remain inside the exact allowlist.
3. `behind = 0`.
4. No schema/migration/database-model changes.
5. Normal CI and demos remain zero-network and synthetic.
6. Focused tests, full repository tests and configured offline demos succeed on one exact HEAD.
7. Fresh fixed-head review contains exactly:

```text
AUTHORIZED TODAY MARKET DAILY MARKET ACQUISITION FOUNDATION V1 IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

8. Unresolved review threads = 0.
9. Project owner separately authorizes Ready/merge.
10. Any new commit invalidates previous exact-HEAD CI/review evidence.

Merge does not authorize Slice B or Slice C and does not close Issue #273 without separate authorization.
