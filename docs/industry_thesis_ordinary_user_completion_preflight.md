# Industry Thesis Ordinary-User Completion v1 — Architecture Preflight

## 1. Status, authority and decision

This document is the architecture contract for Issue #238.

Authority:

- Product Roadmap: #137;
- accepted owner-acceptance architecture: Issue #234 / merged PR #235;
- accepted owner-acceptance implementation: completed Issue #236 / merged PR #237;
- accepted ordinary-user Workbench foundation: #215/#216 and #217/#218;
- workflow: `.codex/WORKFLOW.md`;
- exact architecture base: `a6da9bc8483606a67b7ca5f1329e46232d5b47be`.

Project-owner authorization on 2026-07-25:

```text
批准，基于规划进去下一步开发
```

Decision:

```text
architecture_status = proposed_for_fixed_head_review
future_implementation_risk = strict
schema_migration = none
new_persisted_ui_state = none
external_network = prohibited
provider_or_ai_path = prohibited
```

The next implementable product slice is a thin local ordinary-user adapter over the accepted Industry Thesis owner-acceptance core. It does not create a new domain owner, new accepted meaning or new scoring system.

Today Market automatic-refresh architecture already exists through #221/#222, while live source activation remains blocked by Issue #225. This preflight advances the independent P0-B ordinary-user industry-research path without bypassing the P0-A external-contract gate.

## 2. Product objective

Complete the current local industry-research flow:

```text
reviewed_plan_ready
  -> 查看研究结果
  -> 检查并接受研究成果
  -> 核对每个成员的正式归属与状态
  -> 生成变更预览
  -> 明确确认接受
  -> accepted_outputs_linked
  -> 查看已接受成果
  -> exact history reopening
```

An ordinary user must be able to finish this flow without understanding UUIDs, SHA-256 fingerprints, database schemas, transaction keys or owner-port terminology.

The UI may simplify presentation, but it may not simplify away exact ownership. Every accepted owner binding remains explicit and server-validated.

## 3. Existing contracts preserved

The implementation must reuse, not reinterpret:

1. `IndustryThesisOwnerAcceptanceCoordinator` and its strict preview/commit contract;
2. exact `reviewed_plan_ready -> accepted_outputs_linked` transition;
3. one outer atomic transaction;
4. Stage 1 and Typed Semantics owner validation inside their owning modules;
5. complete accepted result separated from supported-only candidate-pool handoff;
6. valid zero-supported acceptance;
7. deterministic UUIDv5 transaction/output identities and identical replay;
8. conflicting replay, stale expected-latest and graph corruption fail-closed behavior;
9. exact dual-as-of output, result and readiness reads;
10. no automatic Company Research or Investment Candidate creation.

The web adapter owns only transport, ordinary-language projection, safe route construction and temporary browser form state.

## 4. User-visible pages and exact routes

### 4.1 Reviewed result page

Existing route:

```text
GET /industry-analysis/sessions/{session_id}/revisions/{reviewed_session_revision_id}/result
```

For exact `workflow_state = reviewed_plan_ready`, the page adds one primary action:

```text
检查并接受研究成果
```

The path is generated server-side from the exact session ID, exact reviewed revision ID and the existing `as_of_cutoff` / `as_of_recorded_at_utc` boundaries.

### 4.2 Acceptance page

Chosen route:

```text
GET /industry-analysis/sessions/{session_id}/revisions/{reviewed_session_revision_id}/acceptance
```

The page is served only for an exact cutoff-visible `reviewed_plan_ready` revision belonging to the exact session.

The page contains:

- accepted scope summary;
- complete selected-member list in frozen order;
- exact owner-binding controls in ordinary Chinese;
- blocked/missing prerequisites;
- revision note;
- one primary preview action;
- technical details under progressive disclosure.

### 4.3 Accepted-result page

Chosen route:

```text
GET /industry-analysis/sessions/{session_id}/revisions/{accepted_session_revision_id}/accepted-result
```

The route is keyed by the exact accepted session revision, not by a latest session lookup. The server-side projection reads the frozen output-link revision ID from the accepted session contract, verifies the exact graph through existing core query services and returns one complete first-render response.

For `accepted_outputs_linked`, history continuation becomes:

```text
查看已接受成果
```

For `superseded`, `abandoned`, unknown or malformed state, continuation remains fail closed.

## 5. Local API contract

All APIs retain the existing prefix:

```text
/industry-analysis/api
```

Every write model is strict and rejects unknown fields. Request bodies remain JSON-only and within the existing 1 MiB ceiling.

### 5.1 Acceptance view

```text
GET /industry-analysis/api/session-revisions/{reviewed_session_revision_id}/owner-acceptance-view
    ?session_id={session_id}
    &as_of_cutoff={date}
    &as_of_recorded_at_utc={utc}
```

Purpose:

- verify exact session/revision/state/boundaries;
- return reviewed-plan summary and complete selected members;
- return exact compatible owner options and explicit missing prerequisites;
- return a form contract, not a commit-ready fingerprint.

The response must include:

```text
session_id
reviewed_session_revision_id
reviewed_plan_fingerprint
expected_session_latest_revision_number
research_case
industry_map_revision
information_cutoff_date
recorded_at_utc
members[]
allowed_operation_versions
revision_note_constraints
primary_action
technical_details
```

Each member projection includes:

```text
sequence
reviewed_candidate_revision_id
ordinary_identity_label
identity_state
stock_basic_options[]
stage1_identity_state
stage1_reuse_options[]
stage1_create_or_append_contract
semantic_reuse_options[]
semantic_authoring_state
supported_handoff_options
blocking_reasons[]
readiness_hints[]
technical_details
```

No option is generated by company-name, ticker, Provider label or free-text similarity.

### 5.2 Preview

```text
POST /industry-analysis/api/session-revisions/{reviewed_session_revision_id}/owner-acceptance/preview
    ?session_id={session_id}
    &as_of_cutoff={date}
    &as_of_recorded_at_utc={utc}
```

Body:

```text
{
  "expected_session_latest_revision_number": 1,
  "owner_acceptance_plan": { ...strict accepted core payload... },
  "revision_note": "..."
}
```

The adapter normalizes the body only through the accepted core. It does not add, infer or rewrite owner fields.

Success returns:

```text
commit_ready
owner_plan_fingerprint_sha256
reviewed_plan_fingerprint_sha256
complete_member_count
supported_handoff_count
candidate_pool_mode
operations[]
blocking_reasons[]
readiness_gaps[]
preview_summary
```

No database write occurs.

### 5.3 Commit

```text
POST /industry-analysis/api/session-revisions/{reviewed_session_revision_id}/owner-acceptance/commit
    ?session_id={session_id}
    &as_of_cutoff={date}
    &as_of_recorded_at_utc={utc}
```

Body:

```text
{
  "expected_session_latest_revision_number": 1,
  "owner_acceptance_plan": { ...same normalized payload... },
  "expected_owner_plan_fingerprint_sha256": "...",
  "revision_note": "..."
}
```

Commit is rejected unless the fingerprint matches the current normalized plan and all expected-latest values remain valid.

Success returns only exact committed identifiers and safe navigation:

```text
accepted_session_revision_id
output_link_revision_id
owner_transaction_id
identical_replay
accepted_result_path
history_path
```

The ordinary page navigates only to the server-returned same-origin `accepted_result_path` after validating its expected route kind.

### 5.4 Accepted-result view

```text
GET /industry-analysis/api/session-revisions/{accepted_session_revision_id}/accepted-result-view
    ?session_id={session_id}
    &as_of_cutoff={date}
    &as_of_recorded_at_utc={utc}
```

One workbench query service composes existing exact output, complete-result and readiness reads inside one caller-owned read session.

Composition rules:

- the accepted session must belong to the exact session;
- workflow state must be `accepted_outputs_linked`;
- its frozen output-link revision ID must match the exact output graph;
- all three core reads must succeed;
- any integrity mismatch fails the entire view closed;
- no partial accepted page is returned from a corrupted graph.

## 6. Owner-binding interaction contract

### 6.1 Identity

The ordinary label may show company name, exchange and code, but selection value is one exact accepted identity ID.

Rules:

- exact `stock_basic` is mandatory for create/append Stage 1 operations;
- listed-instrument-only identity is visibly blocked;
- one compatible option may be visibly preselected, but the member remains unconfirmed until the user checks `确认使用此正式公司记录` or performs the equivalent explicit action;
- multiple options require explicit choice;
- zero options are blocked and provide one corrective action.

### 6.2 Stage 1 operation

The v1 UI supports all core Stage 1 operation modes only when production-reachable exact inputs exist:

```text
reuse_exact_revision
create_identity_and_revision
append_revision
```

`reuse_exact_revision` displays frozen kind, status, assertion/claim count, cutoff and revision note.

Create/append displays explicit editable fields already accepted by the core:

- exact `stock_basic`;
- legacy beneficiary kind;
- assessment status;
- exact map assertion revision selections;
- exact claim revision selections;
- rationale;
- information cutoff;
- expected latest revision when appending.

The page never derives legacy kind from reviewed exposure.

### 6.3 Typed Semantics operation

The v1 ordinary-user completion page supports:

```text
none
reuse_exact_revision
```

It does **not** author a new complete Typed Semantics profile in this slice. The accepted core’s append capability remains available to local JSON commands and later owner-specific UX, but exposing the full assertions/evidence/verification authoring contract would broaden this slice into a second complex workspace.

When no compatible semantic revision exists, the user may explicitly choose `本次不绑定类型化语义记录`; readiness remains incomplete where applicable.

When the user needs a new semantic profile, the page shows a non-committing secondary link to the existing owning workspace if an exact route exists. It does not auto-create or infer one.

### 6.4 Supported handoff

The page shows two independent concepts:

```text
完整接受成员
可进入后续研究的 supported 成员
```

Rules:

- only resulting exact `supported` Stage 1 revisions can enter handoff;
- draft/disputed members remain in the complete accepted result and are excluded with explicit reasons;
- rejected is blocked before preview;
- zero-supported acceptance displays `本次成果可以接受，但当前没有成员进入 supported 后续研究池`;
- no empty/fake candidate pool is created.

## 7. Preview and confirmation UX

The acceptance page has two presentation states.

### 7.1 Editing state

Primary action:

```text
生成变更预览
```

Preview is disabled only when client-side required fields are visibly missing. Server validation remains authoritative.

### 7.2 Commit-ready preview state

The page freezes the submitted form payload in browser memory and renders:

- how many owner revisions will be reused, created or appended;
- which members enter supported handoff;
- which members remain draft/disputed;
- semantic reuse/absence;
- zero-supported state;
- readiness gaps;
- data cutoff and recorded boundary;
- research-only/non-advisory notice.

Primary action:

```text
确认接受研究成果
```

Any edit invalidates the local preview and removes the commit-ready fingerprint. The user must generate a new preview.

Commit never runs on page load, preview, route navigation, browser refresh or automatic retry.

## 8. Conflict, replay and failure behavior

### 8.1 Stable HTTP mapping

- exact record not found/not visible: `404`;
- stale expected-latest, moved owner boundary, duplicate/conflicting acceptance: `409`;
- strict payload or blocked owner condition: `422`;
- database unavailable: `503`;
- invalid JSON/content type/body ceiling: existing `400/413/422` behavior.

### 8.2 Ordinary-language error projection

Every error returns:

```text
code
message
technical_message (progressive details only)
recovery_action
preserve_form
```

Examples:

- stale revision: `研究状态已经变化，请保留当前选择并重新读取后再次预览。`
- missing exact identity: `这家公司还没有可接受的正式公司记录，当前不能提交。`
- graph corruption: `已接受成果的本地链接不完整，系统已停止展示，请先执行完整性检查。`
- conflicting replay: `这条研究已经用另一套接受方案完成，原结果不会被覆盖。`

### 8.3 Form preservation

On `409`, `422` or `503`:

- keep all user selections, rationale and revision note in DOM/page memory;
- do not retry automatically;
- do not fetch latest and silently apply the form;
- remove commit-ready state when the server says the preview is stale;
- expose one primary recovery action.

Identical replay navigates to the original exact accepted result.

## 9. Accepted-result presentation

First render order:

1. `成果已接受` status, accepted time and visible cutoff;
2. 5–8 concise result facts;
3. complete accepted member list in frozen order;
4. supported-only handoff as a separate section;
5. per-member readiness;
6. evidence/owner-operation details;
7. technical metadata.

Required concise facts include:

- complete member count;
- supported-handoff count;
- draft/disputed count;
- semantic coverage state;
- Company Research readiness state;
- largest missing prerequisite;
- whether this was an identical replay;
- explicit `研究用途，不构成投资建议` notice.

Per-member cards show:

```text
正式公司身份
Stage 1 状态与链路位置
是否进入 supported handoff
类型化语义状态
Company Research / downstream readiness
缺失、争议、待验证或失败原因
```

No priority score, recommendation, target price, expected return or position instruction is added.

## 10. Exact history continuation

The existing sessions response extends the presentation-owned continuation mapping:

- `reviewed_plan_ready` -> exact reviewed result path;
- `accepted_outputs_linked` -> exact accepted-result path;
- `superseded` / `abandoned` / malformed -> unavailable.

The server projection must obtain the accepted output reference from the exact accepted session revision. The browser must not parse canonical owner JSON to discover navigation IDs.

The first record is never skipped to find a more convenient continuable record.

## 11. Query and performance contract

### 11.1 HTTP budget

Acceptance first load:

```text
one existing page asset load
one owner-acceptance-view request
zero per-member requests
```

Preview/commit:

```text
one preview request per explicit user action
one commit request per explicit user action
zero silent retries
```

Accepted-result first load:

```text
one accepted-result-view request
zero per-member requests
```

### 11.2 Database statement ceilings

The future workbench projection must bulk-load options and exact reads.

Required ceilings, independent of member count within the accepted core’s existing bound:

```text
owner-acceptance-view <= 12 SQL statements
accepted-result-view <= 10 SQL statements
```

Preview and commit retain the existing core’s deterministic owner locking/writing behavior; the UI layer adds no per-member session or API call.

Tests must assert statement ceilings on at least 3-member and 20-member fixtures.

### 11.3 Complete-universe rendering

The first response contains every frozen accepted member. UI virtualization, collapsed details or client-side paging may improve rendering, but no server-side page may imply that a partial page is the complete accepted universe.

## 12. Persistence, migration and rollback

Decision:

```text
migration = none
new table = none
new accepted field = none
new browser-local identity = none
new server-side draft = none
```

Temporary editing and preview payloads live only in page memory. Browser refresh intentionally discards unsaved preview state unless the browser itself restores form controls; no accepted meaning is persisted outside the existing owner transaction.

Rollback of the future implementation is deletion/reversion of the adapter, pages and tests. Existing accepted owner data remains readable through local JSON commands/core query services.

If implementation discovers a required persistent field, new owner, migration or inability to produce exact selector options, it must stop and return to architecture review.

## 13. Security and locality

- same-origin local routes only;
- no external URL or redirect accepted from payloads;
- server validates UUIDs, session/revision relationships, fingerprints and boundaries;
- no raw HTML from user or domain labels;
- text rendered through safe DOM APIs/templates;
- no credentials, Provider fields or network calls;
- no AI or remote transmission;
- no request replay after page closure;
- strict unknown-field rejection for all writes;
- technical errors do not leak connection strings or secrets.

## 14. Accessibility and copy

- Chinese-first labels;
- exact five-step workbench progression remains visible;
- acceptance is part of `研究结果`, not a sixth hidden workflow owner;
- one primary action per state;
- keyboard-reachable member controls and disclosure panels;
- focus moves to preview summary or error summary after submission;
- `aria-current="step"` on `研究结果`;
- explicit text/icons, never color alone;
- technical details use `<details>` or equivalent progressive disclosure;
- comfortable/compact density and existing appearance settings remain presentation-only.

## 15. Production-realistic offline golden path

Fixture prerequisites:

- one exact session and `reviewed_plan_ready` revision;
- one exact Research Case and existing Industry Map revision;
- three selected reviewed candidates in frozen order;
- exact persisted owner records reachable through production queries.

Path:

1. User opens reviewed result and selects `检查并接受研究成果`.
2. Acceptance view returns all three members and exact options in one response.
3. Company A explicitly reuses a supported Stage 1 revision and compatible semantic revision; it enters handoff.
4. Company B explicitly reuses/appends a draft or disputed Stage 1 revision; it remains in complete result and is excluded from handoff.
5. Company C explicitly reuses/creates/appends a supported Stage 1 revision, chooses no semantic binding and enters handoff with readiness gaps.
6. User generates preview; no writes occur.
7. Preview displays complete count `3`, supported handoff `2`, draft/disputed `1` and readiness gaps.
8. User explicitly confirms with the matching fingerprint.
9. One atomic core commit returns exact accepted session/output IDs.
10. Accepted-result view returns all three in frozen order under both boundaries.
11. Reload and exact history reopening reproduce the same result.
12. No Company Research, Investment Candidate, recommendation, portfolio or trading state is created.

Zero-supported path:

- at least two valid draft/disputed members;
- preview clearly shows no supported handoff;
- explicit commit succeeds;
- accepted result shows all complete members and no fabricated pool.

## 16. Primary blocked path

One selected candidate has only a listed-instrument identity or lacks exact Stage 1 assertion/claim bindings.

Required result:

- the exact member is marked blocked in acceptance view;
- ordinary explanation identifies the missing prerequisite;
- preview returns no commit-ready fingerprint;
- no commit primary action appears;
- one corrective/review action is shown;
- no owner, session, pool or output row is written;
- reviewed plan remains exact and reopenable;
- no name/ticker/free-text/Provider/AI inference fills the gap.

## 17. Future implementation file families

A separately authorized Strict implementation Issue may permit bounded changes to:

```text
backend/api/industry_analysis.py
backend/api/industry_analysis_review.py
backend/api/industry_analysis_acceptance.py (new bounded adapter if chosen)
industry_alpha/industry_thesis_owner_acceptance_workbench.py
industry_analysis/static/review_result.html
industry_analysis/static/review_result.js
industry_analysis/static/owner_acceptance.html
industry_analysis/static/owner_acceptance.js
industry_analysis/static/accepted_result.html
industry_analysis/static/accepted_result.js
bounded shared industry_analysis/static CSS/JS helpers
focused tests/test_industry_analysis* and tests/test_industry_thesis_owner_acceptance*
one offline ordinary-user acceptance demo
.github/workflows/local-tests.yml only to add that demo without weakening checks
docs/architecture_baseline.md only after implementation acceptance
```

The implementation Issue must decide exact filenames; this list authorizes no code now.

## 18. Future validation requirements

Minimum executable coverage:

- exact continuation mapping for `reviewed_plan_ready` and `accepted_outputs_linked`;
- fail-closed continuation for terminal/malformed states;
- route values from exact response-owned IDs and boundaries;
- selector options from exact compatible owners only;
- no automatic exposure-to-legacy/typed mapping;
- single-option explicit confirmation;
- multiple/zero-option behavior;
- three-company golden path;
- zero-supported path;
- listed-instrument/missing-claim blocked path;
- preview zero writes and fingerprint stability;
- explicit commit and one exact atomic result;
- identical replay navigation;
- conflicting replay preservation;
- stale `409` form preservation and no retry;
- exact accepted-result graph and readiness;
- cutoff and recorded-UTC negative visibility;
- graph corruption ordinary fail-closed state;
- one primary action;
- accessibility and safe text rendering;
- HTTP/query ceilings and no per-row requests;
- no schema/migration/new persistence;
- import/startup/page/test/demo network denial;
- no Provider, credential or AI path;
- no recommendation, target price, expected return, portfolio or trading semantics;
- complete repository regression and every configured offline demo on the exact final HEAD.

## 19. Locked exclusions

No Today Market source activation, THS/iFinD/Tushare/AKShare/CNINFO access, credentials, external network, automatic refresh, scheduler, background worker, retry loop, notification, AI call, new Industry Map facts, draft-graph promotion, fuzzy identity bridge, automatic classification mapping, automatic semantic-profile authoring, automatic Company Research, automatic component scoring, automatic Investment Candidate snapshot, recommendation, target price, expected return, position sizing, research holdings, portfolio, broker, order, trading, release, tag or version change.

## 20. Stop conditions

Stop implementation authorization if:

- exact selector options cannot reach a complete golden path;
- ordinary completion depends on hidden inference;
- raw IDs must become mandatory primary inputs;
- a second workflow owner or server-side draft is required;
- the adapter must duplicate owner validation or write ORM rows directly;
- a migration or accepted-field change is required;
- exact reopening requires latest fallback;
- the complete result and supported handoff cannot remain separate;
- typed-semantic authoring must be embedded to make the first slice useful;
- scope expands into general redesign, Follow/Track, Research Portfolio, announcement acquisition or Today Market source work;
- any Provider, network, AI, recommendation, portfolio or trading behavior appears.

## 21. Fixed-head architecture gate

Before merge consideration:

1. exact branch base `a6da9bc8483606a67b7ca5f1329e46232d5b47be`;
2. only the Issue #238 task snapshot and this document changed;
3. repository checks succeed on one exact immutable HEAD;
4. fresh process-independent fixed-head architecture review;
5. zero unresolved review threads;
6. exact approval phrase:

```text
AUTHORIZED INDUSTRY THESIS ORDINARY-USER COMPLETION PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

7. separate explicit project-owner merge authorization.

Any new commit invalidates prior exact-head CI and review evidence.

Architecture approval does not authorize production implementation, Issue closure, release or any later roadmap phase.
