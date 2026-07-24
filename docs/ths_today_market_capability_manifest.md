# THS Today Market Capability Manifest

## 1. Manifest identity

```text
manifest_schema = aquantai.ths-today-market-capability-manifest.v1
source_key = ths-account-structured-provider-v1
provider_name = 同花顺扶摇金融数据 API
reviewed_at_utc = 2026-07-24T14:59:47Z
approved_host = fuyao.aicubes.cn
credential_mechanism = X-api-key
credential_value_persisted = false
cookie_used = false
browser_session_used = false
raw_provider_response_persisted_by_validation = false
security_scan = passed
```

Validation fingerprints:

```text
p0_report_sha256 = b1b0648a33dcd677c91430370d20d22a83cc2eb88c227c54a418f570302451f1
transport_v3_sha256 = 544d9a63aaa50fcca4a6629274df8009bbbb99de3ea1911db578375c9622569e
```

These hashes identify owner-supplied sanitized local validation reports. They do not embed Provider values or credentials.

## 2. Manifest state vocabulary

Capability entitlement:

```text
confirmed
not_entitled
unsupported
unknown
```

Readiness:

```text
implementation_ready
deferred_not_entitled
deferred_contract_incomplete
rejected_undocumented
blocked_retention_or_use
validation_failed
```

Contract facts:

```text
confirmed
not_applicable
pending_owner_evidence
pending_provider_evidence
unsupported
```

Unknown facts fail closed.

## 3. Use and retention evidence

```text
automated_api_access = supported_by_official_api_documentation
quantitative_research_use = supported_by_official_product_documentation
personal_developer_use = supported_by_official_product_documentation
local_secret_storage = supported_by_official_guidance
noncommercial_self_use = conditional_on_applicable_product_or_special_agreement
local_response_retention = pending_owner_or_provider_evidence
sanitized_fixture_retention = pending_owner_or_provider_evidence
redistribution = not_authorized
commercial_redistribution = not_authorized
```

Current gate:

```text
contract_gate = blocked_pending_retention_or_use
```

Acceptable future evidence must be non-secret and applicable to the account/product. Examples include official terms, an official Provider support response, an account-visible agreement, or a redacted owner-supplied contract excerpt.

## 4. Transport and credential facts

Confirmed by sanitized local validation:

```text
validation_client = curl.exe
validation_ssl_backend = Schannel
validation_http_version = HTTP/1.1
tls_transport = confirmed
redirects_followed = false
json_api_envelope = confirmed
credential_mechanism = X-api-key
api_key_status = confirmed
```

Production transport remains a future reviewed implementation decision. Validation success with curl does not authorize production shell-out to curl.

Production requirements:

- TLS verification;
- exact host allowlist;
- bounded timeouts and response bytes;
- no secret in command arguments, environment files, repository, database or logs;
- complete request-header and error redaction;
- no alternate host or Provider fallback;
- no verbose credential-bearing traces;
- deterministic JSON-envelope and schema validation.

Any API key exposed in chat must be revoked and must not be reused.

## 5. Confirmed capability matrix

| Capability key | Entitlement | Observed rows | Product role | Readiness | Material remaining facts |
|---|---:|---:|---|---|---|
| `a_share_ticker_list` | confirmed | 5 | Provider instrument candidates | blocked_retention_or_use | full pagination, stable natural key, status chronology, complete coverage, quota |
| `a_share_trading_calendar` | confirmed | 243 | completed-session owner candidate | blocked_retention_or_use | timezone, forward coverage, correction behavior, completion-time interaction |
| `a_share_daily_history_raw` | confirmed | 2 | raw individual-security daily bars | blocked_retention_or_use | units, currency, completion time, batch/pagination shape, correction behavior |
| `a_share_index_ticker_list` | confirmed | 5 | Provider index identity candidates | blocked_retention_or_use | stable identity, full pagination, classification semantics |
| `a_share_index_daily_history` | confirmed | 2 | core/sector index daily bars | blocked_retention_or_use | units, completion time, correction behavior, bounded request shape |
| `ths_industry_index_catalog` | confirmed | 320 | THS industry-index catalog | blocked_retention_or_use | taxonomy versioning, publication/effective dates, correction behavior |
| `ths_concept_index_catalog` | confirmed | 389 | THS concept-index catalog | blocked_retention_or_use | taxonomy versioning, publication/effective dates, correction behavior |
| `ths_index_current_constituents` | confirmed | 30 | current constituents only | blocked_retention_or_use | effective snapshot time, weights, full coverage, correction behavior |
| `limit_up_pool` | confirmed | 5 | Provider-defined limit-up pool | blocked_retention_or_use | exact coverage, fields, terminal conditions, completion time |
| `limit_up_ladder` | confirmed | 30 | Provider-defined ladder | blocked_retention_or_use | exact history/window semantics, completion time, revision behavior |
| `hot_stock_list` | confirmed | 30 | `market_attention_candidate` | blocked_retention_or_use | ranking time, refresh cadence, stable ordering, revision behavior |
| `stock_anomaly_reasons` | confirmed | 0 | `market_attention_candidate` | blocked_retention_or_use | zero-row semantics, event time, text provenance, revision behavior |

Observed row counts are bounded validation observations, not production limits or complete dataset sizes.

## 6. Unsupported capability

```text
capability_key = ths_index_historical_constituents
entitlement = unsupported
readiness = rejected_undocumented
dated_membership_supported = false
```

Required consequences:

```text
current_sector_membership = supported
historical_sector_membership = unsupported
historical_sector_breadth = prohibited
current_membership_backfilled_into_history = prohibited
```

Current constituents may be displayed and may support same-session observations only after coverage semantics are reviewed. They may not establish historical membership.

## 7. Capabilities requiring separate validation

### 7.1 Corporate actions / adjustment events

```text
capability_key = corporate_action_adjustment_events
entitlement = unknown
readiness = deferred_contract_incomplete
```

Required facts:

- exact official endpoint and method;
- account entitlement;
- adjustment-event schema;
- effective date and chronology;
- split/dividend/rights issue semantics;
- units and precision;
- correction and restatement behavior;
- pagination and limits;
- production-reachable sanitized success/error fixtures;
- retention permission.

Until confirmed:

```text
adjusted_return_features = disabled
multi_session_factor_price = disabled
price_discontinuity_factor_inference = prohibited
```

### 7.2 Bounded full-market daily acquisition

```text
capability_key = bounded_full_market_daily_acquisition
entitlement = unknown
readiness = deferred_contract_incomplete
```

Required acceptable acquisition shape:

```text
one all-market daily request
or documented bounded multi-symbol batches
or deterministic bounded pagination
```

Required facts:

- full A-share coverage definition;
- batch/page selectors and terminal condition;
- stable ordering and natural key;
- request/day/page/row/byte ceilings;
- QPS, daily total and concurrency;
- missing/suspension/listing semantics;
- completion time and correction behavior;
- production-reachable sanitized fixtures;
- retention permission.

Until confirmed:

```text
full_market_daily_refresh = disabled
full_market_breadth = disabled
full_market_turnover = disabled
full_market_anomaly_scan = disabled
per_security_startup_loop = prohibited
```

### 7.3 Exact per-security daily limit prices

```text
capability_key = exact_daily_limit_prices
entitlement = unknown
readiness = deferred_contract_incomplete
```

`limit_up_pool` and `limit_up_ladder` do not automatically satisfy this capability.

Until confirmed:

```text
provider_limit_up_pool_analysis = candidate_supported
provider_limit_up_ladder_analysis = candidate_supported
full_market_up_limit_price_reference = disabled
full_market_down_limit_analysis = disabled
```

## 8. Today Market role mapping

| Product need | THS capability | Current architecture status |
|---|---|---|
| Provider instrument candidates | `a_share_ticker_list` | entitlement confirmed; production blocked |
| Trading sessions | `a_share_trading_calendar` | entitlement confirmed; production blocked |
| Raw individual-security daily bars | `a_share_daily_history_raw` | entitlement confirmed; full-market shape unknown |
| Core index identities | `a_share_index_ticker_list` | entitlement confirmed; production blocked |
| Core/sector index daily bars | `a_share_index_daily_history` | entitlement confirmed; production blocked |
| Industry identities | `ths_industry_index_catalog` | entitlement confirmed; version contract incomplete |
| Concept identities | `ths_concept_index_catalog` | entitlement confirmed; version contract incomplete |
| Current constituent display | `ths_index_current_constituents` | entitlement confirmed; historical use prohibited |
| Historical membership | none reviewed | unsupported |
| Provider limit-up state | `limit_up_pool`, `limit_up_ladder` | candidate within documented pool meaning only |
| Market attention | `hot_stock_list`, `stock_anomaly_reasons` | attention candidate only |
| Adjusted return basis | separate corporate-action capability | pending validation |
| Full-market daily coverage | separate bounded batch contract | pending validation |

## 9. Revised implementation-slice mapping

### Candidate Slice 1

```text
name = THS Provider Foundation + Index Market Overview
status = blocked_pending_retention_or_use
```

Candidate components after all required gates close:

- source authorization/capability revisions;
- runtime-only credential reference;
- reviewed transport adapter;
- trading calendar;
- core index catalog and daily bars;
- industry/concept index catalogs and index bars;
- current constituent display;
- limit-up pool and ladder;
- market-attention projections;
- bounded refresh attempts;
- complete validation and atomic snapshot publication;
- retained prior snapshot and ordinary-Chinese status.

Excluded:

- full-market individual-security daily ingestion;
- full-market breadth and turnover claims;
- adjusted multi-session analytics;
- historical sector breadth;
- full-market exact up/down-limit price claims;
- recommendation, portfolio or trading behavior.

### Candidate Slice 2

```text
name = Bounded Full-Market Daily Acquisition
status = blocked_pending_bounded_batch_contract
```

### Candidate Slice 3

```text
name = Corporate Actions and Adjusted Analytics
status = blocked_pending_corporate_action_validation
```

### Historical sector slice

```text
name = Historical Sector Breadth
status = unsupported_until_dated_membership_exists
```

It does not block Slices 1–3.

## 10. Required contract facts

The following remain unresolved:

```text
automated_personal_research_use_permission
local_response_retention_permission
sanitized_fixture_retention_permission
qps_limit
daily_total_limit
concurrency_limit
retry_contract
volume_unit
turnover_unit
currency
snapshot_market_time
daily_data_completion_time
stable_sorting_contract
natural_key_contract
provider_correction_behavior
provider_revision_behavior
late_data_behavior
api_key_expiry
api_key_revocation
api_key_rotation
```

An entitlement result of `confirmed` does not override these contract gates.

## 11. Fixture and raw-data boundary

Until retention permission is reviewed:

- do not persist complete Provider responses;
- do not commit actual Provider market values;
- do not create distributable Provider fixtures;
- do not store private headers, request IDs, account identifiers or credential-derived values;
- schema-only examples may use invented synthetic values clearly marked as synthetic;
- validation report hashes and sanitized field/type summaries may be recorded.

A future production fixture must be reachable through the exact reviewed production contract and must not add fields unavailable in production.

## 12. Failure semantics

When any required manifest fact is unknown or invalid:

```text
source_readiness = blocked
network_attempt = prohibited_or_failed_closed
published_snapshot = prior_complete_snapshot
provider_fallback = none
row_mixing = none
partial_publication = none
```

User-facing reasons must distinguish at least:

```text
数据源使用或留存条款尚未确认
数据源额度或调用规则尚未确认
凭据失效，请重新配置
当前账户权限不足
无法确认最新完整交易日
数据源暂不可用，已保留上次数据
数据校验失败，已保留上次数据
缺少全市场批量能力，完整市场宽度暂不可用
缺少复权事件能力，多周期复权指标暂不可用
缺少历史成分，历史板块宽度暂不可用
```

## 13. Current deterministic gate

```text
ths_transport_gate = confirmed
ths_authentication_gate = confirmed
ths_required_p0_entitlements = confirmed
ths_use_intent_evidence = supported_by_public_docs
ths_local_retention_evidence = pending_owner_or_provider_evidence
ths_fixture_retention_evidence = pending_owner_or_provider_evidence
ths_quota_and_revision_contract = pending_owner_or_provider_evidence
ths_full_market_batch_contract = pending_separate_validation
ths_corporate_action_entitlement = pending_separate_validation
ths_historical_membership = unsupported
production_implementation_authorized = false
overall_gate = blocked_pending_retention_or_use
```

This manifest is secret-free architecture evidence. It is not a credential profile, production configuration, Provider dataset, implementation authorization or investment recommendation.