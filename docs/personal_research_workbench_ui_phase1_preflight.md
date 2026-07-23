# Chinese Personal Investment Research Workbench UI Phase 1

## 1. Decision status

- Authoritative Issue: #198.
- Product Roadmap: #137.
- Required base: `1ce3abace07d00e60fd911f9cc4f96a768f47a06`.
- Risk tier: **Strict architecture**.
- This document is a Product / Architecture Preflight for **UI Phase 1 — Research Workbench only**.
- It authorizes no production UI, API, schema, migration, dependency, Provider, scheduler, AI, portfolio, trading, release, tag or version change.

## 2. Product decision

AQuantAI should converge on one Chinese-first application shell with five visible product areas:

1. 今日市场;
2. 产业研究;
3. 关注与跟踪;
4. 研究组合;
5. 系统设置.

Phase 1 activates only the manual/offline **产业研究** workbench and minimal browser-local display settings. Future modules remain visibly planned but disabled. They must not show fabricated market, tracking or portfolio values.

The Phase 1 outcome is:

```text
ordinary Chinese thesis input
  -> explicit scope confirmation
  -> exact local thesis session/revision
  -> deterministic proposals from exact local selections
  -> complete reviewed local-scope candidate universe
  -> selected / rejected / unresolved review
  -> exact reviewed-plan result and history reopening
```

Users do not type or copy UUIDs, revision numbers, fingerprints or database URLs. Those values remain available through advanced technical details and exact internal links.

## 3. Feasibility decision

### 3.1 Existing usable foundation

The accepted runtime already provides:

- append-only Industry Thesis session creation and revision;
- exact local candidate proposal persistence;
- exact candidate-universe reads under information-cutoff and recorded-UTC boundaries;
- explicit `selected_for_acceptance`, `rejected_by_user` and `unresolved` review;
- deterministic reviewed-plan preview and fingerprint;
- existing Industry Map, Stage 1 beneficiary, Typed Beneficiary Semantics, Company Research, Evidence Intelligence, Canonical Price, normalized valuation and Investment Candidate reads;
- static HTML/CSS/vanilla JavaScript pages served by FastAPI;
- local database and no-network test discipline.

### 3.2 Unavailable capabilities

The current runtime does not provide:

- free-text-only automatic full-market company discovery;
- an accepted owner transaction from a reviewed plan into Industry Map / Stage 1 and output links;
- automatic downstream Investment Candidate snapshots for a new thesis;
- authorized news/announcement/market-data acquisition for daily hotspot detection;
- scheduler, notifications, followed-entity state or portfolio ledger.

Phase 1 must not claim that a vague phrase has automatically found all beneficiaries or produced final investable companies.

### 3.3 Practical Phase 1 behavior

A vague thesis may start the workflow, but candidate build requires at least one explicit deterministic source:

- an exact existing Industry Map revision;
- an exact accepted local mapping when available;
- an explicitly selected persisted company or listed-instrument record as a user seed.

Local text search may help users find options, but text, ticker prefix, similarity or model output never establishes identity. Explicit selection of one persisted result establishes the chosen identity.

The universe label is always **当前已审阅本地范围全量**, paired with one coverage state:

- `reviewed_local_scope`;
- `partial_local_coverage`;
- `coverage_unknown`.

## 4. Technology and shell decision

### 4.1 Front-end stack

Reuse the current repository stack:

- FastAPI page and JSON routes;
- static HTML;
- shared CSS custom properties;
- vanilla JavaScript with same-origin `fetch`;
- no Node, npm, bundler, React, Vue or other front-end framework;
- no new server-side template engine unless implementation proves static composition impossible.

This matches the existing Dashboard, Market Cockpit, Evidence Intelligence, Industry Research, Company Research, Company Comparison and Investment Candidate pages.

### 4.2 Shell layout

The new workbench pages use a shared shell without refactoring all existing pages in Phase 1:

- fixed left navigation;
- sticky top bar;
- central workspace;
- optional right evidence/details drawer;
- global `aria-live` status region;
- skip link to main content.

Existing standalone pages remain valid advanced/read-only tools.

### 4.3 Top bar contract

Phase 1 top bar contains:

- **本地搜索**: searches only visible local research sessions, exact Industry Map options and persisted company/instrument options;
- **快速研究**: links to `/industry-analysis/new`;
- **数据边界**: displays the active information cutoff and recorded-UTC boundary;
- **本地状态**: database available/unavailable and current operation state;
- **通知**: disabled with `后续阶段`, because no notification contract exists;
- **设置**: links to `/workbench/settings`.

Search is navigation assistance only. It does not create identity, evidence, membership or candidate status and never calls a network or model.

### 4.4 Persistence decision

No UI database tables are added.

- Research history comes from Industry Thesis identities/revisions.
- Decisions come from candidate revisions.
- Results come from reviewed-plan revisions.
- Appearance/density preferences may use browser `localStorage`.
- Credentials, model profiles and Provider configuration are not stored through Phase 1 UI.

## 5. Canonical page routes

| Route | User job | State |
| --- | --- | --- |
| `GET /workbench` | Enter the personal research application | Redirect to `/industry-analysis` |
| `GET /industry-analysis` | View active and historical manual research sessions | Active |
| `GET /industry-analysis/new` | Enter thesis and confirm explicit scope | Active |
| `GET /industry-analysis/sessions/{session_id}/revisions/{session_revision_id}/review` | Review one exact source revision and its complete candidate universe | Active |
| `GET /industry-analysis/sessions/{session_id}/revisions/{reviewed_session_revision_id}/result` | View one exact reviewed-plan revision | Active |
| `GET /workbench/settings` | Adjust browser-local display preferences | Minimal Phase 1 |

今日市场, 关注与跟踪 and 研究组合 are rendered disabled with `aria-disabled="true"` and `后续阶段`. They receive no fake page route in Phase 1.

### Identifier policy

- Session and revision IDs may appear in URLs after user selection or creation.
- Users never manually enter them.
- The server cross-checks that the route session ID owns the route revision ID.
- Candidate revision IDs and fingerprints remain internal or advanced metadata.
- Browser back/forward never issues a write.
- Review and result deep links are exact and never silently move to a newer revision.

## 6. Canonical API boundary

Use router prefix `/industry-analysis/api`. It is a local web adapter over accepted services, not a new business owner.

### 6.1 Reads

| Endpoint | Purpose | Owner/service |
| --- | --- | --- |
| `GET /industry-analysis/api/bootstrap` | Shell capability flags, local database state and active boundaries | Thin adapter |
| `GET /industry-analysis/api/sessions` | Deterministic history under explicit boundaries | New read method over thesis identities/revisions |
| `GET /industry-analysis/api/sessions/{session_id}` | Exact session chronology under explicit boundaries | `IndustryThesisQueryService.get_session` |
| `GET /industry-analysis/api/session-revisions/{session_revision_id}` | Exact scope revision | `IndustryThesisQueryService.get_session_revision` |
| `GET /industry-analysis/api/session-revisions/{session_revision_id}/candidates` | Complete exact candidate universe | `IndustryThesisQueryService.list_candidate_revisions` |
| `GET /industry-analysis/api/reviewed-plans/{reviewed_session_revision_id}` | Exact verified reviewed plan | `IndustryThesisReviewedPlanQueryService.get_reviewed_plan` |
| `GET /industry-analysis/api/candidate-revisions/{candidate_revision_id}/details` | Exact candidate source/provenance and supported linked-owner details | Bounded composition adapter |
| `GET /industry-analysis/api/local-options/maps` | Selectable exact local Industry Map revisions | Existing map query services |
| `GET /industry-analysis/api/local-options/companies` | Persisted company/instrument candidates requiring explicit selection | Bounded local identity query |
| `GET /industry-analysis/api/search` | Local navigation results across sessions/maps/companies | Presentation-only search adapter |

Every time-aware read uses one explicit pair:

- `as_of_cutoff`;
- `as_of_recorded_at_utc`.

Responses return the pair, and pages display it as `数据截止` and `系统记录边界`.

The candidate-details endpoint is keyed by one exact candidate revision. It may follow only exact stored source references or exact owner IDs. It never performs generic text inference or latest-record fallback.

### 6.2 Writes

| Endpoint | Purpose | Owner/service |
| --- | --- | --- |
| `POST /industry-analysis/api/sessions` | Create one exact thesis session | `IndustryThesisCommandService.create_session` |
| `POST /industry-analysis/api/sessions/{session_id}/revisions` | Confirm/edit scope through append-only revision | `IndustryThesisCommandService.revise_session` |
| `POST /industry-analysis/api/session-revisions/{session_revision_id}/candidate-builds` | Persist candidates from exact selected sources | `IndustryThesisCommandService.build_candidates` plus bounded proposal composer |
| `POST /industry-analysis/api/session-revisions/{session_revision_id}/reviews` | Review the complete universe and create a reviewed plan | `IndustryThesisProposalReviewService.review_candidates` |

Rules:

- JSON only;
- strict Pydantic models with extra fields forbidden;
- maximum body size 1 MiB;
- no writes through `GET`;
- no CORS enablement;
- same-origin fetch only;
- no automatic retry;
- no hidden AI or network call;
- structured error code plus Chinese user message;
- expected-latest and atomic domain behavior preserved.

### 6.3 Review dry-run

The review page provides:

1. `检查审阅结果` -> `dry_run=true`;
2. `保存审阅计划` -> commit the same normalized decisions and expected-latest values.

Any state change between the two calls returns a conflict. The UI retains unsaved decisions and requires explicit reload/review; it never auto-rebases.

## 7. Existing-service inventory

### Directly reusable

- `IndustryThesisCommandService.create_session`;
- `IndustryThesisCommandService.revise_session`;
- `IndustryThesisCommandService.build_candidates`;
- `IndustryThesisQueryService.get_session`;
- `IndustryThesisQueryService.get_session_revision`;
- `IndustryThesisQueryService.list_candidate_revisions`;
- `IndustryThesisProposalReviewService.review_candidates`;
- `IndustryThesisReviewedPlanQueryService.get_reviewed_plan`;
- existing Industry Map/Beneficiary/Company Research/Evidence/Investment Candidate/Price/Valuation read services where exact IDs already exist.

### Not directly available

- session-history listing;
- bounded local map/company option search designed for explicit selection;
- deterministic conversion of exact UI selections into candidate proposal payloads;
- Chinese page view-model composition;
- browser page/API routes.

### Intentionally unavailable

- reviewed-plan owner acceptance;
- output-link writes;
- automatic company research or Investment Candidate snapshot creation;
- Provider/scheduler/notification/portfolio behavior.

## 8. Required bounded backend seams

### 8.1 Session-history query

Add a read-only method returning:

- session ID and state;
- exact visible latest revision ID/number;
- title or thesis excerpt;
- driver and horizon;
- workflow and coverage states;
- bounded candidate/review counts when available;
- cutoff and recorded time;
- primary next action.

Order by visible latest recorded UTC descending, then session ID ascending. No fuzzy latest fallback.

### 8.2 Exact local-option queries

Map options return exact visible map/revision IDs.

Company options:

- require at least two characters unless an exact code is supplied;
- return at most 20 records;
- include exact persisted IDs and source metadata;
- use deterministic name/code/ID order;
- never auto-select the first result;
- never use provider name alone as identity.

### 8.3 Deterministic proposal composer

Convert exact selections into the existing candidate-build proposal objects.

Allowed sources:

- exact accepted local mapping;
- exact Industry Map/beneficiary revision;
- exact user-selected StockBasic or ListedInstrument identity.

It may copy labels and exact references. It may not infer exposure, benefit strength, product fit or industry position from company name or thesis text. Unsupported fields remain unknown, nullable or unresolved under the accepted contract.

### 8.4 Non-persistent view-model adapter

May:

- translate closed enums to Chinese labels;
- group exact rows;
- calculate counts from the returned complete universe;
- generate exact navigation links;
- expose owner/source metadata.

May not:

- create scores;
- infer identity or benefit classification;
- choose decisions;
- hide rejected/unresolved rows;
- parse narrative valuation into numbers;
- choose newer domain revisions.

### 8.5 Local search adapter

Searches only:

- visible thesis sessions;
- visible exact Industry Map options;
- persisted company/instrument options.

It returns grouped navigation candidates. Search results are not accepted identity until the user explicitly selects an exact record in the relevant workflow.

## 9. Page architecture

### 9.1 Research home `/industry-analysis`

User job: start a new manual research session or reopen one.

Content:

- boundary statement;
- dominant `发起新研究` action;
- tabs: 每日产业雷达 disabled, 发起新研究, 研究进行中, 历史研究;
- compact session cards/table;
- database and boundary status;
- no market-hotspot content.

Session card:

- title/thesis excerpt;
- workflow, driver and coverage;
- counts by review state when available;
- cutoff and last recorded time;
- `继续审阅` or `查看结果` using exact revision links.

Empty state:

> 还没有产业研究。可以从一个行业、产业链、技术、政策或投资逻辑开始。

### 9.2 New research `/industry-analysis/new`

Use one page with two progressive sections.

#### Research idea

Required:

- thesis text;
- explicit market confirmation;
- information cutoff.

Optional:

- known companies;
- products/services;
- technologies;
- bottlenecks;
- exclusions.

#### Scope confirmation

- reviewed title;
- driver including `暂不确定`;
- horizon;
- chain/process boundary;
- coverage state;
- exact map selections;
- exact company seed selections.

Persistent notice:

> 系统只使用你确认的本地范围，不代表全市场完整覆盖。

When only fuzzy text exists, save a draft but disable candidate build:

> 研究主题已保存。请至少选择一张现有产业地图或一个精确公司种子后构建候选公司池。

### 9.3 Exact candidate review

Route includes both session and source session-revision IDs.

Header:

- thesis title;
- workflow and coverage;
- cutoff/recorded boundary;
- edit scope;
- reload exact latest state;
- total/decided/undecided counts.

Candidate fields:

- company label/code when exact;
- identity state;
- source kind;
- product/service fit;
- industry position;
- benefit path;
- proposed exposure;
- proposal confidence;
- rationale;
- uncertainty;
- evidence/details action;
- explicit decision.

Decision labels map exactly:

- 纳入后续研究 -> `selected_for_acceptance`;
- 暂不纳入 -> `rejected_by_user`;
- 待确认 -> `unresolved`.

Selected rows require one authoritative identity, explicit non-unknown final exposure, rationale and uncertainty.

Filters never alter the submitted universe. Every latest row must have one decision before save.

### 9.4 Exact result

Route includes both session and reviewed session-revision IDs.

Sections:

1. research summary and exact boundaries;
2. coverage notice;
3. selected candidates;
4. unresolved candidates;
5. temporarily excluded candidates;
6. source/provenance summary;
7. evidence drawer actions;
8. advanced technical details.

Required ownership notice:

> 审阅计划已生成，但尚未写入正式产业地图、Stage 1 受益公司或投资候选快照。

`selected_for_acceptance` is never displayed as accepted beneficiary membership.

An Investment Candidate panel appears only when a future separately authorized exact output link and exact snapshot exist. Otherwise it shows an honest unavailable state and no synthetic ranking.

### 9.5 Minimal settings

Browser-local only:

- light/dark/system appearance;
- comfortable/compact density;
- red-up-green-down or green-up-red-down convention for future market pages;
- advanced metadata shown/hidden by default.

No credentials, model settings, Provider settings, scheduler or notifications.

## 10. Evidence drawer

Open from one exact candidate or exact supported owner record.

### Four lanes

| Lane | Label | Meaning |
| --- | --- | --- |
| Fact | 事实证据 | Direct source-backed record |
| Calculation | 确定性计算 | Deterministic result with inputs |
| Judgment | 研究判断 | Human D3 interpretation |
| AI draft | AI 草稿 | Unaccepted bounded model text |

Each lane uses text and icon/shape labels, not color alone.

Metadata when owned:

- source kind/title/reference;
- information date/cutoff;
- recorded UTC;
- evidence grade;
- conflict/missing/stale/falsified state;
- owner domain and exact revision;
- fingerprint in advanced details.

If only a user-seed source exists, state that no accepted source evidence is attached. Do not generate an explanation.

## 11. Ordinary versus advanced information

### Ordinary

- readable names;
- statuses and reasons;
- source category;
- freshness and coverage;
- missing/uncertainty states;
- next action.

### Advanced `技术详情`

- UUIDs and revision numbers;
- rule/version IDs;
- fingerprints;
- raw enums;
- as-of boundaries;
- owner service;
- structured failure code.

Advanced metadata is copyable but never required input.

## 12. User-visible states

| Condition | Behavior |
| --- | --- |
| Initial loading | Skeleton plus `正在读取本地研究数据` |
| Synchronous write | Disable duplicate submit and name the operation |
| No sessions | First-research empty state |
| No candidates | Explain missing exact sources; no fallback |
| Partial/unknown coverage | Persistent notice; no exhaustive wording |
| Ambiguous identity | Row-level block requiring explicit selection |
| Incomplete review | Undecided count and focus first undecided row |
| Revision conflict | Keep unsaved choices; explicit reload/review |
| Historical not visible | Explain boundary; no latest fallback |
| Missing downstream research | `尚无相关研究记录`, never zero/neutral |
| Database unavailable | 503 panel with local configuration guidance |
| Future module | Disabled with `后续阶段` |

Errors show a Chinese explanation/next action and collapsible exact code/details.

## 13. Visual, responsive and accessibility rules

### Visual

- restrained deep blue/blue-gray primary palette;
- red/green reserved for market/risk semantics;
- amber for unresolved;
- purple for AI draft;
- blue for deterministic calculations;
- gray for source metadata;
- red for risk/falsification;
- no excessive glass, flashing colors or decorative charts;
- system Chinese font stack; no bundled proprietary fonts.

### Responsive

Desktop:

- visible left navigation;
- table-first candidate review;
- bounded right drawer.

Tablet/narrow:

- labelled collapsible navigation;
- candidate cards;
- full-height drawer overlay.

### Accessibility

- `lang="zh-CN"`;
- skip link and semantic landmarks;
- labelled forms and accessible descriptions;
- visible focus;
- polite `aria-live` status;
- errors linked with `aria-describedby`;
- keyboard-operable decisions;
- non-color-only status cues;
- drawer focus trap and focus restoration;
- scoped table headers;
- reduced-motion support.

## 14. Local security and write safety

Phase 1 remains single-user/local and adds no authentication system.

- same-origin JSON fetch;
- no CORS middleware;
- strict content type and body limit;
- no writes on page load or through GET;
- explicit action for every append-only write;
- duplicate activation disabled while in flight;
- no automatic retry;
- no secrets in browser storage/source/logs/errors;
- no remote assets required.

After an ambiguous transport failure, instruct the user to reopen history and verify whether the operation committed before retrying.

## 15. Performance and bounded queries

- History defaults to 20 sessions per page.
- Company option search returns at most 20 records.
- Candidate review initially renders the complete exact universe.
- For more than 100 rows, client windowing/pagination is allowed only if completeness checks still include every row.
- Evidence details load on demand.
- No polling, websocket, scheduler or background refresh.
- Optional downstream panel failure must not erase the core thesis/candidate result.
- Database engines remain lazy at request boundaries.

## 16. Offline golden path

The later implementation must demonstrate through production routes/services:

1. open `/industry-analysis/new`;
2. enter `AI 数据中心扩张带动电子特气需求`;
3. confirm A-share scope, demand expansion, medium-term horizon, cutoff and reviewed local coverage;
4. select exact local source records producing three candidates;
5. create session and build candidates;
6. open the exact revision review URL;
7. select one exact direct beneficiary;
8. reject one with rationale;
9. leave one unresolved with uncertainty;
10. dry-run and commit the complete review;
11. open the exact reviewed-revision result URL;
12. show all three candidates, coverage, source kinds and fingerprint;
13. reopen the same exact result from history;
14. perform no AI/network call;
15. create no Industry Map, Stage 1, output-link, Investment Candidate or portfolio owner write.

## 17. Primary failure path

One candidate has ambiguous identity or stale expected-latest revision while other decisions are valid.

Expected:

- no reviewed session/candidate revision appended;
- unsaved choices retained;
- affected row identified;
- controlled reload offered;
- no candidate disappears;
- no overwrite, deduplication, inference or fallback.

## 18. Validation plan for later implementation

### Backend/API

- strict models and extra-field rejection;
- body-size/content-type boundary;
- exact service delegation;
- exact session/revision route ownership checks;
- history ordering/boundaries;
- local search/option limits and explicit selection;
- expected-latest conflict mapping;
- database-unavailable mapping;
- no CORS/network/AI side effect.

### UI/static contracts

- all canonical routes return intended pages;
- shell shows five modules and honest disabled states;
- top search stays local and presentation-only;
- forms are labelled and errors accessible;
- filters cannot exclude rows from completeness;
- result preserves all review states;
- exact route revisions survive reload/deep link;
- technical details hidden by default;
- no raw UUID ordinary input;
- no fake market/tracking/portfolio data.

### Regression

- full repository tests;
- existing pages/APIs remain available;
- exact-ID APIs unchanged;
- local fixture demo remains offline;
- new three-candidate browser/API fixture uses production boundaries.

No new front-end test dependency is required unless existing tools cannot prove the contract.

## 19. Proposed bounded implementation slice

After approval, one later Strict implementation Issue may authorize:

- `backend/main.py` for mounts/page routes;
- `backend/api/industry_analysis.py` for bounded web adapters;
- `industry_alpha/industry_thesis_query.py` for session-history read only;
- one bounded `industry_alpha/industry_thesis_workbench.py` module for view models, local search and proposal composition;
- `research_workbench/static/**` for HTML/CSS/JavaScript;
- focused API/static-route tests;
- existing or dedicated offline workbench demo.

No migration and no accepted-owner semantic change.

## 20. Deferred phases

- **Today Market**: requires authorized market/sector data and refresh contract.
- **Daily Industry Radar**: requires authorized news/announcement ingestion, immutable capture, grouping and scheduler.
- **Follow and Track**: requires followed-entity persistence, change rules and notifications.
- **Research Portfolio**: observation portfolio needs price/benchmark semantics; simulated portfolio additionally needs an append-only virtual ledger and corporate-action handling.
- **Model/Provider settings**: requires credential security, explicit roles and Provider authorization.
- **Owner acceptance/output links**: separate orchestration implementation after explicit architecture/owner authorization.

## 21. Stop conditions

Return to Issue #198 when:

- a visible field lacks an authoritative owner;
- ordinary flow requires manual technical-ID entry;
- fuzzy text must establish company identity;
- free text is represented as full-market discovery;
- the complete universe cannot be preserved;
- a result requires automatic owner or Investment Candidate writes;
- implementation needs Provider, scheduler, notification, AI or portfolio ledger;
- a new front-end framework is proposed without concrete necessity;
- an error requires latest fallback or history mutation.

## 22. Definition of Ready

A Phase 1 implementation Issue may open only after exact-head architecture approval and separate owner authorization. It must freeze:

- exact main base SHA;
- page/API routes in this document;
- authorized file families;
- no-migration/no-new-framework decisions;
- history, local-option, local-search and proposal-composer contracts;
- exact revision deep links;
- complete-universe review behavior;
- evidence drawer and visible states;
- offline golden and atomic failure paths;
- locked Provider/scheduler/AI/portfolio/trading exclusions;
- exact CI and fixed-head implementation review gates.

## 23. Required approval phrase

```text
AUTHORIZED PERSONAL RESEARCH WORKBENCH UI PHASE 1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates the fixed-head review.
