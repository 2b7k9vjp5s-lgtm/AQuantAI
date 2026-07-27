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

## Objective

Freeze the smallest application/runtime integration architecture for the already accepted provider-neutral Today Market refresh contracts:

```text
application start or first /today-market entry
  -> render prior complete local snapshot immediately
  -> perform one deterministic stale check
  -> build one bounded refresh plan
  -> call one explicitly selected acquisition port
  -> validate one complete candidate batch
  -> atomically expose one complete candidate projection
  -> retain prior snapshot on failure or shutdown
  -> show stable ordinary-Chinese status and next action
```

The first executable candidate after architecture acceptance is Mock-only and zero-network. It must not change THS readiness or represent synthetic output as current market truth.

## Authorized files

Exactly:

```text
.codex/tasks/issue-259-today-market-refresh-runtime-integration-v1-preflight.md
docs/today_market_refresh_runtime_integration_v1_preflight.md
```

No other file may change in this architecture PR.

## Required architecture decisions

1. Exact trigger boundary: application startup versus first `/today-market` entry, repeated navigation, explicit retry and shutdown.
2. One deterministic active attempt and idempotency boundary per exact runtime scope/policy.
3. Ownership separation among prior valid snapshot, refresh attempt, acquisition batch, validated candidate and published runtime projection.
4. Closed application/runtime DTO and stable Chinese state projection.
5. Explicit acquisition-port selection with no discovery, fallback, source mixing or arbitrary URL/query input.
6. Exact isolation among persisted local snapshots, synthetic Mock results and future live Provider results.
7. Future THS adapter insertion without duplicating source-specific contracts or bypassing Issue #225.
8. Later API/UI implementation boundary and ordinary-user primary actions.
9. Complete-batch validation and all-or-nothing publication.
10. Concurrency, replay, shutdown, rollback and zero-network CI contracts.
11. Migration/persistence decision. Preferred v1 outcome is no schema, migration or new persistence; otherwise stop and return for owner review.

## Golden path

A prior complete local snapshot renders immediately. One injected stale completed session produces one bounded plan. An explicitly selected deterministic Mock returns a complete synthetic batch. Existing validators accept it, one synthetic candidate projection is exposed atomically, and the UI labels it demo/synthetic. No database, Provider readiness, accepted research, recommendation, portfolio or trading state changes.

## Primary failure path

A required Mock family is partial, schema-invalid or coverage-incomplete. The candidate is rejected, no partial result is exposed, the prior snapshot remains visible and the user receives one stable Chinese reason and explicit next action. Shutdown before publication has the same no-partial-publish outcome.

## Locked invariants

```text
live_ths_gate = Issue #225
production_live_network_authorized = false
overall_live_gate = blocked_quota_contract
schema_migration = prohibited
new_persistence = prohibited unless architecture stops for owner review
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
3. The architecture document resolves every required decision and stop condition.
4. A fresh process-independent fixed-head review contains exactly:

```text
AUTHORIZED TODAY MARKET REFRESH RUNTIME INTEGRATION V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

5. Zero unresolved review threads.
6. Separate explicit project-owner merge authorization.

Architecture merge does not authorize production implementation. Any new commit invalidates prior exact-head CI and review evidence.
