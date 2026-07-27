# Today Market Provider-Neutral Acquisition Port and Deterministic Mock — Architecture Preflight

## 1. Decision status

- Governing Issue: #253.
- Product Roadmap: #137.
- Accepted automatic-refresh architecture: #221 / merged PR #222.
- Accepted THS source synchronization: #223 / merged PR #224.
- Controlling live Provider gate: #225.
- Accepted THS Stage C0 offline foundation: #227/#229 and #230/#231.
- Accepted THS market-dump evidence amendment: #251 / merged PR #252.
- Exact required base: `6084b20a2467f02465d3a9a342009a78f58e9773`.
- Risk tier: **Strict Architecture Preflight**.
- Product version remains `0.2.0`.
- This document is architecture only.

Architecture outcome:

```text
provider_neutral_application_port = ready_for_separate_mock_implementation_issue_after_merge
deterministic_mock_adapter = architecture_defined
mock_network = prohibited
mock_credentials = prohibited
mock_provider_values = prohibited
mock_persistence_migration = prohibited
live_stage_c1_gate = blocked_quota_contract
production_live_network_authorized = false
```

This document defines a narrow application seam and deterministic Mock boundary. It does not authorize code, a Mock implementation Issue, merge, live transport, credential setup, schema, migration or Provider acquisition.

## 2. Purpose

The accepted Today Market product path requires the application to render the latest complete local snapshot immediately, determine whether the snapshot is stale, acquire only bounded missing completed sessions, validate a complete candidate result and publish atomically.

The runtime currently has:

- a Chinese-first local-only Today Market read surface;
- accepted local snapshot repositories and deterministic Market Cockpit calculations;
- source-specific THS Stage C0 contracts, readiness, selectors, dry-run planning, fingerprints and synthetic schema validation;
- no live transport or credentials;
- no application-level refresh orchestration that can be exercised end to end without a real Provider.

Issue #225 remains blocked because account-specific quota, completion, correction/revision/late-data and key-lifecycle facts are unresolved.

The safe next step is therefore not a guessed THS live adapter. It is an application-level port plus a deterministic zero-network Mock that proves orchestration, boundedness, failure handling and CI behavior without changing Provider readiness.

## 3. Authority and precedence

For facts outside the narrow seam defined here, existing accepted documents remain authoritative:

1. `docs/today_market_automatic_daily_refresh_preflight.md` owns startup-refresh, bounded increment, stale-state and atomic-publication invariants.
2. `docs/today_market_ths_source_sync_preflight.md` owns THS source selection, capability staging, no-fallback policy and live Stage C decomposition.
3. `docs/ths_stage_c0_offline_foundation_preflight.md` owns THS source-specific offline contracts, readiness classes, selectors, planner and zero-network restriction.
4. `docs/ths_today_market_contract_evidence.md` owns accepted public retention, fixture and official reference-client evidence.
5. `docs/ths_market_dump_and_snapshot_contract_evidence_20260727.md` owns the reviewed public full-market snapshot and market-dump facts.
6. `docs/architecture_baseline.md` owns current repository state and domain direction.
7. `.codex/WORKFLOW.md` owns execution and merge gates.

When this document conflicts with a source-specific readiness or live-access gate, the stricter source-specific gate wins.

This document does not prospectively supersede THS as the selected first live source candidate. It only separates application orchestration from source-specific acquisition mechanics.

## 4. Core layering decision

```text
Today Market presentation/read surface
  -> Today Market refresh orchestration
      -> provider-neutral application acquisition port
          -> deterministic Mock adapter
          -> future THS application adapter
               -> datasource.ths_structured_provider Stage C0 contracts/readiness
               -> future live transport only after #225
```

### 4.1 Meaning of provider-neutral

Provider-neutral means:

- the orchestration layer expresses requested completed sessions, required capability families, bounds, coverage and failure semantics without accepting raw HTTP details;
- a source-specific adapter translates an accepted application plan into source-specific contract/selectors;
- every result still exposes exact source provenance and source-contract fingerprints;
- the application can be tested against a synthetic adapter without changing orchestration meaning.

Provider-neutral does **not** mean:

- a generic plug-in marketplace;
- arbitrary endpoint/path/query registration;
- runtime source selection from names or availability;
- automatic fallback to another Provider;
- blending rows from multiple Providers;
- treating equivalent-looking fields as semantically interchangeable;
- moving source-specific contracts, selectors or readiness out of `datasource/ths_structured_provider`.

### 4.2 Ownership table

| Meaning | Authoritative owner | Decision |
|---|---|---|
| Startup-refresh intent and bounded missing-session plan | `backend.today_market_refresh` application layer | New neutral owner after a separately authorized implementation. |
| Source endpoint/schema/selectors and capability readiness | source-specific adapter family, currently `datasource.ths_structured_provider` | Unchanged. |
| Temporary synthetic quota/completion values | deterministic Mock scenario | Test-only; never Provider evidence. |
| Raw Provider response and acquisition chronology | future source-specific acquisition domain | Not implemented by Mock. |
| Local market-data persistence | existing market-data persistence | Unchanged; Mock architecture adds no migration. |
| Market overview calculations | existing Market Cockpit calculators/service | Reused; no duplicate calculation owner. |
| Today Market labels and ordinary-Chinese states | Today Market projection/orchestration | Presentation only. |
| Canonical Price, Evidence, Industry Map and Investment Candidate | existing accepted owners | Never written by Mock refresh. |

## 5. Package boundary

Repository packaging currently includes `backend*` and does not include the static top-level `today_market/` directory as a Python package.

The future Mock implementation candidate therefore uses:

```text
backend/today_market_refresh/
```

Candidate modules for the later Implementation Issue:

```text
backend/today_market_refresh/__init__.py
backend/today_market_refresh/contracts.py
backend/today_market_refresh/planner.py
backend/today_market_refresh/port.py
backend/today_market_refresh/orchestrator.py
backend/today_market_refresh/mock.py
backend/today_market_refresh/fingerprint.py
backend/today_market_refresh/projection.py
```

The later Implementation Issue must re-inspect the repository and freeze exact files. This architecture does not authorize all listed modules automatically.

Explicitly absent from the Mock slice:

```text
transport.py
http_client.py
credentials.py
secret_store.py
repository.py
models.py
migration.py
provider_router.py
```

## 6. Temporary engineering-assumption profile

The project owner approved temporary average-like values so application and Mock work can continue before exact THS account facts are available.

Freeze exactly one synthetic profile:

```text
assumption_profile = aquantai.today-market.mock-planning-assumption.v1
assumption_class = synthetic_engineering_scenario
mock_qps = 5
mock_concurrency = 2
mock_daily_request_budget = 50000
mock_completion_after_local_time = 18:00:00
mock_timezone = Asia/Shanghai
provider_confirmed = false
production_eligible = false
```

### 6.1 Allowed use

The profile may be used only to:

- generate deterministic Mock quota-consumption scenarios;
- test one-process concurrency suppression;
- test bounded request planning;
- produce an injected synthetic completion decision;
- test ordinary-Chinese quota/completion warnings;
- prove that assumptions are visible and non-authoritative.

### 6.2 Prohibited use

The profile may not:

- populate `AccountQuotaFact`;
- populate `DatasetCompletionFact`;
- populate `CredentialLifecycleFact`;
- set any THS capability to `confirmed` or `implementation_ready`;
- set `remote_executable = true` in THS Stage C0;
- be written into a source authorization or capability revision;
- be used by a future live adapter;
- be described as a Provider average, entitlement, SLA or promise;
- close or weaken Issue #225.

### 6.3 Retry separation

The accepted product policy remains:

```text
startup_refresh_attempts = 1
```

unless a later reviewed source contract explicitly permits a bounded retry.

Official reference-client defaults may remain source evidence, but the Mock assumption profile does not convert them into product retries.

## 7. Application contract

### 7.1 `TodayMarketRefreshIntent`

Represents one local application decision to check or refresh one exact scope.

Required fields:

```text
scope_revision_id
trigger = application_start | first_today_market_entry | explicit_user_retry | explicit_manual_catchup
prior_snapshot_id_or_none
local_clock_utc
planning_policy_version
```

Rules:

- no implicit current time;
- no Provider name, endpoint or credential;
- one exact scope revision;
- trigger vocabulary is closed;
- application startup and first entry collapse to one process-scoped automatic opportunity.

### 7.2 `TodayMarketRefreshPlan`

Represents one fully validated bounded application plan before adapter invocation.

Required fields:

```text
scope_revision_id
refresh_attempt_id
trigger
prior_snapshot_id_or_none
requested_completed_sessions
capability_set
family_bounds
information_cutoff
recorded_at_utc
planning_policy_version
assumption_profile_id_or_none
plan_fingerprint
```

Rules:

- requested sessions are explicit, sorted, unique and non-empty for acquisition;
- automatic plans contain at most 10 completed sessions;
- more than 10 sessions produces `manual_catchup_required` and no adapter call;
- no URL, path, raw query mapping, header or credential field exists;
- an assumption profile is allowed only for `mock` mode and must be marked non-production;
- fingerprint uses canonical UTF-8 JSON and excludes presentation labels.

### 7.3 `TodayMarketAcquisitionPort`

Conceptual interface:

```text
acquire(plan: TodayMarketRefreshPlan) -> TodayMarketAcquisitionBatch
```

The port:

- accepts only an already validated plan;
- has no credential argument;
- has no arbitrary transport/configuration argument;
- returns one complete batch object or one typed failure;
- exposes no partially yielded family stream to orchestration;
- does not persist or publish.

A future live THS adapter may depend on source-specific contracts/readiness internally, but the port itself does not own those facts.

### 7.4 `TodayMarketSourceProvenance`

Required fields:

```text
source_key
adapter_contract_version
source_contract_fingerprints
source_mode = synthetic_mock | source_specific_live
observed_at_utc
provider_confirmed
```

Rules:

- Mock source key is exactly `aquantai-synthetic-today-market-v1`;
- Mock may never use `ths-account-structured-provider-v1` as its source key;
- `provider_confirmed` is always `false` for Mock;
- source-contract fingerprints remain explicit for future live adapters.

### 7.5 `TodayMarketCoverage`

Closed status vocabulary:

```text
complete
partial
empty
incompatible
```

Required fields:

```text
status
requested_sessions
covered_sessions
required_families
complete_families
missing_families
excluded_items
coverage_reason_codes
```

A batch is publishable only when:

```text
coverage.status = complete
covered_sessions = requested_sessions
missing_families = []
all required family results validate
```

### 7.6 `TodayMarketAcquisitionBatch`

Required fields:

```text
refresh_attempt_id
scenario_or_source_attempt_id
source_provenance
requested_sessions
data_through_session
coverage
family_results
redacted_diagnostics
batch_fingerprint
```

Rules:

- one source mode per batch;
- no cross-source rows;
- data-through must equal the latest covered requested session for a complete batch;
- diagnostics use closed codes and contain no credential or Provider raw bytes;
- batch fingerprint includes exact family-result fingerprints and source provenance;
- orchestration validates the entire batch before calculation or publication.

### 7.7 `TodayMarketAcquisitionFailure`

Closed failure categories:

```text
plan_invalid
assumption_budget_exhausted
concurrency_conflict
capability_unavailable
schema_mismatch
coverage_incomplete
source_unavailable
application_shutdown
internal_validation_failed
```

A failure contains:

```text
failure_code
category
refresh_attempt_id
source_key_or_none
redacted_details
retryability = none | explicit_user_retry | manual_catchup
```

No failure may silently trigger another source, another endpoint or an automatic retry.

## 8. Closed capability families

The first Mock slice mirrors only the accepted index-led Stage C candidate:

```text
trading_calendar
core_index_daily_history
industry_index_daily_history
concept_index_daily_history
current_constituents
limit_up_pool
limit_up_ladder
market_attention_candidates
```

### 8.1 Family result contract

Every family result includes:

```text
family_key
schema_version
requested_sessions
covered_sessions
item_count
synthetic
source_key
content_fingerprint
validation_status
reason_codes
payload
```

For Mock:

```text
synthetic = true
source_key = aquantai-synthetic-today-market-v1
```

### 8.2 Explicit exclusions

```text
full_market_individual_security_daily_ingestion
full_market_breadth_or_turnover_claims
full_market_down_limit_claims
historical_sector_breadth
historical_constituent_claims
adjusted_multi_session_returns
60_session_high_low_rules
full_market_exact_limit_price_claims
historical_gap_fill_from_current_snapshot
```

The Mock must not fabricate excluded coverage merely to make the UI look complete.

## 9. Deterministic Mock adapter

### 9.1 Structural zero-network rule

The future Mock package may not import or call:

```text
requests
httpx
urllib.request
socket
subprocess transport
browser automation
Provider SDK or CLI transport
```

Tests must enforce the absence of network activity during:

- import;
- FastAPI startup;
- ordinary read endpoints;
- Mock planning;
- Mock acquisition;
- fixture demos;
- CI.

### 9.2 Fixture policy

- invented values only;
- no copied Provider row values;
- no Provider-valued screenshots or responses;
- explicit `.synthetic.json` naming;
- stable UTF-8 JSON bytes;
- explicit schema version;
- exact expected fingerprints stored in tests where useful;
- no random generation during tests;
- scenario data cannot add a field unavailable to the reviewed intended production contract.

### 9.3 Clock and chronology

The Mock receives an injected timezone-aware clock and explicit synthetic calendar fixture.

It may use `mock_completion_after_local_time = 18:00:00` only when:

```text
assumption_profile_id = aquantai.today-market.mock-planning-assumption.v1
source_mode = synthetic_mock
```

Every projection must expose that the completion decision is synthetic.

No production default is created.

### 9.4 Quota and concurrency simulation

The Mock assumption profile may produce deterministic counters for one scenario:

```text
qps_window_capacity = 5
max_concurrent = 2
daily_request_budget = 50000
```

These counters are in-memory scenario inputs, not persisted account usage.

Required behavior:

- the third simultaneous synthetic acquisition fails with `mock_concurrency_exceeded`;
- the sixth request in one synthetic second fails with `mock_qps_exceeded`;
- the first request after the synthetic daily budget is consumed fails with `mock_daily_budget_exhausted`;
- failures do not change live readiness;
- tests use injected clocks and counters, never sleep-based timing.

## 10. Required Mock scenarios

### 10.1 `current_no_refresh_needed`

```text
prior data-through = expected completed session
-> no acquisition plan
-> no Mock call
-> status = current
```

### 10.2 `stale_one_session_success`

```text
one completed session missing
-> one bounded plan
-> complete synthetic batch
-> candidate projection succeeds
```

### 10.3 `stale_ten_sessions_success`

```text
ten completed sessions missing
-> automatic ceiling accepted
-> complete synthetic batch
-> candidate projection succeeds
```

### 10.4 `stale_more_than_ten_requires_manual_catchup`

```text
more than ten sessions missing
-> no automatic adapter call
-> status = manual_catchup_required
```

### 10.5 `not_initialized`

```text
no prior complete snapshot
-> no hidden startup bootstrap
-> explicit initialization plan required
```

### 10.6 `quota_assumption_exhausted`

```text
synthetic budget exhausted
-> typed failure
-> prior snapshot retained
-> assumption remains visibly synthetic
```

### 10.7 `partial_family_failure`

```text
one required family partial
-> batch rejected
-> no calculation/publish
```

### 10.8 `schema_mismatch`

```text
one family fixture violates its schema
-> deterministic validation failure
-> no partial result
```

### 10.9 `coverage_incomplete`

```text
requested session missing from one required family
-> coverage.status = partial
-> no publish
```

### 10.10 `synthetic_correction_revision`

```text
same natural key, changed synthetic content at later observed_at
-> distinct source-observation candidate fingerprint
-> no in-place history rewrite
```

This scenario tests AQuantAI append-only handling only. It does not assert that THS uses any particular correction mechanism.

### 10.11 `application_shutdown_before_publish`

```text
candidate batch validated
-> shutdown/cancellation observed before publish
-> no work continues after shutdown
-> prior snapshot remains current
```

## 11. Refresh orchestration state machine

Closed candidate states:

```text
idle
planning
no_refresh_needed
manual_catchup_required
acquiring
validating
calculating
candidate_ready
published_demo
failed_retained_prior
cancelled_retained_prior
```

Allowed transitions:

```text
idle -> planning
planning -> no_refresh_needed
planning -> manual_catchup_required
planning -> acquiring
acquiring -> validating
validating -> calculating
calculating -> candidate_ready
candidate_ready -> published_demo
acquiring|validating|calculating|candidate_ready -> failed_retained_prior
acquiring|validating|calculating|candidate_ready -> cancelled_retained_prior
```

The Mock implementation may expose `published_demo` only as an in-memory/demo candidate. It does not authorize database publication or alter accepted persisted snapshot identity.

## 12. Atomicity and persistence decision

```text
migration_required = false
new_database_tables = false
provider_persistence = false
mock_persistence = false
```

The Mock slice proves atomic candidate handling in memory:

- prior complete snapshot reference remains stable;
- no partial family result becomes visible as current;
- only a fully validated candidate projection is returned from the demo orchestration;
- a failure returns the prior snapshot plus failure state;
- no existing `IngestionRun` is fabricated or mutated.

A later live implementation requiring persistence must receive its own Strict architecture/implementation authorization and must reuse existing market-data ownership.

## 13. Ordinary-Chinese projection

Stable messages for the Mock slice:

```text
当前本地市场数据已是最新
正在使用模拟数据验证更新流程
模拟更新成功，真实数据源仍未启用
缺失交易日超过自动更新上限，需要手动补齐
模拟额度已用尽，未影响真实数据源状态
部分模拟数据不完整，已保留上一次完整结果
模拟数据结构不符合合同，未发布更新
应用已关闭，更新未继续执行
真实数据源额度或调用规则尚未确认
```

The primary UI must never present synthetic results as current market facts.

Every synthetic projection includes:

```text
is_synthetic = true
source_label = 模拟数据
production_live_source_ready = false
```

## 14. Security and redaction

The Mock contract has no credential field.

Tests must use sentinel secret strings placed only in rejected/untrusted test inputs and prove they do not appear in:

- plan canonical JSON;
- fingerprints;
- batch results;
- diagnostics;
- exceptions;
- API responses;
- demo output;
- CI logs.

No account ID, API-key fragment, Cookie, browser-session token, request ID, pre-signed URL or Provider market value may enter the Mock package or fixtures.

## 15. Compatibility with THS Stage C0

The future THS application adapter may consume Stage C0 concepts such as:

```text
PublicEndpointContract
CapabilityReadiness
source-specific selector
redacted request plan
contract fingerprint
```

But this architecture does not authorize that adapter.

Mandatory compatibility rules:

- Stage C0 remains source-specific and offline;
- `CapabilityReadiness.remote_executable = false` remains unchanged;
- Mock assumptions cannot be converted to `AccountQuotaFact` or `DatasetCompletionFact`;
- Mock selector values use the existing reserved synthetic namespace where source-like identity is needed;
- no application contract imports a live transport;
- no live adapter becomes constructible until a separate Stage C1 Issue closes all required gates.

## 16. Later Mock implementation decomposition

Only after this architecture PR is merged and the owner separately authorizes an Implementation Issue may the project add:

### Slice M1 — contracts and fingerprints

- immutable application DTOs;
- closed enums;
- canonical JSON fingerprinting;
- validation tests.

### Slice M2 — planner and state machine

- exact stale-session planning from injected calendar/completion decision;
- 10-session automatic ceiling;
- no-refresh and manual-catchup states;
- no adapter invocation for invalid plans.

### Slice M3 — deterministic Mock adapter

- frozen synthetic scenarios;
- in-memory quota/concurrency simulation;
- complete/partial/schema-invalid batches;
- zero-network enforcement.

### Slice M4 — orchestration and demo projection

- prior-snapshot retention;
- candidate calculation boundary;
- in-memory atomic demo result;
- ordinary-Chinese synthetic labels.

A single bounded implementation PR may contain M1–M4 if the later Issue freezes the files and tests and remains within the no-migration/no-network scope.

## 17. CI contract for the later Mock implementation

The exact implementation HEAD must pass:

1. full repository pytest;
2. all configured offline demos;
3. focused provider-neutral contract tests;
4. focused planner/state-machine tests;
5. deterministic Mock scenario tests;
6. explicit no-network guard tests;
7. sentinel-secret redaction tests;
8. deterministic fingerprint tests;
9. 1-session and 10-session success tests;
10. more-than-10 manual-catchup negative test;
11. partial/schema-invalid zero-publish tests;
12. prior-snapshot retention tests;
13. synthetic provenance tests;
14. a negative test proving assumptions cannot satisfy THS readiness;
15. import and FastAPI startup network-free regression.

No live smoke test belongs in the Mock implementation PR.

## 18. Production-realistic offline golden path

```text
fixture prior snapshot with exact data-through session
  -> injected synthetic calendar and synthetic completion rule
  -> one missing completed session
  -> exact refresh intent
  -> exact bounded refresh plan and fingerprint
  -> deterministic Mock complete index-led batch
  -> full coverage and schema validation
  -> existing deterministic calculation boundary
  -> complete in-memory synthetic candidate
  -> ordinary-Chinese result explicitly labeled 模拟数据
```

Required assertions:

- no network construction or call;
- no credential input;
- source key remains synthetic;
- previous snapshot remains available until candidate completion;
- repeated run is byte-identical;
- live-source readiness remains blocked.

## 19. Primary failure path

```text
fixture prior snapshot
  -> exact refresh plan
  -> Mock returns partial required family
  -> coverage validation rejects batch
  -> calculation not invoked
  -> no candidate published
  -> prior snapshot returned with stable Chinese failure
  -> live readiness unchanged
```

## 20. Migration, rollback and downgrade

```text
migration_required = false
schema_change = false
persistent_data_change = false
rollback = delete additive backend.today_market_refresh Mock modules, tests, fixtures and demo wiring
downgrade_data_loss = none
```

The later Mock implementation may update `.github/workflows/local-tests.yml` only to invoke a new zero-network fixture demo. Removing that additive invocation is sufficient rollback.

## 21. Readiness outcome

After this architecture is accepted:

```text
provider_neutral_port_architecture = accepted
mock_implementation_issue_candidate = allowed_after_separate_owner_instruction
mock_executable_candidate = true
live_ths_implementation_issue_candidate = prohibited
live_stage_c1_gate = blocked_quota_contract
issue_225 = open
production_live_network_authorized = false
```

Architecture acceptance does not authorize the Mock implementation Issue automatically and does not change the THS contract gate.

## 22. Locked exclusions

- real THS calls;
- credentials or credential lookup;
- source authorization activation;
- database schema/migration;
- Provider-valued fixtures;
- full-market individual-security daily ingestion;
- full-market breadth/turnover claims;
- historical sector breadth;
- adjusted multi-session analytics;
- live retry execution;
- scheduler, daemon, service worker or continuous polling;
- notifications or alerts;
- automatic evidence/research/candidate acceptance;
- recommendation, target price, expected return, portfolio or trading behavior;
- generic Provider plug-in framework;
- runtime fallback or row mixing.

## 23. Stop conditions

Stop if:

- temporary assumptions are required to pass source readiness;
- application contracts require arbitrary URLs/query dictionaries;
- source provenance would be erased;
- a Mock fixture requires actual Provider values;
- network or credential modules become necessary;
- a database migration is proposed;
- the Mock must modify accepted Canonical Price, Evidence, Industry Map or Investment Candidate state;
- live Stage C1 is started before #225 closes and receives separate owner authorization;
- frozen PR #241 would need to move;
- scope expands beyond the exact index-led families.

## 24. Required architecture review

Before merge consideration:

1. verify exact base and complete two-file inventory;
2. validate this document against Issue #253, `.codex/WORKFLOW.md`, architecture baseline, PR #222, PR #224 and Stage C0;
3. verify no executable code, workflow, schema, migration or fixture change;
4. verify the synthetic-assumption and live-readiness separation;
5. verify the packaged `backend/today_market_refresh/` boundary;
6. verify zero unresolved review threads;
7. record exactly:

```text
AUTHORIZED TODAY MARKET PROVIDER-NEUTRAL MOCK ARCHITECTURE APPROVED at fixed head <FULL_HEAD_SHA>
```

A new commit invalidates all fixed-head review and CI evidence. Merge requires separate explicit project-owner authorization.
