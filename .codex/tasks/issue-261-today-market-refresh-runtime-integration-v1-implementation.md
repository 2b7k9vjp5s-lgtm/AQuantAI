# Issue #261 — Today Market Refresh Runtime Integration v1 Strict Implementation

## Exact authority

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
base_sha = cec6ef0b6cbd26a15c8121f70adc8ec3d0c012ec
architecture_issue = #259
architecture_pr = #260
live_ths_gate = open Issue #225
branch = feat/today-market-refresh-runtime-integration-v1
risk_tier = Strict Implementation
```

This task implements only the accepted Mock-only runtime-integration slice. It does not authorize merge.

## Exact changed files

```text
.codex/tasks/issue-261-today-market-refresh-runtime-integration-v1-implementation.md
backend/today_market_refresh/runtime.py
backend/today_market_refresh/__init__.py
backend/main.py
today_market/static/today_market.html
tests/test_today_market_runtime_integration.py
scripts/demo_today_market_runtime_integration.py
.github/workflows/local-tests.yml
```

This is a strict subset of the files authorized by Issue #261. No other file may change.

## Implemented contracts

- one server-owned `runtime_scope_revision_id` canonical payload;
- one opaque server-owned `runtime_status_fingerprint`;
- exact authoritative prior snapshot ID/content fingerprint;
- immutable application-factory Mock configuration;
- default disabled + null scenario;
- GET runtime status with zero acquisition/write;
- POST closed command with unknown-field rejection;
- process-local coordinator, optimistic concurrency and single-flight;
- one bounded automatic `FIRST_TODAY_MARKET_ENTRY` attempt only when Mock is explicitly enabled;
- explicit retry only after retained-prior failure/cancellation;
- complete synthetic publication only;
- ordinary-Chinese runtime projection;
- zero-network tests and demo.

## Validation

```text
python -m pytest -q --tb=short
node --check extracted Today Market runtime JavaScript
python -m scripts.demo_today_market_runtime_integration
full Local Tests workflow
```

Tests must prove default disabled behavior, scope/status fingerprint determinism, stale conflict before planning/acquisition, same-scope single-flight, replay without reacquisition, closed scenario ownership, authoritative prior identity, no partial publication, prior retention and no polling/network/persistence.

## Locked exclusions

No live THS, credentials, network, Provider SDK, Provider-valued fixture, fallback, source mixing, schema, migration, database write, new persistence, scheduler, daemon, background task, polling, AI call, accepted-state mutation, recommendation, portfolio, trading, version, Tag or Release.

Do not modify or resume PR #241. Do not rebase, force-push or change Base.

## Stop conditions

Stop for project-owner review if implementation requires any file outside the exact list, client-owned scenario/planning clock, a second scope identity, live planning, persistence, startup/raw-page acquisition, background execution, partial publication, Provider access or advisory/trading semantics.

## Delivery gate

Keep the implementation PR Draft. Every new commit invalidates prior exact-head CI and review. Do not merge until the project owner explicitly says `批准合并 PR #<编号>`.
