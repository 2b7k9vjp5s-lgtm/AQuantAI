# THS Today Market Contract Resolution

## 1. Purpose and precedence

This focused resolution is part of Issue #223 and PR #224. It resolves facts learned from the official-contract review after the initial architecture draft.

Within PR #224, interpret potentially conflicting statements in this order:

1. this resolution;
2. `docs/ths_today_market_official_contract_appendix.md`;
3. `docs/ths_today_market_capability_manifest.md`;
4. `docs/today_market_ths_source_sync_preflight.md`.

This order applies only to the specific facts resolved below. All other architecture, exclusions and stop conditions remain unchanged.

## 2. Current full-market snapshot is documented

The official contract documents a current A-share snapshot path with full-market pagination when `thscodes` is omitted:

```text
GET /api/a-share/prices/snapshot
ordering = thscode ascending
pagination = limit + offset
data.total = current full code-table total
```

The account's snapshot entitlement and JSON envelope were separately confirmed by the owner-supplied sanitized transport validation.

Therefore replace any earlier statement that deterministic current full-market snapshot pagination is wholly unknown with:

```text
ths_current_full_market_snapshot_contract = documented_publicly
ths_current_full_market_snapshot_entitlement = confirmed
ths_current_full_market_snapshot_production_readiness = blocked_pending_retention_quota_completion_and_fixture_facts
```

The published endpoint units are also treated as documented contract facts:

```text
snapshot_volume_unit = shares
snapshot_turnover_unit = CNY for A shares
snapshot_price_currency = CNY
historical_volume_unit = shares
historical_turnover_unit = CNY for A shares
historical_price_currency = CNY
```

These unit facts no longer belong in the generic unknown list for the reviewed A-share price endpoints. Precision, null behavior, correction behavior and cross-endpoint consistency remain unresolved.

## 3. Current snapshot is not historical gap fill

The current full-market snapshot endpoint has no reviewed historical trade-date selector. It returns current/latest source state and therefore cannot deterministically reconstruct every missing completed session.

The official historical-price endpoint is reviewed as single-security:

```text
GET /api/a-share/prices/historical
thscode count = exactly one
interval = 1d
adjust = none must be explicit
```

An unbounded per-security startup loop remains prohibited.

Therefore:

```text
ths_historical_full_market_gap_fill = blocked_pending_bounded_historical_acquisition_contract
ths_missing_session_catchup = blocked_for_full_market_security_rows
per_security_startup_loop = prohibited
```

This is the material difference from the acquisition shape selected in PR #222.

## 4. Effect on the revised delivery plan

### Stage C remains index-led

The candidate first implementation remains:

```text
THS Provider Foundation + Index Market Overview
```

It does not automatically expand to full-market individual-security ingestion merely because the current snapshot can be paginated.

The current full-market snapshot may be considered only as a separately bounded optional capability when all of the following are reviewed:

- local response retention permission;
- sanitized fixture retention permission;
- QPS, daily-total and concurrency limits;
- daily completion time and current-session completeness rules;
- pagination terminal behavior in a production-reachable fixture;
- correction, revision and late-arrival behavior;
- exact identity mapping and coverage predicates;
- behavior after one or more missed completed sessions.

Until then:

```text
stage_c_full_market_snapshot = disabled
stage_c_full_market_breadth = disabled
stage_c_full_market_turnover = disabled
```

### Stage D is split by meaning

Stage D must distinguish:

```text
D1 = bounded current-session full-market snapshot acquisition
D2 = bounded historical full-market missing-session acquisition
```

D1 may become ready before D2. D1 alone cannot claim that automatic daily history is complete after application downtime.

A D1-only product must disclose one of:

```text
current_session_only
history_gap_present
history_gap_unknown
```

and must not publish a continuous full-market historical dataset when D2 is unavailable.

D2 requires one exact documented and validated shape such as:

```text
historical all-market endpoint
or documented historical multi-symbol batches
or deterministic bounded historical pagination
```

## 5. Updated external contract gates

Facts closed by official documentation:

```text
current snapshot full-market pagination
current snapshot ordering by thscode ascending
snapshot and historical A-share volume unit = shares
snapshot and historical A-share turnover unit = CNY
snapshot and historical A-share price currency = CNY
ticker-list page maximum = 10000
calendar timezone/order/backward window
historical and index-history maximum window = ten years
limit-up pool page-size maximum = 200
anomaly stock batch maximum = 50
```

Facts still blocking production execution:

```text
local_response_retention_permission
sanitized_fixture_retention_permission
qps_limit
daily_total_limit
concurrency_limit
retry_contract
daily_data_completion_time
snapshot_complete-session_cutoff
stable natural-key behavior across revisions
provider correction behavior
provider revision behavior
late-data behavior
API-key expiry, suspension, revocation and rotation
production-reachable sanitized fixtures
historical full-market gap-fill acquisition
corporate-action entitlement and deterministic semantics
```

## 6. Updated deterministic readiness state

Use the following state for the fixed-head architecture review:

```text
ths_transport_gate = confirmed
ths_authentication_gate = confirmed
ths_required_p0_entitlements = confirmed
ths_current_full_market_snapshot_contract = documented_publicly
ths_current_full_market_snapshot_entitlement = confirmed
ths_current_full_market_snapshot_readiness = blocked_pending_retention_quota_completion_and_fixture_facts
ths_historical_full_market_gap_fill = blocked_pending_bounded_historical_acquisition_contract
ths_corporate_action_entitlement = pending_separate_validation
ths_historical_membership = unsupported
ths_local_retention_evidence = pending_owner_or_provider_evidence
ths_fixture_retention_evidence = pending_owner_or_provider_evidence
ths_quota_and_revision_contract = pending_owner_or_provider_evidence
production_implementation_authorized = false
overall_gate = blocked_pending_retention_or_use
```

## 7. No implementation authorization

This resolution closes documentation ambiguity only. It does not authorize:

- live application network access;
- storing complete Provider responses;
- creating Provider-value fixtures;
- current full-market snapshot implementation;
- historical gap-fill implementation;
- corporate-action implementation;
- schema or migration work;
- an implementation Issue;
- merge.

A separate project-owner instruction remains required after the Strict architecture gates are complete.