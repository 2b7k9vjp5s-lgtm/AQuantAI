# AQuantAI Current-State Baseline — 2026-07-27

## Status and focused authority

This document synchronizes the current repository and governance state after the accepted Today Market Refresh Runtime Integration v1.

It has focused precedence over older current-state, active-gate and next-action statements in `docs/architecture_baseline.md` as of the exact baseline recorded below.

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
main = 518d14fb6cc40e8dc5804bbed436497bfdb97ee7
released_version = 0.2.0
python = >=3.12
state_observed_on = 2026-07-27
```

The exact `main` commit is the squash merge of PR #262:

```text
[Strict Implementation] Today Market Refresh Runtime Integration v1 (#262)
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

The accepted Industry Thesis and ordinary-user flow includes:

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

### THS public acquisition-contract evidence

Accepted official and public evidence is synchronized through PRs #224, #226 and #252.

Reviewed documentation establishes candidate acquisition shapes for:

- current full-market A-share snapshot;
- approximately ten-year unadjusted full-market daily-K Market Dump;
- recent ten-trading-day unadjusted daily-K Market Dump;
- full-history adjustment-factor event Market Dump;
- source-specific index history and related account-capability candidates.

Documented shape does not equal production readiness. Browser Cookie/session replay remains prohibited, and unresolved account quota, completion, revision and API-key lifecycle facts remain controlled by Issue #225.

### Provider-neutral Today Market acquisition seam

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

The zero-network Mock implementation is accepted through:

```text
implementation Issue = #255
implementation PR = #256
reviewed head = 42d0de01dee275ac5ae37c1279d18c568aa84b1c
merge commit = 517c39db9dab848faf365e3a1e7bbd9cf94b0663
Issue #255 = closed / completed
```

Implemented slices include:

```text
M1 immutable contracts and canonical fingerprints
M2 bounded refresh planning and closed state machine
M3 deterministic synthetic fixture-backed acquisition adapter
M4 prior-snapshot retention, complete-batch validation and demo projection
```

The Mock is application-test infrastructure only. It does not create a valid live Provider contract or production market observation.

### Today Market Refresh Runtime Integration v1

The application/runtime integration architecture and implementation are accepted through:

```text
architecture Issue = #259
architecture PR = #260
architecture reviewed head = 2b021a9ef17332b8afae5611c348bbc6d62ad6c4
implementation Issue = #261
implementation PR = #262
implementation reviewed head = dcf3cf18d962cc91d178a2de1bd5e9c8971594ee
Local Tests = #947
workflow run = 30269900750
merge commit = 518d14fb6cc40e8dc5804bbed436497bfdb97ee7
Issue #261 = closed / completed
PR #262 = closed / merged
```

The accepted runtime contract includes:

- one immutable application-factory Mock configuration;
- default application state `mock_enabled = false` and `mock_scenario_id = null`;
- zero acquisition during raw application/page load;
- one server-owned `runtime_scope_revision_id` as the sole canonical runtime-scope identity;
- one server-owned `runtime_status_fingerprint` covering the complete visible state generation;
- one authoritative prior-snapshot identity and canonical content path using exact selected `IngestionRun` components and service/repository provenance agreement;
- stable prior content fingerprints that exclude only request-time `generated_at_utc` while retaining original projected and technical details;
- `GET /today-market/api/runtime-status` with no acquisition and no database write;
- a closed `POST /today-market/api/runtime-refresh` command that rejects client-owned scenario, source, adapter, fixture, planning-clock, URL, header, query and credential fields;
- optimistic status comparison before planning or acquisition;
- one process-local active attempt per exact scope;
- same-scope concurrent single-flight behavior;
- completed identical replay without reacquisition;
- exactly one bounded `FIRST_TODAY_MARKET_ENTRY` attempt only in explicitly Mock-enabled test/demo application instances;
- explicit retry only after retained-prior failure or cancellation;
- complete synthetic candidate publication only;
- prior persisted snapshot retention on every failure, cancellation or rejected candidate;
- a separate ordinary-Chinese panel visibly labelled `MOCK-ONLY`, `PROCESS-LOCAL` and synthetic/demo;
- no polling, background task, scheduler, daemon or runtime identity in `localStorage`.

Database and HTTP adaptation remain in the existing Today Market API owner. The provider-neutral runtime core contains no SQLAlchemy, database, credential, network, subprocess or HTTP-framework dependency.

## Synthetic engineering assumption boundary

The accepted Mock-only planning profile remains:

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
- change source capability readiness;
- be read by a future live adapter;
- prove account entitlement;
- close Issue #225;
- authorize production transport, persistence or automatic live refresh.

## Current live THS gate

Issue #225 remains the sole live THS external-contract gate and must remain open until its required evidence is reviewed or the gate is explicitly resolved fail-closed.

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

No live Stage C1 Issue, branch, PR, credential boundary, HTTP client, raw Provider capture, source activation, Provider persistence or production smoke request may be created from this state alone.

## Runtime state after PR #262

When the configured local database and assets are available, the reviewed runtime includes:

1. exact accepted Industry Thesis result assembly with an optional explicit exact candidate overlay;
2. provider-neutral Today Market refresh contracts and deterministic Mock acquisition;
3. first-entry runtime status integration over one authoritative local prior snapshot;
4. process-local single-flight, optimistic concurrency and completed replay;
5. Chinese-first synthetic/demo status projection separated from local persisted market state.

The default application still performs no live or Mock acquisition because Mock is disabled and no production source is authorized.

The runtime still does **not** provide:

- real THS transport or credential use;
- automatic trading-calendar or daily-bar acquisition;
- persistence of acquisition candidates or runtime state;
- immutable raw live-Provider capture and source normalization;
- full-market individual-security history;
- corporate-action correction and adjustment implementation;
- dated historical industry/concept membership;
- production full-market breadth, turnover or exact limit-price claims;
- production sector-strength/hotspot and stock-anomaly calculations over authorized full coverage;
- official announcement acquisition or first-class manual PDF import;
- operating-system scheduler, daemon, push notification or continuous polling.

A successful synthetic candidate is not current-market truth and cannot replace the accepted local persisted snapshot.

## Governance state

### Open controlling work

```text
Issue #137 = open / authoritative product roadmap
Issue #225 = open / sole live THS external-contract gate
Issue #263 = open / Light current-state synchronization
open pull requests at Issue #263 creation = none
```

### Completed Runtime Integration work

```text
Issue #259 = closed / completed
PR #260 = closed / merged
Issue #261 = closed / completed
PR #262 = closed / merged
```

### Historical merged-work cleanup candidates

Historical Issues with merged or superseded work remain separate governance items unless the project owner explicitly authorizes closure. This synchronization closes none beyond the separately completed Issue #261.

### Frozen superseded work

PR #241 is closed, unmerged and permanently read-only at:

```text
state = closed
draft = true
merged = false
head = 3116a67ec472131eea3bf3d1bd9daee884c69ee9
reopen = prohibited
resume = prohibited
rebase = prohibited
force_push = prohibited
merge = prohibited
```

Its predecessor Issue #240 is superseded by the accepted Owner Context v2 replacement path. Neither #240 nor #241 may be resumed or modified without an explicit new project-owner decision.

## Next governed gate

The next controlling gate for production Today Market automatic daily data is the existing Issue #225 evidence closure or explicit fail-closed resolution.

Required sequence:

```text
Issue #225 non-secret contract evidence
  -> exact reviewed outcome
  -> ready_for_separate_stage_c_implementation_issue
     or one explicit blocked outcome
  -> separate project-owner instruction
  -> only then create any live Stage C1 architecture or implementation Issue/PR
```

Runtime Integration completion does not bypass this sequence.

While Issue #225 remains blocked:

- no live THS source is enabled;
- no credential boundary or production HTTP transport is added;
- no source-valued fixture enters the public repository;
- no quota, completion or revision value is inferred from the Mock profile;
- no hidden Tushare, AKShare or other Provider fallback is introduced;
- no cross-Provider row mixing is permitted.

Any separate non-live product slice also requires an explicit project-owner instruction and its own governed Issue/PR.

## Required execution sequence for this synchronization

```text
Issue #263
  -> one-file Light documentation branch and Draft PR
  -> exact-head CI and author-side fixed-head review
  -> separate explicit project-owner merge authorization
  -> merge to main
  -> separately choose and authorize the next governed product slice
```

This synchronization does not itself authorize the next architecture or implementation task.

## Locked boundaries

This synchronization authorizes no change to:

- runtime code or behavior;
- API or UI routes;
- database schemas or migrations;
- dependencies, fixtures, executable tests or workflow configuration;
- Provider transport, credentials or account probing;
- accepted research or candidate history;
- release, tag or version;
- recommendation, target price, expected return, position sizing, portfolio, broker, order or trading behavior.
