# Issue #273 Task Snapshot — Today Market Daily Market Acquisition Foundation v1

## Authority

Project-owner instruction on 2026-07-29:

```text
启动 Issue #273 的实现开发，先完成仓库与 schema/migration stop-condition 审计；
确认无需 migration 后，创建只包含精确授权文件的 Draft PR
```

Authoritative start state:

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
exact_base = afc6ae442a440fa9099494d0aa3f6ab12e64fb57
implementation_issue = #273
parent_roadmap = #137
branch = feat/today-market-daily-market-acquisition-foundation-v1
risk_tier = Strict Implementation
workflow = .codex/WORKFLOW.md
selected_source = ths-account-structured-provider-v1
```

Accepted predecessors:

```text
Today Market architecture = #270 / merged PR #271
source-contract amendment = #272 / closed / completed
THS Stage C0 offline foundation = #227/#229 + #230/#231
provider-neutral acquisition port = #253/#254
Today Market deterministic Mock = #255/#256
Today Market runtime integration = #259/#260 + #261/#262
```

PR #241 remains permanently frozen, closed, Draft and unmerged at
`3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

## Repository and schema/migration audit

The implementation start audit reviewed the exact-base versions of:

```text
backend/database/models.py
backend/database/market_data.py
backend/database/benchmark_data.py
backend/database/series.py
datasource/base.py
datasource/ths_structured_provider/contracts.py
datasource/ths_structured_provider/readiness.py
datasource/ths_structured_provider/selectors.py
datasource/ths_structured_provider/planner.py
datasource/ths_structured_provider/schemas.py
backend/today_market_refresh/contracts.py
backend/today_market_refresh/port.py
.codex/WORKFLOW.md
```

Deterministic audit result:

```text
schema_migration_required = false
migration_files_authorized = none
database_model_changes_authorized = none
```

### Why existing persistence is sufficient for Slice A v1

1. `IngestionRun` already records immutable attempt provenance through:
   - `batch_identifier`;
   - `series_key` and canonical `series_identity`;
   - provider and dataset;
   - requested start/end and information cutoff;
   - requested scope and secret-filtered provider request metadata;
   - adapter/contract versions;
   - pending/succeeded/failed status and completion time.
2. Successful identical content converges through the existing partial unique index over
   `(batch_identifier, series_key)`; changed source content produces a different batch and
   therefore an additional immutable observation rather than rewriting prior rows.
3. `DailyPriceRecord` already supports distinct raw/qfq/hfq observations through
   `adjust_type`, with run-bound natural keys and append-only version selection.
4. `TradeCalendarRecord` already supports exact run-bound open/closed session rows.
5. `BenchmarkIndexDailyRecord` already supports exact run-bound benchmark OHLCV/amount rows.
6. `StockBasicRecord` already supports source, exchange, listing chronology and run-bound identity rows.
7. Existing persistence services validate requested scope, dates, identities, OHLC consistency,
   duplicate natural keys, exact source and idempotent replay before atomic commit.

### Locked no-migration interpretation

Slice A v1 will use the existing `daily_price.adjust_type` series boundary for raw/qfq/hfq.
It will **not** add or emulate a standalone adjustment-factor/company-action table.

```text
raw/qfq/hfq daily series reachable through existing owner -> allowed
standalone adjustment-factor persistence required -> STOP
company-action event persistence required -> STOP
changed values cannot be represented as a new immutable run -> STOP
```

Historical industry/concept membership is not persisted by Slice A. Source-supported exact-date
block snapshots may be validated as acquisition evidence only. Durable dated membership needed by
Slice B requires a separately authorized owner/migration if the existing schema cannot represent it.

```text
current constituents backfilled into history = prohibited
JSON blob / hidden side store / ad-hoc file persistence = prohibited
schema workaround = prohibited
```

### Code-only gap found by the audit

The existing Today Market application contracts were intentionally frozen for the synthetic Mock:

```text
TodayMarketRefreshPlan.assumption_profile_id = exact Mock profile only
TodayMarketFamilyResult.synthetic = true only
```

Live THS handoff therefore requires an explicit code-level contract extension during M6. This is
not a database or migration requirement. The Mock profile and its tests must remain unchanged and
must not be silently reinterpreted as Provider readiness.

## Project-owner provisional source contract

Issue #272 closed with:

```text
private_local_retention = allowed for project use
private_local_retention_period = indefinite
provider_historical_query_horizon = rolling 10 years
locally persisted valid history may outlive the later Provider query window
public Provider-valued repository fixtures = prohibited
unsupported taxonomy/date = fail closed
```

These are project-owner provisional operating assumptions, not a representation that the Provider
issued a legal confirmation. Later contradictory official terms invalidate live readiness and require
a new reviewed amendment.

## Exact authorized file inventory

The implementation PR may add or modify **only** the following exact paths:

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

If a required change falls outside the exact list, stop before editing and return for owner review.

## Initial Draft PR increment

The first Draft PR increment is intentionally limited to M1:

```text
task snapshot
+ immutable live source-policy/readiness contracts
+ package exports
+ zero-network contract tests
```

It does not add transport, credentials, persistence execution or runtime wiring yet. Later commits may
use only the exact authorized paths above and invalidate any prior fixed-HEAD CI/review evidence.

## Implementation sequence

### M1 — live source policy and readiness

- preserve `SOURCE_KEY = ths-account-structured-provider-v1`;
- freeze reviewed host family, authentication-reference type, QPS and ten-year boundary;
- distinguish Provider-documented facts from project-owner provisional assumptions;
- make public repository fixtures synthetic-only;
- default remote execution to disabled;
- keep contract fingerprints secret-free and deterministic.

### M2 — selectors and request planning

- closed capability registry only;
- exact instrument/exchange/date selectors;
- exact trading-calendar-driven sessions;
- rolling ten-year rejection with no silent truncation;
- quota/data-volume budgeting;
- no arbitrary host/path/header/query dictionaries;
- deterministic request fingerprints without credentials.

### M3 — response validation

- strict envelope and field validation;
- requested capability/date/identity agreement;
- OHLC, units, chronology and natural-key checks;
- duplicate/conflicting/unrequested/partial rows fail closed;
- synthetic repository fixtures only.

### M4 — credential reference and transport

- credential reference only; no value/hash/fragment persistence;
- reviewed THS host family and endpoint contracts only;
- disabled by default;
- explicit timeout, rate-limit and bounded retry mapping;
- no Provider fallback or source mixing;
- ordinary CI/demo remains zero-network.

### M5 — immutable persistence

- reuse existing `MarketDataPersistenceService` and `BenchmarkPersistenceService`;
- bind source contract/request/attempt metadata to `IngestionRun`;
- identical facts replay idempotently;
- changed facts append as a new run;
- partial attempts never become a completed acquisition batch;
- hit the schema stop condition instead of adding side storage.

### M6 — provider-neutral handoff

- extend application contracts explicitly for source-specific live mode;
- preserve all existing Mock-only invariants and tests;
- expose acquisition completeness/provenance only;
- do not calculate market state, sector state or stock anomalies;
- do not activate startup/first-entry networking.

## Required golden path

Zero-network synthetic test path:

```text
exact reviewed source policy
  -> exact requested sessions D1/D2
  -> synthetic production-reachable envelopes
  -> strict validation
  -> existing append-only persistence owners
  -> complete provider-neutral acquisition result
  -> exact IngestionRun/batch provenance
```

A failure fixture must reject a partial D2 response and preserve all prior valid local history.

## Locked exclusions

No schema/migration/backfill, standalone adjustment-factor owner, durable historical-membership owner,
startup live wiring, API/UI, Market Overview, sector/hotspot/anomaly calculation, scheduler, daemon,
polling, notification, Tushare/AKShare fallback, mixed sources, announcement/news/PDF/OCR, AI-owned
acceptance, recommendation, target price, expected return, portfolio, broker, trading, release, tag or
version change.

## Validation and delivery gate

Before merge consideration:

1. Base remains the exact implementation start or any later base drift is explicitly handled before review.
2. Base-to-HEAD inventory is limited to the exact authorized paths.
3. `behind = 0`.
4. No schema/migration/database-model changes.
5. Normal CI and demos remain zero-network and synthetic.
6. Focused tests, full repository tests and configured offline demos succeed at one exact HEAD.
7. Fixed-head review contains exactly:

```text
AUTHORIZED TODAY MARKET DAILY MARKET ACQUISITION FOUNDATION V1 IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

8. Unresolved review threads = 0.
9. Project owner separately authorizes Ready/merge.
10. Any new commit invalidates previous exact-HEAD CI/review evidence.

Merge does not authorize Slice B or Slice C and does not close Issue #273 without separate authorization.
