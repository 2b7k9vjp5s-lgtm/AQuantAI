# Today Market Refresh Runtime Integration v1 — Architecture Preflight

## 1. Status, authority and exact base

This document defines the bounded architecture for Issue #259 and resolves the five blockers recorded by fixed-head review `4786108502`.

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
base_sha = 1b2de3544844647ad02beffe2e6a8e14c467fd98
released_version = 0.2.0
risk_tier = Strict Architecture Preflight
```

Project-owner authority permits only this architecture preflight, its architecture branch and one Draft architecture PR. It does not authorize production implementation, live THS access, credentials, network, schema, migration, persistence, scheduler, recommendation, portfolio, trading, release, tag or version change.

Controlling authorities remain:

- Product Roadmap Issue #137;
- live THS external-contract gate Issue #225;
- current-state baseline Issue #257 / merged PR #258;
- Today Market automatic-refresh architecture Issue #221 / merged PR #222;
- THS source synchronization Issue #223 / merged PR #224;
- THS Stage C0 architecture/implementation #227/#229 and #230/#231;
- public full-market snapshot and Market Dump evidence #251/#252;
- provider-neutral acquisition-port architecture #253/#254;
- deterministic zero-network Mock implementation #255/#256.

PR #241 remains closed, unmerged and read-only at exact HEAD:

```text
3116a67ec472131eea3bf3d1bd9daee884c69ee9
```

## 2. Selected v1 outcome

The selected boundary is:

```text
FastAPI import/startup
  -> no refresh and no runtime side effect
raw GET /today-market
  -> static page only; no acquisition
explicit dual-as-of boundaries + explicit local series
  -> server reads one exact prior local snapshot
  -> page renders the prior snapshot first
  -> server returns exact runtime scope/status/fingerprint
Mock demo mode explicitly injected by server-side application factory
  -> browser automatically submits one first-eligible-scope command
  -> one synchronous bounded process-local Mock attempt runs
  -> one complete synthetic candidate is validated
  -> one separate synthetic runtime projection is exposed
failure, stale state or shutdown
  -> no partial publication; prior persisted snapshot remains authoritative
```

Mock is disabled by default. When disabled, runtime status is `mock_not_enabled` and no acquisition occurs. When explicitly enabled for tests or a demo launcher, the first eligible scoped interaction performs exactly one automatic Mock attempt.

Rejected alternatives:

```text
FastAPI application-start refresh                  = rejected
raw page-load acquisition before exact scope       = rejected
hidden local-series selection                      = rejected
Mock as default production source                  = rejected
Mock result persisted as local market history      = rejected
background task / scheduler / polling              = rejected
live THS adapter in v1                              = blocked by Issue #225
```

## 3. Existing contracts reused

V1 composes the accepted package:

```text
backend.today_market_refresh
```

It reuses without weakening:

- `TodayMarketRefreshIntent`;
- `TodayMarketRefreshPlan`;
- `TodayMarketAcquisitionPort`;
- `TodayMarketAcquisitionBatch`;
- `TodayMarketAcquisitionFailure`;
- `SnapshotReference`;
- `TodayMarketRefreshOutcome`;
- `build_refresh_plan`;
- `run_mock_refresh`;
- `validate_publishable_batch` / `build_demo_projection`.

The runtime layer does not create a second planner, a second complete-batch validator or source-specific schema meaning.

## 4. Exact authoritative prior-snapshot identity

### 4.1 One authoritative read path

Every eligible runtime scope is created from the same server-side read path used to build the existing Today Market snapshot:

1. validate `as_of_cutoff` and `as_of_recorded_at_utc`;
2. validate exact equity series key and optional benchmark/sector series keys;
3. use the existing Market Cockpit repositories and service to load the exact visible snapshot;
4. resolve the exact succeeded/complete `IngestionRun` component selected for each requested family under those same boundaries;
5. require one unique component identity for each selected family;
6. build the snapshot identity and content fingerprint from those exact results.

The implementation may add a bounded read-only provenance projection to existing repository/service results. It may not create a new persisted owner, select a maximum-coverage context, select a latest-compatible context outside the existing deterministic repository order, or infer identity from browser labels.

If the exact selected component set is not unique, a required component is missing, or repository/service results disagree, runtime scope creation fails closed.

### 4.2 `TodayMarketLocalSnapshotIdentityV1`

Canonical identity payload:

```text
snapshot_identity_version = aquantai.today-market-local-snapshot-identity.v1
as_of_cutoff
as_of_recorded_at_utc
selected_components = [equity, benchmark, sector]
market_snapshot_contract_version
```

Each family position is fixed; an unselected optional family is explicit `null`. A selected component contains:

```text
family_key
 ingestion_run_id
 dataset
 provider
 series_key
 information_cutoff_date
 imported_at_utc
 completed_at_utc
 snapshot_mode
 effective_session
 canonical_series_identity
```

Rules:

- dates use ISO `YYYY-MM-DD`;
- timestamps are normalized to UTC with `Z`;
- mapping keys are sorted;
- canonical series identities use their existing validators;
- tuple/list ordering is explicit and stable;
- no localized label, UI copy, database connection detail or browser state enters the identity.

Derived identifier:

```text
prior_snapshot_id = "today-market-local-v1:" + canonical_sha256(identity_payload)
```

### 4.3 Content fingerprint

Canonical content payload:

```text
snapshot_content_version = aquantai.today-market-local-snapshot-content.v1
identity_payload
market_cockpit_domain_snapshot = {
  provenance,
  universe_stock_count,
  available_stock_count,
  scope_coverage_status,
  calculation_status,
  completeness_status,
  warnings,
  price_behavior_context,
  liquidity_context,
  benchmark_context,
  sector_context,
  latest_data_diagnostics
}
```

The content fingerprint is:

```text
prior_snapshot_content_fingerprint = canonical_sha256(content_payload)
```

The domain snapshot is taken before Today Market presentation copy is added. Warnings and set-like values are canonically sorted; nulls are preserved; floats and dates use the repository's existing canonical serializer. Raw presentation JSON, HTML, localized prose, `allowed_actions` and progressive disclosure wrappers are excluded.

### 4.4 Moved or stale prior snapshot

GET status and POST command must independently re-run the same authoritative read path. Before planning or acquisition, POST compares the server-rebuilt:

```text
prior_snapshot_id
prior_snapshot_content_fingerprint
runtime_scope_revision_id
```

against the exact values represented by the submitted status fingerprint. Any mismatch returns `runtime_scope_stale` or `runtime_prior_snapshot_moved` with zero acquisition and no process-local candidate change.

## 5. Runtime scope contract

A `TodayMarketRuntimeScopeV1` is server-owned and not persisted.

```text
runtime_scope_version = aquantai.today-market-runtime-scope.v1
as_of_cutoff
as_of_recorded_at_utc
equity_series_key
benchmark_series_key | null
sector_series_key | null
prior_snapshot_id
prior_snapshot_content_fingerprint
prior_snapshot_data_through_session
required_capability_set
planning_policy_version
planning_recorded_at_utc
runtime_scope_revision_id
```

Rules:

1. All identity-bearing values come from one successful authoritative snapshot read.
2. The browser never constructs IDs or fingerprints from labels or raw JSON.
3. Changing either boundary or any series invalidates the scope.
4. No fuzzy, first-visible, maximum-coverage or latest-compatible fallback is allowed.
5. `planning_recorded_at_utc` is not a client field. It is exactly the normalized `as_of_recorded_at_utc` already bound into the scope.
6. `runtime_scope_revision_id` is canonical SHA-256 over every preceding identity-bearing field.

This closes the planning-clock ambiguity: one exact scope has exactly one planning clock.

## 6. Runtime status and optimistic-concurrency fingerprint

### 6.1 Closed DTO

Every status response contains:

```text
runtime_status_version = aquantai.today-market-runtime-status.v1
runtime_scope
runtime_scope_fingerprint
runtime_status_revision
phase
prior_snapshot_state
refresh_state
source_mode
source_label
is_synthetic
mock_enabled
automatic_attempt_state
active_attempt_id | null
plan_fingerprint | null
candidate_projection | null
failure | null
state_explanation
allowed_actions
technical_details
runtime_status_fingerprint
```

`runtime_status_revision` is a process-local monotonically increasing integer per coordinator scope. It starts at zero after process restart and increments for every accepted state transition.

### 6.2 Canonical status fingerprint

The server computes:

```text
runtime_status_fingerprint = canonical_sha256({
  runtime_status_version,
  runtime_scope_fingerprint,
  runtime_status_revision,
  phase,
  prior_snapshot_state,
  refresh_state,
  source_mode,
  is_synthetic,
  mock_enabled,
  automatic_attempt_state,
  active_attempt_id,
  plan_fingerprint,
  candidate_projection_fingerprint,
  failure_code,
  failure_category,
  retryability,
  allowed_action_codes
})
```

Explicit exclusions:

- localized Chinese prose;
- presentation ordering;
- expanded technical details;
- transient request time;
- browser state.

GET and POST both return this field. The browser treats it as opaque and never recalculates it.

### 6.3 POST comparison point

`POST /today-market/api/runtime-refresh` requires:

```text
expected_runtime_status_fingerprint
```

Under the coordinator lock, before building an intent, plan or calling an acquisition port, the server:

1. re-resolves the exact authoritative prior snapshot;
2. rebuilds the runtime scope;
3. reads the current matching process-local state;
4. rebuilds the current status fingerprint;
5. compares it byte-for-byte with the expected fingerprint.

Mismatch returns HTTP 409 with stable code `runtime_status_conflict`, the current complete status, and:

```text
planning_called = false
acquisition_called = false
candidate_changed = false
```

## 7. Trigger and bounded automatic attempt

### 7.1 No startup or raw-load side effect

- importing or starting FastAPI performs no refresh;
- requesting `/today-market` performs no acquisition;
- unrelated routes are never blocked by Today Market runtime work.

### 7.2 First eligible scoped interaction

After the user explicitly selects boundaries and series and the page renders one exact prior snapshot:

1. browser calls `GET /today-market/api/runtime-status`;
2. server returns exact scope, phase and status fingerprint;
3. if `mock_enabled = true` and `automatic_attempt_state = not_attempted`, the browser automatically submits exactly one POST;
4. the POST trigger is `FIRST_TODAY_MARKET_ENTRY`;
5. the request runs synchronously and is bounded by the existing ten-session ceiling;
6. prior snapshot remains visible during the command;
7. no second automatic command occurs for the same scope generation.

If Mock is disabled, GET returns `mock_not_enabled`; no POST is sent automatically.

### 7.3 Explicit retry

A failed/cancelled status may expose one explicit action:

```text
重新运行模拟演示
```

That command uses `EXPLICIT_USER_RETRY` and the newest server-returned status fingerprint. It is not an automatic retry loop.

`EXPLICIT_MANUAL_CATCHUP` remains a separately named trigger but v1 does not implement historical bulk catch-up.

## 8. Single-flight, command identity and replay

### 8.1 Coordinator scope

```text
coordinator_scope_key = canonical_sha256({
  runtime_scope_revision_id,
  source_mode,
  mock_scenario
})
```

At most one active command exists for this key in one process.

### 8.2 Command generation

```text
command_key = canonical_sha256({
  expected_runtime_status_fingerprint,
  trigger
})

refresh_intent_scope_revision_id = canonical_sha256({
  runtime_scope_revision_id,
  expected_runtime_status_fingerprint,
  trigger
})
```

`TodayMarketRefreshIntent.scope_revision_id` receives `refresh_intent_scope_revision_id`. Its `local_clock_utc` receives the server-owned `planning_recorded_at_utc` from the runtime scope.

Consequences:

- the first automatic attempt and a later retry have distinct deterministic attempt IDs;
- two simultaneous requests using the same stale expected fingerprint cannot both acquire;
- a changed status transition creates a new status fingerprint and therefore a new command generation;
- planning time cannot vary independently inside one runtime scope;
- identical completed replay returns the current immutable status and does not silently reacquire.

### 8.3 Concurrency rules

1. Lock by `coordinator_scope_key` before status-fingerprint comparison.
2. First valid command transitions status to `refresh_in_progress`, increments revision and publishes the new status atomically.
3. A simultaneous request carrying the old expected fingerprint receives `runtime_status_conflict` and zero acquisition.
4. A request with changed boundaries/series resolves to a different runtime scope.
5. Process restart discards locks and synthetic state; persisted local data is unchanged.

## 9. Mock-only plan and future live boundary

### 9.1 V1 plan eligibility

The current `TodayMarketRefreshPlan` and `build_refresh_plan` are explicitly Mock-only:

```text
assumption_profile_id = MOCK_ASSUMPTION_PROFILE_ID
production_eligible = false
```

Runtime Integration v1 constructs only this plan and may call only an explicitly injected deterministic Mock port.

### 9.2 What is provider-neutral today

Reusable in v1 and future architecture:

- high-level runtime status/orchestration shape;
- all-or-nothing candidate publication;
- explicit acquisition seam concept;
- failure retention of the prior snapshot;
- no hidden fallback or source mixing.

Not production-neutral:

- the current Mock assumption-bearing plan payload;
- Mock quota/completion assumptions;
- synthetic source provenance.

### 9.3 Future THS insertion

After Issue #225 is closed by reviewed evidence, live integration requires a separate Strict Architecture Preflight that freezes either:

1. a new production planning contract/version accepted by a live acquisition port; or
2. a reviewed source-specific plan translation owner outside the runtime coordinator.

A future adapter must not:

- relax the current Mock assumption-profile validation;
- disguise live inputs as synthetic;
- interpret THS quotas, completion, corrections or credentials inside the runtime coordinator;
- reuse Provider-valued fixtures without reviewed permission;
- create fallback from THS to Mock or another Provider.

Until that separate architecture is accepted:

```text
SOURCE_SPECIFIC_LIVE request = rejected
live adapter construction = absent
credential lookup = absent
network transport = absent
```

## 10. Runtime phases and Chinese projection

Closed phases:

```text
runtime_not_started
prior_snapshot_ready
no_refresh_needed
not_initialized
manual_catchup_required
refresh_in_progress
demo_published
failed_retained_prior
cancelled_retained_prior
mock_not_enabled
live_source_blocked
scope_stale
local_database_unavailable
```

Every status answers exactly:

```text
发生了什么
为什么重要
现在可以做什么
```

Minimum meanings:

### `prior_snapshot_ready`

```text
发生了什么 = 已读取明确选择的本地完整快照，模拟更新尚未开始。
为什么重要 = 当前页面展示的是已持久化的本地数据，不是模拟结果。
现在可以做什么 = 继续查看本地快照；若演示模式已启用，系统会执行一次有界模拟更新。
```

### `refresh_in_progress`

```text
发生了什么 = 正在执行一次有界的模拟更新演示。
为什么重要 = 原本地快照仍保持可见，只有完整候选通过校验后才会显示演示结果。
现在可以做什么 = 继续查看本地快照，不需要重复提交。
```

### `demo_published`

```text
发生了什么 = 模拟更新流程已完成，并生成一份进程内演示结果。
为什么重要 = 这只证明刷新编排可运行，不代表真实数据源已启用。
现在可以做什么 = 查看模拟来源和覆盖详情，或继续使用本地真实快照。
```

### `failed_retained_prior`

```text
发生了什么 = 模拟候选未通过完整批次校验。
为什么重要 = 未发布部分或不完整结果，原本地快照保持不变。
现在可以做什么 = 查看失败原因，并明确选择是否重新运行模拟演示。
```

### `mock_not_enabled`

```text
发生了什么 = 当前应用进程没有启用模拟更新演示。
为什么重要 = 系统不会隐藏运行模拟数据，也不会把模拟结果当成真实市场数据。
现在可以做什么 = 继续查看本地快照；测试或演示启动器可显式注入 Mock。
```

### `live_source_blocked`

```text
发生了什么 = 真实 THS 数据源尚未达到生产接入条件。
为什么重要 = 配额、完成时间、修订和鉴权合同仍由 Issue #225 控制。
现在可以做什么 = 继续使用本地快照；不能从本页面启用真实数据源。
```

Technical identifiers remain under progressive disclosure.

## 11. API boundary for later implementation

### 11.1 Runtime status read

Candidate route:

```text
GET /today-market/api/runtime-status
```

Inputs are the exact dual-as-of boundaries and explicit series keys used by the snapshot read. The server:

1. validates inputs before constructing database resources;
2. resolves the exact authoritative local snapshot identity/content;
3. derives the exact runtime scope;
4. reads only process-local state matching that scope;
5. returns the complete status and `runtime_status_fingerprint`.

GET performs no acquisition and no database write. Creating an initial in-memory status projection is allowed only as deterministic request-local/coordinator initialization; it does not trigger refresh.

### 11.2 Runtime command

Candidate route:

```text
POST /today-market/api/runtime-refresh
```

Closed request shape:

```text
runtime_scope_version
runtime_scope_revision_id
prior_snapshot_id
prior_snapshot_content_fingerprint
as_of_cutoff
as_of_recorded_at_utc
equity_series_key
benchmark_series_key | null
sector_series_key | null
trigger
source_mode = synthetic_mock
mock_scenario
expected_runtime_status_fingerprint
```

Rules:

- strict unknown-field rejection;
- exact request/server-resolved scope equality;
- only reviewed trigger values;
- only `synthetic_mock` source mode;
- only reviewed `MockScenario` values;
- stale scope/status/prior snapshot rejected under lock before planning;
- no client planning clock;
- no arbitrary URL, headers, queries, capability names or source keys;
- no automatic retry loop;
- no credential or network field.

The response is the complete new runtime status with a new fingerprint.

## 12. UI boundary for later implementation

Existing selection-first flow remains:

```text
set exact dual-as-of boundaries
  -> read local series catalog
  -> explicitly select equity / optional benchmark / optional sector
  -> read and render exact local snapshot
  -> read exact runtime status
```

A separate panel is added only after the persisted snapshot is visible:

```text
模拟更新演示
```

Rules:

1. Persisted local snapshot remains primary page content.
2. Synthetic panel is visibly separate and never labelled as real/latest/live market data.
3. If Mock is enabled and status is eligible/not-attempted, browser sends one automatic first-entry command.
4. Browser keeps a request-local guard against duplicate submission, but server status/single-flight remains authoritative.
5. Failures expose an explicit retry button; no retry loop or polling.
6. Changing boundaries or series immediately invalidates and hides the old candidate.
7. Runtime candidate identity/status fingerprint is never stored in localStorage.
8. Current series-selection storage may remain, but it does not authorize acquisition.
9. Text uses safe text nodes; status does not rely on color alone.
10. Prior snapshot remains visible during `refresh_in_progress`.

No action may imply recommendation, buy, sell, hold, target price, expected return, position sizing, portfolio addition or execution.

## 13. Complete-batch publication

The coordinator calls the accepted Mock acquisition port with one already validated Mock plan.

Existing validation must prove:

- plan and batch fingerprints are valid;
- provenance is explicitly synthetic;
- `provider_confirmed = false`;
- required family identity and ordering are compatible;
- every family is schema-valid;
- coverage is complete;
- covered sessions exactly equal requested sessions;
- no required family is missing;
- every family covers every requested session.

Successful publication is one immutable process-local pointer replacement under the exact coordinator scope. It increments status revision and produces a new status fingerprint.

Any failure produces:

```text
candidate_projection = null
prior_snapshot = unchanged
persisted_write = none
```

A synthetic correction scenario creates a distinct process-local candidate fingerprint and never rewrites persisted local history.

## 14. No-prior and manual-catch-up states

### No prior snapshot

The existing planner's `NOT_INITIALIZED` meaning is preserved. Mock never initializes production local history.

```text
phase = not_initialized
candidate_projection = null
allowed_actions = [view_initialization_explanation]
```

### More than ten missing sessions

```text
phase = manual_catchup_required
planning_or_acquisition_called = false
candidate_projection = null
prior_snapshot = unchanged
```

V1 explains this state but does not split requests, loop automatically or implement historical bulk catch-up.

## 15. Persistence, rollback and shutdown

Selected decision:

```text
schema_migration = none
new_table = none
new_column = none
data_backfill = none
new_market_snapshot_persistence = none
new_runtime_state_persistence = none
browser_runtime_identity_persistence = none
```

Process-local coordinator state owns only:

- current status revision;
- automatic-attempt state;
- active command identity;
- latest successful synthetic candidate;
- latest typed failure.

It does not survive restart. Restart truthfully returns to `runtime_not_started` while persisted local snapshots remain unchanged.

Shutdown before publication produces `cancelled_retained_prior`, clears active ownership and publishes no candidate.

If implementation requires durable attempt history, cross-process coordination or persisted synthetic candidates, it must stop and return for a new architecture review.

## 16. Candidate implementation families

Architecture acceptance may authorize a later separately governed implementation Issue to consider only a frozen subset of:

```text
backend/today_market_refresh/runtime.py
backend/today_market_refresh/runtime_projection.py
backend/today_market_refresh/__init__.py
backend/api/today_market.py
backend/main.py                         # dependency/application-factory wiring only; no startup hook
today_market/static/today_market.html
today_market/static/today_market.js
today_market/static/today_market.css
tests/test_today_market_runtime_*.py
scripts/demo_today_market_runtime_integration.py
.github/workflows/local-tests.yml       # additive offline demo only if required
.codex/tasks/issue-<IMPLEMENTATION>-*.md
```

Explicitly excluded:

```text
datasource/ths_structured_provider/**
backend/database/models.py
migrations/**
Provider transport or credential modules
market_cockpit calculation ownership
Industry Thesis / Evidence / Candidate owners
```

This list authorizes nothing by itself.

## 17. Query, locality and security bounds

Later implementation must preserve:

- one local-series catalog request when user asks;
- one exact snapshot request;
- at most one status request per eligible scope load;
- one automatic command per eligible Mock-enabled scope generation;
- one explicit command per user retry;
- zero per-family or per-row browser requests;
- no polling/background status loop;
- one bounded revalidation read before command acquisition.

Security properties:

- same-origin local API only;
- strict closed schemas and unknown-field rejection;
- no arbitrary redirect, URL, header or query construction;
- no HTML injection;
- no credential/token/Cookie/API key/account ID;
- no environment-secret read;
- no HTTP, DNS, socket, subprocess, browser automation or Provider SDK path in Mock mode;
- no external AI or remote transmission;
- redacted typed diagnostics only.

## 18. Required later executable validation

### Exact snapshot identity

- identical authoritative reads produce identical snapshot ID/content fingerprint;
- changed selected run, content, boundary or series changes the exact identity/fingerprint;
- ambiguous/non-unique component resolution fails closed;
- GET and POST rebuild through the same authoritative path;
- stale or moved prior snapshot produces zero acquisition.

### Status fingerprint

- every GET/POST returns a valid server-owned status fingerprint;
- localized copy changes do not change fingerprint;
- identity/phase/candidate/failure/action changes do change fingerprint;
- stale expected fingerprint returns conflict and zero planning/acquisition;
- simultaneous commands using the same fingerprint create one acquisition only.

### Trigger and single-flight

- import/startup/raw page load performs no refresh;
- first eligible Mock-enabled scope automatically submits exactly one command;
- Mock-disabled scope submits none;
- automatic command uses `FIRST_TODAY_MARKET_ENTRY`;
- explicit retry uses `EXPLICIT_USER_RETRY` and a newer status fingerprint;
- same scope has one server-owned planning clock;
- repeated rendering/navigation does not create a second automatic attempt;
- process restart drops runtime state without changing persisted data.

### Golden/failure paths

- no-refresh-needed;
- one-session and ten-session complete synthetic refresh;
- valid synthetic correction;
- no prior snapshot;
- more than ten missing sessions;
- Mock not enabled;
- live source requested while #225 open;
- assumption budget exhausted;
- partial family failure;
- schema mismatch;
- incomplete coverage;
- invalid fingerprint;
- shutdown before publication;
- database unavailable;
- stale scope/status/prior snapshot.

Every failure proves zero partial publication and retained prior snapshot where one exists.

### Zero-network and boundaries

- import, startup, page load, status read, command, tests and demo remain zero-network;
- forbidden transport imports/calls are denied;
- sentinel credentials never appear;
- no schema, migration or database write;
- no Provider readiness mutation;
- no research, recommendation, portfolio or trading mutation;
- full pytest and configured offline demos remain green.

## 19. Stop conditions

Stop and return for explicit project-owner review if later design or implementation requires:

- FastAPI startup refresh side effects;
- raw page-load acquisition before exact scope;
- hidden source or series selection;
- client-supplied planning clock;
- identity inferred from labels/presentation JSON;
- non-unique or fuzzy snapshot selection;
- live THS, credentials or network;
- weakening Issue #225;
- treating Mock assumptions as Provider facts;
- current Mock plan used as a live production plan;
- arbitrary adapter discovery, fallback or source mixing;
- source-specific validation inside runtime coordinator;
- schema, migration or durable runtime state;
- synthetic result persisted as real local data;
- background task, daemon, scheduler, polling or work after close;
- partial publication;
- automatic retry/catch-up loop;
- mandatory raw identifiers as ordinary-user inputs;
- AI-owned state, evidence acceptance, recommendation, target price, expected return, position sizing, portfolio, broker, order or trading behavior;
- release, tag or version change.

## 20. Locked exclusions

This architecture preflight authorizes no production code, API route, UI change, executable test, fixture, workflow, dependency, schema, migration, persistence, Provider transport, credential, source activation, scheduler, daemon, push notification, continuous polling, AI call, accepted-state mutation, recommendation, portfolio, trading, release, tag or version change.

## 21. Strict delivery gates

Before architecture merge consideration:

1. Branch base remains exactly `1b2de3544844647ad02beffe2e6a8e14c467fd98`.
2. Base-to-head diff contains exactly:

```text
.codex/tasks/issue-259-today-market-refresh-runtime-integration-v1-preflight.md
docs/today_market_refresh_runtime_integration_v1_preflight.md
```

3. Applicable repository CI succeeds on one immutable HEAD.
4. A fresh process-independent review verifies all five previous blockers and contains exactly:

```text
AUTHORIZED TODAY MARKET REFRESH RUNTIME INTEGRATION V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

5. Every review thread is resolved.
6. The project owner separately and explicitly authorizes merge.
7. Any new commit invalidates previous exact-head CI and review evidence.

Architecture merge will not authorize implementation. A later implementation requires its own bounded Strict Issue, branch, Draft PR, exact-head CI/review and separate merge authorization.
