# Issue #255 — Today Market Deterministic Mock Adapter MVP

## Authority

- Project-owner implementation instruction on 2026-07-27: `继续`.
- Governing Issue: #255.
- Accepted architecture: Issue #253 / merged PR #254.
- Exact implementation base: `66cdf5d4dc69b1bc757e61453b191680c8b61b72`.
- Branch: `feat/today-market-deterministic-mock-mvp`.
- Product Roadmap: #137.
- Controlling live Provider gate: #225.
- Frozen superseded PR #241 remains read-only at `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.
- Risk tier: **Strict Implementation**.
- Workflow authority: `.codex/WORKFLOW.md`.

## Objective

Implement the accepted provider-neutral Today Market application port and deterministic synthetic Mock so startup-refresh orchestration can be proven end to end with zero network, zero credentials, zero persistence and no change to THS readiness.

Delivery:

```text
M1 immutable contracts and canonical fingerprints
  -> M2 bounded planner and closed orchestration states
  -> M3 deterministic synthetic Mock and frozen fixtures
  -> M4 in-memory candidate projection and offline demo
  -> exact-head full CI and fixed-head implementation review
```

## Locked layering

```text
Today Market read surface
  -> backend.today_market_refresh
       -> provider-neutral application plan/port
       -> deterministic synthetic Mock
       -> no live adapter in this Issue
```

Source-specific THS contracts and readiness remain owned by `datasource.ths_structured_provider`. This implementation does not import, mutate or reinterpret those owners in production code.

## Synthetic assumption profile

```text
profile_id = aquantai.today-market.mock-planning-assumption.v1
assumption_class = synthetic_engineering_scenario
mock_qps = 5
mock_concurrency = 2
mock_daily_request_budget = 50000
mock_completion_after_local_time = 18:00:00
mock_timezone = Asia/Shanghai
provider_confirmed = false
production_eligible = false
```

These values are test-only. They may not populate account quota, dataset completion, credential lifecycle, source authorization or capability-readiness state. They may not be consumed by a future live adapter or close #225.

## Exact authorized files

```text
.codex/tasks/issue-255-today-market-deterministic-mock-implementation.md
backend/today_market_refresh/__init__.py
backend/today_market_refresh/contracts.py
backend/today_market_refresh/fingerprint.py
backend/today_market_refresh/planner.py
backend/today_market_refresh/port.py
backend/today_market_refresh/mock.py
backend/today_market_refresh/projection.py
backend/today_market_refresh/orchestrator.py
scripts/demo_today_market_mock_refresh.py
tests/test_today_market_mock_contracts.py
tests/test_today_market_mock_orchestration.py
tests/fixtures/today_market_mock/complete_index_led.synthetic.json
tests/fixtures/today_market_mock/partial_family.synthetic.json
tests/fixtures/today_market_mock/schema_mismatch.synthetic.json
tests/fixtures/today_market_mock/coverage_incomplete.synthetic.json
tests/fixtures/today_market_mock/correction_revision.synthetic.json
.github/workflows/local-tests.yml
```

No other file is authorized.

## M1 contracts and fingerprints

Implement frozen closed concepts:

```text
TodayMarketRefreshIntent
TodayMarketRefreshPlan
TodayMarketAcquisitionPort
TodayMarketSourceProvenance
TodayMarketFamilyResult
TodayMarketCoverage
TodayMarketAcquisitionBatch
TodayMarketAcquisitionFailure
SnapshotReference
TodayMarketDemoProjection
TodayMarketRefreshOutcome
MockPlanningAssumption
MockScenario
```

Requirements:

- no arbitrary URL, endpoint, query, header or credential field;
- timezone-aware injected clocks only;
- sorted unique explicit sessions and capability sets;
- canonical UTF-8 JSON with SHA-256 fingerprints;
- synthetic source key exactly `aquantai-synthetic-today-market-v1`;
- Mock provenance always `provider_confirmed=false`;
- no mutable Provider-readiness state.

## M2 planner and state machine

The planner accepts one exact local intent, explicit expected completed sessions, one prior snapshot reference and one closed capability set.

Closed planning outcomes:

```text
acquisition_required
current
manual_catchup_required
not_initialized
```

Automatic acquisition is allowed only for 1–10 missing sessions. More than 10 sessions produces `manual_catchup_required` and makes no adapter call. No prior snapshot produces `not_initialized` and no hidden bootstrap.

Closed orchestration outcomes:

```text
no_refresh_needed
manual_catchup_required
not_initialized
published_demo
failed_retained_prior
cancelled_retained_prior
```

## M3 deterministic Mock

The Mock:

- requires an explicit fixture root and scenario;
- has no default network, credential or database path;
- uses invented `.synthetic.json` fixtures only;
- uses injected plan time and in-memory usage counters;
- simulates 5 QPS, 2 concurrency and 50000 daily requests without sleeping;
- returns one complete batch or raises one typed failure;
- preserves exact synthetic provenance and canonical fingerprints;
- never impersonates THS.

Required fixture scenarios:

```text
complete index-led success
partial required family
schema mismatch
coverage incomplete
synthetic correction revision
```

Quota exhaustion is a deterministic in-memory scenario and needs no separate fixture.

## M4 orchestration and projection

Golden path:

```text
prior snapshot reference
  -> one missing completed session
  -> exact bounded plan
  -> complete synthetic acquisition batch
  -> full batch validation
  -> in-memory synthetic candidate projection
```

The projection must expose:

```text
is_synthetic = true
source_label = 模拟数据
production_live_source_ready = false
overall_live_gate = blocked_quota_contract
```

No database publication occurs. `published_demo` means only that a complete in-memory candidate is returned. Prior snapshot identity remains available throughout.

Primary failure path:

```text
partial/schema-invalid/coverage-invalid batch
  -> reject complete candidate
  -> no projection
  -> retain prior snapshot
  -> stable Chinese failure message
```

An injected shutdown signal after acquisition and before publication returns `cancelled_retained_prior`.

## Security and zero-network

Production package files may not import:

```text
requests
httpx
urllib.request
socket
subprocess
sqlalchemy
psycopg
sqlite3
```

The port and DTOs contain no API-key, token, Cookie, account or credential-profile field. Tests use sentinel secret inputs only to prove the constructor cannot accept them and the sentinel does not appear in output.

## Migration, rollback and downgrade

```text
migration_required = false
schema_change = false
persistent_data_change = false
fastapi_route_change = false
rollback = remove the additive package, tests, fixtures, demo and CI step
downgrade_data_loss = none
```

## Validation

Focused isolated pre-push validation:

```text
16 passed
demo = success
network_used = false
credentials_used = false
persistence_used = false
```

Exact PR HEAD must pass:

1. full repository pytest;
2. all configured offline demos;
3. the new Today Market deterministic Mock demo;
4. no-network import/demo guard;
5. deterministic fingerprints;
6. one-session and ten-session success;
7. more-than-ten manual-catchup behavior;
8. partial/schema/coverage zero-publish behavior;
9. prior snapshot retention;
10. synthetic correction fingerprint change;
11. negative compatibility proof that Mock success leaves THS Stage C0 blocked.

## Stop conditions

Stop if work would require:

- live THS calls or credentials;
- environment-secret lookup;
- Provider-valued fixture data;
- schema, migration or persistence;
- FastAPI route activation;
- Provider fallback or row mixing;
- changing #225;
- changing THS Stage C0 readiness;
- moving frozen PR #241;
- recommendation, portfolio or trading behavior;
- merge, Issue closure, release, tag or version change without separate owner authorization.

## Fixed-head review

Before merge consideration, the implementation review must record exactly:

```text
AUTHORIZED TODAY MARKET DETERMINISTIC MOCK IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates exact-head CI and review.
