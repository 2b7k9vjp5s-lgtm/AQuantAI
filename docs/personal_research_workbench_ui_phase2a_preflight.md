# Personal Research Workbench UI Phase 2A — Today Market Local Snapshot

## 1. Decision status

This document defines the first bounded **今日市场** product slice after the completed Personal Research Workbench UI Phase 1A–1D.

The selected direction is:

```text
explicit persisted local market-data series
  -> exact local read under information-cutoff and recorded-UTC boundaries
  -> existing Market Cockpit deterministic calculations
  -> non-persistent Chinese-first Today Market presentation
```

Phase 2A is deliberately **local snapshot only**. It does not implement a Provider, remote refresh, intraday feed, scheduler, market-news timeline, stock-anomaly cause engine or recommendation system.

The architecture is ready for a later bounded implementation only after this preflight receives fixed-head approval and merge authorization.

## 2. Why this is the next phase

The five-module target is:

1. 今日市场;
2. 产业研究;
3. 关注与跟踪;
4. 研究组合;
5. 系统设置.

产业研究 and 系统设置 are already active through UI Phase 1. The next product module in the accepted sequence is 今日市场.

A full Today Market implementation depends on an authorized market-data Provider and refresh contract. The account-authorized THS architecture is accepted, but production access remains blocked until account-specific non-secret capability, host, endpoint, pagination, timestamp, rate-limit, retention and revision facts are reviewed.

The repository already contains a useful offline foundation:

- persisted complete equity-series snapshots;
- persisted benchmark-series snapshots;
- persisted sector-series snapshots;
- exact SHA-256 series identities;
- database-backed repositories;
- deterministic Market Cockpit calculations;
- explicit scope, completeness, session-alignment and provenance warnings;
- a read-only FastAPI route that performs no network access.

Therefore the smallest honest next slice is a local presentation over existing persisted snapshots.

## 3. Product job

A user should be able to answer:

> 在我明确选择的本地数据范围和截止时间内，市场价格行为、流动性、基准和行业强弱是什么状态？这些数据覆盖了什么，又缺少什么？

The page must not imply:

- complete A-share coverage;
- real-time or intraday freshness;
- authoritative full-market breadth;
- a causal explanation for market movement;
- investment quality or trading advice.

## 4. Canonical route and navigation

### 4.1 Page route

Phase 2A uses:

```text
GET /today-market
```

The route serves one static Chinese-first page using the existing application shell.

### 4.2 Workbench entry

`GET /workbench` continues to redirect to `/industry-analysis` in Phase 2A.

Reason:

- 产业研究 remains the product's highest-priority and most complete workflow;
- changing the default home route is a separate product preference decision;
- Today Market may have no local eligible series on a new installation;
- the user can explicitly select 今日市场 from the primary navigation.

A later ordinary setting may choose a default page, but Phase 2A does not add that persistence or behavior.

### 4.3 Navigation activation

The shared shell displays:

- 今日市场 — active, links to `/today-market`;
- 产业研究 — active, links to `/industry-analysis`;
- 关注与跟踪 — disabled, labelled 后续阶段;
- 研究组合 — disabled, labelled 后续阶段;
- 系统设置 — active, links to `/workbench/settings`.

No disabled module may show sample values as live state.

## 5. Existing owner and dependency direction

Phase 2A must not create a second market calculation or data owner.

```text
IngestionRun + persisted source rows
  -> validated equity / benchmark / sector series identities
  -> existing MarketCockpitRepository / BenchmarkRepository / SectorRepository
  -> existing MarketCockpitService
  -> bounded non-persistent Today Market adapter
  -> static Today Market page
```

Ownership remains:

- source runs and source-normalized rows: market-data persistence;
- exact series identity: `backend.database.series`;
- market, benchmark and sector calculations: existing Market Cockpit calculators/service;
- page labels, grouping and notices: non-persistent Today Market view model;
- red/green convention and density: existing browser-local settings;
- Canonical Price: separate owner and not used to relabel Market Cockpit source observations;
- accepted investment-candidate state: separate owner and never changed by this page.

## 6. Local series catalog

### 6.1 Purpose

The existing `/market-cockpit/snapshot` API correctly requires explicit SHA-256 `series_key` values. Those keys are appropriate internal identities but are not suitable ordinary-user inputs.

Phase 2A adds a bounded read-only catalog adapter. It does not create a new persisted registry.

### 6.2 Catalog route

```text
GET /today-market/api/local-series
  ?as_of_cutoff=YYYY-MM-DD
  &as_of_recorded_at_utc=<explicit UTC timestamp>
```

Both boundaries are required.

### 6.3 Eligible rows

The catalog reads only `IngestionRun` rows that are:

- `status = succeeded`;
- `snapshot_mode = complete`;
- visible at or before `as_of_cutoff`;
- completed and locally recorded at or before `as_of_recorded_at_utc`;
- members of one closed dataset family:
  - equity: `market_data_bundle`;
  - benchmark: accepted benchmark dataset constant;
  - sector: accepted sector dataset constant;
- backed by a valid canonical series identity whose recomputed SHA-256 equals the stored `series_key`.

A row with missing or invalid identity, chronology or completion state is not silently repaired or displayed as eligible.

### 6.4 Deduplication and ordering

The catalog returns at most 20 options per family.

For each exact `series_key`, expose the latest visible successful complete run under both supplied boundaries. Do not combine rows from different series.

Deterministic ordering:

1. visible information cutoff descending;
2. visible completion/recorded time descending;
3. readable label ascending;
4. exact `series_key` ascending.

This ordering is presentation only. It does not select an option.

### 6.5 Readable labels

Labels are deterministic projections of validated canonical identity fields, not inferred market meaning.

Equity example shape:

```text
股票范围 · 128家公司 · 2025-01-01 至 2026-06-30 · 不复权 · provider-id
```

Benchmark example shape:

```text
基准指数 · 000001, 399001 · 2025-01-01 至 2026-06-30 · provider-id
```

Sector example shape:

```text
行业范围 · classification-system / level · 31个行业 · 2025-01-01 至 2026-06-30 · provider-id
```

The page may show a bounded code preview and count. It must not claim “全A股”, “主要指数” or “全行业” unless the exact accepted selector contract owns that statement.

### 6.6 No automatic selection

- No first option is selected automatically.
- No newest option is selected automatically.
- Browser-local prior selection may be restored only when the exact key is still visible under the current boundaries and the user previously chose it explicitly.
- Restoring a choice does not trigger a snapshot request until the user activates `查看本地市场快照`.
- Benchmark and sector choices remain optional and independent.
- No name, Provider or date-range similarity establishes compatibility.

## 7. Snapshot API

### 7.1 Route

```text
GET /today-market/api/snapshot
  ?equity_series_key=<exact key>
  &benchmark_series_key=<optional exact key>
  &sector_series_key=<optional exact key>
  &as_of_cutoff=YYYY-MM-DD
  &as_of_recorded_at_utc=<explicit UTC timestamp>
```

### 7.2 Recorded-UTC correction

The legacy Market Cockpit route selects by information cutoff and then orders visible runs by completion time, but it does not accept a caller-supplied recorded-UTC boundary.

Phase 2A must not claim dual-as-of reproducibility while using that legacy selection unchanged.

The implementation must add a bounded read-only compatibility seam so each repository can select only a succeeded complete run satisfying both:

```text
information_cutoff_date <= as_of_cutoff
completed_at <= as_of_recorded_at_utc
imported_at <= as_of_recorded_at_utc
```

Where a source contract exposes another system-owned local recording timestamp, it may be validated additionally, but no user-controlled Provider timestamp substitutes for local chronology.

The change must:

- preserve the existing default behavior for the legacy `/market-cockpit/snapshot` route;
- add the explicit boundary only for the Today Market adapter or as an optional repository/service argument with regression coverage;
- never rebind to a later run;
- never select another compatible-looking series;
- fail with not-visible/not-found when no run satisfies both boundaries.

### 7.3 Delegation

After exact run visibility is established, the adapter delegates calculation to the existing `MarketCockpitService`.

The Today Market adapter may translate existing contract fields into Chinese labels and grouped view data. It may not:

- recalculate market metrics;
- change thresholds or ranking rules;
- drop warnings;
- turn `partial`, `insufficient_data`, `different_session` or `different_cutoff` into success;
- relabel source-normalized prices as Canonical Price;
- infer cause, opportunity or recommendation.

### 7.4 Query ceiling

- catalog: maximum 4 SQL statements independent of returned option count;
- one Today Market snapshot: maximum 14 SQL statements independent of stock, benchmark or sector row count;
- no per-stock, per-index or per-sector query loop;
- no initial claim/evidence, Company Research or Investment Candidate loading.

The implementation must record actual measured counts in tests. If the current repository path exceeds the ceiling, return to Issue #208 before creating a generic cache or query framework.

## 8. Supported page content

### 8.1 Scope and freshness strip

Always visible:

- local-only badge;
- selected equity scope label;
- optional benchmark and sector scope labels;
- requested information cutoff;
- requested recorded-UTC boundary;
- effective equity session;
- effective benchmark and sector sessions when present;
- source information cutoff;
- local ingestion completion/recorded time;
- scope coverage status;
- calculation/completeness status;
- alignment status;
- `不是全市场覆盖` notice.

### 8.2 Selected-universe overview

Only existing Market Cockpit metrics may appear.

The page groups them as:

- 价格行为;
- 流动性;
- 数据完整性.

Labels must describe the exact selected universe. A metric whose calculation state is unavailable remains visibly unavailable with its existing reason/warning.

### 8.3 Benchmark context

When an explicit benchmark series is selected and visible:

- display every returned exact benchmark metric;
- show benchmark codes and effective session;
- show alignment and missing-code notices;
- retain exact provenance in progressive details.

When no benchmark is selected, show `未选择本地基准数据` rather than an empty chart or inferred default.

### 8.4 Sector context

When an explicit sector series is selected and visible:

- display existing deterministic sector cross-section;
- display existing ranked metrics in their accepted ordering;
- show taxonomy/classification level, requested and available counts;
- show missing sector codes and session/cutoff alignment;
- show exact provenance in progressive details.

Sector strength is market behavior within the exact selected local classification scope. It is not industry benefit certainty or investment quality.

### 8.5 Warnings and technical details

Warnings are first-class output and cannot be hidden by a successful HTTP status.

Progressive technical details may expose:

- exact series keys;
- ingestion run IDs;
- Provider and dataset IDs;
- contract and adapter versions;
- canonical selector payload summaries;
- source endpoints as public identifiers only;
- collection/import/completion timestamps;
- package version and network-mode metadata already stored locally.

Credentials, raw connection values, local filesystem paths and secrets never appear.

## 9. Explicitly unavailable sections

The page contains compact unavailable cards, not blank placeholders or invented values, for:

### 9.1 Full-market breadth

Unavailable unless a later exact accepted contract proves full-scope membership and breadth semantics:

- advancing/declining counts;
- limit-up/limit-down counts;
- total-market turnover;
- all-market new highs/lows.

Existing selected-universe participation metrics may be displayed only under the selected-universe label.

### 9.2 Stock anomalies

Not in Phase 2A:

- largest gains/declines;
- unusual volume;
- rapid moves/gaps;
- new highs/lows;
- followed-company anomalies.

The page must not derive an anomaly list from current snapshot rows without a separately reviewed anomaly contract.

### 9.3 Events and causes

Not in Phase 2A:

- policy/news/announcement timeline;
- price-move cause attribution;
- Provider reason-text parsing;
- evidence acceptance;
- automatic launch of a research session from an event.

### 9.4 Refresh

Not in Phase 2A:

- remote manual refresh;
- auto-refresh;
- scheduler/background polling;
- live/intraday updates;
- notification.

The only action is `重新读取本地快照`, which repeats a database read under the same explicit selections and boundaries. It performs no network request.

## 10. Error and state contract

Stable responses contain a Chinese message and technical code. They never include SQL, stack traces, credentials or raw connection values.

- `400`: malformed query encoding where applicable;
- `404`: exact series/run not found or not visible under both boundaries;
- `409`: selected exact series becomes stale/inconsistent between catalog and snapshot read, or canonical identity conflicts;
- `422`: missing/invalid key, cutoff, UTC boundary or incompatible exact source graph;
- `503`: local database unavailable or database query failure.

Page states:

- loading catalog;
- no eligible local data;
- selection required;
- loading snapshot;
- complete selected scope;
- partial selected scope;
- insufficient data;
- mixed cutoff;
- mixed session;
- stale/not visible;
- database unavailable;
- unsupported future feature.

A failed read preserves user selections. It does not switch keys, advance boundaries or retry automatically.

## 11. Presentation and accessibility

- Chinese-first copy;
- static HTML/CSS/vanilla JavaScript;
- no Node/npm/bundler;
- keyboard-operable selectors, buttons and disclosure sections;
- visible focus states;
- semantic headings, lists, tables and status text;
- color is never the only carrier of gain/loss or warning meaning;
- browser-local red/green preference changes presentation only;
- compact desktop layout adapts into stacked cards on narrow screens;
- no chart is required for Phase 2A; if a simple chart is later proposed, it must use existing returned values and accessible text equivalents without adding a framework.

## 12. No-write and no-network contract

The following actions perform zero database writes and zero external network calls:

- import/startup;
- page load;
- local series catalog;
- snapshot read;
- changing selectors;
- browser back/forward;
- tests and CI;
- offline fixture demo.

The page has no Provider credential input, refresh token, AI action, follow action, portfolio action or trading control.

## 13. Production-realistic offline golden path

The future implementation must use normal persisted production boundaries to prove:

1. persist one successful complete equity snapshot with exact series identity;
2. persist one successful complete benchmark snapshot;
3. persist one successful complete sector snapshot;
4. request a catalog under explicit cutoff and recorded UTC;
5. catalog returns all three families with no selected option;
6. user explicitly selects the three exact keys;
7. snapshot route delegates to Market Cockpit calculations;
8. page receives selected-universe price/liquidity, benchmark and sector context;
9. effective sessions, scope warning, completeness and alignment remain visible;
10. technical details reproduce exact series/run provenance;
11. breadth, anomalies, events and remote refresh remain explicitly unavailable;
12. a recorded-UTC boundary before the runs returns not-visible and no fallback;
13. no network, AI or write occurs.

## 14. Required failure tests

- invalid SHA-256 key rejected before database construction where possible;
- malformed cutoff/UTC rejected before database construction;
- no first/newest automatic selection;
- catalog limit and deterministic ordering;
- invalid canonical identity excluded or fails closed;
- equity run later than recorded boundary cannot leak;
- benchmark/sector run later than recorded boundary cannot leak;
- unknown exact series returns 404;
- mixed sessions/cutoffs remain explicit warnings, not silent alignment;
- missing benchmark/sector selection remains optional and explicit;
- database unavailable returns stable 503;
- no full-market labels for selected-universe calculations;
- no anomaly/event/cause/live wording presented as active capability;
- no network request in imports, API, page, tests or demo;
- fixed query ceilings;
- shell activation and disabled later modules;
- browser-local settings remain presentation-only.

## 15. Future implementation boundary

After this architecture is approved and merged, create one linked implementation Issue from the exact resulting `main` SHA.

Authorized file families:

- `.codex/tasks/issue-<N>-personal-research-workbench-ui-phase2a-*`;
- `backend/api/today_market.py`;
- bounded optional recorded-UTC arguments in:
  - `market_cockpit/repository.py`;
  - `market_cockpit/benchmark_repository.py`;
  - `market_cockpit/sector_repository.py`;
  - `market_cockpit/service.py`;
  - `backend/api/market_cockpit.py` only when compatibility tests require it;
- one non-persistent `today_market` projection module;
- minimal `backend/main.py` route/static registration;
- `today_market/static/**`;
- bounded shared workbench shell assets only for navigation activation;
- `tests/test_today_market*`;
- focused existing Market Cockpit tests for recorded-UTC compatibility and regressions;
- one production-boundary offline Today Market demo;
- `.github/workflows/local-tests.yml` only to add that demo without removing or weakening existing checks.

No other file is authorized without an Issue amendment.

## 16. Stop conditions

Return to architecture rather than implementing if:

- a safe exact local catalog requires a new persisted registry;
- recorded-UTC visibility cannot be enforced without changing historical ownership;
- ordinary usage requires manually typing series hashes;
- Market Cockpit must be replaced or duplicated to serve the page;
- the page needs Provider access, network refresh, scheduler or credentials;
- a requested metric requires full-market membership not owned by the selected series;
- anomaly or event meaning requires unreviewed inference;
- query behavior becomes row-count dependent;
- a schema, migration, dependency or framework becomes necessary;
- market behavior would be represented as investment quality or advice.

## 17. Locked exclusions

Phase 2A excludes:

- production Provider/THS adapter;
- credentials or account configuration;
- live/intraday acquisition;
- network/manual remote refresh;
- scheduler/background worker;
- notifications;
- news, announcement or event ingestion;
- market-attention/fund-flow/social data;
- stock-anomaly and cause engine;
- full-market coverage claim;
- Canonical Price promotion;
- accepted evidence or research-state mutation;
- automatic Industry Thesis creation;
- Investment Candidate score/status mutation;
- recommendation, target price, expected return or position size;
- follow state or portfolio ledger;
- broker, order or automated trading;
- AI call;
- schema, migration, dependency, release, tag or version change.

## 18. Definition of Ready

The implementation is ready only when this document and Issue #208 receive fixed-head approval proving:

- exact route and navigation behavior;
- local series catalog semantics and no auto-selection;
- explicit dual-as-of visibility for selected runs;
- deterministic delegation to existing Market Cockpit ownership;
- supported and unavailable content;
- bounded queries and error states;
- no schema/migration/Provider/network requirement;
- accessible presentation and honest coverage notices;
- offline golden and failure paths;
- exact future file families and stop conditions.

Required approval phrase:

`AUTHORIZED PERSONAL RESEARCH WORKBENCH UI PHASE 2A PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`
