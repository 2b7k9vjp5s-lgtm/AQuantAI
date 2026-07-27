# Issue #253 — Today Market Provider-Neutral Acquisition Port and Deterministic Mock

## Authority

- Project-owner instruction on 2026-07-27:

```text
Today Market Architecture Preflight
↓
Provider-neutral contract
↓
Mock implementation
↓
CI validation
```

- Linked Issue: #253.
- Product Roadmap: #137.
- Accepted automatic-refresh architecture: #221 / merged PR #222.
- Accepted THS source synchronization: #223 / merged PR #224.
- Controlling live Provider gate: #225.
- Accepted THS Stage C0: #227/#229 and #230/#231.
- Accepted market-dump evidence amendment: #251 / merged PR #252.
- Exact architecture base: `6084b20a2467f02465d3a9a342009a78f58e9773`.
- Branch: `docs/today-market-provider-neutral-mock-preflight`.
- Frozen superseded PR #241 remains read-only at `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.
- Risk tier: **Strict Architecture Preflight**.
- Workflow authority: `.codex/WORKFLOW.md`.

## Objective

Define one narrow provider-neutral application acquisition port and one deterministic, zero-network Mock boundary for Today Market startup-refresh orchestration.

This architecture must preserve source-specific THS ownership and keep live Stage C1 blocked by #225.

The governed delivery order is:

```text
architecture Issue/PR
  -> exact-head CI and fixed-head architecture review
  -> separate owner merge authorization
  -> separate Mock implementation Issue/PR
  -> exact-head implementation CI and review
```

This task does not authorize production code, Mock code, network access, credentials, schema, migration, persistence, Provider data, fixture values from THS, release, tag, version change, Issue closure or merge.

## Layering decision

```text
Today Market orchestration
  -> provider-neutral application acquisition port
      -> deterministic Mock adapter for tests/demo only
      -> future source-specific adapter
           -> datasource.ths_structured_provider
           -> future live transport only after #225
```

The application port is neutral only at the orchestration seam. It must not become:

- a generic arbitrary-endpoint Provider registry;
- runtime Provider fallback;
- cross-Provider row mixing;
- a replacement owner for source contracts, source selectors or readiness;
- a path that erases source provenance.

## Temporary engineering-assumption profile

Freeze one test-only profile:

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

The profile may drive deterministic Mock scenarios only. It must never:

- populate an account quota, dataset completion or credential lifecycle fact;
- set a THS capability to `implementation_ready`;
- close or weaken #225;
- be read by a future live adapter;
- be represented as a Provider average, entitlement or promise.

The product-level startup policy remains one bounded attempt. Mock planning must not turn official reference-client retry defaults into product retries.

## Provider-neutral contract candidates

The architecture document must close the meaning and ownership of:

```text
TodayMarketRefreshIntent
TodayMarketRefreshPlan
TodayMarketAcquisitionPort
TodayMarketAcquisitionBatch
TodayMarketAcquisitionFailure
TodayMarketCoverage
TodayMarketSourceProvenance
MockScenario
MockPlanningAssumption
```

The port accepts one already validated bounded refresh plan. It must not accept:

- arbitrary URLs or endpoint paths;
- arbitrary query dictionaries;
- raw request headers;
- credential values or credential-profile lookup;
- Provider-specific response bodies.

Minimum refresh-plan identity:

```text
scope_revision_id
refresh_attempt_id
requested_completed_sessions
capability_set
request_bounds
information_cutoff
recorded_at_utc
planning_policy_version
plan_fingerprint
```

Minimum acquisition-batch identity:

```text
source_key
adapter_contract_version
source_contract_fingerprints
scenario_or_attempt_id
observed_at_utc
data_through_session
coverage_status
family_results
redacted_diagnostics
batch_fingerprint
```

The Mock uses an explicit synthetic source key and may never impersonate THS.

## Closed first capability surface

Allowed for the later Mock implementation:

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

Excluded:

```text
full_market_individual_security_daily_ingestion
full_market_breadth_or_turnover_claims
historical_sector_breadth
adjusted_multi_session_returns
full_market_exact_limit_price_claims
historical_gap_fill_from_current_snapshot
```

## Deterministic Mock boundary

The future Mock implementation must be structurally zero-network:

- no `requests`, `httpx`, `urllib.request`, `socket`, subprocess transport, browser automation or Provider SDK;
- no credential argument or lookup;
- no database migration or Provider persistence;
- invented fixture values only;
- explicit synthetic labels and provenance;
- injected clock only;
- canonical JSON fingerprints;
- byte-identical output for an identical plan and scenario;
- changed synthetic content represented as a distinct candidate revision, never historical in-place rewrite.

Required scenarios:

```text
current_no_refresh_needed
stale_one_session_success
stale_ten_sessions_success
stale_more_than_ten_requires_manual_catchup
not_initialized
quota_assumption_exhausted
partial_family_failure
schema_mismatch
coverage_incomplete
synthetic_correction_revision
application_shutdown_before_publish
```

## Readiness separation

The port and Mock must keep separate:

```text
mock_executable = true | false
live_source_readiness = ready | blocked
```

For the later Mock slice:

```text
mock_executable = true
live_source_readiness = blocked
production_live_network_authorized = false
overall_live_gate = blocked_quota_contract
```

No Mock result may mutate or reinterpret THS Stage C0 `remote_executable = false`.

## Offline golden path

```text
render prior complete local snapshot
  -> injected calendar identifies one missing completed session
  -> build one exact bounded refresh plan
  -> deterministic Mock acquisition
  -> validate complete synthetic index-led batch
  -> compute refreshed candidate projection in memory
  -> expose one complete synthetic demo result atomically
```

The prior snapshot remains visible until candidate validation succeeds.

## Primary failure path

```text
render prior complete local snapshot
  -> required Mock family is partial or schema-invalid
  -> reject candidate batch
  -> perform no partial publish
  -> retain prior complete snapshot
  -> expose stable Chinese error and next action
```

## Migration and rollback

```text
migration_required = false
persistence_change = false
rollback = remove additive application/mock modules and tests
downgrade_data_loss = none
```

## Candidate implementation file families

Repository inspection confirms that Python packages are discovered under `backend*`, while the existing top-level `today_market/` directory is a static-resource surface. A later separately authorized implementation Issue may therefore use only bounded files under:

```text
backend/today_market_refresh/
tests/test_today_market_*mock*.py
tests/fixtures/today_market_mock/
scripts/demo_today_market_mock_refresh.py
.github/workflows/local-tests.yml  # additive focused invocation only if required
```

It may not add live transport or credentials and may not modify `datasource/ths_structured_provider` except for explicitly authorized import-free compatibility tests.

## Later Mock CI contract

Exact-head validation must prove:

1. imports, FastAPI startup, ordinary reads, tests and fixture demos remain zero-network;
2. sentinel credentials never appear in outputs, errors or diagnostics;
3. fixed plan plus scenario yields deterministic fingerprints;
4. synthetic assumptions cannot satisfy Provider readiness;
5. 1-session and 10-session automatic paths succeed;
6. more than 10 sessions requires manual catch-up;
7. partial/schema-invalid results perform zero publish writes;
8. the prior complete snapshot remains available on failure;
9. synthetic source provenance is explicit;
10. full pytest and all configured offline demos remain green.

## Authorized architecture files

Exactly:

```text
.codex/tasks/issue-253-today-market-provider-neutral-mock-preflight.md
docs/today_market_provider_neutral_mock_preflight.md
```

No accepted architecture document is rewritten.

## Architecture validation

- exact base-to-head inventory;
- exactly two Markdown files;
- Markdown structure and repository-link review;
- no executable code, dependency, workflow, schema, migration or fixture change;
- no secret, account identifier, Provider value or live request;
- zero unresolved review threads;
- fixed-head review containing exactly:

```text
AUTHORIZED TODAY MARKET PROVIDER-NEUTRAL MOCK ARCHITECTURE APPROVED at fixed head <FULL_HEAD_SHA>
```

## Stop conditions

Stop if work would require:

- treating temporary values as Provider-confirmed facts;
- changing #225 to ready;
- live transport, client or credential setup;
- account identifiers, Cookies, browser sessions or pre-signed URLs;
- Provider-valued fixtures;
- schema or migration changes;
- generic Provider plug-ins, fallback or row mixing;
- modification of frozen PR #241;
- starting the Mock implementation before this architecture PR is merged;
- merge, Issue closure, release, tag or version change without separate owner authorization.

Any new commit invalidates fixed-head validation and review.
