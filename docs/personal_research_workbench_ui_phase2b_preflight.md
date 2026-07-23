# Personal Research Workbench UI Phase 2B — Ordinary-User Usability Consolidation

## 1. Decision status

This document defines the bounded Phase 2B architecture authorized by Issue #215 against exact base:

`2780442efa0a6c110bf7887c68cf2919ea3cc443`

The selected direction is:

```text
existing exact dual-as-of workbench records and routes
  -> one ordinary-user continuation projection
  -> consistent five-module navigation
  -> shared five-step industry-research presentation
  -> one deterministic primary action
  -> stable Chinese state explanations
```

Phase 2B is a usability consolidation only. It does not add analytical breadth, accepted research semantics, external data, automation, alerts, portfolio state or trading behavior.

The architecture PR is documentation-only. Production implementation requires a later separately authorized Strict implementation Issue and PR after this preflight is approved and merged.

## 2. Product job

A returning personal user should be able to answer within the first screen:

1. 我上次研究的是什么？
2. 当前做到哪一步？
3. 现在唯一应该做什么？

A new user should be able to understand how to start without reading technical identifiers or architecture terminology.

The page must continue to make clear that:

- the system is local-first and research-only;
- an orchestration result is not an accepted Industry Map, Stage 1 beneficiary, Investment Candidate or recommendation;
- history and continuation are bounded by information cutoff and local recorded time;
- incomplete, stale, conflicting and unavailable states are not success;
- technical provenance remains available for reproduction and audit.

## 3. Current exact repository findings

### 3.1 Existing page routes

The accepted runtime already serves:

```text
GET /workbench
  -> 307 /industry-analysis

GET /industry-analysis
GET /industry-analysis/new
GET /workbench/settings

GET /industry-analysis/sessions/{session_id}/revisions/{session_revision_id}/review
GET /industry-analysis/sessions/{session_id}/revisions/{reviewed_session_revision_id}/result

GET /today-market
```

The history, new-scope and settings routes share `industry_analysis/static/workbench.html`. Candidate construction and complete review share `candidate_review.html`. The exact reviewed-plan result uses `review_result.html`.

### 3.2 Existing history owner

`GET /industry-analysis/api/sessions` already owns the bounded recent-session projection. It requires:

```text
as_of_cutoff=<date>
as_of_recorded_at_utc=<explicit UTC timestamp>
limit=1..100
```

The underlying `IndustryThesisWorkbenchQueryService.list_sessions`:

- selects only revisions visible under both requested boundaries;
- selects the maximum visible revision number per exact session identity;
- orders by `recorded_at_utc DESC`, then exact session identity `ASC`;
- applies the limit after deterministic ordering;
- returns exact session and latest-visible revision identifiers;
- returns exact information-cutoff and recorded-UTC values;
- returns `workflow_state`, `coverage_state` and `next_surface`;
- performs one bounded SQL statement independent of returned session count.

The response already includes the fields needed for an exact ordinary-user card:

- `session_id`;
- `visible_latest_revision_id`;
- `visible_latest_revision_number`;
- `thesis_title`;
- `thesis_text_preview`;
- `coverage_state`;
- `workflow_state`;
- `next_surface`;
- `information_cutoff_date`;
- `recorded_at_utc`;
- technical fingerprint and supersession details.

No new recent-activity table, cross-domain activity feed or generic activity service is justified.

### 3.3 Current continuation gap

The existing history UI already loads `/industry-analysis/api/sessions` automatically under explicit browser-generated current boundaries and renders all exact rows.

However:

- only `next_surface = scope` receives an active continuation link;
- `review` and `result` are still described as future even though their exact page/API routes are merged;
- the history list does not surface one first-screen recent-research card;
- the user must visually scan the list to find where to continue;
- technical chronology is more prominent than the ordinary next action.

Phase 2B corrects this presentation gap without selecting a different domain record.

### 3.4 Current navigation inconsistency

Today Market is active and correctly linked on:

- `/today-market`;
- candidate review;
- reviewed-plan result.

The shared `workbench.html` and the `/industry-analysis/api/bootstrap` module projection still describe Today Market as a future module with no path.

This is documentation/presentation drift. Phase 2B must make the following module states identical on every workbench surface:

| Module | State | Path | Secondary label |
| --- | --- | --- | --- |
| 今日市场 | active | `/today-market` | 本地快照 |
| 产业研究 | active | `/industry-analysis` | 本地研究 |
| 关注与跟踪 | unavailable | none | 后续阶段 |
| 研究组合 | unavailable | none | 后续阶段 |
| 系统设置 | active | `/workbench/settings` | 显示偏好 |

No disabled module may contain live-looking fixture values.

## 4. Architecture boundaries

### 4.1 Dependency direction

```text
IndustryThesisSessionIdentity + exact visible revisions
  -> existing IndustryThesisWorkbenchQueryService.list_sessions
  -> existing /industry-analysis/api/sessions adapter
  -> bounded continuation-path projection
  -> ordinary-user recent-research card and history list

exact candidate/review/result APIs already loaded by each page
  -> presentation-only workflow-step mapping
  -> presentation-only state explanation mapping
  -> one deterministic primary action
```

Accepted domain owners remain unchanged.

### 4.2 Presentation ownership

Phase 2B may own only:

- module activation labels and links;
- workflow-step labels and visual state;
- ordinary-user descriptions of already returned stable states;
- selection of one visually dominant existing action;
- placement and progressive disclosure of already returned metadata;
- first-use instructions.

Phase 2B does not own:

- session workflow transitions;
- candidate membership;
- review completeness;
- accepted evidence or beneficiary state;
- valuation, priority or recommendation meaning;
- chronology or exact record identity.

### 4.3 No second workflow state machine

The five-step indicator is not persisted and cannot become a new state owner.

Its state is derived only from:

1. the exact current page route;
2. the exact response-owned `workflow_state` or page response state already loaded for that route;
3. whether the route has an exact session/revision identity.

Browser local storage remains restricted to appearance, density and market-color preferences. It cannot store current research step, recent session identity, accepted review state or a reconstructed continuation link.

## 5. Recent-research card contract

### 5.1 Selection rule

The history page continues to issue one request to:

```text
GET /industry-analysis/api/sessions
  ?as_of_cutoff=<explicit page boundary>
  &as_of_recorded_at_utc=<explicit UTC page boundary>
  &limit=<bounded history count>
```

The same response populates both:

- one recent-research card from `sessions[0]`;
- the ordinary history list from the complete returned `sessions` array.

No second `/sessions?limit=1` request is required.

`sessions[0]` means only:

> the exact first visible session under the caller-supplied boundaries and the existing deterministic ordering.

It does not mean:

- latest compatible session;
- latest session that happens to have an available continuation action;
- latest session with complete coverage;
- latest session matching a title or theme;
- a browser-restored prior choice.

If the first exact record is abandoned, superseded, stale or otherwise non-continuable, the card shows that state honestly. It must not skip to an older convenient record.

### 5.2 Card fields

Ordinary view:

- thesis title;
- one-line preview when useful;
- ordinary workflow label;
- current step label;
- coverage warning when not `reviewed_local_scope`;
- local formatted update time derived from `recorded_at_utc`;
- one primary action.

Progressive technical details:

- session ID;
- exact visible revision ID and number;
- information cutoff;
- recorded UTC;
- input fingerprint;
- superseded revision link identifier when present.

Technical values are never editable ordinary inputs.

### 5.3 Exact continuation projection

The implementation should extend the existing API adapter response with a presentation-only object rather than make the browser infer domain compatibility:

```json
{
  "continuation": {
    "kind": "scope | candidate_review | result | unavailable",
    "label": "继续确认范围 | 构建候选公司 | 继续人工审核 | 查看研究结果 | 当前记录不可继续",
    "path": "/exact-existing-route?... | null",
    "reason_code": "stable_presentation_code"
  }
}
```

The adapter derives this object from the exact returned identifiers, exact record-owned boundaries and a closed workflow-state mapping. It performs no additional query and no write.

Closed mapping:

| `workflow_state` | Continuation kind | Exact action |
| --- | --- | --- |
| `draft` | `scope` | Continue `/industry-analysis/new` with exact session/revision/number and record-owned boundaries |
| `candidate_build_ready` | `candidate_review` | Open exact candidate/review route; page determines candidate-build state from its existing API |
| `awaiting_review` | `candidate_review` | Open the same exact route; page determines review state from its existing API |
| `reviewed_plan_ready` | `result` | Open exact result route with exact reviewed revision and record-owned boundaries |
| `accepted_outputs_linked` | `unavailable` in this phase | Do not infer future output ownership or skip records |
| `superseded` | `unavailable` | Show historical state; offer only a separate new-research action outside continuation |
| `abandoned` | `unavailable` | Show stopped state; offer only a separate new-research action outside continuation |
| unknown value | `unavailable` | Fail closed and expose technical state |

The browser uses the response-owned path. It does not rebuild UUID routes, find a newer revision or substitute page-level broader boundaries.

### 5.4 No automatic navigation

Page load may display the card after the existing history request. It must not:

- navigate automatically;
- focus and activate the action automatically;
- write or revise a session;
- advance either boundary;
- retry with a larger boundary;
- restore a research identity from local storage;
- choose another record when the exact action is unavailable.

## 6. Shared five-step indicator

Exact vocabulary:

```text
研究主题 -> 确认范围 -> 候选公司 -> 人工审核 -> 研究结果
```

### 6.1 Participating pages

The indicator appears only after the user is inside an industry-research flow:

- `/industry-analysis/new`;
- exact candidate/review route;
- exact result route.

The history index, Today Market and settings do not pretend to be a selected research step. The recent card itself shows the derived current step as text.

### 6.2 Route/state mapping

| Page and exact state | Completed | Current | Unavailable/future |
| --- | --- | --- | --- |
| New route without exact session | none | 研究主题 | 确认范围、候选公司、人工审核、研究结果 |
| Scope route with exact session/revision | 研究主题 | 确认范围 | later steps until response state proves them reachable |
| Candidate/review page with `draft` | 研究主题 | 确认范围 | 候选公司、人工审核、研究结果 |
| Candidate/review page with `candidate_build_ready` | 研究主题、确认范围 | 候选公司 | 人工审核、研究结果 |
| Candidate/review page with `awaiting_review` | 研究主题、确认范围、候选公司 | 人工审核 | 研究结果 |
| Candidate/review page with `reviewed_plan_ready` | first four | 研究结果 via exact link | none |
| Exact result page | first four | 研究结果 | none |
| Stale/not-visible exact route | only state proven by loaded response | none | unknown steps remain unavailable |

A step is a link only when an exact accepted route is already available. The indicator cannot create a new back-navigation contract.

### 6.3 Accessibility

Use an ordered list with:

- visible ordinal and label;
- text status such as `已完成`, `当前`, `尚不可用`;
- `aria-current="step"` on the current step;
- `aria-disabled="true"` for unavailable steps;
- visible focus for linked steps;
- no color-only meaning.

## 7. One primary action per page/state

“One primary action” means exactly one visually dominant action at a time. Secondary actions may remain available with lower emphasis.

| Surface/state | Primary action | Secondary actions |
| --- | --- | --- |
| History with continuable first record | response-owned continuation label | change boundaries, view more history, start new research, technical details |
| History with no visible record | `发起新研究` | change boundaries |
| History with first record unavailable | `发起新研究` | inspect stopped record, change boundaries |
| New blank scope | `确认研究范围` | return to history |
| Exact scope after successful dry-run | `保存研究范围` | re-check, return |
| Candidate page `draft` | `确认范围并准备候选池` | edit scope, return |
| Candidate page `candidate_build_ready` | `构建完整候选池` | dry-run check, edit scope, return |
| Review incomplete | `检查审阅结果` | filter display, edit text, return |
| Review dry-run valid | `保存审阅计划` | revise decisions, return |
| Review commit success | `查看研究结果` | return to history |
| Exact result | `返回产业研究` | expand provenance |
| Stale/not-visible | `返回研究历史` | technical details |
| Database unavailable | `重新检查本地数据库` only when it repeats the same local health/read action | settings/help text; no network refresh |

A disabled future module, unavailable capability or technical disclosure is never styled as a primary action.

No action may imply buy, sell, hold, recommendation, target price, expected return, position sizing, portfolio addition or execution.

## 8. Ordinary-user Chinese state explanation contract

Every major state panel uses exactly three headings:

- **发生了什么**;
- **为什么重要**;
- **现在可以做什么**.

These are static reviewed presentation mappings, not generated summaries.

### 8.1 Review decisions

| Stable state | 发生了什么 | 为什么重要 | 现在可以做什么 |
| --- | --- | --- | --- |
| `selected_for_acceptance` | 该候选路径被纳入后续研究计划 | 这里只是审阅计划，不是正式受益公司或投资候选认定 | 补全理由、暴露类型和不确定性，并完成其余候选审阅 |
| `rejected_by_user` | 该候选路径在本次审阅中暂不纳入 | 路径、来源和理由仍保留在历史中，不会被删除 | 记录明确排除理由，或在保存前重新选择状态 |
| `unresolved` | 该候选路径仍待验证 | 证据、身份或受益路径不充分时不能强行得出结论 | 记录缺口与不确定性，后续获得证据后再创建新修订 |

### 8.2 Workflow and coverage

| Stable state | 发生了什么 | 为什么重要 | 现在可以做什么 |
| --- | --- | --- | --- |
| `draft` | 研究主题已记录，范围尚未完成确认 | 未确认范围时不能安全构建完整候选池 | 继续确认市场、产业链、排除项和种子 |
| `candidate_build_ready` | 研究范围已准备好构建候选公司 | 候选来源必须精确选择，不能从名称或热度推断 | 检查来源并构建完整本地范围候选池 |
| `awaiting_review` | 完整候选池已构建，尚未完成逐条审核 | 任何过滤都不能把未审阅候选从提交宇宙中删除 | 为每条路径选择三态、理由和不确定性 |
| `reviewed_plan_ready` | 完整审阅计划已经生成 | 结果可复现，但尚未写入正式领域所有者 | 查看精确研究结果和来源详情 |
| `reviewed_local_scope` | 当前确认的本地范围已完整审阅 | 完整只针对已确认本地范围，不等于全市场覆盖 | 阅读结果并保留范围说明 |
| `partial_local_coverage` | 当前本地来源不能覆盖已声明范围 | 不完整覆盖可能遗漏受益路径，不能标记为完整成功 | 缩小范围、补充精确来源或保留覆盖警告 |
| `coverage_unknown` | 系统无法证明当前范围是否完整 | 未知不能当作完整或中性状态 | 检查范围与来源后再继续 |

### 8.3 Read, alignment and capability states

| Stable state/code family | 发生了什么 | 为什么重要 | 现在可以做什么 |
| --- | --- | --- | --- |
| `partial` / `insufficient_data` | 返回的数据不完整或不足以形成该视图 | 缺失值不能被当作零、正常或成功 | 查看缺失原因，调整明确范围或等待受控数据补充阶段 |
| `different_cutoff` | 参与记录的信息截止日不同 | 混合截止日会影响可比性和复现 | 返回精确边界，选择一致记录或保留明确警告 |
| `different_session` | 参与数据来自不同有效交易日或研究会话 | 不能把未对齐状态描述为同一时点结论 | 查看有效日期并使用精确对齐记录 |
| `stale` / `not_visible` | 链接中的精确记录不在当前双时间边界内 | 自动换成新记录会改变历史含义 | 返回历史页并明确选择当前可见的精确记录 |
| `database_unavailable` / local query failure | 本地数据库当前无法读取 | 页面不能用空值或示例数据伪装成功 | 检查本地数据库配置和迁移状态后重复同一读取 |
| `unsupported_capability` | 当前阶段没有可靠契约支持该功能 | 推测值会混淆事实、分析和产品承诺 | 使用已开放能力；等待该功能单独治理 |
| malformed/unknown metadata | 返回状态缺少受支持的展示映射 | 猜测状态可能改变领域含义 | 显示通用不可用提示并展开技术代码 |

### 8.4 Write conflicts

For revision, candidate-build or review conflicts:

- **发生了什么:** 精确研究或候选版本在提交前发生变化，本次写入未完成。
- **为什么重要:** 静默重试或自动换到新版本可能把决定写入不同研究历史。
- **现在可以做什么:** 保留当前浏览器中的未保存决定，重新读取精确页面，对比后由用户再次确认。

The implementation must preserve entered review decisions, rationale, uncertainty and revision note in DOM memory after a `409`. It may not store them as accepted research state or silently submit again.

## 9. First-use empty-state guide

When the exact history response contains no sessions, replace the generic empty text with:

1. **描述研究主题** — 用普通中文写下行业、产业链、技术、政策或利润池问题；
2. **确认研究范围** — 明确市场、时间、产业链边界、排除项和已知种子；
3. **审核完整候选池** — 构建本地范围全量候选，并逐条选择纳入、排除或待确认。

Primary action: `发起新研究`.

The empty state must also state:

- no visible exact history exists under the current two boundaries;
- local database unavailability is a different failure state, not an empty history;
- fixture/demo data, if linked later, must be labelled `演示数据 / fixture` and cannot appear as current accepted research.

Phase 2B does not add a fake starter project or sample portfolio.

## 10. Navigation and static-shell implementation decision

The repository intentionally uses static HTML/CSS/vanilla JavaScript without a template framework.

Phase 2B must not introduce a frontend framework or generic shell service merely to deduplicate a small navigation block.

The bounded implementation may:

- correct the Today Market entry in `workbench.html`;
- correct `_MODULES` in the existing bootstrap API;
- retain the already correct navigation in `candidate_review.html`, `review_result.html` and `today_market.html`;
- add regression tests that parse every participating HTML surface and compare the exact five module labels, paths and active/disabled states;
- reuse existing workbench CSS classes and browser-local preferences.

A small shared presentation helper under `industry_analysis/static/**` is permitted only for the five-step indicator or state-copy rendering. It cannot fetch cross-domain data, own workflow state or become a client framework.

## 11. Query and performance boundaries

### 11.1 History entry

- one bootstrap request, at most one local `SELECT 1` health statement;
- one `/industry-analysis/api/sessions` request for both recent card and history list;
- `/sessions` remains at most one SQL statement independent of returned session count;
- no per-session detail, candidate, review or result request on history-page load;
- no second request merely to identify the card;
- default history limit remains bounded and never exceeds the accepted API maximum.

Maximum database statements for a successful initial history page: **2**, independent of displayed record count.

### 11.2 Exact flow pages

The five-step indicator and state explanation use the response already loaded by the exact page. They add:

- zero database statements;
- zero network requests beyond existing local API reads;
- zero domain writes.

No overview may issue per-candidate, per-company or per-step requests.

The later implementation must record measured statement counts in regression tests. If the exact existing response cannot support the card without row-count-dependent queries, stop rather than add a cache or generic overview framework.

## 12. Error and failure behavior

Stable failures remain Chinese-first with a technical code under progressive detail. SQL, stack traces, credentials, connection values and local filesystem paths never appear.

### 12.1 Required failure paths

- **No history:** show first-use guide, not database failure.
- **Database unavailable:** show unavailable explanation and no fake history card.
- **First exact record non-continuable:** show that record; do not skip it; primary action is new research, not a fabricated continuation.
- **Exact route target not visible:** show stale/not-visible explanation and return to history; do not select another revision.
- **Candidate universe empty:** keep candidate step active and explain that no exact sources produced candidates.
- **Candidate universe incomplete:** keep coverage warning and block any claim of complete review.
- **Unresolved review items:** allow unresolved as an explicit decision, but require every candidate to have one of the three states before save.
- **Session/cutoff mismatch:** show mismatch; do not align automatically.
- **Concurrent write conflict:** preserve unsaved browser decisions; no automatic retry.
- **Unknown workflow state:** continuation unavailable and technical code visible.
- **Unsupported future module:** disabled with `后续阶段`; no click target and no sample values.
- **Malformed continuation metadata:** ignore path, fail closed and keep the history row visible.

### 12.2 Security of returned paths

A continuation path is accepted only when generated by the local API adapter from exact UUID values and known internal route templates.

The browser must not:

- accept an external origin;
- render arbitrary HTML from labels;
- concatenate user free text into a path;
- follow a path whose `kind` and stable route prefix disagree.

## 13. Accessibility and presentation

- Chinese-first copy;
- semantic headings and ordered workflow list;
- keyboard-operable actions and disclosures;
- visible focus indicators;
- one `aria-current="page"` module and one `aria-current="step"` step where applicable;
- current/completed/unavailable state conveyed by text and shape, not color alone;
- status changes announced through existing polite live regions;
- primary action remains visually clear at comfortable and compact density;
- technical details remain accessible through `<details>` and never trap focus;
- narrow layouts stack the card, workflow and action without horizontal scrolling;
- no chart, animation framework or mobile-specific redesign.

## 14. No-write and no-network contract

The following Phase 2B behavior performs no external network request:

- import and startup;
- workbench page load;
- module navigation;
- history and continuation projection;
- workflow indicator;
- state explanation rendering;
- settings load;
- tests, CI and offline demo.

Phase 2B creates no new write. Existing scope, candidate-build and review writes remain under their accepted exact command contracts.

No read action triggers:

- Provider refresh;
- news, announcement or disclosure acquisition;
- scheduler or background task;
- AI call;
- follow, alert or portfolio mutation.

## 15. Production-realistic offline golden paths

### 15.1 Returning user

Using normal persisted production boundaries:

1. Persist exact sessions representing `draft`, `candidate_build_ready`, `awaiting_review` and `reviewed_plan_ready` histories.
2. Open `/workbench`; receive the existing redirect to `/industry-analysis`.
3. The page generates explicit current information and recorded boundaries and performs one bounded history read.
4. The first exact visible row appears as the recent-research card.
5. The card shows title, ordinary state, current step, coverage and one action without exposing IDs as inputs.
6. Activate the response-owned action.
7. Open the exact existing route with exact record-owned identifiers and boundaries.
8. See the five-step indicator and one current step.
9. See one visually dominant next action and the three-part state explanation.
10. Expand technical detail and reproduce the exact session/revision/fingerprint/chronology.
11. Complete the current exact flow without hidden network, record substitution or automatic state mutation.

### 15.2 No-skipping guarantee

1. Persist the newest visible session as `abandoned` and an older session as `awaiting_review`.
2. Load history under boundaries that see both.
3. The recent card shows the abandoned newest exact session.
4. It does not skip to the older reviewable session.
5. The older session remains available in the ordinary history list.

### 15.3 New user

1. Use an available local database with no session visible under the exact boundaries.
2. Open the workbench.
3. Show the three-step first-use guide.
4. Show `发起新研究` as the primary action.
5. Create a research scope using the existing route and command contract.
6. No fixture is represented as current accepted state.

### 15.4 Navigation consistency

1. Open history, scope, candidate review, result, settings and Today Market surfaces.
2. Confirm identical five-module labels and activation availability.
3. Today Market and Industry Research are active everywhere.
4. Follow/Track and Research Portfolio are unavailable everywhere.
5. Exactly one current page receives `aria-current="page"`.

## 16. Required implementation tests

The later implementation must include focused tests proving:

- `/sessions` deterministic ordering remains unchanged;
- the recent card uses `sessions[0]` from the same history response;
- no second recent-card request or per-row request occurs;
- exact continuation projection for `draft`;
- exact continuation projection for `candidate_build_ready`;
- exact continuation projection for `awaiting_review`;
- exact continuation projection for `reviewed_plan_ready`;
- closed failure for `accepted_outputs_linked`, `superseded`, `abandoned` and unknown states;
- continuation paths contain only response-owned exact IDs and boundaries;
- first record is never skipped to find a convenient action;
- technical identifiers are under disclosure and absent from ordinary form inputs;
- five-step labels and mapping on each participating route/state;
- exactly one primary-styled action for each tested state;
- stable three-part state-copy mappings;
- review conflict preserves unsaved decisions and does not retry;
- empty history differs from database unavailable;
- navigation markup/module projection consistency;
- Today Market remains active and later modules disabled;
- initial history page statement ceiling at two and `/sessions` ceiling at one;
- no hidden network in import, startup, pages, tests or demo;
- no new schema, migration, dependency or persistence.

Documentation-only architecture validation should check Markdown structure, links, issue references, exact base and base-to-head file inventory. Full database regression becomes mandatory in the later Strict implementation PR.

## 17. Candidate future implementation file families

After this architecture is approved, merged and separately authorized, one Strict implementation Issue may authorize only:

- `.codex/tasks/issue-<N>-personal-research-workbench-ui-phase2b-*`;
- `backend/api/industry_analysis.py`;
- `backend/api/industry_analysis_candidates.py` and `backend/api/industry_analysis_review.py` only to reuse one bounded exact-route projection helper, with unchanged command semantics;
- `industry_analysis/static/workbench.html`;
- `industry_analysis/static/workbench.js`;
- `industry_analysis/static/workbench_phase1c.js` only when the one-primary-action transition requires it;
- `industry_analysis/static/candidate_review.html`;
- `industry_analysis/static/candidate_review.js`;
- `industry_analysis/static/review_result.html`;
- `industry_analysis/static/review_result.js`;
- bounded shared `industry_analysis/static/**` CSS/JS presentation helpers;
- `today_market/static/today_market.html` only if exact navigation regression requires a markup correction;
- focused `tests/test_industry_analysis*`, static navigation tests and query-count tests;
- one offline ordinary-user Phase 2B demo;
- `.github/workflows/local-tests.yml` only to add that demo without removing or weakening checks;
- focused README/baseline status text only after implementation acceptance.

No other file family is authorized without an Issue amendment.

The implementation should not modify `industry_alpha/industry_thesis_*` domain services or models unless this preflight is reopened. Existing history fields are sufficient; continuation is an API/presentation projection.

## 18. Migration, rollback and downgrade decision

- Schema migration: none.
- Data backfill: none.
- Persistent state: none.
- Dependency change: none.
- Rollback: revert static/API projection changes; all persisted research history remains unchanged.
- Downgrade: no database or accepted-history effect.
- Browser-local preferences: existing keys unchanged; no new research-state key.

Any implementation finding that requires persistence, backfill or accepted-state repair is an architecture stop condition.

## 19. Stop conditions

Stop and return to Issue #215 architecture review if implementation requires:

- a new table, schema, migration or persistent recent-item state;
- a second workflow-state owner;
- a generic activity feed, cross-domain overview or orchestration service;
- selecting a newer/latest-compatible record outside the exact history ordering;
- skipping the first record to find a continuable record;
- fuzzy matching by title, company, Provider or free text;
- browser-local reconstruction of research identity or workflow progress;
- changing `IndustryThesis` accepted workflow semantics;
- per-row or row-count-dependent history queries;
- Provider, remote acquisition, credential or external network access;
- scheduler, background worker, notification or alert state;
- new AI calls or industry-level AI assistance;
- accepted Evidence, Industry Map, Stage 1, Company Research, Investment Candidate or portfolio writes;
- Daily Radar, Follow/Track, Research Portfolio or market-attention capability;
- a frontend/charting framework;
- mobile-specific redesign;
- release, tag or version change.

## 20. Locked exclusions

Phase 2B excludes:

- new market, evidence, industry, company, valuation or candidate semantics;
- accepted thesis-plan owner handoff or output links;
- automated market-data refresh;
- news, announcement, disclosure or social acquisition;
- Daily Industry/Investment Radar;
- followed-entity state, reminders and alerts;
- research or simulated portfolio ledger;
- global search, tags, folders, favorites or custom dashboards;
- fair value, target price, expected return, recommendation or position sizing;
- broker connection, order management or automated trading;
- external AI, RAG, tool use or persisted AI output;
- schema, migration, dependency, release, tag or version changes.

## 21. Definition of Ready

A later implementation Issue is ready only when this architecture receives fixed-head approval proving:

- exact current routes and API owners are enumerated;
- one existing history response owns both recent card and history list;
- deterministic first-record selection and no-skipping behavior are explicit;
- exact continuation projection is closed and fail-closed;
- five-step route/state mapping is complete;
- one-primary-action rules are complete;
- ordinary-user state-copy mappings cover required success, incomplete, stale, conflict, database and unsupported states;
- navigation states are consistent and later modules remain unavailable;
- query ceilings, accessibility, security and no-network behavior are explicit;
- golden and failure paths are production-realistic and offline;
- migration/rollback decisions, stop conditions and exclusions are fixed;
- the complete architecture diff stays within authorized documentation families;
- applicable CI succeeds at the exact final HEAD;
- a process-independent reviewer re-reads the Issue, workflow, architecture, diff and validation at that exact HEAD;
- all review threads are resolved;
- the project owner separately authorizes merge.

Required fixed-head approval phrase:

`AUTHORIZED PERSONAL RESEARCH WORKBENCH UI PHASE 2B PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`

Architecture merge does not authorize production implementation.
