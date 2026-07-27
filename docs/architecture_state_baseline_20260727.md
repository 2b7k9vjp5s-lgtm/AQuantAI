# AQuantAI Current-State Baseline — 2026-07-27

## Status and focused authority

This document synchronizes the current repository and governance state after the Today Market deterministic Mock MVP.

It has focused precedence over older current-state, active-gate and next-action statements in `docs/architecture_baseline.md` as of the exact base recorded below.

It does **not** replace or modify the authoritative contracts in `docs/architecture_baseline.md` for:

- product boundary;
- domain and field ownership;
- accepted dependency direction;
- semantic and derivation levels;
- shared architecture invariants;
- migration, history and accepted-state rules.

When this document and the detailed architecture baseline differ outside current-state metadata, fail closed and use the detailed architecture baseline.

## Exact repository baseline

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
default_branch = main
main = 517c39db9dab848faf365e3a1e7bbd9cf94b0663
released_version = 0.2.0
python = >=3.12
state_observed_on = 2026-07-27
```

The current `main` commit is the squash merge of PR #256:

```text
[Strict Implementation] Today Market Deterministic Mock Adapter MVP (#256)
```

Documentation synchronization does not change the released version and does not authorize a release, tag or version change.

## Product boundary remains unchanged

AQuantAI remains a local-first, personal-use, research-only and non-advisory A-share market-intelligence and industry-research workbench.

It is not:

- a broker or order-management system;
- an automated-trading system;
- an investment-advice service;
- a target-price or expected-return generator;
- a multi-user SaaS platform;
- a continuously running monitoring or notification service.

Deterministic calculations, canonicalization, accepted workflow state and history remain outside LLM ownership. No capability recorded here authorizes buy/sell/hold output, position sizing, portfolio execution or trading behavior.

## Accepted capability state

### Industry research and accepted-result flow

The accepted Industry Thesis and ordinary-user flow now includes:

```text
ordinary-language scope
  -> deterministic candidate construction
  -> complete selected / rejected / unresolved review
  -> reviewed-plan v2 with exact Owner Context
  -> zero-write acceptance preview
  -> explicit matching-fingerprint atomic commit
  -> accepted_outputs_linked
  -> exact accepted-result and history reopening
  -> read-only assembled result
  -> optional explicitly selected exact Investment Candidate overlay
```

The latest accepted result-assembly capability is merged through:

```text
architecture PR = #248
implementation PR = #250
merge commit = fcecc3446847ceca0f595c7737323b721ea86ce4
```

The result assembler:

- preserves the complete accepted beneficiary universe;
- keeps immutable accepted Industry Thesis meaning separate from a selected current candidate snapshot;
- never auto-selects latest, first or uniquely available candidate state;
- joins overlays only through exact beneficiary and candidate-pool revisions;
- does not recompute score, status, priority or downstream owner state;
- performs no write, migration, Provider call, AI call, portfolio or trading action.

Older statements that describe Issue #247 result assembly as future or active are superseded by this accepted state.

### THS public acquisition-contract evidence

The official public full-market snapshot and Market Dump evidence amendment is accepted through:

```text
PR = #252
merge commit = 6084b20a2467f02465d3a9a342009a78f58e9773
```

Reviewed public documentation establishes candidate acquisition shapes for:

- current full-market A-share snapshot;
- approximately ten-year unadjusted full-market daily-K Market Dump;
- recent ten-trading-day unadjusted daily-K Market Dump;
- full-history adjustment-factor event Market Dump.

Documented shape does not equal production readiness. Browser Cookie/session replay remains prohibited, and production API-key authentication for Market Dump download links remains unresolved.

### Provider-neutral Today Market application seam

The accepted provider-neutral architecture is merged through:

```text
architecture Issue = #253
architecture PR = #254
merge commit = 66cdf5d4dc69b1bc757e61453b191680c8b61b72
```

The accepted layering is:

```text
Today Market application orchestration
  -> backend.today_market_refresh provider-neutral acquisition port
      -> deterministic synthetic Mock adapter
      -> future source-specific application adapter
           -> datasource.ths_structured_provider
           -> future live transport only after Issue #225
```

Provider-neutral applies only at the application seam. It does not authorize:

- arbitrary endpoint plug-ins;
- hidden Provider fallback;
- cross-Provider row mixing;
- erased source provenance;
- moving source-specific contracts or readiness out of their owner.

### Deterministic Today Market Mock MVP

The zero-network implementation is merged through:

```text
implementation Issue = #255
implementation PR = #256
reviewed head = 42d0de01dee275ac5ae37c1279d18c568aa84b1c
merge commit = 517c39db9dab848faf365e3a1e7bbd9cf94b0663
Issue #255 = closed / completed
```

Implemented slices:

```text
M1 immutable contracts and canonical fingerprints
M2 bounded refresh planning and closed state machine
M3 deterministic synthetic fixture-backed acquisition adapter
M4 prior-snapshot retention, complete-batch validation and demo projection
```

The runtime now contains the additive package:

```text
backend.today_market_refresh
```

Its reviewed behavior includes:

- exact refresh intents, plans, capability families and fingerprints;
- one-session and ten-session automatic Mock planning;
- manual catch-up state above the ten-session ceiling;
- deterministic synthetic source provenance;
- typed redacted fixture and validation failures;
- no candidate publication on partial, schema-invalid or coverage-incomplete batches;
- prior snapshot retention on every rejected candidate path;
- distinct fingerprints for changed synthetic correction scenarios;
- no network, credential, environment-secret, HTTP, socket, subprocess, SQLAlchemy or persistence path.

The Mock is application-test infrastructure only. It does not create a valid live Provider contract or production market observation.

## Synthetic engineering assumption boundary

The accepted Mock-only planning profile is:

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

These values may be used only by deterministic Mock scenarios and tests.

They must not:

- populate THS quota or completion facts;
- change `CapabilityReadiness`;
- be read by a future live adapter;
- prove account entitlement;
- close Issue #225;
- authorize production transport, persistence or automatic refresh.

## Current live THS gate

Issue #225 remains the sole live THS external-contract gate and must remain open.

Current deterministic interpretation:

```text
transport_contract = confirmed
authentication_shape = confirmed
required_candidate_entitlements = partially_confirmed
local_normalized_research_storage = supported_by_official_product_evidence
public_provider_valued_fixtures = prohibited_without_explicit_permission
current_full_market_snapshot_shape = documented
market_dump_shapes = documented
numeric_qps_limit = unresolved
daily_total_limit = unresolved
concurrency_limit = unresolved
completion_time = unresolved
correction_revision_late_data_behavior = unresolved
api_key_lifecycle = unresolved
production_dump_api_key_authentication = unresolved
current_account_dump_entitlement = unresolved
production_implementation_authorized = false
overall_gate = blocked_quota_contract
```

No live Stage C1 Issue, branch, PR, credential boundary, HTTP client, raw capture, source activation, Provider persistence or production smoke request may be created from this state alone.

## Runtime state after PR #256

When the configured local database and assets are available, the reviewed runtime includes all previously accepted research workspaces plus:

1. exact accepted Industry Thesis result assembly with an optional explicit exact candidate overlay;
2. the provider-neutral Today Market refresh contract package;
3. deterministic zero-network Mock planning, acquisition, validation, orchestration and demo projection.

The runtime still does **not** provide:

- application-start or first-entry integration of the refresh state machine into `/today-market`;
- a refresh-status API or ordinary-user runtime state projection;
- persistence of Mock or Provider acquisition candidates;
- real THS transport or credentials;
- automatic trading-calendar or daily-bar acquisition;
- full-market individual-security history;
- immutable raw Provider capture and source normalization;
- corporate-action correction and adjustment implementation;
- dated historical industry/concept membership;
- full-market breadth, turnover or exact limit-price claims;
- production sector-strength/hotspot and stock-anomaly calculations over authorized full coverage;
- official announcement acquisition or first-class manual PDF import;
- background scheduler, push notification or continuous polling.

## Governance state

### Open controlling work

- Issue #137 remains the authoritative product roadmap.
- Issue #225 remains open and controls live THS contract readiness.
- Issue #257 is the Light current-state synchronization task for this document.

### Completed implementation

- Issue #255 is closed as completed after PR #256 merge.

### Merged-work cleanup candidates

The following historical Issues have linked merged work or have been superseded, but remain separate governance items until the project owner explicitly authorizes closure:

```text
#219 controlled THS refresh architecture
#221 Today Market automatic-refresh architecture
#223 THS source synchronization
#227 THS Stage C0 architecture
#230 THS Stage C0 implementation
#232 previous state-baseline housekeeping
#234 owner-acceptance architecture
#238 ordinary-user completion architecture
#242 Owner Context v2 architecture
#245 Owner Context v2 implementation
#253 provider-neutral Mock architecture
```

This state synchronization closes none of them.

### Frozen superseded work

PR #241 remains frozen and read-only:

```text
state = open
draft = true
head = 3116a67ec472131eea3bf3d1bd9daee884c69ee9
resume = prohibited
rebase = prohibited
force_push = prohibited
merge = prohibited
```

Its predecessor Issue #240 is superseded by the accepted Owner Context v2 replacement path. Neither #240 nor #241 may be resumed or modified without an explicit new project-owner decision.

## Next governed product gate

After this baseline synchronization PR is explicitly authorized and merged, the next authorized roadmap phase is:

```text
Today Market Refresh Runtime Integration v1
Strict Architecture Preflight
```

The preflight must be created from the exact post-merge `main` commit and must define only the application/runtime integration boundary for already accepted local snapshot and provider-neutral refresh contracts.

Expected product path:

```text
enter /today-market or application-start entry
  -> render the prior valid local snapshot immediately
  -> perform one deterministic stale check
  -> build one bounded provider-neutral refresh plan
  -> call an explicitly selected acquisition port
  -> validate the complete candidate batch
  -> atomically expose a complete candidate projection
  -> retain the prior snapshot on failure or shutdown
  -> show stable ordinary-Chinese refresh state and next action
```

The preflight must decide:

- exact trigger and idempotency boundaries;
- prior-snapshot versus candidate-snapshot ownership;
- application state DTOs and Chinese-first presentation states;
- Mock/demo mode isolation from production local market data;
- behavior when no live Provider is configured or authorized;
- insertion point for a future THS adapter without weakening Issue #225;
- API/UI scope for a later separately authorized implementation;
- migration and persistence decision;
- rollback, failure and zero-network CI contracts.

The preflight must **not** authorize implementation, live THS access, credentials, Provider-valued fixtures, schema/migration, persistence, scheduler, source fallback, recommendation, portfolio or trading behavior.

## Required execution sequence

```text
Issue #257 baseline synchronization
  -> Light PR
  -> checks and author-side exact-head review
  -> separate explicit owner merge authorization
  -> merge to main
  -> create Runtime Integration Strict Architecture Issue from new exact main
  -> architecture branch and Draft PR
  -> exact-head CI and process-independent fixed-head review
  -> separate explicit owner merge authorization
  -> later separate implementation Issue/PR only after architecture merge
```

The current project-owner instruction authorizes entering the Runtime Integration architecture phase **after** baseline synchronization is merged. It does not waive the separate merge gate for either PR.

## Locked boundaries

This synchronization authorizes no change to:

- runtime code or behavior;
- API or UI routes;
- database schemas or migrations;
- dependencies or workflow configuration;
- Provider transport, credentials or account probing;
- accepted research or candidate history;
- release, tag or version;
- recommendation, target price, expected return, position sizing, broker, order or trading behavior.
