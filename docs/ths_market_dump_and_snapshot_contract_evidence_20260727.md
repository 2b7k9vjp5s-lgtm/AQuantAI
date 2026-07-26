# THS Full-Market Snapshot and Market Dump Contract Evidence — 2026-07-27

## 1. Purpose and precedence

This document records a bounded public-documentation evidence amendment under Issue #251 and the controlling contract gate in Issue #225.

For only the facts explicitly resolved here, interpret this document as newer evidence than:

- `docs/ths_today_market_contract_evidence.md`;
- `docs/today_market_ths_source_sync_preflight.md`;
- `docs/ths_today_market_capability_manifest.md`;
- `docs/ths_today_market_contract_resolution.md`.

All existing source-selection, secret-handling, no-browser-replay, no-fallback, no-cross-Provider-mixing and fail-closed implementation rules remain in force.

This document is evidence governance only. It is not a Provider adapter, credential profile, runtime configuration, migration, fixture, implementation Issue or production authorization.

## 2. Evidence packet identity

```text
evidence_type = official_public_product_documentation
provider_product_name = 同花顺金融数据API / Fuyao
observed_at_utc = 2026-07-27
applicability_scope = public endpoint, schema, pagination, dump and API-key management documentation
redaction_statement = no credential, account identifier, account-page content, request ID, pre-signed URL or Provider market value retained
content_sha256 = 0520898bee90dd97ce17f9403e2c1c54b2cf5e33da888c8af4c927b138610c01
```

Primary official sources:

```text
https://fuyao.aicubes.cn/llms-full.txt
https://fuyao.aicubes.cn/docs/introduction/
https://fuyao.aicubes.cn/docs/quickstart/
https://fuyao.aicubes.cn/docs/api-reference/market-dumps/
```

No login-protected account values were reviewed or copied. The API-key management page is referenced only through public quick-start statements.

## 3. Canonical evidence excerpt

Compute `content_sha256` over the UTF-8 bytes inside the following code block using LF line endings and one terminal newline. Exclude the Markdown fences.

```text
observed_at_utc=2026-07-27
source_1=https://fuyao.aicubes.cn/llms-full.txt
source_2=https://fuyao.aicubes.cn/docs/introduction/
source_3=https://fuyao.aicubes.cn/docs/quickstart/
source_4=https://fuyao.aicubes.cn/docs/api-reference/market-dumps/
snapshot: omitting thscodes traverses the complete A-share code list in thscode ascending order using limit/offset pagination.
market_dump_10y: all A-share approximately ten years of unadjusted daily K data.
market_dump_10d: all A-share most recent ten trading days of unadjusted daily K data.
adjustment_dump: all-history adjustment-factor events.
daily_k_key=(thscode,date_ms)
adjustment_key=(thscode,ex_date_ms)
daily_k_timezone=Asia/Shanghai
daily_k_currency=CNY
daily_k_volume_unit=shares
daily_k_turnover_unit=original_currency
download_link_ttl=usually_5_minutes
documented_one_click_download_auth=login_cookie
business_code_4001=agreed_qps_exceeded
api_key_management=create_named_key_list_manage_delete_when_limit_reached
```

The excerpt contains no Provider row value or account-specific fact.

## 4. Current full-market snapshot contract

The official `llms-full.txt` documentation defines:

```text
GET /api/a-share/prices/snapshot
```

Two request shapes are documented:

1. explicit `thscodes`, returned in input order without pagination;
2. omitted `thscodes`, which traverses the complete A-share code list ordered by `thscode` and uses `limit` / `offset` pagination.

Publicly documented request fields:

```text
thscodes = optional comma-separated exact codes
limit = optional integer, default 100 when thscodes is absent
offset = optional integer, default 0 when thscodes is absent
```

Deterministic evidence result:

```text
current_full_market_snapshot_contract = documented_publicly
current_full_market_snapshot_pagination = limit_offset
current_full_market_snapshot_order = thscode_ascending
current_full_market_snapshot_api_key_header = X-api-key
```

This resolves the earlier question of whether a documented full-market snapshot traversal exists. It does not establish:

- account entitlement for production use beyond prior bounded validation;
- a complete-session market cutoff;
- stable historical replay of a snapshot;
- numeric request ceilings or safe automatic-startup cadence;
- correction, revision or late-arrival behavior;
- full-market daily-history catch-up.

Therefore:

```text
current_full_market_snapshot_contract = documented_not_implementation_ready
```

## 5. Full-market Parquet dump contracts

The official market-dumps page documents three full-market Parquet products.

### 5.1 Approximately ten years of unadjusted daily K

```text
dump_id = a_share_daily_k_1d_none_10y
data_type = daily_k
mode = FULL
default_window = approximately_10_years
endpoint = GET /dump/market-dumps/daily-k/download-url
```

### 5.2 Recent ten trading days of unadjusted daily K

```text
dump_id = a_share_daily_k_1d_none_10d
data_type = daily_k
mode = RECENT_TRADING_DAYS
default_window = 10_trading_days
endpoint = GET /dump/market-dumps/daily-k-10d/download-url
```

The documentation describes this dump as suitable for lightweight incremental synchronization. That statement defines a product use candidate; it does not prove when each trading day's file becomes complete or immutable.

### 5.3 Full-history adjustment-factor events

```text
dump_id = a_share_adjustment_factors_event_none_all
data_type = adjustment_factors
mode = FULL
default_window = all_events
endpoint = GET /dump/market-dumps/adjustment-factors/download-url
```

The adjustment dump contains original corporate-action event fields. It does not by itself authorize AQuantAI adjusted-return logic or establish correction/revision semantics.

## 6. Documented keys, units and timezone

The daily-K dumps share the following documented contract:

```text
natural_key = (thscode, date_ms)
interval = 1d
adjusted = none
date_timezone = Asia/Shanghai midnight
currency = CNY
OHLC_unit = original_currency
volume_unit = shares
turnover_unit = original_currency
```

The adjustment-event dump documents:

```text
natural_key = (thscode, ex_date_ms)
ex_date_timezone = Asia/Shanghai midnight
currency = CNY
```

Deterministic evidence result:

```text
daily_bar_natural_key = confirmed_from_official_dump_schema
daily_bar_field_units = confirmed_from_official_dump_schema
daily_bar_timezone = confirmed_from_official_dump_schema
adjustment_event_natural_key = confirmed_from_official_dump_schema
```

These facts narrow schema and unit uncertainty. They do not establish source revision identity, replacement semantics or the chronology of file publication.

## 7. Download-link and authentication boundary

The official page documents a one-click flow that:

1. uses the user's login-state Cookie to request a pre-signed S3 URL;
2. displays the URL in the browser;
3. treats the URL as short lived, usually approximately five minutes;
4. requires a new link after expiry.

Deterministic evidence result:

```text
dump_presigned_link_ttl = usually_5_minutes
dump_documented_one_click_auth = browser_login_cookie
presigned_url_persistence = prohibited
```

The documentation lists download endpoint paths, but the reviewed public material does not explicitly establish that AQuantAI may obtain those links through the accepted `X-api-key` application path.

Required fail-closed state:

```text
production_dump_api_key_auth_contract = unresolved
current_account_dump_entitlement = unresolved
browser_cookie_replay = prohibited
browser_session_capture = prohibited
presigned_url_storage = prohibited
```

AQuantAI must not implement the documented browser-Cookie flow by replaying Cookies or browser sessions. A future production path requires an explicit non-browser application authentication contract and account entitlement evidence.

## 8. API-key management facts

The public quick-start documentation establishes:

- a user can create a named API key;
- keys are bound to the user's Tonghuashun account;
- created keys can be viewed and managed in the API-key management page;
- when the account reaches its key-count limit, the documented action is to delete an unused key and retry.

Deterministic evidence result:

```text
api_key_creation = documented
api_key_named_alias = documented
api_key_account_binding = documented
api_key_list_and_management = documented
api_key_deletion_when_limit_reached = documented
```

Remain unresolved:

```text
maximum_active_keys = unresolved
api_key_expiry = unresolved
api_key_inactivity_expiry = unresolved
revocation_effect_time = unresolved
rotation_contract = unresolved
suspension_behavior = unresolved
compromise_response = unresolved
```

The existence of a key-count limit does not reveal its numeric value.

## 9. Rate-limit evidence

The official error table documents:

```text
business_code = 4001
meaning = agreed_QPS_exceeded
```

This proves that a QPS agreement exists and that the Provider has a stable business error category for exceeding it.

It does not disclose:

```text
numeric_qps_limit
daily_total_limit
concurrency_limit
per_endpoint_or_global_scope
account_specific_reset_time
rate_limit_headers
```

Therefore:

```text
qps_contract_exists = confirmed
numeric_quota_contract = unresolved
quota_gate = blocked
```

Successful low-volume requests, default client retries or absence of an error may not be used to infer limits. Load testing and hidden-limit probing remain prohibited.

## 10. Acquisition-shape effect

This amendment changes only the evidence status of the acquisition shape.

Previously unresolved:

```text
historical_full_market_gap_fill = blocked_pending_bounded_historical_contract
bounded_full_market_incremental_shape = unresolved
```

Now documented as candidates:

```text
historical_full_market_gap_fill_contract = candidate_10y_dump_documented
recent_full_market_incremental_contract = candidate_10_trading_day_dump_documented
full_market_adjustment_event_contract = candidate_full_dump_documented
```

They are not implementation ready because production authentication, account entitlement, quota, completion and revision facts remain open:

```text
historical_full_market_gap_fill_contract = candidate_documented_not_implementation_ready
recent_full_market_incremental_contract = candidate_documented_not_implementation_ready
full_market_adjustment_event_contract = candidate_documented_not_implementation_ready
```

The recent-ten-trading-day dump may eventually support bounded catch-up, but it must not be represented as exact missing-session acquisition until publication time, completion, replacement and late-data behavior are reviewed.

## 11. Facts still unresolved

```text
production_dump_api_key_auth_contract
current_account_dump_entitlement
numeric_qps_limit
daily_total_limit
concurrency_limit
per_endpoint_or_global_limit_scope
stage_c_dataset_completion_time
snapshot_complete_session_cutoff
dump_publication_time
dump_version_identity
provider_correction_behavior
provider_revision_behavior
late_data_behavior
stable_source_update_timestamp
api_key_expiry
api_key_inactivity_expiry
maximum_active_keys
revocation_effect_time
rotation_contract
```

No current official public page reviewed for this amendment explicitly resolves these facts.

## 12. Updated deterministic gate

```text
ths_transport_gate = confirmed
ths_authentication_gate = confirmed
ths_required_p0_entitlements = confirmed
ths_local_normalized_retention = confirmed_from_official_marketdb_product
ths_public_fixture_policy = synthetic_or_schema_only
ths_retry_reference_contract = confirmed_from_official_client
ths_current_full_market_snapshot_contract = documented_not_implementation_ready
ths_full_market_10y_dump_contract = candidate_documented_not_implementation_ready
ths_recent_10_trading_day_dump_contract = candidate_documented_not_implementation_ready
ths_adjustment_factor_dump_contract = candidate_documented_not_implementation_ready
ths_dump_production_auth_contract = unresolved
ths_quota_contract = unresolved
ths_completion_and_revision_contract = unresolved
ths_api_key_lifecycle_contract = unresolved
ths_historical_membership = unsupported
production_implementation_authorized = false
overall_gate = blocked_quota_contract
```

`blocked_quota_contract` remains the controlling #225 outcome. Completion/revision and production dump-authentication facts are additional independent blockers.

## 13. Effect on Today Market delivery

The product goal remains:

```text
render prior valid snapshot immediately
  -> determine freshness from a reviewed trading calendar
  -> generate one bounded missing-data plan
  -> fetch through one authorized non-browser application contract
  -> validate immutable source observations
  -> compute deterministic market and sector projections
  -> atomically publish a complete snapshot
  -> retain the prior valid snapshot on every failure
```

This evidence amendment does not authorize any arrow after request planning.

Until all controlling gates close:

```text
stage_c_implementation_issue = prohibited
application_live_network_access = prohibited
credential_setup = prohibited
browser_cookie_or_session_use = prohibited
schema_or_migration = prohibited
provider_ingestion = prohibited
market_dump_download = prohibited
current_full_market_snapshot_implementation = prohibited
```

THS Stage C0 remains the only accepted Provider-specific executable foundation, and it remains synthetic-only, zero-network, credential-free and non-persistent.

## 14. Failure semantics

When production authentication, quota, completion or revision facts are unknown:

- no live request plan is activated;
- no guessed cadence, concurrency or retry count is persisted;
- no browser login Cookie or pre-signed URL is captured;
- no current-session data is represented as complete without a reviewed cutoff;
- no changed dump or response silently overwrites frozen provenance;
- no full-market claim is published from partial coverage;
- the prior valid local snapshot remains the conceptual fallback;
- no alternate Provider, scraping path or cross-Provider row mixing is introduced.

## 15. No implementation authorization

This document narrows evidence uncertainty only. It does not authorize:

- closing Issue #225;
- creating a Stage C implementation Issue;
- production Provider code or live network access;
- credential storage or setup;
- browser automation or Cookie replay;
- schema, migration or persistence;
- Provider-valued fixtures;
- current or historical market ingestion;
- market overview, sector strength or anomaly production calculations;
- recommendation, portfolio or trading behavior;
- merge, release, tag or version change.
