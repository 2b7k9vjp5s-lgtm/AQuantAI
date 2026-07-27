# Today Market Refresh Runtime Integration v1 — Architecture Preflight

## 1. Status, authority and exact base

This document defines the bounded architecture for Issue #259. It preserves the five resolutions required by fixed-head review `4786108502` and resolves the two additional blockers recorded by fixed-head review `4786209951`.

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
base_sha = 1b2de3544844647ad02beffe2e6a8e14c467fd98
released_version = 0.2.0
risk_tier = Strict Architecture Preflight
```

Project-owner authority permits only this architecture preflight, its existing architecture branch and Draft PR #260. It does not authorize production implementation, live THS access, credentials, network, schema, migration, persistence, scheduler, recommendation, portfolio, trading, release, tag or version change.

Controlling authorities remain:

- Product Roadmap Issue #137;
- live THS external-contract gate Issue #225;
- current-state baseline Issue #257 / merged PR #258;
- Today Market automatic-refresh architecture Issue #221 / merged PR #222;
- THS synchronization architecture Issue #223 / merged PR #224;
- THS Stage C0 architecture/implementation #227/#229 and #230/#231;
- public full-market snapshot and Market Dump evidence #251/#252;
- provider-neutral acquisition-port architecture #253/#254;
- deterministic zero-network Mock implementation #255/#256.

PR #241 remains closed, unmerged and read-only at exact HEAD `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

## 2. Selected v1 outcome

```text
FastAPI import/startup
  -> no refresh and no runtime side effect
raw GET /today-market
  -> static page only; no acquisition
explicit dual-as-of boundaries + explicit local series
  -> server reads one exact prior local snapshot
  -> page renders the prior snapshot first
  -> server returns one exact runtime scope/status/fingerprint
server-side demo factory explicitly injects Mock enabled + one reviewed scenario
  -> browser automatically submits one first-eligible-scope command
  -> one synchronous bounded process-local Mock attempt runs
  -> one complete synthetic candidate is validated
  -> one separate synthetic runtime projection is exposed
failure, stale state or shutdown
  -> no partial publication; prior persisted snapshot remains authoritative
```

Mock is disabled by default. A disabled process has no implicit scenario. A test/demo application factory may explicitly inject exactly one reviewed scenario for the lifetime of that application instance.

Rejected alternatives:

```text
FastAPI application-start refresh                  = rejected
raw page-load acquisition before exact scope       = rejected
hidden local-series selection                      = rejected
client-selected Mock scenario                      = rejected
implicit default Mock scenario                     = rejected
Mock as default production source                  = rejected
Mock result persisted as local market history      = rejected
background task / scheduler / polling              = rejected
live THS adapter in v1                              = blocked by Issue #225
```

## 3. Existing contracts reused without weakening

V1 composes the accepted `backend.today_market_refresh` package and reuses:

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

Every eligible runtime scope is created through the same server-owned path used to build the visible Today Market snapshot:

1. validate `as_of_cutoff` and `as_of_recorded_at_utc`;
2. validate exact equity series key and optional benchmark/sector series keys;
3. invoke the existing Market Cockpit repositories and service under those same boundaries;
4. for each selected family, resolve the exact successful complete `IngestionRun` selected by the existing repository order:

```text
information_cutoff_date DESC
completed_at DESC
id DESC
LIMIT 1
```

5. require the projected provenance/run identity to match the component actually consumed by the service;
6. build snapshot identity and content fingerprint from those exact results.

The implementation may add one bounded read-only provenance projection from existing repository/service results. It may not create a new persisted owner, select a maximum-coverage context, perform fuzzy/latest-compatible selection outside the accepted repository order, or infer identity from browser labels.

If a selected component is absent, no longer visible, internally inconsistent, or disagrees with the service result, runtime scope creation fails closed.

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

Canonicalization rules:

- dates use ISO `YYYY-MM-DD`;
- timestamps are normalized to UTC with `Z`;
- mapping keys are sorted;
- canonical series identities use existing validators;
- tuple/list ordering is explicit and stable;
- localized labels, UI copy, database connection details and browser state are excluded.

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

```text
prior_snapshot_content_fingerprint = canonical_sha256(content_payload)
```

The domain snapshot is taken before Today Market presentation copy is added. Warnings and set-like values are canonically sorted; nulls are preserved; floats, dates and timestamps use the repository's canonical serializer. Raw presentation JSON, HTML, localized prose, `allowed_actions` and progressive-disclosure wrappers are excluded.

### 4.4 Moved or stale prior snapshot

GET status and POST command independently repeat the same authoritative read path. Before planning or acquisition, POST compares the server-rebuilt:

```text
prior_snapshot_id
prior_snapshot_content_fingerprint
runtime_scope_revision_id
```

with the submitted status generation. Any mismatch returns `runtime_scope_stale` or `runtime_prior_snapshot_moved` with:

```text
planning_called = false
acquisition_called = false
candidate_changed = false
```

## 5. Server-owned Mock configuration

### 5.1 Unique owner

The application factory is the only owner of Mock configuration.

```text
TodayMarketMockRuntimeConfigurationV1 = {
  configuration_version,
  mock_enabled,
  mock_scenario_id | null
}
```

Rules:

1. Production/default application construction sets `mock_enabled = false` and `mock_scenario_id = null`.
2. A test/demo factory may set `mock_enabled = true` and inject exactly one reviewed `MockScenario` identity.
3. The browser, query string, route parameters, request body, localStorage and cookies cannot select or change the scenario.
4. GET and POST read the same immutable application-instance configuration dependency.
5. No arbitrary adapter name, scenario string, fixture path, URL, header or query dictionary is accepted.
6. Replacing the server configuration requires a new application instance and creates a different runtime scope/status identity.

### 5.2 No implicit scenario

When `mock_enabled = false`:

```text
mock_scenario_id = null
phase = mock_not_enabled
acquisition_called = false
```

There is no default, fallback or first-available scenario.

## 6. Runtime scope contract

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
mock_configuration_version
mock_enabled
mock_scenario_id | null
runtime_scope_revision_id
```

Rules:

1. All snapshot identity-bearing values come from one successful authoritative read.
2. Mock configuration values come only from the immutable application-factory dependency.
3. The browser never constructs IDs or fingerprints from labels or raw JSON.
4. Changing either boundary, any series, snapshot component or server Mock configuration invalidates the scope.
5. No fuzzy, first-visible, maximum-coverage or latest-compatible fallback is allowed.
6. `planning_recorded_at_utc` is not a client field; it equals normalized `as_of_recorded_at_utc`.
7. `runtime_scope_revision_id` is the sole authoritative runtime-scope identifier.
8. `runtime_scope_revision_id` is canonical SHA-256 over every preceding field in this closed scope payload.

The name `runtime_scope_fingerprint` is not part of the v1 contract. If a later presentation adapter requires that display alias, it must be a literal alias only:

```text
runtime_scope_fingerprint = runtime_scope_revision_id
```

It may not have a separate payload, version, calculation or comparison path.

Any request or process-local state containing a scope identifier that differs from the server-rebuilt `runtime_scope_revision_id` fails before planning and acquisition.

## 7. Runtime status and optimistic-concurrency fingerprint

### 7.1 Closed DTO

Every status response contains:

```text
runtime_status_version = aquantai.today-market-runtime-status.v1
runtime_scope
runtime_scope_revision_id
runtime_status_revision
phase
prior_snapshot_state
refresh_state
source_mode
source_label
is_synthetic
mock_enabled
mock_scenario_id | null
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

`runtime_status_revision` is a process-local monotonically increasing integer per `runtime_scope_revision_id`. It starts at zero after process restart and increments for every accepted state transition.

### 7.2 Canonical status fingerprint

```text
runtime_status_fingerprint = canonical_sha256({
  runtime_status_version,
  runtime_scope_revision_id,
  runtime_status_revision,
  phase,
  prior_snapshot_state,
  refresh_state,
  source_mode,
  is_synthetic,
  mock_enabled,
  mock_scenario_id,
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

GET and POST return this field. The browser treats it as opaque and never recalculates it.

### 7.3 POST comparison point

`POST /today-market/api/runtime-refresh` requires `expected_runtime_status_fingerprint`.

Under the coordinator lock, before building an intent, plan or calling an acquisition port, the server:

1. re-resolves the authoritative prior snapshot;
2. reads the immutable server Mock configuration;
3. rebuilds `runtime_scope_revision_id`;
4. verifies the submitted scope fields equal the rebuilt scope;
5. reads current process-local state for that exact scope;
6. rebuilds the current status fingerprint;
7. compares it byte-for-byte with the expected fingerprint.

Mismatch returns HTTP 409 `runtime_status_conflict`, the current complete status, and zero planning/acquisition/candidate change.

## 8. Trigger and bounded automatic attempt

### 8.1 No startup or raw-load side effect

- importing or starting FastAPI performs no refresh;
- requesting `/today-market` performs no acquisition;
- unrelated routes are never blocked by Today Market runtime work.

### 8.2 First eligible scoped interaction

After the user explicitly selects boundaries and series and the page renders one exact prior snapshot:

1. browser calls `GET /today-market/api/runtime-status`;
2. server returns exact scope, server-owned Mock configuration identity, phase and status fingerprint;
3. if `mock_enabled = true` and `automatic_attempt_state = not_attempted`, browser automatically submits exactly one POST;
4. POST trigger is `FIRST_TODAY_MARKET_ENTRY`;
5. request runs synchronously and is bounded by the existing ten-session ceiling;
6. prior snapshot remains visible during the command;
7. no second automatic command occurs for the same `runtime_scope_revision_id` generation.

If Mock is disabled, GET returns `mock_not_enabled`; no POST is sent automatically.

### 8.3 Explicit retry

A failed/cancelled status may expose `重新运行模拟演示`. That command uses `EXPLICIT_USER_RETRY` and the newest server-returned status fingerprint. It is not an automatic retry loop.

`EXPLICIT_MANUAL_CATCHUP` remains named but v1 does not implement historical bulk catch-up.

## 9. API boundary for later implementation

### 9.1 Runtime status read

Candidate route:

```text
GET /today-market/api/runtime-status
```

Inputs are only the exact dual-as-of boundaries and explicit series keys used by the snapshot read. The server resolves snapshot identity, immutable Mock configuration, exact runtime scope and matching process-local state, then returns the complete status.

GET performs no acquisition and no database write.

### 9.2 Runtime command

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
expected_runtime_status_fingerprint
```

The request does **not** contain:

```text
mock_scenario
mock_scenario_id
mock_enabled
source_mode
adapter_name
fixture_path
planning_clock
```

Rules:

- strict unknown-field rejection;
- exact request/server-rebuilt scope equality;
- only reviewed trigger values;
- client-submitted scenario/configuration fields are rejected as unknown;
- stale scope/status/prior snapshot or server configuration mismatch is rejected under lock before planning;
- no arbitrary URL, headers, queries, capability names or source keys;
- no automatic retry loop;
- no credential or network field.

The server derives source mode and scenario only from the application configuration and returns the complete new runtime status with a new fingerprint.

## 10. Single-flight, command identity and replay

### 10.1 Coordinator scope

```text
coordinator_scope_key = runtime_scope_revision_id
```

Because `runtime_scope_revision_id` already includes `mock_configuration_version`, `mock_enabled` and `mock_scenario_id`, no second scenario-dependent key exists outside the scope contract.

At most one active command exists for this key in one process.

### 10.2 Command generation

```text
command_key = canonical_sha256({
  runtime_scope_revision_id,
  expected_runtime_status_fingerprint,
  trigger
})

refresh_intent_scope_revision_id = canonical_sha256({
  runtime_scope_revision_id,
  expected_runtime_status_fingerprint,
  trigger
})
```

`TodayMarketRefreshIntent.scope_revision_id` receives `refresh_intent_scope_revision_id`. Its `local_clock_utc` receives server-owned `planning_recorded_at_utc` from the runtime scope.

Consequences:

- first automatic attempt and later retry have distinct deterministic attempt IDs;
- two simultaneous requests using the same expected status cannot both acquire;
- changed state creates a new status fingerprint and command generation;
- planning time cannot vary independently inside one runtime scope;
- server scenario cannot vary independently inside one runtime scope;
- identical completed replay returns current immutable status and does not reacquire.

### 10.3 Concurrency rules

1. Rebuild the scope and lock by `runtime_scope_revision_id`.
2. Compare the submitted status generation under that lock.
3. First valid command transitions to `refresh_in_progress`, increments revision and publishes the new status atomically.
4. A simultaneous request carrying the old expected fingerprint receives `runtime_status_conflict` and zero acquisition.
5. Client submission of any scenario field fails schema validation before lock/acquisition.
6. A changed server scenario produces a different scope revision and cannot reuse the old status.
7. Process restart discards locks and synthetic state; persisted local data is unchanged.

## 11. Mock-only plan and future live boundary

The current `TodayMarketRefreshPlan` and `build_refresh_plan` are explicitly Mock-only:

```text
assumption_profile_id = MOCK_ASSUMPTION_PROFILE_ID
production_eligible = false
```

Runtime Integration v1 constructs only this plan and may call only the deterministic Mock port explicitly injected by the application factory.

Reusable for future architecture:

- high-level runtime status/orchestration shape;
- all-or-nothing candidate publication;
- acquisition-seam concept;
- failure retention of prior snapshot;
- no hidden fallback or source mixing.

Not production-neutral:

- current Mock assumption-bearing plan payload;
- Mock quota/completion assumptions;
- synthetic source provenance.

After Issue #225 is closed by reviewed evidence, live integration requires a separate Strict Architecture Preflight that freezes either a new production planning contract/version or a reviewed source-specific translation owner outside the runtime coordinator.

A future adapter must not relax current Mock validation, disguise live inputs as synthetic, interpret THS quota/completion/correction/credential contracts inside the coordinator, or create fallback from THS to Mock/another Provider.

Until then:

```text
SOURCE_SPECIFIC_LIVE request = rejected
live adapter construction = absent
credential lookup = absent
network transport = absent
```

## 12. Runtime phases and ordinary-Chinese projection

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

Warnings and failures remain warnings and failures. Technical IDs, versions, scenario identity and provenance remain under progressive disclosure.

## 13. UI boundary for later implementation

Existing selection-first flow remains:

```text
set exact dual-as-of boundaries
  -> read local series catalog
  -> explicitly select equity / optional benchmark / optional sector
  -> read and render exact local snapshot
  -> read exact runtime status
```

A separate `模拟更新演示` panel appears only after the persisted snapshot is visible.

Rules:

1. Persisted local snapshot remains primary page content.
2. Synthetic panel is visibly separate and never labelled real/latest/live market data.
3. Browser never presents a scenario selector.
4. Browser never sends scenario/configuration fields.
5. If server Mock configuration is enabled and status is eligible/not-attempted, browser sends one automatic first-entry command.
6. Browser request-local duplicate guard is secondary; server scope/status/single-flight is authoritative.
7. Failures expose explicit retry; no retry loop or polling.
8. Changing boundaries or series invalidates and hides the old candidate.
9. Runtime candidate identity/status fingerprint is never stored in localStorage.
10. Text uses safe text nodes and status does not rely on color alone.
11. Prior snapshot remains visible during `refresh_in_progress`.

No action may imply recommendation, buy, sell, hold, target price, expected return, position sizing, portfolio addition or execution.

## 14. Complete-batch publication

The coordinator calls the accepted deterministic Mock acquisition port with one validated Mock plan and the server-injected scenario.

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

Successful publication is one immutable process-local pointer replacement under `runtime_scope_revision_id`; it increments status revision and creates a new status fingerprint.

Any failure produces:

```text
candidate_projection = null
prior_snapshot = unchanged
persisted_write = none
```

A synthetic correction scenario creates a distinct scope revision and candidate fingerprint and never rewrites persisted local history.

## 15. No-prior, catch-up, persistence and shutdown

No prior snapshot preserves `NOT_INITIALIZED`; Mock never initializes production history.

More than ten missing sessions produces `manual_catchup_required` with zero planning/acquisition.

Selected persistence decision:

```text
schema_migration = none
new_table = none
new_column = none
data_backfill = none
new_market_snapshot_persistence = none
new_runtime_state_persistence = none
browser_runtime_identity_persistence = none
```

Process-local coordinator state owns only status revision, automatic-attempt state, active command identity, latest successful synthetic candidate and latest typed failure. It does not survive restart.

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

- one local-series catalog request when requested;
- one exact snapshot request;
- at most one status request per eligible scope load;
- one automatic command per eligible server-configured scope generation;
- one explicit command per user retry;
- zero per-family/per-row browser requests;
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

### 18.1 Exact snapshot and scope identity

- identical authoritative reads produce identical snapshot ID/content fingerprint;
- changed selected run, content, boundary or series changes identity/fingerprint;
- service/repository provenance disagreement fails closed;
- GET and POST rebuild through the same authoritative path;
- stale/moved prior snapshot produces zero acquisition;
- every DTO and comparison uses `runtime_scope_revision_id`;
- any optional alias equals `runtime_scope_revision_id` byte-for-byte;
- unequal scope identifiers fail before planning/acquisition.

### 18.2 Server-owned scenario and status fingerprint

- default application has Mock disabled and scenario `null`;
- enabled test/demo application injects exactly one reviewed scenario;
- GET and POST observe the same server-owned scenario identity;
- client submission of `mock_scenario`, `mock_scenario_id` or `mock_enabled` is rejected as an unknown field;
- scenario change changes `runtime_scope_revision_id` and `runtime_status_fingerprint`;
- server scenario/status-scope mismatch fails before planning;
- repeated GET/POST for one application instance use one scenario identity;
- two same expected statuses cannot select different scenarios or produce two acquisitions;
- no multiple-scenario coordinator keys can bypass single-flight;
- every GET/POST returns a valid server-owned status fingerprint;
- stale expected fingerprint returns conflict and zero planning/acquisition.

### 18.3 Trigger and single-flight

- import/startup/raw page load performs no refresh;
- first eligible Mock-enabled scope automatically submits exactly one command;
- Mock-disabled scope submits none;
- automatic command uses `FIRST_TODAY_MARKET_ENTRY`;
- explicit retry uses `EXPLICIT_USER_RETRY` and a newer status fingerprint;
- same scope has one server-owned planning clock and scenario;
- repeated rendering/navigation does not create a second automatic attempt;
- simultaneous commands using the same fingerprint create one acquisition only;
- process restart drops runtime state without changing persisted data.

### 18.4 Golden/failure and zero-network paths

Validate no-refresh-needed, one-session and ten-session complete synthetic refresh, correction, no prior snapshot, manual catch-up required, Mock disabled, live source blocked, assumption budget exhausted, partial family failure, schema mismatch, incomplete coverage, invalid fingerprint, shutdown, database unavailable and stale scope/status/prior snapshot.

Every failure proves zero partial publication and retained prior snapshot where one exists.

Import, startup, page load, status read, command, tests and demo remain zero-network. No schema, migration, database write, Provider readiness mutation, accepted research mutation, recommendation, portfolio or trading mutation occurs.

## 19. Stop conditions

Stop and return for explicit project-owner review if later design or implementation requires:

- FastAPI startup refresh side effects;
- raw page-load acquisition before exact scope;
- hidden source or series selection;
- client-supplied planning clock or Mock scenario;
- more than one scope identifier or canonical payload;
- identity inferred from labels/presentation JSON;
- non-deterministic/fuzzy snapshot selection;
- live THS, credentials or network;
- weakening Issue #225;
- treating Mock assumptions as Provider facts;
- current Mock plan used as a live plan;
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
4. A fresh process-independent review verifies the five original blockers and the two Review `4786209951` blockers, and contains exactly:

```text
AUTHORIZED TODAY MARKET REFRESH RUNTIME INTEGRATION V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

5. Every review thread is resolved.
6. The project owner separately and explicitly authorizes merge.
7. Any new commit invalidates previous exact-head CI and review evidence.

Architecture merge will not authorize implementation. A later implementation requires its own bounded Strict Issue, branch, Draft PR, exact-head CI/review and separate merge authorization.
