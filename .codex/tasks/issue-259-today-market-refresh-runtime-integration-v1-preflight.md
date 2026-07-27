# Issue #259 — Today Market Refresh Runtime Integration v1 Architecture Preflight

## Authority

Project-owner authorization on 2026-07-27 permits this Strict Architecture Preflight only. It does not authorize production implementation, live THS access, credentials, network, schema, migration, persistence, scheduler, recommendation, portfolio, trading, release, tag or version change.

This revision preserves the five resolutions required by fixed-head review `4786108502` and resolves the two additional blockers recorded by fixed-head review `4786209951`.

## Exact base

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
base_sha = 1b2de3544844647ad02beffe2e6a8e14c467fd98
branch = docs/today-market-refresh-runtime-integration-v1-preflight
risk_tier = Strict Architecture Preflight
```

## Controlling authority

- Product Roadmap: Issue #137.
- Live THS external-contract gate: open Issue #225.
- Current-state baseline: Issue #257 / merged PR #258.
- Accepted Today Market automatic-refresh architecture: Issue #221 / merged PR #222.
- Accepted THS synchronization architecture: Issue #223 / merged PR #224.
- Accepted THS Stage C0 offline foundation: #227/#229 and #230/#231.
- Accepted public full-market snapshot and Market Dump evidence: #251/#252.
- Accepted provider-neutral acquisition port: #253/#254.
- Accepted deterministic zero-network Mock: #255/#256.
- Superseded PR #241 remains closed, unmerged and read-only at `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

## Reviewed v1 outcome

```text
raw application/page load
  -> no refresh
explicit boundaries + explicit local series
  -> exact prior local snapshot is read and rendered
  -> exact server-owned runtime scope/status is returned
server-side demo factory injects Mock enabled + one reviewed scenario
  -> browser automatically submits one bounded first-eligible-scope command
  -> one synchronous process-local attempt runs
  -> complete synthetic candidate is validated and exposed separately
failure or shutdown
  -> prior persisted snapshot remains authoritative and unchanged
```

Mock is disabled by default and has no implicit scenario. A test/demo application factory may inject exactly one reviewed scenario for one application instance. Later user retries use `EXPLICIT_USER_RETRY`.

## Preserved original blocker resolutions

### 1. Server-owned runtime status fingerprint

Every GET/POST status exposes an opaque server-owned `runtime_status_fingerprint`. POST carries `expected_runtime_status_fingerprint`; under the coordinator lock, the server rebuilds exact snapshot, scope, current process-local status and fingerprint before planning/acquisition. Mismatch returns stable conflict with zero planning, acquisition and candidate change.

### 2. Authoritative prior-snapshot identity

`prior_snapshot_id` and `prior_snapshot_content_fingerprint` derive only from one exact server read path using the selected successful complete `IngestionRun` components, exact dual-as-of boundaries, canonical series identities and deterministic Market Cockpit domain snapshot.

The selected run algorithm matches existing repository order:

```text
information_cutoff_date DESC
completed_at DESC
id DESC
LIMIT 1
```

A missing, moved, inconsistent or service/repository-disagreeing component fails closed before acquisition.

### 3. Server-owned planning clock

```text
planning_recorded_at_utc = normalized as_of_recorded_at_utc
```

The client cannot supply a separate planning clock.

### 4. Current Plan strictly Mock-only

The accepted plan requires `MOCK_ASSUMPTION_PROFILE_ID` and is not production-live eligible. Future THS integration requires a separate Strict Architecture Preflight after Issue #225 closes; current Mock validation cannot be weakened.

### 5. One automatic first-eligible attempt

FastAPI startup and raw `/today-market` loading perform no acquisition. After explicit boundaries/series and prior snapshot render, a Mock-enabled application automatically submits exactly one synchronous bounded command using `FIRST_TODAY_MARKET_ENTRY`. Failure allows only explicit retry; no retry loop, scheduler, daemon or polling exists.

## Review 4786209951 blocker resolutions

### 6. One authoritative runtime scope identifier

The sole authoritative field is:

```text
runtime_scope_revision_id
```

It is canonical SHA-256 over the closed runtime scope payload, including:

- exact dual-as-of boundaries;
- exact series selection;
- prior snapshot ID/content fingerprint/data-through session;
- capability set and planning policy;
- server-owned planning time;
- server Mock configuration version;
- `mock_enabled`;
- `mock_scenario_id | null`.

All of the following use that same value and same payload:

- runtime scope DTO;
- runtime status DTO;
- runtime status fingerprint;
- GET response;
- POST equality check;
- coordinator scope key;
- command/refresh intent generation;
- stale/conflict validation;
- executable tests.

`runtime_scope_fingerprint` is not an independent v1 field. If exposed only as a presentation alias:

```text
runtime_scope_fingerprint = runtime_scope_revision_id
```

It cannot have a separate calculation, version or comparison path. Any unequal scope identity fails before planning and acquisition.

### 7. Server-owned Mock scenario

The application factory is the unique scenario owner:

```text
TodayMarketMockRuntimeConfigurationV1 = {
  configuration_version,
  mock_enabled,
  mock_scenario_id | null
}
```

Rules:

- default application: disabled + scenario `null`;
- test/demo application: enabled + exactly one reviewed scenario;
- GET and POST use the same immutable dependency;
- browser, request body, query string, localStorage and cookies cannot select/change scenario;
- server configuration identity enters runtime scope, `runtime_scope_revision_id`, status DTO/fingerprint and coordinator ownership;
- scenario/configuration change creates a new scope/status generation;
- there is no implicit default/fallback scenario.

The POST request excludes and rejects as unknown:

```text
mock_scenario
mock_scenario_id
mock_enabled
source_mode
adapter_name
fixture_path
planning_clock
```

The coordinator key is exactly:

```text
coordinator_scope_key = runtime_scope_revision_id
```

No scenario-dependent parallel key exists outside the scope identity, so different scenarios cannot bypass single-flight.

## Required negative validation

A later implementation must prove:

- every scope/status/API/comparison uses one `runtime_scope_revision_id`;
- optional alias equality is byte-for-byte;
- unequal scope IDs fail before planning/acquisition;
- client-supplied scenario/configuration fields are rejected by unknown-field validation;
- GET and POST repeatedly observe the same server scenario for one application instance;
- server scenario/status-scope mismatch fails before planning;
- scenario change changes both scope revision and status fingerprint;
- two requests with the same expected status cannot select different scenarios;
- two same-status simultaneous commands create one acquisition only;
- multiple scenario coordinator keys cannot bypass single-flight;
- default disabled Mock has scenario `null` and zero acquisition;
- no startup/raw-page acquisition, persistence, network, live THS or Provider fallback appears.

## Authorized files

Exactly:

```text
.codex/tasks/issue-259-today-market-refresh-runtime-integration-v1-preflight.md
docs/today_market_refresh_runtime_integration_v1_preflight.md
```

No other file may change in this architecture PR.

## Locked invariants

```text
live_ths_gate = Issue #225
production_live_network_authorized = false
overall_live_gate = blocked_quota_contract
current_refresh_plan = mock_only
runtime_scope_owner = runtime_scope_revision_id
mock_scenario_owner = server_application_factory
schema_migration = prohibited
new_persistence = prohibited
scheduler_or_daemon = prohibited
hidden_provider_fallback = prohibited
cross_provider_row_mixing = prohibited
partial_publication = prohibited
recommendation_portfolio_trading = prohibited
```

## Golden path

One prior complete local snapshot renders under explicit boundaries and series selection. The server returns exact snapshot identity, server-owned Mock configuration, `runtime_scope_revision_id` and status fingerprint. In an explicitly Mock-enabled demo process, the first eligible interaction automatically submits one bounded command without scenario fields. Existing planner, acquisition port, orchestrator and validators accept one complete synthetic batch. One separate synthetic projection is exposed atomically while persisted local data and THS readiness remain unchanged.

## Primary failure path

A required Mock family is partial, schema-invalid or coverage-incomplete. The candidate is rejected, no partial result is exposed, the prior snapshot remains visible, and one explicit retry action is available. Stale status, moved snapshot, scope mismatch, server configuration mismatch or client scenario field fails before planning/acquisition.

## Strict validation and delivery gates

Before merge consideration:

1. Complete base-to-head inventory contains exactly the two authorized Markdown files.
2. Applicable repository CI succeeds on one exact immutable HEAD.
3. The architecture resolves all five original blockers and both Review `4786209951` blockers.
4. A fresh process-independent fixed-head review contains exactly:

```text
AUTHORIZED TODAY MARKET REFRESH RUNTIME INTEGRATION V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

5. Zero unresolved review threads.
6. Separate explicit project-owner merge authorization.

Architecture merge does not authorize production implementation. Any new commit invalidates prior exact-head CI and review evidence.
