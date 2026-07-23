# Issue #211 — Personal Research Workbench UI Phase 2A Implementation

## Authority

- Product roadmap: #137
- Approved architecture: Issue #208 / merged PR #209
- Implementation Issue: #211
- Required exact base: `e5b201a88d62292d79455879bd56375da4f7f38c`
- Branch: `feat/personal-research-workbench-ui-phase2a`
- Owner direction: `进行下一步开发` on 2026-07-23
- Risk tier: Strict implementation

This task authorizes implementation and validation only. It does not authorize merge, release, tag or version changes.

## Objective

Implement one honest local-only Today Market slice:

```text
explicit persisted local equity series
  + optional explicit persisted benchmark and sector series
  + required information cutoff and recorded-UTC boundary
  -> existing MarketCockpitService calculations
  -> Chinese-first /today-market page
```

## Authoritative owners

- Ingestion runs and rows: existing market-data persistence.
- Exact series identity: `backend.database.series`.
- Price, liquidity, benchmark and sector calculations: existing Market Cockpit repositories, calculators and service.
- Today Market: read-only catalog, chronology adapter, Chinese grouping and presentation only.

## Accepted implementation boundary

- `GET /today-market`.
- `GET /today-market/api/local-series` with both explicit as-of boundaries.
- `GET /today-market/api/snapshot` with an exact equity key, optional exact benchmark/sector keys and both boundaries.
- At most 20 options per family; no automatic selection.
- Optional recorded-UTC repository filter that leaves legacy Market Cockpit behavior unchanged when omitted.
- Static HTML/CSS/vanilla JavaScript; no new framework or dependency.
- One selection-first primary action: `查看本地市场快照`.
- Scope/freshness first, deterministic analysis second, unavailable capability notices third, technical details last.

## Query ceilings

- Catalog: at most 4 SQL statements, implemented as one bounded ingestion-run query.
- Snapshot: at most 14 SQL statements. Existing repository path uses at most 9 when equity, benchmark and sector are all selected.
- No row-by-row SQL loops.

## Golden path

1. Persist one successful complete exact equity series, benchmark series and sector series.
2. Read the catalog under explicit information and recorded-UTC boundaries.
3. Return all three families without a selected option.
4. User explicitly selects exact keys and requests the snapshot.
5. Existing MarketCockpitService owns all calculations.
6. Page renders selected-universe price/liquidity, optional benchmark/sector, scope, freshness and alignment.
7. Unsupported breadth, anomaly, events/causes, attention and remote refresh remain unavailable.
8. Technical provenance is collapsed by default.
9. No write, network, Provider, AI or background action occurs.

## Primary failure path

A recorded-UTC boundary earlier than the selected run's imported or completed chronology returns not-visible/not-found. The system does not select another key, a later run or a later timestamp.

## Authorized file families

- this task snapshot;
- `backend/api/today_market.py`;
- bounded optional recorded-UTC changes in existing Market Cockpit repositories and, only if required, their API/service compatibility seams;
- `today_market/static/**`;
- minimal `backend/main.py` route/router/static registration;
- bounded workbench navigation HTML updates;
- `tests/test_today_market*` and focused Market Cockpit regression tests;
- one offline Today Market demo and a workflow entry only if needed.

## Validation

- request validation occurs before database construction where practical;
- exact identity validation and deterministic catalog ordering;
- recorded-UTC leakage prevention for equity, benchmark and sector;
- unchanged legacy `/market-cockpit/snapshot` behavior;
- stable Chinese 404/409/422/503 responses;
- selection-first page with no automatic snapshot request;
- query ceilings measured in tests;
- full relevant pytest suite and offline golden-path demo;
- no external network, writes, AI, credentials, scheduler or notification;
- base-to-head inventory remains inside Issue #211 families.

## Stop conditions

Return to architecture if implementation requires a new table or registry, schema/migration, Provider/network, credential, scheduler, dependency, front-end framework, duplicated Market Cockpit calculation owner, full-market identity inference, anomaly/event cause inference, investment semantics or row-count-dependent queries.

## Locked exclusions

No schema, migration, table, dependency, Provider adapter, credential, live request, remote refresh, scheduler, background worker, notification, news/announcement ingestion, market-attention acquisition, full-market claim, anomaly/cause inference, AI call, accepted evidence or research-state mutation, Investment Candidate mutation, recommendation, target price, expected return, position sizing, follow state, portfolio, broker, order, automated trading, release, tag or version change.

## Delivery gates

- one Draft implementation PR;
- all validation succeeds on one fixed final HEAD;
- fresh fixed-head implementation review with:

`AUTHORIZED PERSONAL RESEARCH WORKBENCH UI PHASE 2A IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>`

- no unresolved review threads;
- separate project-owner authorization before merge;
- every new commit invalidates prior fixed-head CI and review evidence.
