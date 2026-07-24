# THS Today Market Contract Evidence

## 1. Purpose and precedence

This document records non-secret official evidence accepted under Issue #225 after the architecture synchronization in Issue #223 / merged PR #224.

For only the facts explicitly resolved here, interpret this document after its merge as newer evidence than:

- `docs/ths_today_market_contract_resolution.md`;
- `docs/ths_today_market_capability_manifest.md`;
- `docs/today_market_ths_source_sync_preflight.md`.

All exclusions, source-selection rules, fail-closed behavior and implementation prohibitions from PR #224 remain in force.

## 2. Evidence packet identity

```text
evidence_type = official_public_repository_and_reference_client
provider_product_name = 同花顺金融数据服务 / hithink-finance
source_channel = GitHub official maintained repository
source_repository = HiThink-Tech/Financial-API
source_commit = f8cdea908469b1b3b8bfb88dbb4d4a3959b1905c
observed_at_utc = 2026-07-24
applicability_scope = public documented product workflows and official client behavior
redaction_statement = no credential, account identifier, order information, request ID or Provider market value retained
content_sha256 = b19b6841c9255c18b4d29b58c57029ef25dacef340d41d8f69875f0477ae64d4
```

The SHA-256 identifies the canonical secret-free evidence excerpt used for this review. Source identity is additionally pinned by upstream commit and file blob identifiers.

### 2.1 Canonical evidence excerpt bytes

Compute `content_sha256` over the UTF-8 contents inside the following code block, using LF line endings and one terminal newline. The Markdown fences are excluded.

```text
source_repository=HiThink-Tech/Financial-API
source_commit=f8cdea908469b1b3b8bfb88dbb4d4a3959b1905c
README.md: official service maintained by Tonghuashun for AI Agents, quantitative researchers and application developers; supports Python research programs, scheduled acquisition, Market Dumps, local DuckDB, long-term historical storage, full initialization, incremental updates, SQL research and file export.
python/toolkit/marketdb/README.md: local A-share market database for reading, updating and analyzing local OHLCV and adjusted data; auto-sync selects FULL or INCREMENTAL, stores a local DuckDB database and removes temporary Parquet after application.
hithink-finance-cli/src/infrastructure/fuyao/retry.ts: Retry-After has precedence; exponential delay base 1s, 2s, 4s capped at 8s plus jitter; retryable business codes 4001,5001,5002,5003.
hithink-finance-cli/src/infrastructure/fuyao/client.ts: default timeout 30000ms; default maxAttempts 3; authentication and validation errors are non-retryable.
```

This excerpt contains only deterministic interpretations of the pinned sources. The source paths, commit and Git blob SHAs remain the primary provenance anchors.

## 3. Reviewed source inventory

| Source path | Git blob SHA | Accepted role |
|---|---|---|
| `README.md` | `4939af71990042f8a038532408e7c6d8fae1ac81` | official product identity, supported users, local database, scheduled acquisition, Market Dumps and storage workflows |
| `python/toolkit/marketdb/README.md` | `4a52cb92a4ffaf30cc38bab916eea940980c85fc` | long-term local DuckDB storage, full/incremental synchronization, SQL analysis, export and local data lifecycle |
| `hithink-finance-cli/src/infrastructure/fuyao/retry.ts` | `eb2ee98632bb72531e38c1f89dbb9b425b256504` | official reference-client Retry-After and exponential-backoff behavior |
| `hithink-finance-cli/src/infrastructure/fuyao/client.ts` | `08a560e81f889f3a15b2dfc609ba72569c7913a2` | official reference-client timeout, attempt count, authentication and validation error behavior |

Repository URL:

```text
https://github.com/HiThink-Tech/Financial-API
```

The upstream repository identifies the service as officially provided and maintained by Tonghuashun.

## 4. Local use and retention facts now resolved

The official product repository explicitly supports:

- use by AI Agents, quantitative researchers and application developers;
- REST, MCP, CLI, Python research scripts and quantitative programs;
- scheduled acquisition in Python workflows;
- Market Dumps and large-result local persistence;
- a local `marketdb` DuckDB database;
- long-term historical market-data storage;
- full initialization and incremental synchronization;
- raw, forward-adjusted and backward-adjusted local querying;
- full-market panel and factor research;
- SQL analysis, validation, repair and file export.

Deterministic interpretation:

```text
automated_personal_research_use_permission = confirmed_from_official_repository
local_normalized_market_data_retention_permission = confirmed_from_official_marketdb_product
derived_local_research_output_retention_permission = confirmed_from_official_workflows
local_duckdb_long_term_storage = explicitly_supported
full_market_results_local_persistence = explicitly_supported
```

Scope limitation:

- this evidence supports local normalized storage and local derived outputs within the documented research workflows;
- it does not establish a right to redistribute Provider data;
- it does not establish a right to publish Provider-valued fixtures;
- it does not authorize AQuantAI production access before remaining gates close.

## 5. Fixture policy resolved without Provider-valued repository data

AQuantAI does not need actual Provider market values in the public repository.

Accepted policy:

```text
public_repository_fixture_strategy = synthetic_or_schema_only
public_repository_provider_valued_fixture = prohibited_without_explicit_permission
private_repository_provider_valued_fixture = not_required_and_not_assumed
local_ignored_provider_valued_fixture = not_required_for_repository_tests
production_contract_validation_output = schema_envelope_field_type_and_hash_fingerprints_only
repository_tests_network_access = prohibited
```

Synthetic fixtures must:

- use only fields reachable through the reviewed production endpoint/schema;
- contain clearly invented values;
- preserve exact type, nullability, ordering and envelope constraints;
- add no information unavailable to production;
- never be represented as actual Provider data.

This resolves `fixture_policy` for a future Stage C Issue while preserving redistribution fail-closed behavior.

## 6. Official reference-client retry contract

The maintained Node.js CLI implements the following defaults:

```text
default_timeout_ms = 30000
default_max_attempts = 3
retry_after_header_precedence = true
client_backoff_attempt_0 = 1000ms plus 0-20 percent jitter
client_backoff_attempt_1 = 2000ms plus 0-20 percent jitter
client_backoff_attempt_2 = 4000ms plus 0-20 percent jitter
client_backoff_cap = 8000ms base plus jitter
retryable_business_codes = [4001, 5001, 5002, 5003]
authentication_errors = non_retryable
validation_errors = non_retryable
invalid_json_or_schema = non_retryable
```

Interpretation:

```text
retry_reference_contract = confirmed_from_official_client
```

This is an official reference-client behavior, not proof of an account's QPS, daily-total or concurrency entitlement. AQuantAI may later choose a stricter retry policy but must not become more aggressive than the reviewed Provider-supported behavior without separate evidence.

## 7. Facts still unresolved

The official product README states that data permissions, call frequency and accessible capabilities depend on the website and account authorization. The open-source client does not disclose the current account's exact limits.

Remain blocked:

```text
qps_limit
daily_total_limit
concurrency_limit
per_endpoint_or_global_limit_scope
account_specific_rate_limit_headers_or_capability_fields
stage_c_dataset_completion_time
snapshot_complete_session_cutoff
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

These facts must not be inferred from:

- successful low-volume validation;
- official client retry defaults;
- marketing/product positioning;
- absence of a documented limit;
- HTTP behavior observed through deliberate load testing.

No hidden-limit probing or load testing is authorized.

## 8. Separate unresolved capabilities

The following remain separate from the Stage C contract-evidence slice:

```text
corporate_action_account_entitlement = pending_bounded_local_validation
historical_full_market_gap_fill = blocked_pending_bounded_historical_contract
exact_per_security_daily_limit_prices = pending_separate_contract
historical_dated_sector_membership = unsupported
historical_sector_breadth = prohibited
```

A documented current full-market snapshot is not historical missing-session catch-up.

## 9. Updated deterministic gate

```text
ths_transport_gate = confirmed
ths_authentication_gate = confirmed
ths_required_p0_entitlements = confirmed
ths_automated_personal_research_use = confirmed_from_official_repository
ths_local_normalized_retention = confirmed_from_official_marketdb_product
ths_derived_local_output_retention = confirmed_from_official_workflows
ths_public_fixture_policy = synthetic_or_schema_only
ths_provider_valued_public_fixture = prohibited_without_explicit_permission
ths_retry_reference_contract = confirmed_from_official_client
ths_quota_contract = unresolved
ths_completion_and_revision_contract = unresolved
ths_api_key_lifecycle_contract = unresolved
ths_corporate_action_entitlement = pending_separate_validation
ths_historical_membership = unsupported
production_implementation_authorized = false
overall_gate = blocked_quota_contract
```

`blocked_quota_contract` is the controlling Issue #225 outcome for this evidence revision. Completion, correction, revision, late-data and key-lifecycle facts are also unresolved and must close before Stage C can become ready.

## 10. Effect on Stage C

Candidate remains:

```text
THS Provider Foundation + Index Market Overview
```

This evidence revision removes the generic assumption that all local retention is unknown. It does not authorize Stage C because the following remain missing:

- exact account-safe request ceilings;
- completion cutoffs for Stage C datasets;
- correction/revision/late-arrival handling;
- key lifecycle behavior;
- a separately authorized implementation Issue.

Until those facts close:

```text
stage_c_implementation_issue = prohibited
application_live_network_access = prohibited
credential_setup = prohibited
schema_or_migration = prohibited
provider_ingestion = prohibited
current_full_market_snapshot_implementation = prohibited
```

## 11. Failure semantics

When quota, completion or revision facts are unknown:

- no production request plan is activated;
- no guessed call cadence or concurrency is persisted;
- no current-session data is represented as complete without a reviewed cutoff;
- no corrected response silently overwrites frozen provenance;
- the prior complete local snapshot remains the conceptual fallback;
- no Tushare, AKShare, scraping or cross-Provider row mixing is introduced.

## 12. External clarification channel status

No email communication is required for this evidence path.

A documentation-clarification Issue was prepared for the official public repository, but the connected GitHub App has read-only access to `HiThink-Tech/Financial-API`; GitHub returned `403 Resource not accessible by integration`. Therefore no external Issue or partial message was published.

Remaining facts may be closed later through:

- a publicly documented account/quota capability;
- an account-visible non-secret quota page excerpt;
- a user-posted Issue through the normal GitHub UI;
- a future official documentation update;
- a redacted official support response from any non-email channel.

## 13. No implementation authorization

This document is evidence governance only. It is not:

- a Provider dataset;
- a credential profile;
- a runtime configuration;
- a schema or migration;
- an implementation Issue;
- permission to merge its PR;
- investment advice or trading behavior.
