# Issue #221 — Today Market Automatic Daily Refresh Architecture Preflight

## Authority

- Governing Issue: #221.
- Product Roadmap: #137.
- Related source gate: Issue #219 / merged PR #220.
- Project-owner authorization: `确认进行下一步开发` on 2026-07-24.
- Exact architecture base: `16e21bc6e4e8f233ea6ed0a73b011619dad6449d`.
- Branch: `docs/today-market-automatic-daily-refresh-preflight`.
- Risk tier: **Strict Architecture Preflight**.
- Workflow: `.codex/WORKFLOW.md`.

## Objective

Define one bounded, source-specific architecture for the ordinary-user Today Market path:

```text
render the last complete local snapshot immediately
  -> check staleness once at application startup or first Today Market entry
  -> acquire only missing completed trading days from one reviewed source
  -> validate and append immutable source revisions
  -> recompute deterministic market/sector projections
  -> atomically publish one new complete Today Market snapshot
  -> retain the prior valid snapshot on every failure
```

The architecture must cover daily prices, core indices, market overview, sector strength, bounded daily anomalies and readable refresh status without creating a scheduler, background monitor, notification system or trading workflow.

## Selected source candidate

The bounded first candidate is the official Tushare Pro API under one source-specific contract:

- source key: `tushare-pro-daily-market-v1`;
- intended use: personal, local and non-commercial research;
- candidate families: stock identity candidates, exchange trading calendar, unadjusted A-share daily bars, adjustment factors, core-index daily bars, Shenwan 2021 industry definitions and dated membership intervals;
- concept/theme taxonomies are deferred from the first implementation candidate;
- no runtime fallback or source mixing is allowed.

Selection as the architecture candidate does not prove account entitlement or implementation readiness.

## Current gate result

`blocked_pending_tushare_account_facts`

The following remain unsupported by reviewed owner/account evidence:

- exact enabled account capabilities and point/permission level;
- exact approved HTTPS host and transport contract;
- credential lifecycle and revocation behavior;
- automated startup-access permission;
- personal local-retention and reproducibility boundary;
- exact quotas, concurrency, reset time and retry guidance;
- production-reachable sanitized success/error fixtures;
- exact correction, late-arrival and historical-revision behavior for every required family.

Public documentation is sufficient to choose a bounded candidate and define required fields, but it is not sufficient to authorize implementation or live access.

## Authorized files

- `.codex/tasks/issue-221-today-market-automatic-daily-refresh-preflight.md`;
- `docs/today_market_automatic_daily_refresh_preflight.md`;
- `docs/tushare_daily_market_capability_manifest_template.md`;
- optional focused `docs/architecture_baseline.md` synchronization only if needed before fixed-head review.

No production code, schema, migration, dependency, workflow, credential, live request, downloaded Provider data or UI implementation is authorized.

## Required decisions

- source/account capability manifest and deterministic readiness rule;
- stable Today Market scope versus immutable acquired dataset revisions;
- explicit bootstrap versus bounded startup increment;
- exact calendar-based staleness and completed-session rule;
- immutable raw capture, request fingerprint, redaction and ceilings;
- source identity candidate versus accepted Listed Instrument mapping;
- raw/unadjusted daily bars and append-only adjustment-factor semantics;
- exact dated industry membership and unavailable-history behavior;
- deterministic market overview, sector strength, hotspot-state and anomaly rule versions;
- atomic snapshot publication and prior-valid-snapshot retention;
- ordinary-Chinese refresh/error states;
- source-specific migration, rollback and populated-downgrade candidate;
- zero-network CI and disabled opt-in smoke-test separation.

## Required golden path

The architecture must define an offline production-boundary path proving:

1. one reviewed source/capability revision is implementation-ready;
2. one prior complete local Today Market snapshot renders immediately;
3. the reviewed exchange calendar identifies exactly one missing completed session;
4. one bounded no-network request plan is produced;
5. sanitized production-reachable responses bind to exact contract revisions;
6. raw bytes and normalized observations are append-only and provenance-complete;
7. identities resolve only through explicit reviewed mappings;
8. deterministic market and sector calculations use one exact rule version;
9. one complete snapshot is atomically published under dual-as-of boundaries;
10. no Canonical Price, Evidence Ledger, Industry Map, beneficiary, valuation, Investment Candidate, recommendation, portfolio or trading state changes automatically.

The golden path remains specification-only while the account-fact gate is blocked.

## Primary failure path

Any unknown entitlement, host, endpoint, field, unit, calendar, retention, identity, correction or fixture fact blocks readiness. Runtime refresh validation failures retain the prior complete snapshot and expose an ordinary-Chinese reason. The project must not probe the service, guess missing facts, replay a browser session, use an undocumented endpoint or switch to another Provider.

## Locked exclusions

No:

- production adapter, live request or credential setup;
- schema or migration implementation;
- secret/token/Cookie/account identifier in chat, GitHub, repository, database, fixture, log or screenshot;
- generic multi-provider framework, hidden fallback or row mixing;
- per-stock startup request loop;
- full-history automatic bootstrap on application startup;
- scheduler, daemon, continuous polling, notification or work after application close;
- current industry membership represented as historical membership;
- partial universe represented as the full A-share market;
- automatic Canonical Price, Evidence Ledger, Industry Map, beneficiary, valuation or candidate promotion;
- AI-owned deterministic or accepted state;
- recommendation, target price, expected return, holdings, position sizing, broker or trading behavior;
- release, tag or version change.

## Delivery gates

1. Keep the architecture PR Draft.
2. Verify the complete base-to-head diff remains documentation-only and secret-free.
3. Record the final fixed HEAD and exact validation evidence.
4. Obtain process-independent fixed-head architecture review using:

`AUTHORIZED TODAY MARKET AUTOMATIC DAILY REFRESH PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`

5. Resolve all review threads.
6. Await separate explicit project-owner authorization before merge.
7. Do not create a production implementation Issue while the result is `blocked_pending_tushare_account_facts`.
8. Any new commit invalidates fixed-head validation and review evidence.
