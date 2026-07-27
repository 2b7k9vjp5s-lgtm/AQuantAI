# Issue #259 — Today Market Refresh Runtime Integration v1 Architecture Preflight

## Authority

Project-owner authorization on 2026-07-27 permits this Strict Architecture Preflight only after PR #258 merged. It does not authorize production implementation, live THS access, credentials, network, schema, migration, persistence, scheduler, recommendation, portfolio, trading, release, tag or version change.

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
- Accepted THS source synchronization: Issue #223 / merged PR #224.
- Accepted THS Stage C0 offline foundation: Issues #227/#230 and merged PRs #229/#231.
- Accepted public full-market snapshot and Market Dump evidence: Issue #251 / merged PR #252.
- Accepted provider-neutral acquisition port: Issue #253 / merged PR #254.
- Accepted deterministic zero-network Mock: Issue #255 / merged PR #256.
- Superseded PR #241 remains closed, unmerged and read-only at `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

## Reviewed architecture outcome

The v1 candidate remains zero-network, process-local and Mock-only:

```text
raw application/page load
  -> no refresh
explicit boundaries + explicit local series
  -> exact prior local snapshot is read and rendered
  -> exact server-owned runtime scope/status is returned
server-side Mock demo mode enabled
  -> browser automatically submits one bounded first-eligible-scope command
  -> one synchronous process-local attempt runs
  -> complete synthetic candidate is validated and exposed separately
failure or shutdown
  -> prior persisted snapshot remains authoritative and unchanged
```

Mock is disabled by default. When disabled, no automatic acquisition occurs and the runtime truthfully returns `mock_not_enabled`. When explicitly injected by a test/demo application factory, the first eligible scoped interaction performs exactly one automatic Mock attempt using `FIRST_TODAY_MARKET_ENTRY`; later user retries use `EXPLICIT_USER_RETRY`.

## Fixed review-blocker resolutions

### 1. Runtime status fingerprint

A later implementation must expose a server-owned `runtime_status_fingerprint` in every `TodayMarketRuntimeStatus` returned by GET and POST.

The fingerprint is canonical SHA-256 over the closed status payload, including:

- status contract/version;
- exact runtime scope fingerprint;
- process-local status revision;
- phase and prior-snapshot state;
- source mode and Mock enablement state;
- automatic-attempt state;
- active attempt identity;
- plan fingerprint;
- candidate projection fingerprint;
- typed failure code/category/retryability;
- allowed action codes.

It excludes localized prose, presentation ordering and expanded technical display details. POST must carry `expected_runtime_status_fingerprint`; under the same coordinator lock, the server re-resolves the exact prior snapshot and runtime scope, rebuilds the current status fingerprint, compares it before planning/acquisition, and returns a stable conflict with zero acquisition on mismatch.

### 2. Authoritative prior-snapshot identity

`prior_snapshot_id` and `prior_snapshot_content_fingerprint` are server-derived only from one exact authoritative local read path.

The identity payload is versioned and includes:

- normalized dual-as-of boundaries;
- exact selected equity/benchmark/sector series keys, with explicit nulls;
- exact succeeded/complete `IngestionRun` identities selected by the existing repositories for each family;
- dataset, provider, series key, information cutoff, imported/completed timestamps and snapshot mode for those runs;
- effective equity/benchmark/sector sessions;
- the closed snapshot contract version.

The content fingerprint is canonical SHA-256 over that identity payload plus the deterministic domain snapshot payload returned by the existing Market Cockpit service, excluding UI copy and browser state. Dates use ISO format, timestamps use UTC `Z`, mapping keys are sorted, family order is fixed as equity/benchmark/sector, and warnings/sets are canonically sorted.

The implementation may add a bounded read-only projection from existing repository results, but no new persisted owner. If the exact selected run set cannot be uniquely resolved, if any component becomes invisible, or if the identity/content fingerprint changes between status GET and command POST, the command fails closed before acquisition.

### 3. Planning clock and single-flight

The client cannot supply an independent planning clock. For one runtime scope:

```text
planning_recorded_at_utc = exact normalized as_of_recorded_at_utc
```

That value is already bound into the runtime scope fingerprint, so the same scope cannot have two planning clocks.

The coordinator uses:

```text
coordinator_scope_key = runtime_scope_revision_id + source_mode + mock_scenario
command_key = expected_runtime_status_fingerprint + trigger
refresh_intent_scope_revision_id = canonical_sha256(
  runtime_scope_revision_id + expected_runtime_status_fingerprint + trigger
)
```

At most one command is active for a coordinator scope. The first automatic command and every later retry start from a different server-returned status fingerprint, so they receive distinct deterministic intent/attempt identities without changing the underlying local snapshot scope. Simultaneous stale requests fail with conflict and zero second acquisition.

### 4. Mock-only plan and future live seam

The accepted `TodayMarketRefreshPlan` and current planner are explicitly Mock-only because the plan requires `MOCK_ASSUMPTION_PROFILE_ID`.

Runtime Integration v1 may construct only this Mock plan. A future live THS adapter may reuse the high-level runtime orchestration and provider-neutral seam, but it may not consume the current Mock assumption-bearing plan.

After Issue #225 is closed by reviewed evidence, live integration requires a separate Strict Architecture Preflight that freezes either:

- a new production planning contract/version; or
- a reviewed source-specific translation owner outside the runtime coordinator.

It may not weaken the current assumption-profile validation, disguise live inputs as synthetic, or move THS quota/completion/revision semantics into the coordinator.

### 5. Bounded automatic attempt

V1 preserves the Issue #259 automatic-attempt requirement without adding startup side effects:

- FastAPI import/startup and raw `/today-market` page load perform no refresh.
- After the user explicitly establishes boundaries/series and the prior snapshot is rendered, GET returns the exact eligible runtime status.
- When server-side Mock demo mode is enabled and that exact scope has not attempted automatic refresh, the browser automatically sends one POST with trigger `FIRST_TODAY_MARKET_ENTRY` and the returned status fingerprint.
- The attempt is synchronous, bounded and single-flight.
- The page continues to show the prior snapshot while the command runs.
- No second automatic attempt occurs for the same scope generation.
- Failures expose one explicit retry action using `EXPLICIT_USER_RETRY`.
- When Mock mode is disabled, the status is `mock_not_enabled` and no acquisition is attempted.

## Authorized files

Exactly:

```text
.codex/tasks/issue-259-today-market-refresh-runtime-integration-v1-preflight.md
docs/today_market_refresh_runtime_integration_v1_preflight.md
```

No other file may change in this architecture PR.

## Golden path

One prior complete local snapshot renders under explicit boundaries and series selection. The server returns its exact snapshot identity, runtime scope and status fingerprint. In an explicitly Mock-enabled demo process, the first eligible scoped interaction automatically submits one bounded command. Existing planner, acquisition port, orchestrator and validators accept one complete synthetic batch. One separate synthetic projection is exposed atomically, while the persisted local snapshot, database and THS readiness remain unchanged.

## Primary failure path

A required Mock family is partial, schema-invalid or coverage-incomplete. The candidate is rejected, no partial result is exposed, the prior snapshot remains visible and the user receives a stable Chinese reason and one explicit retry action. Shutdown, stale status, moved prior snapshot or non-unique identity resolution all fail before publication; stale identity/status failures occur before acquisition.

## Locked invariants

```text
live_ths_gate = Issue #225
production_live_network_authorized = false
overall_live_gate = blocked_quota_contract
current_refresh_plan = mock_only
schema_migration = prohibited
new_persistence = prohibited
scheduler_or_daemon = prohibited
hidden_provider_fallback = prohibited
cross_provider_row_mixing = prohibited
partial_publication = prohibited
recommendation_portfolio_trading = prohibited
```

## Validation and review gates

Before merge consideration:

1. Complete base-to-head inventory contains exactly the two authorized Markdown files.
2. Applicable repository CI succeeds on one exact immutable HEAD.
3. The architecture document resolves every required decision and all five fixed-head review blockers.
4. A fresh process-independent fixed-head review contains exactly:

```text
AUTHORIZED TODAY MARKET REFRESH RUNTIME INTEGRATION V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

5. Zero unresolved review threads.
6. Separate explicit project-owner merge authorization.

Architecture merge does not authorize production implementation. Any new commit invalidates prior exact-head CI and review evidence.
