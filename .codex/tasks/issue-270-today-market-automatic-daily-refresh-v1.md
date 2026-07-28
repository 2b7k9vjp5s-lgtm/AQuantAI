# Issue #270 Task Snapshot — Today Market Automatic Daily Refresh v1

## Authority

Project-owner instruction on 2026-07-28:

```text
启动 Issue #270 的架构预检开发，创建仅包含授权架构文档的 Draft PR
```

Authoritative repository state at branch creation:

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
exact_base = 2295bcf71968f0e00d88cd0a8fa5775060079995
architecture_issue = #270
parent_roadmap = #137
branch = arch/today-market-automatic-daily-refresh-v1
risk_tier = Strict Architecture Preflight
workflow = .codex/WORKFLOW.md
```

Accepted predecessor state that this architecture must preserve:

```text
Industry Research ordinary-user E2E = #266/#267 + #268/#269 / completed
Today Market automatic-refresh architecture = #221/#222 / accepted history
THS source synchronization = #223/#224 / accepted history
THS contract gate = #225 / closed / completed / blocked_quota_contract
Provider-neutral acquisition seam = #253/#254 / accepted
Deterministic zero-network Mock = #255/#256 / accepted
Today Market runtime integration = #259/#260 + #261/#262 / accepted
Current-state synchronization = #263/#264 / accepted
```

PR #241 remains closed, Draft, unmerged, permanently frozen and read-only at
`3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

## Exact authorized architecture files

Only:

```text
.codex/tasks/issue-270-today-market-automatic-daily-refresh-v1.md
docs/today_market_automatic_daily_refresh_v1_preflight.md
```

No third architecture file is authorized in this PR. In particular:

```text
docs/architecture_baseline.md = unchanged
production code = unchanged
API/UI = unchanged
tests/fixtures/workflows = unchanged
schema/migration = unchanged
Provider/credential/network code = unchanged
release/tag/version = unchanged
```

## Objective

Freeze one architecture that converges the accepted Today Market foundations on
the Roadmap #137 P0-A user job:

```text
open application
  -> immediately render last valid complete local snapshot
  -> determine expected latest completed trading session from one authorized calendar
  -> resolve exact missing completed sessions
  -> execute at most one bounded source-specific incremental attempt
  -> validate identities, chronology, units and complete coverage
  -> append immutable source observations
  -> derive one coherent complete publication candidate
  -> deterministically calculate market overview, sector strength/hotspot state and stock anomalies
  -> switch the ordinary-user view only after complete publication eligibility
  -> retain the prior valid snapshot on every failure
```

No market behavior may automatically become research causality, accepted evidence,
Investment Candidate state or a recommendation.

## Current source decision and fail-closed gate

Source history must remain explicit:

```text
PR #222 historical candidate = tushare-pro-daily-market-v1
PR #224 superseding preferred candidate = ths-account-structured-provider-v1
Tushare = deferred by accepted owner decision
AKShare = deferred by accepted owner decision
runtime fallback = disabled
cross-provider row mixing = prohibited
```

Issue #225 is final and controlling for the selected THS candidate:

```text
retention_gate = closed_for_documented_local_normalized_storage
fixture_policy = resolved_synthetic_only
retry_reference_contract = confirmed_from_official_client
quota_gate = blocked
completion_and_revision_semantics_gate = blocked
api_key_lifecycle_gate = blocked
production_dump_authentication_gate = blocked
production_implementation_authorized = false
overall_gate = blocked_quota_contract
resolution_mode = explicit_fail_closed
```

Therefore Issue #270 must not reactivate THS and must not silently fall back to a
previous candidate. Its current architecture source result is:

```text
preferred_source_candidate = ths-account-structured-provider-v1
live_source_contract_state = blocked_quota_contract
today_market_daily_refresh_source_gate = blocked_source_contract
production_live_network_authorized = false
```

A future source may become eligible only through separately reviewed architecture
and non-secret contract evidence. This PR does not choose an unreviewed alternate.

## Existing owners to reuse

The architecture must reuse rather than duplicate:

- `IngestionRun` complete snapshot and `batch_identifier` provenance;
- existing Stock Basic, Trade Calendar, Daily Price, Benchmark Index Daily,
  Sector Definition and Sector Daily normalized owners;
- `MarketCockpitRepository`, `BenchmarkRepository`, `SectorRepository`;
- `MarketCockpitService` and existing deterministic Market Cockpit calculators;
- accepted provider-neutral acquisition-port and Mock validation contracts;
- `runtime_scope_revision_id`, `runtime_status_fingerprint`, authoritative prior
  snapshot identity, optimistic concurrency, single-flight and completed replay;
- Today Market API/page projection as presentation, not accepted research truth.

The architecture may identify future missing normalized families such as exact
company-action/adjustment revisions and dated sector membership, but it may not
implement a table, migration or second market-data domain in this PR.

## Locked architecture decisions

### 1. Trading-calendar freshness

Freshness is driven only by a reviewed source trading calendar plus a reviewed
source completion policy. Wall-clock date subtraction is prohibited.

Required deterministic projection:

```text
latest_complete_local_trading_date
expected_latest_complete_trading_date
missing_trading_dates[]
refresh_required
refresh_reason
```

If the source contract does not establish when a session is complete enough to
be canonical, automatic live planning is blocked rather than guessed.

### 2. Existing bounded runtime semantics stay authoritative

Preserve:

```text
automatic missing-session ceiling = 10 completed sessions
no prior complete snapshot -> explicit initialization required
>10 missing sessions -> explicit manual catch-up required
raw app/page load -> no acquisition
first eligible Today Market entry -> at most one bounded automatic attempt
failure -> explicit user retry only
no scheduler / daemon / continuous polling / post-shutdown work
```

The current `TodayMarketRefreshPlan` is Mock-only and must not be made live by
relaxing `MOCK_ASSUMPTION_PROFILE_ID`. A future live plan requires a separately
reviewed source-specific contract.

### 3. Immutable raw observations; derived adjustment only

Production daily observations are append-only source facts. Historical company
actions or adjustment factors may create new immutable revisions but never
rewrite raw OHLCV/amount rows.

Cross-session return, new-high/new-low, gap and relative-strength calculations
must use an explicit analysis-price policy. If exact adjustment/reference-close
semantics are unavailable, affected metrics return an unavailable/insufficient
state; they do not silently use incompatible raw closes.

### 4. Dated membership is mandatory for constituent breadth

Current constituents cannot be backfilled into history. Sector/theme constituent
breadth, representative-company calculations and sector-relative stock anomaly
rules require exact effective-dated membership.

Because accepted THS evidence does not establish historical dated constituents,
that capability remains blocked until separate evidence/source architecture
closes it. Sector index price history may remain separately readable, but it may
not be presented as full constituent-confirmed hotspot truth.

### 5. Atomic publication uses coherent exact components

A future source-specific attempt should bind every required component to one
exact `batch_identifier` / refresh attempt and one data-through session. A new
Today Market snapshot becomes eligible only when all required component runs are
successful, complete, source-consistent and chronology-consistent.

Partial successful source rows may remain as immutable ingestion evidence, but a
partial attempt cannot replace the prior valid Today Market snapshot.

No new publication table is authorized by this architecture PR. If a future
implementation proves a durable publication index is necessary, that schema
change requires a separate explicitly authorized implementation preflight.

### 6. Exact snapshot identity and history

The architecture must define one deterministic snapshot identity over exact
component run identities, data-through session, source contract identity and
calculation-rule versions. Historical reopen binds to those exact components and
must never substitute newer source rows, adjustment revisions, membership
revisions or calculation versions.

### 7. Deterministic market overview

The architecture must define exact formulas and coverage states for:

```text
core index returns
advancing / declining / unchanged counts
advance_ratio and breadth_balance
market turnover/amount
20-session new-high/new-low breadth
limit-up/limit-down counts only when exact limit semantics exist
coverage and missing-data diagnostics
ordinary-user market state: strong / weak / mixed / insufficient_coverage
```

No AI/LLM owns these calculations.

### 8. Deterministic sector strength and hotspot state

Use exact sector identity plus dated membership when constituent-confirmed state
is claimed. The preflight must freeze explicit thresholds, missing-data behavior,
tie-breaking and state precedence for:

```text
new
strengthening
spreading
persistent_strong
high_level_divergence
cooling
neutral
insufficient_coverage
```

No unexplained opaque score becomes canonical truth.

### 9. Deterministic stock anomalies

The architecture must freeze exact rule versions and lookback requirements for:

```text
large_move
unusual_volume
new_high
new_low
gap
persistent_relative_strength
sector_relative_outlier
```

An anomaly is only a market-behavior observation.

### 10. Market heat and research truth remain separated

```text
price/volume observation
  -> deterministic market state
  != accepted causal explanation
  != accepted Evidence Ledger fact
  != accepted Industry Thesis
  != Investment Candidate state
  != recommendation
```

Any displayed research link must resolve an already accepted exact research/evidence
owner; market movement cannot manufacture one.

## Required architecture output

The preflight document must define at least:

1. source-capability decision table and exact current gate;
2. host/credential-reference boundary without secrets;
3. exact identity, calendar and completed-session contracts;
4. daily-bar and adjustment/company-action semantics;
5. dated sector/theme membership semantics;
6. bounded incremental refresh state machine;
7. coherent batch / atomic-publication eligibility;
8. last-valid-snapshot read contract;
9. exact snapshot identity and historical reopen;
10. market-overview formulas and coverage thresholds;
11. sector-strength metrics, thresholds, state priority and tie-breaking;
12. stock-anomaly formulas and lookback requirements;
13. Chinese-first status/error taxonomy;
14. zero-network golden and failure fixtures;
15. future implementation slices and candidate file families only.

## Golden path requirement

Use a zero-network synthetic fixture with:

```text
prior complete snapshot = D0
reviewed completed sessions after D0 = [D1, D2]
automatic missing sessions = exactly [D1, D2]
source mode = synthetic fixture / zero network
new source rows = complete and identity-valid
new publication candidate = D2 only after all required components complete
prior D0 = immutable and exactly reopenable
```

The fixture must include enough synthetic instruments and dated sectors to prove:

- complete market breadth;
- at least one strengthening/new-or-spreading sector;
- at least one cooling/high-level-divergence sector;
- large-move, unusual-volume and relative-strength anomaly examples;
- stable deterministic replay;
- no Provider-valued secret or market data.

A failure fixture must reject an incomplete D2 candidate, retain D0 and expose an
explicit retry path.

## Locked exclusions

No production Provider adapter, live THS/Tushare/AKShare request, credential,
HTTP transport, raw Provider capture, schema, migration, dependency change,
production persistence implementation, Provider-valued fixture, live smoke test,
announcement acquisition, OCR/PDF import, AI causality, automatic evidence or
research acceptance, candidate rewriting, recommendation, target price,
expected return, holdings, portfolio, broker, trading, scheduler, daemon,
polling, notification, release, tag or version change.

Do not modify PR #241.

## Future implementation slices

Architecture may nominate, but does not authorize, three bounded follow-on slices:

```text
A. Daily Market Acquisition Foundation
B. Market Overview + Sector Strength + Hotspot/Anomaly Rules
C. Ordinary-User Today Market Runtime/UI Integration
```

Each future Issue must re-read current `main`, reduce its own exact file inventory,
state whether schema/migration is required, and obtain separate authorization.

While the selected source remains `blocked_source_contract`, no live source
activation implementation may be created from this preflight alone.

## Delivery gates

Before merge consideration:

1. Base remains exact `2295bcf71968f0e00d88cd0a8fa5775060079995`.
2. Base-to-HEAD changes exactly the two authorized Markdown files.
3. `behind = 0`.
4. No executable/configuration/Provider/credential/schema file changes.
5. Applicable repository CI succeeds on one exact immutable HEAD.
6. Fresh independent fixed-head architecture review contains exactly:

```text
AUTHORIZED TODAY MARKET AUTOMATIC DAILY REFRESH V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

7. Unresolved review threads = 0.
8. Project owner separately authorizes Ready/merge.

Any new commit invalidates prior fixed-head CI and review evidence.

Merging architecture does not close Issue #270, authorize implementation, update
`docs/architecture_baseline.md`, or change the blocked source contract.