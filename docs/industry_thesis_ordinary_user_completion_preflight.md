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

Remediation authorization on 2026-07-25:

```text
修复阻断项
```

The old fixed-head review at `dd8e7331cbe2fb18cf77b97aca647d21c03df0f3` recorded three blockers in Review `4779124457`. This revision resolves those blockers by aligning the ordinary-user surface exactly with the accepted core rather than introducing a second interpretation.

Decision:

```text
architecture_status = remediated_for_new_fixed_head_review
future_implementation_risk = strict
schema_migration = none
new_persisted_ui_state = none
external_network = prohibited
provider_or_ai_path = prohibited
identity_replacement_during_acceptance = prohibited
core_request_shape = exact_flat_owner_acceptance_plan
supported_handoff_owner = one_global_candidate_pool_operation
```

The future slice is a thin local ordinary-user adapter over the accepted Industry Thesis owner-acceptance core. It creates no new domain owner, accepted meaning, ranking, score or recommendation.

Today Market automatic-refresh architecture already exists through #221/#222, while live source activation remains blocked by Issue #225. This preflight advances only the independent P0-B ordinary-user industry-research path.

## 2. Product objective

Complete the current local industry-research flow:

```text
reviewed_plan_ready
  -> 查看研究结果
  -> 检查并接受研究成果
  -> 核对已冻结的正式归属与 Owner 操作
  -> 选择一个全局 supported handoff 操作
  -> 生成变更预览
  -> 明确确认接受
  -> accepted_outputs_linked
  -> 查看已接受成果
  -> exact history reopening
```

An ordinary user must finish this flow without understanding UUIDs, SHA-256 fingerprints, database schemas, transaction keys or owner-port terminology.

The UI may simplify presentation, but it must not simplify away exact ownership. Every accepted owner binding and every write field remains explicit and server-validated.

## 3. Existing contracts preserved

The implementation must reuse, not reinterpret:

1. `IndustryThesisOwnerAcceptanceService.preview` and `.commit`;
2. `normalize_owner_acceptance_plan` and its strict unknown-field rejection;
3. exact `reviewed_plan_ready -> accepted_outputs_linked` transition;
4. one outer atomic transaction;
5. Stage 1 and Typed Semantics validation inside their owning modules;
6. complete accepted result separated from supported-only candidate-pool handoff;
7. valid zero-supported acceptance;
8. deterministic owner-plan fingerprint and owner transaction/output identities;
9. idempotent replay and conflicting replay behavior;
10. exact dual-as-of output, result and readiness reads;
11. no automatic Company Research or Investment Candidate creation.

The web adapter owns only transport, ordinary-language projection, safe route construction, exact DTO construction and temporary browser form state.

## 4. Resolution of Review 4779124457

### 4.1 Frozen `stock_basic` binding, not a selector

Owner acceptance cannot choose a different formal stock identity.

For each selected reviewed candidate, the coordinator requires:

```text
submitted stage1.stock_basic_record_id
  == reviewed_candidate.proposed_stock_basic_record_id
```

Therefore the acceptance page exposes exactly one of two states:

```text
frozen_stock_binding_available
frozen_stock_binding_missing_or_listed_instrument_only
```

When available, the page displays:

- ordinary company label;
- exchange/code label from the exact frozen record;
- exact `stock_basic_record_id` under technical details;
- explicit checkbox/action `确认使用审核结果中已冻结的正式公司记录`.

The confirmation is presentation state only. It does not modify the frozen identity.

When missing:

- no alternative identity options are returned;
- no name/ticker similarity lookup is attempted;
- no preview-ready plan is constructed;
- the primary action returns to an explicit pre-acceptance candidate review/identity correction path;
- the reviewed plan remains unchanged.

Any future ability to replace a reviewed candidate identity requires a separate accepted revision before owner acceptance and is outside this slice.

### 4.2 Exact flat core request

Preview and commit expose the exact flat core request accepted by `normalize_owner_acceptance_plan`.

There is no `owner_acceptance_plan` wrapper and no duplicated authority.

Preview fields:

```text
reviewed_session_revision_id
expected_session_latest_revision_number
reviewed_plan_fingerprint_sha256
research_case_id
map_mode
industry_map_id
industry_map_revision_id
candidate_owner_bindings
candidate_pool_operation
output_title
output_scope
information_cutoff_date
revision_note
owner_acceptance_plan_version
```

Commit uses the same fields plus:

```text
preview_fingerprint_sha256
```

The route revision ID and body `reviewed_session_revision_id` must match exactly. The adapter rejects a mismatch before calling the core.

The adapter must preserve the core field names and meanings. It may add presentation-only summaries and same-origin navigation paths to responses, but it must not rename:

```text
preview_fingerprint_sha256
owner_acceptance_plan_fingerprint_sha256
idempotent_replay
blocked_reasons
operation_summaries
```

### 4.3 One global `candidate_pool_operation`

Supported-handoff membership is not a per-member choice.

It is derived by the core from resulting Stage 1 revisions where:

```text
assessment_status == supported
```

The form contains one top-level candidate-pool operation using exactly one core mode:

```text
create_supported_handoff
append_supported_handoff
reuse_exact_supported_handoff
none_no_supported_members
```

The server returns exact compatible pool information; the user explicitly selects/confirms one global mode. Final membership remains core-derived and is never edited independently.

### 4.4 Mandatory field ownership

Every strict core field has one source. No field is created from display labels or similarity.

Top-level field ownership:

| Field | Authority |
|---|---|
| `reviewed_session_revision_id` | exact reviewed revision in route/acceptance view |
| `expected_session_latest_revision_number` | exact current session identity returned by acceptance view |
| `reviewed_plan_fingerprint_sha256` | frozen reviewed-plan preview |
| `research_case_id` | exact reviewed plan / accepted local case |
| `map_mode` | fixed accepted constant `reuse_exact_existing_map_revision` |
| `industry_map_id` | exact reviewed plan |
| `industry_map_revision_id` | exact reviewed plan |
| `candidate_owner_bindings` | explicit per-member form projected without inference |
| `candidate_pool_operation` | one explicit top-level operation defined in section 8 |
| `output_title` | explicit user-confirmed field; may be prefilled from exact reviewed title |
| `output_scope` | explicit user-confirmed field; may be prefilled from exact reviewed scope |
| `information_cutoff_date` | exact reviewed revision cutoff; not editable |
| `revision_note` | one explicit user-entered field |
| `owner_acceptance_plan_version` | exact server-returned accepted constant |
| `preview_fingerprint_sha256` | successful preview response, commit only |

Per-member field ownership is defined in section 7.

## 5. User-visible pages and exact routes

### 5.1 Reviewed result page

Existing route:

```text
GET /industry-analysis/sessions/{session_id}/revisions/{reviewed_session_revision_id}/result
```

For exact `workflow_state = reviewed_plan_ready`, the page adds one primary action:

```text
检查并接受研究成果
```

The path is generated server-side from the exact session ID, exact reviewed revision ID and the existing `as_of_cutoff` / `as_of_recorded_at_utc` boundaries.

### 5.2 Acceptance page

Chosen route:

```text
GET /industry-analysis/sessions/{session_id}/revisions/{reviewed_session_revision_id}/acceptance
```

The page is served only for an exact cutoff-visible `reviewed_plan_ready` revision belonging to the exact session.

The page contains:

- accepted scope summary;
- output title and output scope fields;
- complete selected-member list in frozen order;
- frozen identity confirmation for every member;
- Stage 1 and Typed Semantics operation controls;
- one top-level candidate-pool operation section;
- blocked/missing prerequisites;
- one revision note;
- one primary preview action;
- technical details under progressive disclosure.

### 5.3 Accepted-result page

Chosen route:

```text
GET /industry-analysis/sessions/{session_id}/revisions/{accepted_session_revision_id}/accepted-result
```

The route is keyed by the exact accepted session revision, not by latest-session lookup. The server reads the frozen output-link revision from the accepted session contract, verifies the graph through existing exact query services and returns one complete first-render response.

For `accepted_outputs_linked`, history continuation becomes:

```text
查看已接受成果
```

For `superseded`, `abandoned`, unknown or malformed state, continuation remains fail closed.

## 6. Local API contract

All APIs retain the existing prefix:

```text
/industry-analysis/api
```

Every write model is strict, rejects unknown fields, requires JSON and retains the existing 1 MiB body ceiling.

### 6.1 Acceptance view

```text
GET /industry-analysis/api/session-revisions/{reviewed_session_revision_id}/owner-acceptance-view
    ?session_id={session_id}
    &as_of_cutoff={date}
    &as_of_recorded_at_utc={utc}
```

Purpose:

- verify exact session/revision/state/boundaries;
- return reviewed-plan summary and complete selected members;
- return one frozen stock binding per member or a stable blocking state;
- return exact Stage 1 reuse/append options and exact assertion/claim choices;
- return exact compatible semantic-reuse options;
- return one top-level candidate-pool operation catalog;
- return exact constants/default sources required to construct the flat core payload;
- return a form contract, not a commit-ready fingerprint.

Response includes:

```text
session_id
reviewed_session_revision_id
reviewed_plan_fingerprint_sha256
expected_session_latest_revision_number
research_case
industry_map
information_cutoff_date
recorded_at_utc
map_mode
owner_acceptance_plan_version
output_metadata_defaults
members[]
candidate_pool_operation_contract
revision_note_constraints
primary_action
technical_details
```

Each member includes:

```text
sequence
reviewed_candidate_revision_id
ordinary_identity_label
frozen_stock_binding
frozen_stock_confirmation_required
stage1_reuse_options[]
stage1_append_options[]
stage1_create_contract
semantic_reuse_options[]
semantic_authoring_state
derived_handoff_rule
blocking_reasons[]
readiness_hints[]
technical_details
```

`frozen_stock_binding` is either:

```text
{
  "state": "available",
  "stock_basic_record_id": 123,
  "ordinary_label": "...",
  "stage1_create_source": "...",
  "stage1_create_stock_code": "..."
}
```

or:

```text
{
  "state": "missing_or_listed_instrument_only",
  "stock_basic_record_id": null,
  "ordinary_label": "...",
  "stage1_create_source": null,
  "stage1_create_stock_code": null
}
```

The create source/code values must come from exact persisted identity fields owned by the frozen stock record or an existing accepted deterministic bridge. If the current production model cannot supply stable exact values, create mode is unavailable and implementation must stop rather than infer them.

No option is generated by company-name, ticker, Provider label or free-text similarity.

### 6.2 Preview

```text
POST /industry-analysis/api/session-revisions/{reviewed_session_revision_id}/owner-acceptance/preview
    ?session_id={session_id}
    &as_of_cutoff={date}
    &as_of_recorded_at_utc={utc}
```

Body is the exact flat core payload:

```json
{
  "reviewed_session_revision_id": "...",
  "expected_session_latest_revision_number": 7,
  "reviewed_plan_fingerprint_sha256": "...",
  "research_case_id": "...",
  "map_mode": "reuse_exact_existing_map_revision",
  "industry_map_id": "...",
  "industry_map_revision_id": "...",
  "candidate_owner_bindings": [],
  "candidate_pool_operation": {},
  "output_title": "...",
  "output_scope": "...",
  "information_cutoff_date": "2026-07-25",
  "revision_note": "...",
  "owner_acceptance_plan_version": "aquantai.industry-thesis-owner-acceptance-plan.v1"
}
```

The adapter performs only:

1. strict HTTP/JSON validation;
2. route/body ID equality validation;
3. exact projection of already explicit form values;
4. call to `IndustryThesisOwnerAcceptanceService.preview`.

It does not add, infer, rename or rewrite owner fields.

Successful response preserves core fields:

```text
dry_run
commit_ready
idempotent_replay
owner_acceptance_plan_version
owner_acceptance_plan_fingerprint_sha256
preview_fingerprint_sha256
reviewed_session_revision_id
owner_transaction_id
research_case_id
industry_map_id
industry_map_revision_id
complete_universe_count
supported_handoff_count
candidate_pool_mode
operation_summaries[]
blocked_reasons[]
recorded_at_utc
```

The presentation layer may add:

```text
preview_summary
primary_action
```

No database write occurs.

Blocked preview preserves:

```text
dry_run = true
commit_ready = false
preview_fingerprint_sha256 = null
blocked_reasons[]
```

### 6.3 Commit

```text
POST /industry-analysis/api/session-revisions/{reviewed_session_revision_id}/owner-acceptance/commit
    ?session_id={session_id}
    &as_of_cutoff={date}
    &as_of_recorded_at_utc={utc}
```

Body is byte-equivalent in meaning to the preview payload plus the exact successful preview field:

```json
{
  "preview_fingerprint_sha256": "..."
}
```

The complete commit body still contains every preview field; the fragment above shows only the additional field.

Commit is rejected unless:

- route/body reviewed revision IDs match;
- the fingerprint equals the normalized owner-plan fingerprint;
- all expected-latest values remain valid;
- the exact owner graph remains valid.

Success preserves core fields, including:

```text
commit_ready
idempotent_replay
accepted_session_revision_id
output_link_id
output_link_revision_id
owner_transaction_id
accepted_candidate_pool_revision_id
complete_universe_count
supported_handoff_count
candidate_pool_mode
operation_summaries[]
recorded_at_utc
```

The adapter may add only validated same-origin navigation:

```text
accepted_result_path
history_path
```

The ordinary page navigates only to the server-returned expected route kind.

### 6.4 Accepted-result view

```text
GET /industry-analysis/api/session-revisions/{accepted_session_revision_id}/accepted-result-view
    ?session_id={session_id}
    &as_of_cutoff={date}
    &as_of_recorded_at_utc={utc}
```

One workbench query service composes existing exact output, complete-result and readiness reads inside one caller-owned read session.

Composition rules:

- accepted session belongs to the exact session;
- workflow state is `accepted_outputs_linked`;
- frozen output-link revision matches the exact output graph;
- all core reads succeed;
- any integrity mismatch fails the entire view closed;
- no partial accepted page is returned from a corrupted graph.

## 7. Per-member owner-binding contract

### 7.1 Frozen identity confirmation

The only eligible stock binding is the reviewed candidate’s frozen `proposed_stock_basic_record_id`.

Rules:

- available binding is displayed and explicitly confirmed;
- submitted Stage 1 stock ID is copied exactly from that frozen value;
- zero binding or listed-instrument-only state is blocked;
- multiple-choice identity UI does not exist;
- alternate identity correction happens before owner acceptance.

### 7.2 Stage 1 operation

The UI supports exact core modes:

```text
reuse_exact_beneficiary_revision
create_beneficiary_identity_and_revision
append_beneficiary_revision
```

#### Reuse

Payload:

```text
beneficiary_id
beneficiary_revision_id
stock_basic_record_id
```

All values come from one exact cutoff-visible compatible revision bound to the frozen stock record, exact Research Case, exact map and exact selected map revision.

#### Create

Payload:

```text
stock_basic_record_id
source
stock_code
legacy_beneficiary_kind
assessment_status
rationale_summary
map_assertion_revisions[]
claim_revision_ids[]
```

Authority:

- stock ID is frozen and non-editable;
- `source` and `stock_code` are exact values returned for the frozen stock record and explicitly confirmed, not free text;
- legacy kind and assessment status are explicit user choices from accepted enums;
- rationale is explicit user text;
- assertion and claim revisions are exact persisted cutoff-visible choices under the accepted case/map.

If exact create source/code cannot be produced, create is unavailable.

#### Append

Payload:

```text
beneficiary_id
expected_latest_revision_id
stock_basic_record_id
legacy_beneficiary_kind
assessment_status
rationale_summary
map_assertion_revisions[]
claim_revision_ids[]
```

`source` and `stock_code` are owned by the existing beneficiary identity and are not resubmitted because the accepted append core does not accept them.

The page never derives legacy kind from reviewed exposure.

### 7.3 Typed Semantics operation

The v1 ordinary-user page supports only:

```text
none
reuse_exact_semantic_revision
```

For `none`, semantic payload is exactly `null`.

For reuse, payload is exactly:

```text
profile_id
profile_revision_id
```

A reused profile must already be compatible with the exact beneficiary revision, selected map revision and as-of boundaries. The page does not author `append_complete_semantic_profile` in this slice.

When no compatible semantic revision exists, the user may explicitly choose `本次不绑定类型化语义记录`; readiness remains incomplete where applicable.

### 7.4 Readiness note

Every binding contains one explicit bounded `readiness_note`. A server-provided empty/default display may be offered, but the final normalized value is explicit in the form and payload.

### 7.5 Derived handoff state

Members do not have an editable handoff checkbox.

The page displays the rule:

```text
resulting Stage 1 supported -> included by global candidate-pool operation
resulting Stage 1 draft/disputed -> preserved in complete result, excluded from handoff
rejected -> acceptance blocked
```

The core remains authoritative.

## 8. Global candidate-pool operation

### 8.1 Top-level operation catalog

The acceptance view returns:

```text
candidate_pool_operation_contract
  create_contract
  append_options[]
  reuse_options[]
  zero_supported_contract
```

Compatible pool queries are bounded and exact. A pool option must share:

- exact Research Case;
- exact Industry Map identity;
- compatible selected map revision as required by the owner;
- information cutoff not later than the reviewed cutoff;
- recorded UTC not later than the requested boundary;
- complete, non-corrupt identity/revision graph.

No pool is selected by title similarity or latest-compatible fallback.

### 8.2 Create supported handoff

Mode:

```text
create_supported_handoff
```

Payload:

```text
mode
pool_key
title
scope
```

`pool_key` is a deterministic technical identity generated by the server:

```text
industry-thesis-acceptance-v1:{reviewed_session_revision_id}
```

It is displayed only under technical details and is not user-editable.

`title` and `scope` are explicit user-confirmed fields in the top-level handoff section. They may be prefilled from exact output metadata, but the final values are explicit.

Create is available when at least one resulting Stage 1 member may be supported and no existing exact pool must be reused/appended by product choice.

### 8.3 Append supported handoff

Mode:

```text
append_supported_handoff
```

Payload:

```text
mode
candidate_pool_id
expected_latest_revision_id
title
scope
```

The user chooses one exact compatible pool identity and confirms its exact latest revision returned by the acceptance view. Title and scope are explicit fields for the new pool revision.

No silent latest lookup occurs at commit. A moved latest revision produces conflict and requires re-preview.

### 8.4 Reuse exact supported handoff

Mode:

```text
reuse_exact_supported_handoff
```

Payload:

```text
mode
candidate_pool_id
candidate_pool_revision_id
```

Reuse is offered only when:

- every member expected to be supported uses `reuse_exact_beneficiary_revision`;
- one exact visible pool revision already contains exactly those supported beneficiary revision IDs;
- case/map/cutoff/chronology all match.

Reuse is not offered when any supported member would be created or appended, because the required new beneficiary revision does not yet exist in an accepted pool.

### 8.5 Zero-supported acceptance

Mode:

```text
none_no_supported_members
```

Payload contains only `mode`.

It is valid only when all resulting accepted Stage 1 revisions are draft/disputed and zero are supported.

If supported members exist, `none_no_supported_members` is invalid. If zero supported members exist, create/append/reuse is invalid. Preview enforces this fail closed.

### 8.6 Membership presentation

Preview displays core-derived membership only after owner validation:

- complete accepted member count;
- supported handoff count;
- exact candidate-pool mode;
- members included because their resulting Stage 1 revision is supported;
- draft/disputed members excluded with explicit reason;
- zero-supported notice.

No fake or empty pool is created.

## 9. Output metadata and constants

The acceptance view returns exact defaults and constraints.

### 9.1 Output title and scope

`output_title` and `output_scope` are explicit top-level user-confirmed fields.

They may be prefilled from exact reviewed thesis title, accepted case title or exact scope text only. Prefill is not acceptance: the user can edit and must confirm the final values before preview.

### 9.2 Constants

The server supplies and the body submits exact accepted constants:

```text
map_mode = reuse_exact_existing_map_revision
owner_acceptance_plan_version = aquantai.industry-thesis-owner-acceptance-plan.v1
```

The browser does not invent version values.

### 9.3 Revision note

There is one `revision_note` field in the flat body. It is not duplicated at adapter or wrapper level.

## 10. Preview and confirmation UX

### 10.1 Editing state

Primary action:

```text
生成变更预览
```

Preview remains unavailable when:

- any frozen identity is unconfirmed/missing;
- required Stage 1 fields are missing;
- top-level candidate-pool operation is incomplete;
- output title/scope or revision note is missing;
- client-side shape is known invalid.

Server validation remains authoritative.

### 10.2 Commit-ready preview state

The page freezes the exact submitted flat payload in browser memory and renders:

- owner revisions reused, created or appended;
- semantic reuse/absence;
- global candidate-pool operation;
- core-derived supported membership;
- complete/draft/disputed counts;
- zero-supported state;
- readiness gaps;
- data cutoff and recorded boundary;
- research-only/non-advisory notice.

Primary action:

```text
确认接受研究成果
```

Any edit invalidates the preview and removes `preview_fingerprint_sha256`. The user must generate a new preview.

Commit never runs on page load, preview, route navigation, browser refresh or automatic retry.

## 11. Conflict, replay and failure behavior

### 11.1 Stable HTTP mapping

- exact record not found/not visible: `404`;
- stale expected-latest, moved owner boundary, duplicate/conflicting acceptance: `409`;
- strict payload or blocked owner condition: `422`;
- database unavailable: `503`;
- invalid JSON/content type/body ceiling: existing `400/413/422` behavior.

### 11.2 Ordinary-language error projection

Every error returns:

```text
code
message
technical_message
recovery_action
preserve_form
```

Technical messages are progressive details only.

Examples:

- stale revision: `研究状态已经变化，请保留当前选择并重新读取后再次预览。`
- missing frozen identity: `这家公司在审核结果中没有冻结正式公司记录，当前不能接受成果。`
- incomplete pool operation: `请先确认 supported 后续研究池的创建、追加、复用或零成员方式。`
- graph corruption: `已接受成果的本地链接不完整，系统已停止展示，请先执行完整性检查。`
- conflicting replay: `这条研究已经用另一套接受方案完成，原结果不会被覆盖。`

### 11.3 Form preservation

On `409`, `422` or `503`:

- keep all explicit user fields in DOM/page memory;
- do not retry automatically;
- do not fetch latest and silently apply the form;
- remove commit-ready state when preview is stale;
- expose one primary recovery action.

`idempotent_replay = true` navigates to the original exact accepted result. Conflicting replay never overwrites it.

## 12. Accepted-result presentation

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
- candidate-pool operation/mode;
- draft/disputed count;
- semantic coverage state;
- Company Research readiness state;
- largest missing prerequisite;
- whether `idempotent_replay` is true;
- explicit `研究用途，不构成投资建议` notice.

No priority score, recommendation, target price, expected return or position instruction is added.

## 13. Exact history continuation

The sessions response extends the presentation-owned continuation mapping:

- `reviewed_plan_ready` -> exact reviewed result path;
- `accepted_outputs_linked` -> exact accepted-result path;
- `superseded` / `abandoned` / malformed -> unavailable.

The server obtains the accepted output reference from the exact accepted session revision. The browser does not parse canonical owner JSON to discover navigation IDs.

The first record is never skipped to find a more convenient continuable record.

## 14. Query and performance contract

### 14.1 HTTP budget

Acceptance first load:

```text
one page asset load
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

### 14.2 Database statement ceilings

The future workbench projection bulk-loads:

- frozen candidate identities;
- exact stock records;
- Stage 1 identities/revisions and latest revisions;
- exact assertion/claim options;
- semantic profiles/revisions;
- candidate-pool identities/revisions/memberships;
- exact output/result/readiness graph.

Required ceilings, independent of member count within the existing accepted-core bound:

```text
owner-acceptance-view <= 14 SQL statements
accepted-result-view <= 10 SQL statements
```

Preview and commit retain existing core locking/writing behavior; the UI adds no per-member session or HTTP call.

Tests assert ceilings on at least 3-member and 20-member fixtures and include candidate-pool option loading.

### 14.3 Complete-universe rendering

The first response contains every frozen accepted member. UI virtualization or collapsed details may improve rendering, but no server page may imply that a partial page is the complete universe.

## 15. Persistence, migration and rollback

Decision:

```text
migration = none
new table = none
new accepted field = none
new browser-local identity = none
new server-side draft = none
```

Temporary editing and preview payloads live only in page memory. Browser refresh discards unsaved preview state unless ordinary browser form restoration applies; no accepted meaning is persisted outside the existing owner transaction.

Rollback of the future implementation is deletion/reversion of adapter, pages and tests. Existing accepted owner data remains readable through local JSON commands/core query services.

If implementation discovers a required persistent field, new owner, migration, inability to expose the frozen identity, inability to supply exact create source/code or inability to construct an exact candidate-pool operation, it stops and returns to architecture review.

## 16. Security and locality

- same-origin local routes only;
- no external URL or redirect accepted from payloads;
- server validates UUIDs, route/body relationships, fingerprints and boundaries;
- no raw HTML from user or domain labels;
- text rendered through safe DOM APIs/templates;
- no credentials, Provider fields or network calls;
- no AI or remote transmission;
- no request replay after page closure;
- strict unknown-field rejection for all writes;
- technical errors do not leak connection strings or secrets.

## 17. Accessibility and copy

- Chinese-first labels;
- exact five-step workbench progression remains visible;
- acceptance remains part of `研究结果`, not a sixth workflow owner;
- one primary action per state;
- keyboard-reachable member, pool and disclosure controls;
- focus moves to preview or error summary after submission;
- `aria-current="step"` on `研究结果`;
- explicit text/icons, never color alone;
- technical details use `<details>` or equivalent progressive disclosure;
- frozen identity confirmation is explicit and screen-reader labelled;
- comfortable/compact density and appearance settings remain presentation-only.

## 18. Production-realistic offline golden path

Fixture prerequisites:

- one exact session and `reviewed_plan_ready` revision;
- one exact Research Case and existing Industry Map revision;
- three selected reviewed candidates in frozen order;
- each candidate has an exact frozen `proposed_stock_basic_record_id`;
- exact persisted owner records reachable through production queries.

Path:

1. User opens reviewed result and selects `检查并接受研究成果`.
2. Acceptance view returns all three members, each with one frozen identity, exact Stage 1/semantic options and the top-level pool catalog.
3. User explicitly confirms each frozen identity.
4. Company A selects `reuse_exact_beneficiary_revision`, reuses a supported Stage 1 revision and compatible semantic revision.
5. Company B selects reuse or append for a draft/disputed Stage 1 revision and remains excluded from handoff.
6. Company C selects create or append for a supported Stage 1 revision, using exact frozen stock ID, exact create source/code when creating, exact assertion/claim revisions and `semantic_operation = none`.
7. User selects `create_supported_handoff`.
8. Server supplies deterministic pool key `industry-thesis-acceptance-v1:{reviewed_session_revision_id}`; user confirms explicit pool title and scope.
9. User confirms output title, output scope and one revision note.
10. Browser submits the exact flat preview payload; no writes occur.
11. Core preview returns complete count `3`, supported count `2`, candidate-pool mode `create_supported_handoff`, operation summaries and a non-null preview fingerprint.
12. Preview displays A and C as derived supported handoff members and B as complete-result-only.
13. User explicitly commits the unchanged flat plan plus exact `preview_fingerprint_sha256`.
14. One atomic core commit returns exact accepted session/output/pool identifiers.
15. Accepted-result view returns all three in frozen order under both boundaries.
16. Reload and exact history reopening reproduce the same result.
17. No Company Research, Investment Candidate, recommendation, portfolio or trading state is created.

Zero-supported path:

- at least two valid draft/disputed members;
- each frozen identity is confirmed;
- candidate-pool mode is exactly `none_no_supported_members`;
- preview clearly shows zero supported handoff;
- explicit commit succeeds;
- accepted result shows all complete members and no fabricated pool.

## 19. Primary blocked paths

### 19.1 Frozen identity missing

One selected candidate has only a listed-instrument identity or lacks exact `proposed_stock_basic_record_id`.

Required result:

- exact member is blocked in acceptance view;
- no identity alternatives are returned;
- no commit-ready plan/fingerprint is produced;
- primary action returns to explicit pre-acceptance correction;
- zero owner/session/pool/output writes occur;
- reviewed plan remains exact and reopenable.

### 19.2 Create identity fields unavailable

Create is chosen but the exact frozen stock record cannot supply stable accepted `source` and `stock_code`.

Required result:

- create mode is blocked for that member;
- no free-text source/code fallback appears;
- reuse/append may remain available only if exact compatible owner records exist;
- otherwise no preview-ready plan is returned.

### 19.3 Candidate-pool operation incomplete or inconsistent

Examples:

- supported members exist but no complete create/append/reuse mode is selected;
- append expected-latest moved;
- reuse membership does not exactly equal resulting supported revisions;
- zero supported members use a non-none mode;
- supported members use `none_no_supported_members`.

Required result:

- top-level handoff section identifies the exact conflict;
- member form values are preserved;
- preview returns no commit-ready fingerprint;
- zero writes occur.

No name/ticker/free-text/Provider/AI inference fills any blocked gap.

## 20. Future implementation file families

A separately authorized Strict implementation Issue may permit bounded changes to:

```text
backend/api/industry_analysis.py
backend/api/industry_analysis_review.py
backend/api/industry_analysis_acceptance.py
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

## 21. Future validation requirements

Minimum executable coverage:

- exact continuation mapping for `reviewed_plan_ready` and `accepted_outputs_linked`;
- fail-closed continuation for terminal/malformed states;
- route values from exact response-owned IDs and boundaries;
- one frozen stock binding only;
- explicit frozen identity confirmation;
- missing/listed-only identity blocked with no alternatives;
- exact flat preview DTO and exact flat commit DTO;
- route/body reviewed-revision mismatch rejection;
- unknown-field rejection;
- no duplicated expected-latest/revision-note authority;
- exact `preview_fingerprint_sha256` semantics;
- every mandatory top-level field source;
- Stage 1 reuse/create/append exact payloads;
- exact create `source`/`stock_code` ownership and unavailable-source failure;
- no automatic exposure-to-legacy/typed mapping;
- semantic none/reuse only;
- top-level candidate-pool create mode and deterministic pool key;
- append exact option and moved-latest conflict;
- reuse exact membership and unsupported new-revision case;
- zero-supported none mode;
- member handoff derived and non-editable;
- three-company golden path;
- preview zero writes and fingerprint stability;
- explicit commit and one exact atomic result;
- `idempotent_replay` navigation;
- conflicting replay preservation;
- stale `409` form preservation and no retry;
- exact accepted-result graph and readiness;
- cutoff and recorded-UTC negative visibility;
- graph corruption ordinary fail-closed state;
- one primary action;
- accessibility and safe text rendering;
- HTTP/query ceilings including pool catalog and no per-row requests;
- no schema/migration/new persistence;
- import/startup/page/test/demo network denial;
- no Provider, credential or AI path;
- no recommendation, target price, expected return, portfolio or trading semantics;
- complete repository regression and every configured offline demo on the exact final HEAD.

## 22. Locked exclusions

No Today Market source activation, THS/iFinD/Tushare/AKShare/CNINFO access, credentials, external network, automatic refresh, scheduler, background worker, retry loop, notification, AI call, new Industry Map facts, draft-graph promotion, fuzzy identity bridge, identity replacement during acceptance, automatic classification mapping, automatic semantic-profile authoring, automatic Company Research, automatic component scoring, automatic Investment Candidate snapshot, recommendation, target price, expected return, position sizing, research holdings, portfolio, broker, order, trading, release, tag or version change.

## 23. Stop conditions

Stop implementation authorization if:

- the frozen stock identity cannot be exposed exactly;
- owner acceptance would need to replace the frozen identity;
- exact create source/code cannot be produced without free-text/provider/name inference;
- the flat HTTP DTO cannot map one-to-one to the accepted core;
- a valid top-level candidate-pool operation cannot reach the golden path;
- ordinary completion depends on hidden inference;
- raw IDs must become mandatory primary inputs;
- a second workflow owner or server-side draft is required;
- the adapter must duplicate owner validation or write ORM rows directly;
- a migration or accepted-field change is required;
- exact reopening requires latest fallback;
- complete result and supported handoff cannot remain separate;
- typed-semantic authoring must be embedded to make the slice useful;
- scope expands into general redesign, Follow/Track, Research Portfolio, announcement acquisition or Today Market source work;
- any Provider, network, AI, recommendation, portfolio or trading behavior appears.

## 24. Fixed-head architecture gate

Before merge consideration:

1. exact branch base `a6da9bc8483606a67b7ca5f1329e46232d5b47be`;
2. only the Issue #238 task snapshot and this document changed;
3. repository checks succeed on one new exact immutable HEAD;
4. fresh process-independent fixed-head architecture review re-reads Review `4779124457` and verifies every blocker is closed;
5. zero unresolved review threads;
6. exact approval phrase:

```text
AUTHORIZED INDUSTRY THESIS ORDINARY-USER COMPLETION PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

7. separate explicit project-owner merge authorization.

Any new commit invalidates prior exact-head CI and review evidence.

Architecture approval does not authorize production implementation, Issue closure, release or any later roadmap phase.