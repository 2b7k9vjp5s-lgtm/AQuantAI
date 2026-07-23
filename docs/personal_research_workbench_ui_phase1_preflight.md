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

The first production slice must implement only the **产业研究 manual/offline workbench** plus minimal local appearance settings. Other navigation items remain visibly planned but disabled. They must not display fabricated market, tracking or portfolio data.

The Phase 1 product outcome is:

```text
ordinary Chinese thesis input
  -> explicit scope confirmation
  -> exact local thesis session/revision
  -> deterministic candidate proposals from exact local selections
  -> complete reviewed local-scope candidate universe
  -> selected / rejected / unresolved review
  -> exact reviewed-plan result and history reopening
```

The user should never need to type or copy UUIDs, revision numbers, fingerprints or database URLs. The application still preserves and exposes those values in an advanced technical-details layer.

## 3. Feasibility decision

### 3.1 What the accepted runtime can support now

The accepted runtime already provides:

- append-only Industry Thesis session creation and revision;
- exact local candidate proposal persistence;
- complete candidate-revision reads under information-cutoff and recorded-UTC boundaries;
- explicit `selected_for_acceptance`, `rejected_by_user` and `unresolved` review;
- deterministic reviewed-plan preview and fingerprint;
- existing Industry Map, Stage 1 beneficiary, Typed Beneficiary Semantics, Company Research, Evidence Intelligence, Canonical Price, normalized valuation and Investment Candidate read contracts;
- existing static HTML/CSS/vanilla JavaScript pages served by FastAPI `FileResponse`;
- local database configuration and no-network test discipline.

### 3.2 What the accepted runtime cannot truthfully support yet

The current runtime does not provide:

- free-text-only automatic full-market company discovery;
- an accepted owner transaction from a reviewed thesis plan into Industry Map / Stage 1 and output links;
- a deterministic downstream Investment Candidate snapshot automatically linked to a newly reviewed thesis;
- authorized news/announcement/market-data acquisition for daily hotspot detection;
- a scheduler, notifications, followed-entity state or portfolio ledger.

Therefore Phase 1 must not claim that a vague phrase by itself has automatically found all beneficiaries or produced final investable companies.

### 3.3 Practical Phase 1 compromise

A vague thesis is accepted as the starting point, but the user must confirm exact scope and at least one deterministic candidate source before candidate build:

- one or more explicitly selected existing Industry Map revisions;
- one or more explicitly selected accepted local mappings when available;
- one or more explicitly selected persisted company / listed-instrument records as user seeds.

Text search may help the user find local options, but text, ticker prefix, similarity or model output never establishes identity. Clicking an exact persisted result establishes the selected identity.

The complete-universe claim is always qualified as **当前已审阅本地范围全量** and is paired with the persisted coverage state:

- `reviewed_local_scope`;
- `partial_local_coverage`;
- `coverage_unknown`.

## 4. Technology and delivery decision

### 4.1 Front-end stack

Phase 1 reuses the current repository stack:

- FastAPI page and JSON routes;
- static HTML;
- shared CSS custom properties and responsive layout;
- vanilla JavaScript using same-origin `fetch`;
- no Node, npm, bundler, React, Vue or another front-end framework;
- no server-side template engine unless implementation inspection proves static composition impossible.

This is the lowest-risk path because the current `/dashboard`, `/market-cockpit`, `/evidence-intelligence`, `/industry-research`, `/company-research`, `/company-comparison` and `/investment-candidates` pages already follow this model.

### 4.2 Application shell

Phase 1 introduces a new shared shell only for new workbench pages. It does not refactor all existing pages in the first implementation.

Shell regions:

- fixed left primary navigation;
- fixed or sticky top bar;
- central content workspace;
- optional right evidence/details drawer;
- global status/notification region using `aria-live`;
- skip link to the main content.

Existing standalone pages remain valid advanced/read-only tools and may be linked from technical details.

### 4.3 No new UI persistence domain

Phase 1 adds no UI database tables.

- Research history comes from Industry Thesis identities/revisions.
- Candidate decisions come from Industry Thesis candidate revisions.
- Reviewed results come from the reviewed-plan revision.
- Appearance and density preferences may use browser `localStorage` only.
- Credentials, model profiles and data-source configuration are not stored through Phase 1 UI.

## 5. Canonical Phase 1 route map

### 5.1 Page routes

| Route | User job | State |
| --- | --- | --- |
| `GET /workbench` | Enter the personal research application | Redirect to `/industry-analysis` |
| `GET /industry-analysis` | View active and historical manual research sessions | Active in Phase 1 |
| `GET /industry-analysis/new` | Enter thesis and confirm explicit scope | Active in Phase 1 |
| `GET /industry-analysis/sessions/{session_id}/review` | Review the exact current session revision and complete candidate universe | Active in Phase 1 |
| `GET /industry-analysis/sessions/{session_id}/result` | View one exact reviewed plan and its evidence/coverage state | Active in Phase 1 |
| `GET /workbench/settings` | Adjust local appearance, density and display preferences | Minimal Phase 1 |

The navigation labels 今日市场, 关注与跟踪 and 研究组合 are rendered disabled with `aria-disabled="true"` and a visible `后续阶段` label. They receive no fake page route in Phase 1.

### 5.2 URL and identifier policy

- A session UUID may appear in a browser URL after the user creates or selects a session.
- Users never manually enter the UUID.
- Exact revision IDs, candidate revision IDs and plan fingerprints remain internal page state and advanced metadata.
- Browser back/forward must preserve the current route without issuing a write.
- A result route re-resolves an exact reviewed session revision from the selected session history; it does not silently use a newer compatible-looking plan.

## 6. Canonical Phase 1 API boundary

Use a new router prefix `/industry-analysis/api`. It is a thin local web adapter over accepted domain services, not a new domain owner.

### 6.1 Read endpoints

| Endpoint | Purpose | Owner/service |
| --- | --- | --- |
| `GET /industry-analysis/api/bootstrap` | Shell capability flags, database availability and local display metadata | Thin workbench adapter |
| `GET /industry-analysis/api/sessions` | Deterministic current/history list under explicit boundaries | New read method over Industry Thesis identities/revisions |
| `GET /industry-analysis/api/sessions/{session_id}` | Session chronology and current visible revision | `IndustryThesisQueryService.get_session` |
| `GET /industry-analysis/api/session-revisions/{session_revision_id}` | Exact scope revision | `IndustryThesisQueryService.get_session_revision` |
| `GET /industry-analysis/api/session-revisions/{session_revision_id}/candidates` | Complete exact candidate universe | `IndustryThesisQueryService.list_candidate_revisions` |
| `GET /industry-analysis/api/reviewed-plans/{reviewed_session_revision_id}` | Exact verified reviewed plan | `IndustryThesisReviewedPlanQueryService.get_reviewed_plan` |
| `GET /industry-analysis/api/local-options/maps` | Selectable exact local Industry Map revisions | Existing Industry Research/Map query services |
| `GET /industry-analysis/api/local-options/companies` | Candidate persisted company/instrument options requiring explicit user selection | Thin read adapter over accepted local identity records |
| `GET /industry-analysis/api/evidence-details` | Bounded details for one exact supported entity/revision | Composition adapter over existing owners; no generic inference |

Every time-aware read accepts or derives one explicit pair:

- `as_of_cutoff`;
- `as_of_recorded_at_utc`.

The pair is returned in the response and shown in the page header as `数据截止` and `系统记录边界`.

### 6.2 Write endpoints

| Endpoint | Purpose | Owner/service |
| --- | --- | --- |
| `POST /industry-analysis/api/sessions` | Create one exact thesis session | `IndustryThesisCommandService.create_session` |
| `POST /industry-analysis/api/sessions/{session_id}/revisions` | Confirm/edit scope through append-only revision | `IndustryThesisCommandService.revise_session` |
| `POST /industry-analysis/api/session-revisions/{session_revision_id}/candidate-builds` | Persist deterministic candidates from exact selected sources | `IndustryThesisCommandService.build_candidates` plus bounded proposal composer |
| `POST /industry-analysis/api/session-revisions/{session_revision_id}/reviews` | Review the complete candidate universe and create a reviewed plan | `IndustryThesisProposalReviewService.review_candidates` |

Rules:

- JSON only;
- Pydantic strict models with `extra="forbid"`;
- maximum request body 1 MiB;
- no write through `GET`;
- no automatic retry;
- no CORS enablement;
- browser requests use same-origin JSON fetch;
- no hidden AI or network call;
- domain errors retain structured code and a Chinese user message;
- all writes preserve expected-latest values and atomic domain behavior.

### 6.3 Dry-run behavior

- The candidate-review page offers `检查审阅结果` before `保存审阅计划`.
- The check calls the existing review service with `dry_run=true`.
- The commit sends the same normalized decisions and expected-latest values.
- Any change or stale revision between check and commit returns a conflict and requires explicit reload/review.
- The UI never auto-rebases decisions.

Session creation and candidate build may expose advanced dry-run controls but do not require a separate ordinary-user confirmation page.

## 7. New bounded backend seams required for implementation

### 7.1 Session-history query

Add one read-only method to list Industry Thesis sessions visible under explicit boundaries.

Required result fields:

- session ID;
- state;
- visible latest revision ID and revision number;
- reviewed title or original thesis excerpt;
- driver type;
- horizon;
- workflow state;
- coverage state;
- candidate count when bounded without unbounded scans;
- information cutoff;
- recorded UTC;
- last action label.

Ordering:

1. visible latest revision recorded UTC descending;
2. session ID ascending as deterministic tie break.

No fuzzy latest fallback is permitted.

### 7.2 Exact local-option queries

The UI needs bounded option lists for:

- visible Industry Maps;
- persisted StockBasic / ListedInstrument identities.

A search string is only a display filter. Returned records include exact IDs and source metadata. Identity is accepted only after explicit user selection.

Limits and behavior:

- minimum two visible characters for company search unless an exact code is entered;
- maximum 20 results;
- deterministic name/code/ID ordering;
- no provider-only identity;
- no network;
- no AI;
- no automatic first-result selection.

### 7.3 Deterministic candidate-proposal composer

The current candidate command accepts explicit proposal objects. Phase 1 needs one pure composition helper that turns exact UI selections into those proposal objects.

Allowed inputs:

- exact accepted local mapping reference;
- exact Industry Map/beneficiary revision reference;
- exact user-selected StockBasic or ListedInstrument identity.

The composer may copy labels and exact references from accepted local records. It may not infer benefit strength, exposure type, product fit or industry position from company name or thesis text.

When those analytical fields are not supplied by an accepted source or explicit user input, they remain `unknown`, nullable or unresolved as allowed by the accepted command contract.

### 7.4 Workbench view-model adapter

Add one non-persistent composition layer for page-friendly Chinese labels and grouped sections.

It may:

- translate closed enum values into Chinese display labels;
- group candidate rows by review state or source kind;
- create counts from the exact returned universe;
- generate navigation links using exact internal IDs;
- expose owner/source metadata.

It may not:

- create a new score;
- infer identity;
- classify benefit strength;
- choose a candidate decision;
- hide rejected/unresolved rows;
- parse narrative valuation text into numeric values;
- choose newer domain revisions.

## 8. Page architecture

## 8.1 `/industry-analysis` — research home and history

### User job

Start a new manual industry research session or reopen an existing one.

### Primary content

- page title and one-sentence boundary;
- prominent `发起新研究` action;
- four conceptual tabs:
  - 每日产业雷达 — disabled, later phase;
  - 发起新研究 — link to active new page;
  - 研究进行中;
  - 历史研究;
- compact session cards/table;
- explicit database/update state;
- no market hotspot content in Phase 1.

### Session card fields

- reviewed title or thesis excerpt;
- workflow label;
- driver type;
- coverage label;
- candidate counts by review state when available;
- information cutoff;
- last recorded time;
- primary action: `继续审阅` or `查看结果`.

### Empty state

```text
还没有产业研究。
从一个行业、产业链、技术、政策或投资逻辑开始。
```

The empty state does not suggest that automatic news scanning is active.

## 8.2 `/industry-analysis/new` — thesis and scope confirmation

### User job

Convert an ordinary-language idea into explicit governed research inputs.

### Visible step structure

Use one page with two progressive sections, not a long wizard.

#### A. 研究想法

Required:

- thesis text;
- market scope confirmation, with A股 suggested but not silently persisted;
- information cutoff.

Optional:

- known companies;
- products/services;
- technologies;
- bottlenecks;
- exclusions.

#### B. 确认研究范围

Explicit controls:

- reviewed title;
- driver type including `暂不确定`;
- horizon;
- chain/process boundary;
- coverage state;
- exact existing map selections;
- exact company seed selections.

The page must state:

> 系统只会使用你确认的本地范围，不代表全市场完整覆盖。

### Submission result

Successful create/revise returns the internal session ID and navigates to the review route. The user sees a success summary, not raw JSON.

### No-source state

When the user provides only fuzzy text and selects no exact local source, the page may save a draft session but candidate build remains disabled with:

> 研究主题已保存。请至少选择一张现有产业地图或一个精确公司种子后构建候选公司池。

No hidden fuzzy company discovery occurs.

## 8.3 `/industry-analysis/sessions/{session_id}/review` — complete candidate review

### User job

Understand every candidate in the reviewed local scope and explicitly decide its next state.

### Header

- thesis title;
- workflow and coverage badges;
- data cutoff and recorded boundary;
- `编辑研究范围`;
- `重新读取最新状态`;
- candidate counts.

### Default candidate table/card fields

- company label and code when exact;
- identity state;
- source kind;
- product/service fit;
- industry position;
- benefit path;
- proposed exposure type;
- proposal confidence;
- rationale summary;
- uncertainty state;
- evidence/source action;
- one explicit review control.

### Review controls

Chinese labels map exactly to domain values:

- `纳入后续研究` -> `selected_for_acceptance`;
- `暂不纳入` -> `rejected_by_user`;
- `待确认` -> `unresolved`.

Selected candidates additionally require:

- one exact authoritative identity;
- explicit non-unknown final exposure type;
- non-empty rationale object;
- explicit uncertainty state.

The ordinary UI supplies structured form fields and serializes strict JSON; users do not edit JSON.

### Complete-universe rule

- Every latest candidate revision must receive one decision before save.
- Filters may change display but never change the submitted universe.
- A sticky summary shows total, decided and undecided counts.
- Rejected and unresolved rows remain visible after save.

### Conflict behavior

On stale expected-latest conflict:

- keep unsaved local choices in memory;
- block commit;
- show which session/candidate state changed;
- offer `打开最新版本并重新核对`;
- never silently overwrite, merge or rebase.

## 8.4 `/industry-analysis/sessions/{session_id}/result` — reviewed-plan result

### User job

Review the exact saved plan, understand what is selected/rejected/unresolved and reopen evidence.

### Primary sections

1. research summary and boundaries;
2. coverage notice;
3. selected candidates;
4. unresolved candidates;
5. temporarily excluded candidates;
6. exact candidate-source summary;
7. evidence drawer links;
8. advanced technical details.

### Important ownership notice

Until a later owner-acceptance implementation exists, the page must show:

> 审阅计划已生成，但尚未写入正式产业地图、Stage 1 受益公司或投资候选快照。

It must not label `selected_for_acceptance` as accepted beneficiary membership.

### Investment-candidate panel

The panel appears only when an exact accepted output link and exact Investment Candidate snapshot already exist through a separately authorized capability.

Otherwise it shows an honest unavailable state and no synthetic ranking.

## 8.5 `/workbench/settings` — minimal local settings

Phase 1 supports only browser-local display preferences:

- light / dark / system appearance;
- comfortable / compact density;
- red-up-green-down or green-up-red-down display convention for later market surfaces;
- show/hide advanced technical metadata by default.

No model credentials, Provider configuration, scheduler, notification or server-side preference persistence is included.

## 9. Evidence drawer contract

The right evidence drawer is opened from one exact candidate, map observation or supported downstream research record.

### 9.1 Four visual lanes

| Lane | Chinese label | Meaning | Visual role |
| --- | --- | --- | --- |
| Fact | 事实证据 | Direct source-backed record | Neutral/gray-blue |
| Calculation | 确定性计算 | Deterministic formula or count with inputs | Blue |
| Judgment | 研究判断 | Human D3 interpretation | Orange/amber |
| AI draft | AI 草稿 | Unaccepted bounded model text | Purple |

The color is never the only cue; every lane has text and an icon/shape label.

### 9.2 Required metadata

When available from the authoritative owner:

- source kind and title;
- source reference;
- information date/cutoff;
- recorded UTC;
- evidence grade;
- conflict/missing/stale/falsified state;
- exact owner domain;
- exact revision ID;
- fingerprint in advanced details.

### 9.3 Unsupported details

If a candidate has only a user-seed source and no accepted evidence link, the drawer states that no accepted source evidence is attached. It does not generate an explanation.

## 10. Ordinary and advanced information policy

### 10.1 Ordinary layer

Show:

- readable names;
- statuses and reasons;
- source category;
- freshness;
- coverage;
- missing and uncertainty states;
- actionable next step.

### 10.2 Advanced layer

Collapsible `技术详情` may show:

- UUIDs;
- revision numbers;
- exact rule/version identifiers;
- input and plan fingerprints;
- raw closed enum value;
- as-of boundaries;
- owner service;
- structured failure code.

Technical metadata is copyable but is never a required ordinary input.

## 11. User-visible state system

Use one consistent state vocabulary across Phase 1 pages.

| System condition | Primary UI behavior |
| --- | --- |
| Initial loading | Skeleton/placeholder plus `正在读取本地研究数据` |
| Synchronous write | Disable duplicate submit; show exact operation label |
| No sessions | Friendly first-research empty state |
| No candidates | Explain missing exact local sources; do not fall back |
| Partial coverage | Persistent amber notice; prohibit exhaustive wording |
| Unknown coverage | Neutral/amber notice; prohibit exhaustive wording |
| Ambiguous identity | Row-level block; require exact user selection |
| Incomplete review | Show undecided count and focus first undecided row |
| Revision conflict | Preserve unsaved choices; explicit reload/review path |
| Historical not visible | Explain requested boundary; no latest fallback |
| Missing downstream research | `尚无相关研究记录`, not zero/neutral |
| Database unavailable | 503 panel with local configuration guidance |
| Future module | Disabled navigation with `后续阶段` |
| Unsupported AI/network | Never call; show feature not enabled only where relevant |

Error messages have two layers:

- Chinese user-facing explanation and next action;
- collapsible exact failure code/details.

## 12. Visual direction

### 12.1 Palette and tokens

Use restrained semantic tokens rather than hard-coded page-specific colors:

- primary: deep blue / blue-gray;
- surface: neutral light/dark layers;
- market up/down: user-configurable red/green convention;
- unresolved: amber/orange;
- AI draft: purple;
- deterministic calculation: blue;
- risk/falsification: red;
- source metadata: gray.

Avoid large gradients, excessive glass effects, flashing market colors and decorative charts without data meaning.

### 12.2 Density

- default desktop content width supports dense research tables;
- summary first;
- row expansion or drawer second;
- technical details third;
- no more than one dominant primary action per section;
- long rationale text is clamped with explicit expansion.

### 12.3 Typography

Use system Chinese fonts and existing project-compatible font stacks. No bundled proprietary font files.

## 13. Responsive and accessibility requirements

### Desktop

- left navigation remains visible;
- candidate table is primary;
- evidence drawer overlays or occupies a bounded right column.

### Tablet/narrow desktop

- left navigation collapses to a labelled menu;
- candidate table switches to cards below the defined breakpoint;
- evidence drawer becomes a full-height overlay.

### Accessibility

- valid `lang="zh-CN"`;
- skip link;
- semantic headings and landmarks;
- form labels and descriptions;
- visible keyboard focus;
- status updates through polite `aria-live`;
- errors linked with `aria-describedby`;
- review decision controls usable by keyboard;
- no status conveyed by color alone;
- dialogs/drawers trap focus and restore focus on close;
- tables use scoped headers;
- reduced-motion preference respected.

## 14. Local security and write safety

Phase 1 remains a single-user local application and adds no authentication system.

Write safety rules:

- same-origin JSON fetch only;
- no CORS middleware;
- strict content type and body limit;
- no write on page load;
- no write through links or GET;
- explicit user action for every append-only write;
- disable duplicate button activation while a request is in flight;
- no automatic network retry;
- no secrets in browser storage, source, logs or errors;
- no remote assets required for normal page rendering.

An ambiguous transport failure instructs the user to reopen research history and verify whether the operation committed before retrying.

## 15. Performance and bounded-query decisions

Phase 1 is local and prioritizes predictability over live streaming.

- Research history defaults to 20 sessions per page.
- Company option search returns at most 20 records.
- Candidate review initially renders the exact complete universe; when over 100 rows, use client-side windowing/pagination only if every row remains included in decision completeness checks.
- Evidence details load on demand.
- No polling, websocket, scheduler or background refresh.
- Page bootstrap may make bounded parallel reads, but one failed optional downstream panel must not erase the core thesis/candidate result.
- Database engines remain lazily created at request boundaries, consistent with current APIs.

## 16. Production-realistic offline golden path

The implementation must demonstrate through production routes and services:

1. open `/industry-analysis/new`;
2. enter `AI 数据中心扩张带动电子特气需求`;
3. explicitly confirm A-share scope, `demand_expansion`, medium-term horizon, cutoff and reviewed local coverage;
4. select exact local source records producing three candidates;
5. create the session and build candidate revisions;
6. open the review page;
7. select one exact company with `direct` exposure;
8. reject one company with an explicit rationale;
9. leave one candidate unresolved with an explicit uncertainty state;
10. dry-run and commit the complete review;
11. open the result page;
12. show all three candidates, exact coverage, source kinds and the reviewed-plan fingerprint in advanced details;
13. return to history and reopen the same exact result;
14. perform no AI or external network call;
15. create no Industry Map, Stage 1, output-link, Investment Candidate or portfolio owner write.

## 17. Primary failure path

The required failure demonstration is one atomic review refusal where:

- one candidate has ambiguous identity or stale expected-latest revision;
- the other rows contain valid user decisions.

Expected result:

- no reviewed session or candidate revision is appended;
- the page retains all unsaved choices;
- the affected row receives the exact reason;
- the user is offered a controlled latest-state reload;
- no candidate disappears;
- no silent overwrite, deduplication, inference or fallback occurs.

## 18. Validation plan for the later implementation

### Backend/API

- strict request model and extra-field rejection;
- body-size and content-type boundary;
- exact service delegation;
- session-history ordering and boundaries;
- local option search limits and explicit identity selection;
- expected-latest conflict mapping;
- database-unavailable mapping;
- no CORS/network/AI side effect.

### UI/static pages

- all canonical routes return the intended static page;
- shell contains five labelled modules and honest disabled states;
- forms have labels, descriptions and accessible errors;
- candidate completeness count cannot exclude filtered rows;
- result page preserves selected/rejected/unresolved candidates;
- technical details are hidden by default and available on demand;
- no raw UUID input is present in ordinary forms;
- no fake market, tracking or portfolio data.

### Regression

- full repository tests;
- current existing page routes remain available;
- current exact-ID APIs remain unchanged;
- standard local fixture demo remains no-network;
- new three-candidate browser/API fixture uses production boundaries.

No new front-end test dependency is required in the first implementation unless existing test tools cannot prove the required behavior.

## 19. Proposed bounded implementation slice after approval

A later Strict implementation Issue may authorize these file families:

- `backend/main.py` for static mount and page routes;
- `backend/api/industry_analysis.py` for the bounded web adapter;
- `industry_alpha/industry_thesis_query.py` for session-history read only;
- one bounded `industry_alpha/industry_thesis_workbench.py` view-model/proposal-composition module;
- `research_workbench/static/**` for HTML/CSS/JavaScript assets;
- focused `tests/test_industry_analysis_api.py` and UI route/static-contract tests;
- the existing offline demo or one dedicated no-network workbench demo.

The implementation must make no migration and must not modify existing accepted owner semantics.

## 20. Explicitly deferred phases

### Today Market

Requires an authorized market-data/sector Provider and refresh contract. No implementation in Phase 1.

### Daily Industry Radar

Requires authorized news/announcement acquisition, immutable capture, deduplication, theme grouping and scheduler architecture. No implementation in Phase 1.

### Follow and Track

Requires followed-entity persistence, change rules, scheduler and notification contracts. No implementation in Phase 1.

### Research Portfolio

Observation portfolio requires price-history and benchmark semantics. Simulated portfolio additionally requires an append-only virtual ledger, transaction costs and corporate-action handling. No implementation in Phase 1.

### Model and Provider settings

Requires credential security, explicit model roles and Provider authorization. Phase 1 settings are browser-local display preferences only.

## 21. Stop conditions

Return to Issue #198 rather than implement when:

- a page field lacks an authoritative owner;
- the ordinary flow requires manual UUID/revision entry;
- fuzzy text must establish company identity;
- free-text-only input is represented as full-market discovery;
- the complete candidate universe cannot be preserved;
- a result requires automatic accepted Industry Map, beneficiary or Investment Candidate writes;
- the implementation requires a Provider, scheduler, notification system, AI call or portfolio ledger;
- a new front-end framework/build system is proposed without concrete necessity;
- static pages cannot share the shell without a cross-project refactor;
- an error path requires latest-record fallback or history mutation.

## 22. Architecture Definition of Ready

The Phase 1 implementation may be opened only after this architecture is fixed-head approved and separately authorized by the owner.

The implementation Issue must freeze:

- exact main base SHA;
- the page and API routes in this document;
- authorized file families;
- no-migration decision;
- session-history, local-option and proposal-composer contracts;
- complete-universe review behavior;
- evidence drawer and user-visible state behavior;
- offline golden and atomic failure paths;
- no Provider, scheduler, AI, portfolio or trading scope;
- exact CI and fixed-head implementation review gates.

## 23. Required architecture approval phrase

```text
AUTHORIZED PERSONAL RESEARCH WORKBENCH UI PHASE 1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates the fixed-head review.
