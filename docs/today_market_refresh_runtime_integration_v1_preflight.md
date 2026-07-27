# Today Market Refresh Runtime Integration v1 — Architecture Preflight

## 1. Status, authority and exact base

This document defines the bounded architecture for Issue #259.

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

## 2. Architecture outcome

The selected v1 boundary is:

```text
first eligible /today-market interaction
  -> exact local boundaries and explicit local series are selected
  -> prior complete local snapshot is read and rendered
  -> user explicitly enables the synthetic Mock demonstration
  -> one synchronous, bounded, process-local refresh attempt runs
  -> one complete synthetic candidate projection is validated
  -> the candidate is exposed in a separate synthetic runtime panel
  -> the persisted local snapshot remains authoritative and unchanged
```

The following alternatives are rejected for v1:

```text
FastAPI application-start refresh                  = rejected
raw route-load refresh before exact scope exists   = rejected
hidden automatic source selection                  = rejected
Mock as default source                             = rejected
Mock result persisted as local market history      = rejected
background task / scheduler / continuous polling   = rejected
live THS adapter                                   = blocked by Issue #225
```

The v1 architecture is therefore a **runtime integration proof over the accepted Mock**, not a claim that ordinary production market data is automatically refreshed.

## 3. Why first eligible page interaction is selected

The current application has no accepted startup lifecycle owner for Today Market refresh. `backend/main.py` mounts static pages and routers without a startup refresh hook. Adding hidden application-start work would:

- affect unrelated modules before a Today Market scope exists;
- require selecting or inferring a local market scope;
- create new lifecycle and shutdown ownership;
- risk database or network side effects during import/startup;
- weaken the current zero-side-effect application startup contract.

The current Today Market surface also requires:

- an explicit information cutoff;
- an explicit recorded-at boundary;
- an explicit local equity series;
- optional explicit benchmark and sector series.

The catalog response explicitly reports `auto_selected = false`. Runtime integration must preserve that meaning.

For v1, “first entry” means the first **eligible scoped interaction** after the current page has successfully loaded one exact prior local snapshot. Merely requesting `/today-market` does not trigger acquisition.

The existing `RefreshTrigger.APPLICATION_START` enum remains reserved for a later separately reviewed architecture. V1 uses:

```text
RefreshTrigger.FIRST_TODAY_MARKET_ENTRY
RefreshTrigger.EXPLICIT_USER_RETRY
RefreshTrigger.EXPLICIT_MANUAL_CATCHUP
```

`FIRST_TODAY_MARKET_ENTRY` is emitted only after exact scope and prior-snapshot identity are server-validated.

## 4. Existing contracts reused without redefinition

Runtime Integration v1 composes the accepted package:

```text
backend.today_market_refresh
```

It reuses, rather than duplicates:

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

The existing planner already freezes:

- one exact scope revision;
- one exact prior snapshot identity;
- requested completed sessions;
- one closed capability set;
- one planning policy version;
- one synthetic assumption profile;
- canonical plan and attempt fingerprints;
- a maximum automatic gap of ten completed sessions.

The existing orchestrator already provides:

- no-refresh-needed;
- manual-catch-up-required;
- not-initialized;
- complete synthetic publication;
- failure with retained prior snapshot;
- shutdown cancellation with retained prior snapshot.

Runtime Integration must not create a second planner, validator or source-specific schema owner.

## 5. Product and truth boundary

Three meanings remain strictly separate.

### 5.1 Persisted local market snapshot

```text
owner = existing IngestionRun / market_cockpit repositories
source = existing explicitly selected local series
persistence = existing database only
ordinary meaning = local historical market snapshot
```

This remains the authoritative content shown by the existing Today Market snapshot page.

### 5.2 Synthetic runtime candidate

```text
owner = process-local Today Market runtime coordinator
source_key = aquantai-synthetic-today-market-v1
source_mode = synthetic_mock
is_synthetic = true
persistence = none
ordinary meaning = refresh-flow demonstration only
```

It may be displayed only in a separately labelled section such as:

```text
模拟更新演示
```

It must never be labelled “最新市场数据”, “实时数据”, “今日真实行情” or any equivalent production claim.

### 5.3 Future live Provider candidate

```text
owner = future source-specific application adapter
source contract owner = datasource.ths_structured_provider
transport = prohibited in v1
readiness = blocked by Issue #225
overall_live_gate = blocked_quota_contract
```

Runtime Integration v1 includes no live adapter, no credential profile and no network path.

## 6. Exact runtime scope

A runtime attempt requires one immutable `TodayMarketRuntimeScope` projection. It is presentation/application-owned and is not persisted.

Candidate fields:

```text
runtime_scope_version
scope_revision_id
as_of_cutoff
as_of_recorded_at_utc
equity_series_key
benchmark_series_key | null
sector_series_key | null
prior_snapshot_id
prior_snapshot_data_through_session
prior_snapshot_content_fingerprint
required_capability_set
planning_policy_version
```

Rules:

1. All fields are derived from one successful server-side exact local snapshot read.
2. The browser never constructs `scope_revision_id`, `prior_snapshot_id` or the snapshot fingerprint from labels.
3. Series keys and both as-of boundaries are revalidated server-side on every runtime request.
4. Changing any boundary or series invalidates the current runtime scope and any candidate projection.
5. No latest-compatible, first-visible or fuzzy scope fallback is permitted.
6. The scope revision fingerprint is canonical over all identity-bearing fields.

The exact projection mechanism may reuse existing snapshot technical details or add one bounded server-owned runtime-scope projection in a later implementation. If the current snapshot response cannot supply an exact scope without adding a new persisted owner, implementation must stop and return to architecture review.

## 7. Explicit Mock enablement

Mock execution is disabled by default.

A later implementation may expose one explicit ordinary-user action:

```text
运行模拟更新演示
```

This action is available only when a non-secret server-side dependency explicitly enables the deterministic Mock port for the current process. The accepted mechanism is dependency injection or an application factory parameter used by tests/demo launchers.

V1 does not authorize:

- an environment-secret lookup;
- a credential lookup;
- a persistent user setting;
- a browser local-storage source mode;
- an arbitrary adapter name from the client;
- activation of `SOURCE_SPECIFIC_LIVE`.

The write request may contain only the closed source mode:

```text
synthetic_mock
```

The server rejects every other mode. The future live mode remains absent rather than disabled by a client-visible switch.

## 8. Runtime coordinator ownership

A later implementation may add one bounded process-local coordinator with the following ownership only:

```text
active single-flight attempt identity
latest immutable process-local runtime status
latest successful synthetic candidate projection
latest typed failure for the same runtime scope
```

It does not own:

- persisted market history;
- Provider observations;
- source readiness;
- trading calendar truth;
- accepted research state;
- recommendation or portfolio state.

The coordinator state is ephemeral:

```text
schema_migration = none
database_write = none
browser_persisted_runtime_state = none
survives_process_restart = false
```

Process restart truthfully returns to `runtime_not_started` while the persisted prior local snapshot remains available.

## 9. Single-flight and concurrency contract

The single-flight key is canonical over:

```text
scope_revision_id
prior_snapshot_id
planning_policy_version
source_mode
mock_scenario
```

Rules:

1. At most one active attempt exists for one exact key in one application process.
2. The attempt itself runs synchronously inside the explicit request boundary; no detached background task is created.
3. A simultaneous identical request receives the current immutable status or a stable `runtime_attempt_already_active` conflict; it does not start a second acquisition.
4. An identical completed request may return the same exact process-local outcome and fingerprints.
5. A changed scope, prior snapshot, scenario or planning time creates a different attempt identity.
6. A request with a stale prior snapshot fails before acquisition.
7. Application shutdown is observed through the existing shutdown callback before publication.
8. No lock or attempt remains authoritative after process restart.

The coordinator must not use a global “latest result” without an exact scope key.

## 10. Runtime state model

The runtime projection composes existing planning/orchestration states instead of replacing them.

A closed `TodayMarketRuntimeStatus` candidate contains:

```text
runtime_status_version
runtime_scope
phase
prior_snapshot_state
refresh_state
source_mode
source_label
is_synthetic
active_attempt_id | null
plan_fingerprint | null
candidate_projection | null
failure | null
state_explanation
allowed_actions
technical_details
```

Closed `phase` values:

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

The runtime adapter maps from existing `PlanningState`, `OrchestrationState`, failure category and local-snapshot read result. It must not invent success when the existing outcome is blocked or failed.

## 11. Ordinary-Chinese state contract

Every runtime status provides exactly:

```text
发生了什么
为什么重要
现在可以做什么
```

Minimum stable mappings:

### `prior_snapshot_ready`

```text
发生了什么 = 已读取明确选择的本地完整快照，尚未运行模拟更新。
为什么重要 = 当前页面展示的仍是已持久化的本地数据，不是模拟结果。
现在可以做什么 = 可以查看本地快照，或在明确启用时运行模拟更新演示。
```

### `no_refresh_needed`

```text
发生了什么 = 按当前模拟交易日场景，本地快照不需要补充会话。
为什么重要 = 系统没有创建不必要的候选更新。
现在可以做什么 = 继续查看本地快照，或更换明确的数据边界。
```

### `demo_published`

```text
发生了什么 = 模拟更新流程已完成，并生成一份进程内演示结果。
为什么重要 = 这只证明刷新编排可运行，不代表真实数据源已启用。
现在可以做什么 = 查看模拟来源和覆盖详情，或返回本地真实快照。
```

### `failed_retained_prior`

```text
发生了什么 = 模拟候选未通过完整批次校验。
为什么重要 = 未发布部分或不完整结果，原本地快照保持不变。
现在可以做什么 = 查看失败原因，并明确选择是否重试演示。
```

### `live_source_blocked`

```text
发生了什么 = 真实 THS 数据源尚未达到生产接入条件。
为什么重要 = 配额、完成时间、修订和鉴权合同仍由 Issue #225 控制。
现在可以做什么 = 继续使用本地快照；不能从本页面启用真实数据源。
```

Warnings and failures must remain warnings and failures. Technical identifiers, fingerprints, source contracts and chronology remain under progressive disclosure.

## 12. API boundary for a later implementation

A later separately authorized implementation may add exactly two bounded API responsibilities.

### 12.1 Runtime status read

Candidate route:

```text
GET /today-market/api/runtime-status
```

Required exact inputs are the same boundaries and explicit series keys used by the local snapshot read. The server:

1. validates all inputs before constructing database resources;
2. resolves the exact visible local snapshot;
3. derives the exact runtime scope;
4. reads only matching process-local runtime state;
5. returns a deterministic `TodayMarketRuntimeStatus`.

This GET performs no acquisition and no write.

### 12.2 Explicit Mock runtime command

Candidate route:

```text
POST /today-market/api/runtime-refresh
```

Closed request shape:

```text
runtime_scope_version
scope_revision_id
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
- route/body and server-resolved scope equality;
- only closed trigger values;
- only `synthetic_mock` source mode;
- only reviewed `MockScenario` values;
- stale scope or moved prior snapshot returns conflict before planning;
- no arbitrary URL, headers, queries, capability names or source keys;
- no automatic retry;
- no credential or network field.

The response is the complete runtime status and is sufficient for first render. No per-family browser requests are permitted.

## 13. UI boundary for a later implementation

The existing selection-first Today Market flow remains unchanged:

```text
set exact dual-as-of boundaries
  -> read local series catalog
  -> explicitly select equity / optional benchmark / optional sector
  -> read and render exact local snapshot
```

Runtime Integration may add one secondary synthetic panel after the persisted snapshot is visible.

Required hierarchy:

1. persisted local snapshot remains the primary page content;
2. synthetic runtime status is visually separated and labelled `模拟更新演示`;
3. one dominant action exists inside the synthetic panel for its current state;
4. the panel never hides scope/freshness warnings from the persisted snapshot;
5. changing boundaries or selection immediately invalidates and hides the old runtime candidate;
6. runtime candidate identity is never stored in localStorage;
7. current selection storage may remain unchanged, but it does not authorize acquisition;
8. all text rendering uses safe text nodes;
9. status is distinguishable without color alone;
10. keyboard focus moves to the status/error summary after an explicit command.

Candidate primary actions by state:

```text
prior_snapshot_ready       -> 运行模拟更新演示
failed_retained_prior      -> 重新运行模拟演示
manual_catchup_required    -> 查看手动补齐说明
not_initialized            -> 查看初始化说明
demo_published             -> 查看模拟结果详情
live_source_blocked        -> 查看真实数据源限制
```

No action may imply recommendation, buy, sell, hold, target price, expected return, position sizing, portfolio addition or execution.

## 14. Complete-batch publication boundary

The runtime coordinator calls the accepted `TodayMarketAcquisitionPort` with one already validated plan.

Before exposing a candidate, the existing validator must prove:

- plan and batch fingerprints are valid;
- source provenance is explicitly synthetic;
- `provider_confirmed = false`;
- required family identity and ordering are compatible;
- every family is schema-valid;
- coverage status is complete;
- covered sessions exactly equal requested sessions;
- no required family is missing;
- every family covers every requested session.

Publication is one immutable in-memory pointer replacement under the exact single-flight key. The operation is atomic at the coordinator boundary.

Any failure produces:

```text
candidate_projection = null
prior_snapshot = unchanged
persisted_write = none
```

A synthetic correction scenario creates a distinct fingerprinted process-local candidate. It never rewrites persisted local history.

## 15. No-prior-snapshot behavior

The existing planner returns `NOT_INITIALIZED` when no prior snapshot exists. V1 preserves that state.

Runtime Integration v1 does not fabricate an empty prior snapshot and does not use the Mock to initialize production local market history.

Required result:

```text
phase = not_initialized
candidate_projection = null
allowed_actions = [view_initialization_explanation]
```

A future initialization workflow requires a separate architecture decision and, if persistent, separate migration/persistence authorization.

## 16. Manual catch-up behavior

The automatic session ceiling remains exactly ten completed sessions.

When the missing session count exceeds ten:

```text
phase = manual_catchup_required
acquisition_called = false
candidate_projection = null
prior_snapshot = unchanged
```

The v1 page may explain the state but must not implement historical bulk catch-up, split the request silently or loop automatically.

## 17. Future THS insertion point

The future architecture remains:

```text
Today Market runtime coordinator
  -> TodayMarketAcquisitionPort
      -> future THS application adapter
          -> datasource.ths_structured_provider contracts/readiness
          -> future reviewed transport
```

The future adapter must consume existing source-specific contracts. Runtime Integration may not own or duplicate:

- THS host, endpoint or selector rules;
- account entitlement;
- QPS, daily quota or concurrency;
- dataset completion time;
- correction, revision or late-data behavior;
- API-key lifecycle;
- authentication or credential redaction;
- Provider-valued fixture permission.

Until Issue #225 is closed by reviewed evidence:

```text
SOURCE_SPECIFIC_LIVE request = rejected
live adapter construction = absent
credential lookup = absent
network transport = absent
```

Mock success cannot change this result.

## 18. Migration, persistence, rollback and downgrade

Selected v1 decision:

```text
schema_migration = none
new_table = none
new_column = none
data_backfill = none
new_market_snapshot_persistence = none
new_runtime_state_persistence = none
browser_runtime_identity_persistence = none
```

Rollback for a later implementation is a code/static/test/demo revert. Existing local market data is untouched.

Process-local synthetic runtime state is discarded on restart and has no downgrade data-loss concern.

If implementation discovers that truthful runtime status requires durable attempt history, cross-process coordination or persisted synthetic candidates, it must stop and return for a new architecture review. Such persistence is not authorized by this v1 contract.

## 19. Candidate implementation file families

Architecture acceptance may authorize a later separately governed implementation Issue to consider only bounded changes in:

```text
backend/today_market_refresh/runtime.py                 # new process-local coordinator
backend/today_market_refresh/runtime_projection.py      # stable runtime/Chinese projection
backend/today_market_refresh/__init__.py                # bounded exports
backend/api/today_market.py                             # bounded status/command adapter
backend/main.py                                         # router/dependency wiring only; no startup hook
today_market/static/today_market.html                   # separate synthetic panel
today_market/static/today_market.js                     # explicit command and exact invalidation
today_market/static/today_market.css                    # bounded presentation/accessibility
tests/test_today_market_runtime_*.py
scripts/demo_today_market_runtime_integration.py
.github/workflows/local-tests.yml                        # additive offline demo only if required
.codex/tasks/issue-<IMPLEMENTATION>-*.md
```

The later implementation Issue must re-read the repository and freeze an exact subset. This list authorizes nothing by itself.

Explicitly excluded implementation families:

```text
datasource/ths_structured_provider/**
backend/database/models.py
migrations/**
Provider transport or credential modules
market_cockpit calculation ownership
Industry Thesis / Evidence / Candidate owners
```

## 20. Query and performance boundaries

A later implementation must preserve bounded operations:

- one existing local-series catalog request when the user asks for it;
- one existing exact snapshot request;
- at most one runtime-status request per eligible scope load;
- one explicit runtime-refresh request per user action;
- zero per-family browser requests;
- zero per-row runtime API requests;
- no polling loop;
- no background refresh status requests;
- no additional database statements after a validated exact local snapshot is already available unless the adapter must revalidate that same exact scope before the command.

The server must revalidate the prior snapshot before acquisition even when this adds one bounded read. Correctness takes priority over trusting browser state.

## 21. Security and locality

Required properties:

- same-origin local API only;
- strict request schemas and unknown-field rejection;
- no arbitrary redirect or external origin;
- no URL/header/query construction from free text;
- no HTML injection;
- no credential, token, Cookie, API key, account ID or request ID;
- no environment-secret read;
- no HTTP, DNS, socket, subprocess, browser automation or Provider SDK path in Mock mode;
- no external AI or remote transmission;
- redacted typed diagnostics only;
- runtime fingerprints and technical details are read-only.

## 22. Required executable validation for a later implementation

### 22.1 Exact scope and trigger

- raw `/today-market` page request performs no refresh;
- FastAPI import/startup performs no refresh;
- no eligible scope exists before explicit boundaries, series and prior snapshot;
- first eligible scoped interaction uses `FIRST_TODAY_MARKET_ENTRY`;
- explicit retry uses `EXPLICIT_USER_RETRY`;
- changed boundary or selection invalidates old runtime state;
- no automatic source selection.

### 22.2 Single-flight and idempotency

- two identical simultaneous commands create one acquisition call;
- duplicate active request gets a stable conflict/current status;
- identical completed replay returns the same process-local outcome;
- stale prior snapshot is rejected before acquisition;
- changed scenario produces a distinct fingerprint;
- restart drops runtime state without changing persisted local data.

### 22.3 Golden paths

- prior snapshot current / no refresh needed;
- one-session complete synthetic refresh;
- ten-session complete synthetic refresh;
- valid synthetic correction revision;
- explicit demo publication remains separate from persisted local snapshot.

### 22.4 Failure paths

- no prior snapshot;
- more than ten missing sessions;
- Mock not enabled;
- live source requested while #225 remains open;
- assumption budget exhausted;
- concurrency conflict;
- partial family failure;
- schema mismatch;
- incomplete coverage;
- invalid fingerprint;
- shutdown before publication;
- database unavailable;
- stale scope conflict.

Every failure must prove zero partial publication and retained prior snapshot where one exists.

### 22.5 Zero-network and scope safety

- import, FastAPI startup, page load, status read, command, tests and demo remain zero-network;
- forbidden transport imports and calls are denied;
- sentinel credentials never appear in request, response, log or failure details;
- no schema, migration or database write;
- no Provider readiness mutation;
- no accepted research, recommendation, portfolio or trading mutation;
- full repository pytest and every configured offline demo remain green.

## 23. Production-realistic offline golden path

```text
1. One exact persisted local snapshot is visible under explicit dual-as-of boundaries.
2. The browser renders that snapshot before any runtime command.
3. The user explicitly chooses “运行模拟更新演示”.
4. The server revalidates exact scope and prior snapshot fingerprint.
5. The injected completed-session sequence identifies one missing session.
6. The accepted planner creates one exact bounded plan.
7. The explicitly injected Mock port returns one complete synthetic batch.
8. Existing validation accepts all required families and coverage.
9. The coordinator atomically exposes one process-local synthetic projection.
10. The page renders it in a separate “模拟更新演示” panel.
11. The persisted local snapshot remains visible and unchanged.
12. The technical details show synthetic source, plan/batch/projection fingerprints and blocked live gate.
13. No database write, credential, network, Provider readiness, research, recommendation, portfolio or trading state changes.
```

## 24. Primary failure path

```text
1. One exact persisted local snapshot is visible.
2. The user explicitly runs the Mock demonstration.
3. The Mock returns one required family as partial, schema-invalid or coverage-incomplete.
4. Existing validation rejects the entire candidate.
5. The process-local candidate pointer is not replaced.
6. The persisted local snapshot remains visible.
7. The page shows a stable Chinese failure reason and one explicit retry action.
8. No partial result, database write, source fallback or hidden retry occurs.
```

Shutdown before publication follows the same no-publication outcome.

## 25. Stop conditions

Stop and return for explicit project-owner review if a later design or implementation requires:

- FastAPI startup side effects;
- a raw page-load acquisition before exact scope selection;
- hidden source or series selection;
- live THS, credentials or network;
- weakening Issue #225;
- treating Mock assumptions as Provider facts;
- arbitrary adapter discovery or source fallback;
- cross-Provider row mixing;
- source-specific validation inside the runtime coordinator;
- schema, migration, database table/column or durable runtime state;
- synthetic result persisted as real local market data;
- background task, daemon, scheduler, polling or work after application close;
- partial publication;
- automatic retry or catch-up loop;
- latest-compatible or fuzzy snapshot selection;
- mandatory raw identifiers as ordinary-user inputs;
- AI-owned state, evidence acceptance, recommendation, target price, expected return, position sizing, portfolio, broker, order or trading behavior;
- release, tag or version change.

## 26. Locked exclusions

This architecture preflight authorizes no production code, API route, UI change, test, fixture, workflow, dependency, schema, migration, persistence, Provider transport, credential, source activation, scheduler, daemon, push notification, continuous polling, AI call, accepted-state mutation, recommendation, portfolio, trading, release, tag or version change.

## 27. Strict delivery gates

Before architecture merge consideration:

1. Branch base is exactly `1b2de3544844647ad02beffe2e6a8e14c467fd98`.
2. Base-to-head diff contains exactly:

```text
.codex/tasks/issue-259-today-market-refresh-runtime-integration-v1-preflight.md
docs/today_market_refresh_runtime_integration_v1_preflight.md
```

3. Applicable repository CI succeeds on one immutable HEAD.
4. A fresh process-independent fixed-head review contains exactly:

```text
AUTHORIZED TODAY MARKET REFRESH RUNTIME INTEGRATION V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

5. Every review thread is resolved.
6. The project owner separately and explicitly authorizes merge.
7. Any new commit invalidates previous exact-head CI and review evidence.

Architecture merge will not authorize implementation. A later implementation requires its own bounded Strict Issue, branch, Draft PR, exact-head CI/review and separate merge authorization.
