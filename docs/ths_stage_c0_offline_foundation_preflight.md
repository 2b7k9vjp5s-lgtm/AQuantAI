# THS Stage C0 — Offline Contract and Request-Planning Foundation

## 1. Decision status

- Governing Issue: #227.
- Exact architecture base: `2c3c64156ce4dcf88cf3bd7015b71f1ad4e3b933`.
- Risk tier: **Strict Architecture Preflight**.
- Product version remains `0.2.0`.
- This document is architecture only.

Architecture outcome:

```text
stage_c0_name = THS Offline Contract and Request-Planning Foundation
stage_c0_architecture = ready_for_separate_stage_c0_implementation_issue
stage_c0_network = prohibited
stage_c0_credentials = prohibited
stage_c0_persistence = prohibited
stage_c0_provider_valued_fixtures = prohibited
live_stage_c1_gate = blocked_quota_contract
production_live_network_authorized = false
```

The conclusion is deliberately narrow. It approves the shape of a future offline implementation Issue only. It does not authorize that Issue, code, merge or any remote Provider operation.

## 2. Why Stage C0 is safely separable

The accepted Provider architecture already defines `dry_run=true` as a zero-network operation that validates authorization, capability, selector and bounds and emits a redacted deterministic request plan. It also requires imports, FastAPI startup, ordinary reads, tests, CI and fixture demos to remain zero-network.

Merged PR #226 closed the generic local-normalized-retention uncertainty and selected synthetic/schema-only repository fixtures. It did not close account quotas, daily completion cutoffs, correction/revision/late-data behavior or API-key lifecycle.

Those facts affect whether a request may execute and how acquired data may be declared complete. They do not prevent AQuantAI from representing the already reviewed public endpoint contracts, validating invented selectors, generating a non-executable dry-run plan, fingerprinting that plan and validating a synthetic response shape.

Therefore Stage C0 can be separated only when its output is structurally incapable of remote execution.

## 3. Authority and precedence

This document refines only the offline implementation decomposition. For all other facts, accepted documents retain authority:

1. `docs/ths_today_market_contract_evidence.md` for official local-retention, fixture and reference-client evidence;
2. `docs/ths_today_market_contract_resolution.md` for current-snapshot versus historical-gap-fill separation;
3. `docs/ths_today_market_official_contract_appendix.md` for reviewed public endpoint contracts;
4. `docs/ths_today_market_capability_manifest.md` for entitlement/readiness state;
5. `docs/today_market_ths_source_sync_preflight.md` for THS Today Market source policy;
6. `docs/today_market_automatic_daily_refresh_preflight.md` for startup refresh and atomic publication invariants;
7. `docs/controlled_ths_refresh_mvp_preflight.md` for controlled-refresh decomposition;
8. `docs/ths_structured_provider_preflight_decisions.md` and `docs/ths_structured_provider_preflight.md` for Provider ownership, credential, capture and future persistence boundaries.

When this document conflicts with an existing live-access gate, the stricter live-access gate wins.

## 4. Current deterministic state

Facts sufficiently reviewed for offline encoding:

```text
source_key = ths-account-structured-provider-v1
adapter_family = ths_structured_provider
approved_host = fuyao.aicubes.cn
credential_mechanism_label = X-api-key
transport_candidate = documented REST API
personal_research_use = confirmed_from_official_repository
local_normalized_retention = confirmed_from_official_marketdb_product
public_fixture_policy = synthetic_or_schema_only
provider_valued_public_fixture = prohibited_without_explicit_permission
standard_envelope = code + message + optional request_id + data
reference_timeout_ms = 30000
reference_max_attempts = 3
reference_retry_after_precedence = true
reference_retryable_business_codes = 4001,5001,5002,5003
```

Account/live facts still unresolved:

```text
qps_limit
daily_total_limit
concurrency_limit
per_endpoint_or_global_limit_scope
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
corporate_action_account_entitlement
```

These unresolved values are required readiness inputs. Stage C0 must never replace them with guessed defaults.

## 5. Product and ownership boundary

Stage C0 answers only:

> Given one frozen reviewed public THS contract and one invented selector, what bounded request would be planned, what contract/readiness facts would still block execution, and does one synthetic response conform to the reviewed schema?

Stage C0 owns:

- source-specific public contract representation;
- source-specific capability/readiness representation without persistence;
- selector validation;
- non-executable dry-run planning;
- request and schema fingerprinting;
- deterministic redaction of synthetic diagnostic structures;
- synthetic response-envelope/schema validation;
- fail-closed technical and Chinese blocked reason projection.

Stage C0 does not own:

- credential material or credential-profile lookup;
- source authorization activation;
- account entitlement verification;
- network transport or retry execution;
- acquisition attempts;
- immutable raw Provider objects;
- normalized Provider observations;
- Provider-to-Listed-Instrument acceptance;
- Canonical Price or Comparison Eligibility;
- company-action adjustment factors;
- accepted taxonomy identity;
- Evidence Ledger, Industry Map, beneficiary or Investment Candidate state;
- Today Market calculation, persistence or UI.

## 6. Package decision

`pyproject.toml` already packages `datasource*`, and `datasource` is the existing integration ownership family. The source-specific package below does not currently exist and is the narrowest compatible future boundary:

```text
datasource/ths_structured_provider/
```

The future Stage C0 implementation may add exactly:

```text
datasource/ths_structured_provider/__init__.py
datasource/ths_structured_provider/contracts.py
datasource/ths_structured_provider/readiness.py
datasource/ths_structured_provider/selectors.py
datasource/ths_structured_provider/planner.py
datasource/ths_structured_provider/fingerprint.py
datasource/ths_structured_provider/redaction.py
datasource/ths_structured_provider/schemas.py
```

The package name matches the accepted adapter family and allows a future Stage C1 to consume the same contracts without creating a second contract owner.

Explicitly absent from Stage C0:

```text
transport.py
client.py
http.py
credentials.py
secret_store.py
repository.py
models.py
commands.py
api.py
```

No module may import `requests`, `httpx`, `urllib.request`, `socket`, `subprocess`, browser automation or Provider SDK/CLI transport.

## 7. Static contract registry

### 7.1 Registry purpose

`contracts.py` will contain immutable Python value objects for reviewed public contract facts. It is source-specific and not a generic Provider plug-in registry.

One endpoint contract must contain only reviewed facts such as:

```text
contract_key
capability_key
host_key
https_host
http_method
path_template
ordered_query_fields
required_query_fields
optional_query_fields
selector_schema_version
response_schema_version
pagination_contract
ordering_contract
timezone_contract
unit_contract
public_limit_contract
reviewed_at_date
source_document_key
contract_fingerprint
```

It must not contain:

- API keys or credential profile names;
- account IDs or account-plan labels that identify the user;
- QPS/daily/concurrency guesses;
- runtime completion times;
- actual Provider response values;
- mutable runtime overrides;
- arbitrary URLs.

### 7.2 Initial contract subset

The Stage C0 implementation is limited to the first index-led candidate and minimum readiness support:

```text
a_share_trading_calendar
a_share_index_ticker_list
a_share_index_daily_history
ths_industry_index_catalog
ths_concept_index_catalog
ths_index_current_constituents
limit_up_pool
limit_up_ladder
hot_stock_list
stock_anomaly_reasons
```

The offline golden path uses only:

```text
a_share_index_daily_history
```

Current full-market snapshot may be represented in the registry only if the implementation remains bounded and no full-market fixture/data is added. It is not part of the required golden path or Stage C0 completion claim.

Corporate actions, historical full-market gap fill, exact daily limit prices and historical constituents remain excluded.

### 7.3 Fact classes

The registry and readiness layer must distinguish:

```text
PublicEndpointContract
AccountEntitlementFact
AccountQuotaFact
DatasetCompletionFact
CorrectionRevisionFact
CredentialLifecycleFact
```

Only `PublicEndpointContract` is fully source-controlled in Stage C0. The remaining fact classes accept non-secret status labels and evidence fingerprints, but no account record is persisted.

## 8. Readiness contract

### 8.1 Closed status vocabulary

```text
confirmed
unsupported
not_entitled
unresolved
blocked
```

One `CapabilityReadiness` object includes:

```text
source_key
capability_key
public_contract_status
entitlement_status
retention_status
fixture_status
quota_status
completion_status
revision_status
credential_lifecycle_status
historical_membership_status
corporate_action_status
reviewed_evidence_fingerprints
```

### 8.2 Executability

Stage C0 always returns:

```text
remote_executable = false
```

Even when all supplied facts are `confirmed`, the Stage C0 planner cannot become a live executor. A future Stage C1 implementation must add a separately reviewed execution boundary.

The planner may project hypothetical readiness:

```text
live_readiness_candidate = ready | blocked
```

but must not activate a source or credential.

### 8.3 Required blocked reason codes

At minimum:

```text
THS_C0_QUOTA_CONTRACT_UNRESOLVED
THS_C0_COMPLETION_CONTRACT_UNRESOLVED
THS_C0_REVISION_CONTRACT_UNRESOLVED
THS_C0_KEY_LIFECYCLE_UNRESOLVED
THS_C0_CAPABILITY_NOT_ENTITLED
THS_C0_CAPABILITY_UNSUPPORTED
THS_C0_HISTORICAL_MEMBERSHIP_UNSUPPORTED
THS_C0_CORPORATE_ACTION_NOT_VALIDATED
THS_C0_SELECTOR_INVALID
THS_C0_SELECTOR_OUT_OF_BOUNDS
THS_C0_CONTRACT_NOT_REVIEWED
THS_C0_SCHEMA_MISMATCH
THS_C0_UNREACHABLE_FIXTURE_FIELD
THS_C0_NETWORK_PROHIBITED
```

Stable ordinary-Chinese projections include:

```text
数据源额度或调用规则尚未确认
无法确认数据何时完整
数据更正与迟到规则尚未确认
凭据过期与轮换规则尚未确认
当前账户没有该能力
当前数据源不支持该能力
缺少历史成分，历史板块宽度不可用
公司行为能力尚未验证，复权分析不可用
请求范围不符合已审核合同
响应结构与已审核合同不一致
离线基础层禁止联网
```

## 9. Selector contract

### 9.1 Source-specific selectors

`selectors.py` contains closed Pydantic or immutable dataclass selectors per accepted capability. It must not accept arbitrary endpoint paths or arbitrary query dictionaries.

Initial required selector:

```text
IndexHistorySelector
- thscode: synthetic/test value accepted only under explicit schema rules
- start_ms
- end_ms
```

Production semantics represented offline:

- exactly one index `thscode`;
- `start_ms <= end_ms`;
- reviewed maximum history window;
- millisecond Unix timestamps;
- Asia/Shanghai source-market interpretation where the contract requires it;
- no adjustment parameter;
- no automatic current-time default.

### 9.2 Synthetic identity rule

Repository fixtures must not copy a real Provider security/index code. Test selectors use clearly invented, structurally valid values reserved for synthetic testing, for example a contract-owned synthetic namespace rejected by any future live executor.

The Stage C0 planner must mark synthetic selectors:

```text
synthetic_only = true
remote_executable = false
```

A future Stage C1 may introduce a separate production selector identity validation without changing Stage C0 fixtures.

## 10. Dry-run request plan

### 10.1 Required fields

`planner.py` produces an immutable `DryRunRequestPlan` containing:

```text
source_key
capability_key
contract_key
contract_fingerprint
host_key
https_host
http_method
path_key
ordered_query_items
selector_fingerprint
pagination_ceiling
record_ceiling
raw_byte_ceiling
transport_policy_version
readiness_snapshot
blocked_reason_codes
synthetic_only
remote_executable
```

No raw URL string with secrets is needed. A redacted display URL may be derived only from the allowlisted host, static path and synthetic query values.

### 10.2 Plan invariants

- one exact source;
- one exact capability;
- one exact public contract;
- one exact selector;
- no implicit current time;
- deterministic ordered query serialization;
- deterministic bounds;
- no credential field;
- no runtime retry loop;
- no network object or callable;
- no database identity;
- no alternate host or fallback.

### 10.3 Executability invariant

For every Stage C0 plan:

```text
remote_executable = false
```

Unresolved live facts are disclosed as blocked reasons rather than hidden.

## 11. Fingerprint contract

`fingerprint.py` computes SHA-256 over canonical UTF-8 JSON with sorted object keys and stable list ordering.

Request-plan fingerprint input:

```text
source_key
capability_key
contract_key
contract_fingerprint
host_key
http_method
path_key
ordered_query_items
pagination_ceiling
record_ceiling
raw_byte_ceiling
transport_policy_version
selector_schema_version
```

Excluded:

- API key or credential profile;
- account identifier;
- request ID;
- runtime clock;
- random value;
- retry attempt number;
- fetched/recorded time;
- actual Provider response.

Schema fingerprint input includes exact envelope/field/type/nullability/order/unit contract only.

## 12. Redaction contract

`redaction.py` operates on invented/synthetic maps, strings and errors. It must remove or replace keys matching the reviewed sensitive-field vocabulary:

```text
X-api-key
authorization
api_key
token
cookie
set-cookie
account_id
user_id
request_id
credential_profile
```

It must also reject:

- URLs containing userinfo;
- query keys resembling credentials;
- headers outside the allowlisted diagnostic set;
- exception text containing prohibited labels.

Stage C0 does not need to load or inspect a real credential to prove redaction behavior.

## 13. Response schema validation

### 13.1 Envelope

`synchronous.py` is not authorized; validation belongs in `schemas.py`.

The accepted envelope shape is:

```text
code: integer
message: string
request_id: optional string
data: contract-specific object
```

Repository synthetic success fixtures must omit `request_id` unless testing redaction with an invented placeholder. No real request ID is allowed.

### 13.2 Index-history row

The synthetic index-history schema must include only fields documented by the accepted official contract and exact types/nullability. It must preserve:

- source index identity field;
- timestamp/date field;
- open/high/low/close representation;
- volume and turnover fields where documented;
- ordering contract;
- currency/unit semantics;
- no extra unreviewed field.

The architecture document does not duplicate the complete field list from the official-contract appendix. The implementation Issue must bind the exact frozen field inventory and contract fingerprint from that accepted document.

### 13.3 Unknown fields

Default behavior:

```text
unknown_field = reject
missing_required_field = reject
wrong_type = reject
invalid_null = reject
ordering_violation = reject
unit_or_currency_mismatch = reject
```

No automatic repair, coercion from free text or best-effort partial acceptance.

## 14. Synthetic fixture policy

Authorized fixture family for the future implementation:

```text
tests/fixtures/ths_stage_c0/
```

Allowed fixtures:

```text
index_history_success.synthetic.json
index_history_unknown_field.synthetic.json
index_history_wrong_type.synthetic.json
index_history_bad_order.synthetic.json
standard_error.synthetic.json
```

Every fixture must contain a top-level marker such as:

```text
_aquantai_fixture_kind = synthetic
```

and invented values that are not copied from any Provider response, screenshot, documentation example containing real market values or account output.

Fixture review must prove:

- every field is reachable through the reviewed production contract;
- no additional convenience field exists;
- no real security/index identity, price, volume, turnover, date series or request ID is copied;
- fixture bytes are safe for a public repository;
- tests never contact the Provider.

## 15. Network-denial architecture

### 15.1 Import boundary

Importing any `datasource.ths_structured_provider` Stage C0 module must perform:

```text
network_calls = 0
dns_calls = 0
socket_calls = 0
subprocess_calls = 0
environment_secret_reads = 0
database_calls = 0
```

### 15.2 Test guard

Future tests must patch or deny at least:

- `socket.socket`;
- `socket.create_connection`;
- `httpx.Client` and `httpx.AsyncClient` request/send entry points;
- `urllib.request.urlopen`;
- `subprocess.run`, `Popen` and shell execution where relevant.

The package source must also pass a static forbidden-import/forbidden-symbol test.

### 15.3 CI and demo

The offline demo is invoked from `.github/workflows/local-tests.yml` only after focused and full tests. It receives no secret environment variables and must succeed with outbound network unavailable.

No opt-in live smoke test belongs to Stage C0.

## 16. Future implementation file families

A later Strict Stage C0 implementation Issue may authorize only:

```text
.codex/tasks/issue-<N>-ths-stage-c0-offline-foundation-implementation.md
datasource/ths_structured_provider/__init__.py
datasource/ths_structured_provider/contracts.py
datasource/ths_structured_provider/readiness.py
datasource/ths_structured_provider/selectors.py
datasource/ths_structured_provider/planner.py
datasource/ths_structured_provider/fingerprint.py
datasource/ths_structured_provider/redaction.py
datasource/ths_structured_provider/schemas.py
tests/test_ths_stage_c0_contracts.py
tests/test_ths_stage_c0_readiness.py
tests/test_ths_stage_c0_planner.py
tests/test_ths_stage_c0_fingerprint.py
tests/test_ths_stage_c0_redaction.py
tests/test_ths_stage_c0_schemas.py
tests/test_ths_stage_c0_network_denial.py
tests/fixtures/ths_stage_c0/*.synthetic.json
scripts/demo_ths_stage_c0_offline.py
.github/workflows/local-tests.yml
```

The implementation Issue may narrow this list. It may not add transport, credentials, persistence, API, UI or migration files without returning to architecture review.

No dependency change is expected because Python 3.12, Pydantic and existing test tooling are sufficient.

## 17. Offline golden path

A production-reachable offline golden path must prove:

1. import the Stage C0 package with all network/secret/database guards active;
2. load the exact frozen `a_share_index_daily_history` public contract;
3. construct one clearly synthetic `IndexHistorySelector`;
4. validate exact one-index and time-window bounds;
5. provide a readiness object with confirmed public contract/entitlement/retention/fixture facts and unresolved quota/completion/revision/key-lifecycle facts;
6. generate one deterministic dry-run plan;
7. return `remote_executable=false` and the exact unresolved blocked reasons;
8. compute the same request-plan SHA-256 across repeated runs and input dictionary order changes;
9. validate one synthetic standard envelope and index-history row;
10. compute the same schema fingerprint across repeated runs;
11. show a redacted Chinese summary and collapsed technical plan;
12. prove zero network, credential, Provider value, database write, acquisition attempt, raw object, identity acceptance or downstream state mutation.

## 18. Primary failure path

One fixture includes an unknown field or an invalid ordering and one caller attempts to plan historical constituents.

Required result:

```text
schema_validation = rejected
historical_membership = unsupported
remote_executable = false
network_attempt = none
persistence = none
fallback = none
published_snapshot = none
```

The errors remain stable and do not expose fixture payloads as Provider data.

## 19. Rollback and downgrade

Stage C0 has:

```text
schema_migration = none
data_backfill = none
persistent_state = none
credential_state = none
network_side_effect = none
```

Rollback is a code/test/demo revert. No user database or Provider data requires cleanup.

A future Stage C1 may import Stage C0 contracts and planners. It must not mutate or reinterpret an accepted Stage C0 contract through runtime configuration. Contract changes require a new version/fingerprint and reviewed architecture or implementation scope.

## 20. Live Stage C1 remains blocked

This preflight does not change Issue #225:

```text
qps_limit = unresolved
daily_total_limit = unresolved
concurrency_limit = unresolved
stage_c_dataset_completion_time = unresolved
correction_revision_late_data_behavior = unresolved
api_key_lifecycle_contract = unresolved
live_stage_c1_gate = blocked_quota_contract
```

No live Stage C1 Issue, branch or code may be created from this architecture outcome alone.

## 21. Explicit exclusions

No:

- HTTP/DNS/socket/subprocess transport;
- API key, environment secret or credential store;
- source activation or entitlement probing;
- acquisition attempt or raw response storage;
- database model, repository, schema, migration or backfill;
- Provider-valued fixture or downloaded market file;
- FastAPI route, Today Market UI or page refresh;
- current full-market ingestion or historical catch-up;
- company-action/adjusted-return implementation;
- historical membership synthesis;
- scheduler, daemon, background worker or notification;
- fallback, source blending or row mixing;
- AI-owned acceptance or causal conclusion;
- Canonical Price, Evidence Ledger, Industry Map, beneficiary, Investment Candidate, recommendation, target price, expected return, portfolio, broker, order or trading behavior;
- release, tag or version change.

## 22. Delivery gates

The architecture PR must:

1. remain based exactly on `2c3c64156ce4dcf88cf3bd7015b71f1ad4e3b933`;
2. change only this document and the Issue #227 task snapshot;
3. remain Draft;
4. pass exact-head repository CI;
5. receive a process-independent fixed-head review with:

```text
AUTHORIZED THS STAGE C0 OFFLINE FOUNDATION PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

6. have zero unresolved review threads;
7. receive separate explicit owner authorization before merge.

Any new commit invalidates prior CI and fixed-head review. Architecture merge does not authorize implementation.