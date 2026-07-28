# Industry Research Ordinary-User End-to-End Completion v1 — Architecture Preflight

## 1. Status and authority

This document is the Strict Architecture Preflight for Issue #266.

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
default_branch = main
exact_base = 8a085f48cf99f389c810496427d2aa0292c6b6c5
parent_roadmap = #137
architecture_issue = #266
risk_tier = Strict Architecture Preflight
workflow = .codex/WORKFLOW.md
```

Project-owner instruction on 2026-07-28:

```text
根据项目设计，进行下一步开发
```

Issue #225 is closed with the accepted outcome `blocked_quota_contract`.
This architecture is intentionally local-first and independent of live market
data, credentials or Provider work.

PR #241 remains closed, unmerged and permanently read-only at
`3116a67ec472131eea3bf3d1bd9daee884c69ee9`. Issue #240 is superseded.
Neither may be reopened, rebased, force-pushed, merged or copied wholesale.

This preflight changes no executable contract. It defines the exact bounded
architecture that a later separately authorized implementation may follow.

## 2. Product problem

The repository already contains the important domain capabilities:

- ordinary-language Industry Thesis session creation and revision;
- exact local history and continuation links;
- deterministic candidate-universe construction;
- explicit candidate review;
- exact Owner Context v2;
- reviewed-plan fingerprinting;
- owner-acceptance preview and explicit commit;
- immutable accepted output links;
- complete accepted beneficiary projection;
- exact candidate-overlay assembly;
- exact history reopening.

The remaining product gap is continuity.

An ordinary investor can encounter multiple separate pages and technical states
without a single guided explanation of:

- what the system understood;
- what must be confirmed next;
- which exact context is authoritative;
- whether the user is previewing or committing;
- what is immutable accepted history;
- what is a separately selected current candidate overlay;
- how to recover from stale or incomplete state;
- how to reopen the exact result later.

The missing capability is not a new research owner, score, model or database.
It is a deterministic orchestration and presentation contract over existing
owners.

## 3. Accepted authoritative owners

### 3.1 Industry Thesis session owner

`IndustryThesisCommandService` and `IndustryThesisQueryService` own session
identity, revisions, workflow state, scope content, dual-as-of chronology and
optimistic concurrency.

The end-to-end layer may call existing dry-run or commit commands. It may not
persist a second topic, scope or workflow state.

### 3.2 Candidate-universe owner

The existing candidate-universe services own exact candidate identities,
revisions, complete candidate rows and deterministic proposal state.

The end-to-end layer may navigate to the exact review view. It may not generate
a hidden second candidate list in the browser.

### 3.3 Candidate-review and reviewed-plan owner

`IndustryThesisProposalReviewService`,
`IndustryThesisReviewedPlanQueryService` and the review workbench own:

```text
exact session revision
expected latest session revision number
acceptance plan version
exact candidate revision set
explicit per-candidate decisions
frozen Owner Context
reviewed plan fingerprint
reviewed chronology
```

The end-to-end layer may derive a user-facing stage from these records. It may
not infer Case/Map authority from reachable stocks or maximum coverage.

### 3.4 Owner Context

The accepted Owner Context v2 contract freezes:

```text
research_case_id
map_mode
industry_map_id
industry_map_revision_id
```

through one explicit exact `industry_map_revision_id` selected at review time and
server-resolved to one Case and one Map.

The exact reviewed Owner Context is the only acceptance authority.

### 3.5 Owner-acceptance owner

`IndustryThesisOwnerAcceptanceWorkbenchQueryService` owns the authoritative
acceptance view.

`IndustryThesisOwnerAcceptanceService` owns preview and commit semantics,
including owner bindings, candidate-pool operations, optimistic concurrency,
transaction identity and immutable accepted output creation.

The orchestration layer does not become a transaction owner.

### 3.6 Accepted-output owner

`IndustryThesisAcceptedOutputQueryService` owns exact accepted output,
complete accepted member projection and readiness.

One exact accepted graph is historical truth. It may not be rewritten by a
current candidate overlay.

### 3.7 Industry Research result assembly

`IndustryResearchResultQueryService` owns read-only composition of:

```text
one exact accepted output-link revision
zero or one explicitly selected exact Investment Candidate snapshot revision
```

The accepted complete universe remains the outer collection.

### 3.8 Investment Candidate owner

The existing Investment Candidate owner owns snapshot status, priority, reasons,
component revisions, verification and falsification state.

The end-to-end layer may list exact eligible snapshots and display one explicit
selection. It may not recompute or reinterpret candidate state.

## 4. Core architecture decision

The end-to-end capability is a stateless, derived orchestration surface.

```text
new persisted owner = none
new orchestration table = none
new workflow-state column = none
schema change = none
migration = none
```

It has exactly three responsibilities:

1. derive one ordinary-user stage from exact owner records;
2. provide safe navigation and explicit primary actions;
3. preserve exact selectors, fingerprints and dual-as-of boundaries across
   existing query/preview/commit routes.

Every write remains delegated to an accepted owner.

## 5. Contract versions

```text
presentation_contract_version =
  aquantai.industry-research-ordinary-user-e2e.v1

acceptance_view_snapshot_contract_version =
  aquantai.industry-thesis-owner-acceptance-view-snapshot.v1

history_route_contract_version =
  aquantai.industry-research-history-route.v1
```

These are presentation and request-validation contracts. They are not database
record versions.

## 6. End-to-end state machine

### 6.1 Derived state rule

The server derives `e2e_stage` from exact records under supplied boundaries.
The browser may render the stage but may not decide it from local assumptions.

### 6.2 Stage table

| Stage | Authoritative input | Primary action | Write class | Next stage |
|---|---|---|---|---|
| `topic_entry` | no selected session | 输入研究主题 | none | `scope_draft` |
| `scope_draft` | exact draft session revision | 预览研究范围 | preview | `scope_confirmed` or remain |
| `scope_confirmed` | exact revision eligible for candidate build | 生成候选公司 | explicit command | `candidate_review` |
| `candidate_review` | exact review view and frozen candidate set | 提交人工审核 | preview/commit | `reviewed_plan_ready` |
| `reviewed_plan_ready` | exact v2 reviewed plan with Owner Context | 打开接受预览 | read | `acceptance_preview_ready` |
| `acceptance_preview_ready` | exact authoritative acceptance view | 预览接受结果 | preview | `acceptance_commit_ready` |
| `acceptance_commit_ready` | same snapshot plus preview fingerprint | 确认接受研究成果 | commit | `accepted_result` |
| `accepted_result` | exact accepted output graph | 查看完整研究结果 | read | same |
| `history_reopen` | exact historical selectors | 重开该历史结果 | read | exact derived stage |
| `blocked_recovery` | deterministic mismatch/incomplete state | 按明确动作恢复 | read or explicit action | exact recovered stage |

### 6.3 Stage precedence

If several records are reachable, precedence is not “latest wins”.

The server starts from the exact route selectors and verifies the exact graph:

```text
route session/revision
  -> exact visible session revision
  -> exact reviewed plan when present
  -> exact accepted graph when present
```

A completed accepted graph takes precedence only when it is linked from the
exact selected session revision or exact historical route. It does not make a
different session or revision authoritative.

### 6.4 No stage persistence

`e2e_stage` and `primary_action` are response fields only.

```text
writes_performed = false
stage_persisted = false
```

## 7. Exact selector propagation

### 7.1 Scope and review selectors

```text
session_id
session_revision_id
expected_session_latest_revision_number
as_of_cutoff
as_of_recorded_at_utc
```

### 7.2 Reviewed-plan selectors

```text
reviewed_session_revision_id
acceptance_plan_version
reviewed_plan_fingerprint_sha256
owner_context.industry_map_revision_id
```

The server resolves and returns:

```text
research_case_id
map_mode
industry_map_id
industry_map_revision_id
```

### 7.3 Acceptance selectors

```text
session_id
reviewed_session_revision_id
as_of_cutoff
as_of_recorded_at_utc
expected_session_latest_revision_number
reviewed_plan_fingerprint_sha256
research_case_id
map_mode
industry_map_id
industry_map_revision_id
owner_acceptance_plan_version
acceptance_view_snapshot_content_sha256
```

### 7.4 Accepted-result selectors

```text
session_id
accepted_session_revision_id
as_of_cutoff
as_of_recorded_at_utc
optional investment_candidate_snapshot_revision_id
```

The server resolves one exact `output_link_revision_id` from the accepted graph.
A client must not construct or infer an output-link revision.

## 8. Route and action inventory

### 8.1 Existing page routes retained

```text
GET /industry-analysis
GET /industry-analysis/new
GET /industry-analysis/sessions/{session_id}/revisions/{session_revision_id}/review
GET /industry-analysis/sessions/{session_id}/revisions/{reviewed_session_revision_id}/result
GET /industry-analysis/sessions/{session_id}/revisions/{reviewed_session_revision_id}/acceptance
GET /industry-analysis/sessions/{session_id}/revisions/{accepted_session_revision_id}/accepted-result
```

The architecture may unify visual continuity and navigation without introducing
a second accepted-result owner.

### 8.2 Existing read APIs retained

```text
GET /industry-analysis/api/bootstrap
GET /industry-analysis/api/sessions
GET /industry-analysis/api/session-revisions/{session_revision_id}
GET /industry-analysis/api/session-revisions/{session_revision_id}/review-view
GET /industry-analysis/api/session-revisions/{session_revision_id}/owner-context-options
GET /industry-analysis/api/session-revisions/{reviewed_session_revision_id}/owner-acceptance-view
GET /industry-analysis/api/output-link-revisions/{output_link_revision_id}/assembled-result
```

### 8.3 Existing explicit write APIs retained

```text
POST /industry-analysis/api/sessions?dry_run=true|false
POST /industry-analysis/api/sessions/{session_id}/revisions?dry_run=true|false
POST /industry-analysis/api/session-revisions/{session_revision_id}/reviews?dry_run=true|false
POST /industry-analysis/api/session-revisions/{reviewed_session_revision_id}/owner-acceptance/preview
POST /industry-analysis/api/session-revisions/{reviewed_session_revision_id}/owner-acceptance/commit
```

### 8.4 New bounded read projection candidate

A future implementation may add one read-only orchestration projection:

```text
GET /industry-analysis/api/e2e/stage
```

Required exact query fields:

```text
session_id optional only for topic-entry
session_revision_id optional only for topic-entry
accepted_session_revision_id optional
as_of_cutoff
as_of_recorded_at_utc
investment_candidate_snapshot_revision_id optional
```

Response:

```json
{
  "contract_version": "aquantai.industry-research-ordinary-user-e2e.v1",
  "e2e_stage": "candidate_review",
  "stage_source": {
    "session_id": "<uuid>",
    "session_revision_id": "<uuid>",
    "workflow_state": "awaiting_review"
  },
  "primary_action": {
    "kind": "open_exact_review",
    "label": "继续人工审核",
    "path": "/industry-analysis/..."
  },
  "secondary_actions": [],
  "recovery": null,
  "writes_performed": false
}
```

This projection does not replace any domain query. It only validates exact
continuity and supplies ordinary-language navigation.

### 8.5 No catch-all write endpoint

Prohibited:

```text
POST /industry-analysis/api/e2e/run
POST /industry-analysis/api/e2e/advance
POST /industry-analysis/api/e2e/complete
```

There is no endpoint that performs several owner writes in one opaque request.
Each owner write remains explicit and separately previewed where required.

## 9. Acceptance-view snapshot contract

### 9.1 Problem

The current adapter compares important top-level fields and validates member
bindings against a freshly loaded view. The complete end-to-end contract must
also protect the authoritative view body from replacement between page load,
preview and commit.

### 9.2 Canonical snapshot content

The server builds canonical normalized content in stable key and list order:

```text
snapshot_contract_version
route:
  session_id
  reviewed_session_revision_id
  as_of_cutoff
  as_of_recorded_at_utc
reviewed_plan:
  expected_session_latest_revision_number
  reviewed_plan_fingerprint_sha256
  owner_acceptance_plan_version
owner_context:
  research_case_id
  map_mode
  industry_map_id
  industry_map_revision_id
members:
  ordered reviewed_candidate_revision_id
  exact decision/exposure/readiness facts
  exact Stage 1 reuse/append/create options
  exact permitted semantic reuse options
candidate_pool_operation_contract:
  exact append options
  exact reuse options
  exact create/no-supported contract
output_metadata_defaults:
  output_title
  output_scope
```

The canonical serializer must be deterministic and shared by GET, preview and
commit validation.

### 9.3 Snapshot fingerprint

```text
acceptance_view_snapshot_content_sha256 =
  sha256(canonical_json(snapshot_content))
```

The fingerprint contains no secret and no Provider market values. It is not an
authorization token. It proves exact content equality.

### 9.4 Preview validation

Preview must:

1. rebuild the authoritative view under exact route and boundaries;
2. compare every submitted authority field;
3. compare the submitted snapshot-content fingerprint;
4. validate the complete exact binding set and each selected operation;
5. generate a preview fingerprint from canonical authoritative snapshot plus
   normalized requested operations and metadata.

No owner write occurs.

### 9.5 Commit validation

Commit must repeat all preview validation against a freshly rebuilt view and
require:

```text
preview_fingerprint_sha256
acceptance_view_snapshot_content_sha256
```

The server does not trust cached browser view content.

Commit fails before writes when:

- route and body differ;
- Case/Map/Map Revision differ;
- map mode differs;
- cutoff or recorded boundary differs;
- expected latest differs;
- reviewed fingerprint differs;
- plan version differs;
- snapshot body fingerprint differs;
- member set/order/options differ;
- submitted operation leaves the exact reviewed contract.

### 9.6 Preview expiry

Preview has no timer-based authority and no persistent row.

A preview remains usable only while all exact inputs still rebuild to the same
fingerprints. Any owner-state change invalidates it naturally.

## 10. Owner-write boundaries

### 10.1 Session scope

Scope preview and commit call only the session owner.

### 10.2 Candidate review

Candidate review calls only the review owner. It may create one reviewed plan
through the existing command semantics.

### 10.3 Owner acceptance

Owner acceptance calls only the accepted owner transaction. It may write the
existing exact owner graphs already authorized by that owner.

### 10.4 Result and overlay

Accepted-result and candidate-overlay reads perform zero writes.

Selecting an overlay for display changes only the URL/presentation state.

## 11. Complete beneficiary and candidate-overlay composition

### 11.1 Outer collection

```text
accepted_result.members
```

is the immutable outer collection.

Every exact accepted beneficiary remains visible despite:

- unsupported handoff;
- disputed or conditional state;
- missing typed semantics;
- missing Company Research;
- no candidate snapshot;
- pricing-demanding status;
- evidence-insufficient status;
- not-current-candidate status.

### 11.2 Overlay eligibility

An overlay is eligible only when:

```text
accepted_output.accepted_candidate_pool_revision_id is not null
snapshot.candidate_pool_revision_id
  == accepted_output.accepted_candidate_pool_revision_id
snapshot is visible at as_of_cutoff
snapshot is visible at as_of_recorded_at_utc
purpose_code is supported
rule_version is displayable without reinterpretation
```

### 11.3 Explicit selection

No eligible option is selected automatically, even when only one exists.

Options use deterministic ordering for display only:

```text
recorded_at_utc DESC
information_cutoff_date DESC
revision_no DESC
snapshot_revision_id ASC
```

### 11.4 Join and rendering

Join key:

```text
beneficiary_revision_id
```

Candidate fields are nested under `candidate_overlay`, not flattened into the
accepted member.

The accepted ordering remains canonical. A separate candidate highlight section
may use the snapshot priority for convenience, but it must link back to the full
accepted list and state that it is a separate selected snapshot.

### 11.5 Mismatch behavior

If a supplied snapshot belongs to another exact pool or context:

```text
accepted_result = readable
candidate_overlay.state = blocked
candidate_overlay.reason = exact_pool_mismatch|exact_context_mismatch
fallback = none
writes_performed = false
```

## 12. Ordinary-user information architecture

### 12.1 Persistent shell

The existing five-module shell remains. The Industry Research journey lives
inside `产业研究`.

The top area shows only:

- current stage;
- exact cutoff date;
- save/preview/commit state;
- history entry;
- technical details disclosure.

### 12.2 Step indicator

```text
1 输入主题
2 确认范围
3 审核候选
4 预览接受
5 完成结果
```

The step indicator is derived. It is not a progress owner.

### 12.3 Primary action rule

Each screen has one dominant primary action.

Examples:

- `预览研究范围`;
- `确认范围并继续`;
- `提交人工审核`;
- `预览接受结果`;
- `确认接受研究成果`;
- `查看完整研究结果`.

Dangerous or write-capable actions explicitly use confirmation wording.

### 12.4 Conclusion-first accepted result

The completed result shows at most eight first-screen cards from accepted facts:

1. 研究范围;
2. 行业驱动类型 when it exists in the accepted session;
3. 完整受益公司数量;
4. supported 后续研究数量;
5. 类型化语义覆盖;
6. Company Research 准备度;
7. selected candidate-status distribution only when selected;
8. 最大明确缺口.

The UI may not invent an industry stage, value-pool direction or earnings
transmission when no accepted owner record supplies it.

### 12.5 Provenance labels

Visible labels distinguish:

```text
已接受事实
确定性计算
研究判断
AI 草稿
缺失/待验证
```

AI drafts remain absent from accepted state unless separately reviewed by an
existing accepted owner.

## 13. Navigation, back, cancel, retry and resume

### 13.1 Back navigation

Back navigation returns to the exact prior route selectors. It does not load
latest state.

If the prior owner revision is no longer commit-eligible, the page is readable
and shows a stale recovery action.

### 13.2 Cancel

Cancel never deletes accepted history.

Before commit, cancel returns to exact history or review. Unsaved browser form
state may be discarded only after an explicit warning.

### 13.3 Retry

Retry is explicit.

- query retry repeats the same selectors;
- preview retry rebuilds the authoritative snapshot;
- commit retry first queries whether the exact owner transaction already
  completed.

### 13.4 Resume

History continuation is derived from exact workflow state and exact revision
metadata.

Unsupported, superseded or abandoned states show `当前记录不可继续` with an
explicit reason. They do not route to a compatible-looking latest record.

## 14. Exact history contract

### 14.1 History list

The history list may display ordinary labels and exact continuation actions.

It must retain:

```text
session_id
visible exact revision ID
visible exact revision number
workflow state
information cutoff
recorded UTC
```

### 14.2 Accepted-result route

```text
/industry-analysis/sessions/{session_id}/revisions/
{accepted_session_revision_id}/accepted-result
?as_of_cutoff=YYYY-MM-DD
&as_of_recorded_at_utc=...Z
&investment_candidate_snapshot_revision_id=<optional uuid>
```

### 14.3 Reopen rules

Reopen must reproduce:

- exact accepted output graph;
- exact complete beneficiary order;
- exact readiness state visible at the recorded boundary;
- the exact explicitly selected overlay when present.

Reopen must not:

- select a newer candidate snapshot;
- fetch current latest Company Research;
- use a newer Map Revision;
- upgrade a legacy plan;
- mutate accepted links;
- recompute candidate state.

## 15. Legacy and incomplete-state recovery

### 15.1 Legacy reviewed plan

A reviewed plan without exact Owner Context returns:

```text
code = industry_research_e2e_legacy_owner_context_missing
message = 这条历史审核尚未冻结明确的研究归属，不能直接接受。
primary_action = 重新明确研究归属并生成新的审核版本
```

No silent backfill or migration.

### 15.2 Multiple contexts

```text
code = industry_research_e2e_context_not_explicit
message = 当前存在多个可能的研究归属，请明确选择一个产业地图版本。
```

No maximum-coverage or first-row inference.

### 15.3 Incomplete accepted graph

```text
code = industry_research_e2e_output_graph_incomplete
message = 本地研究成果链接不完整，已停止继续操作。
primary_action = 运行本地完整性检查
```

### 15.4 Missing downstream links

Missing exact Company Research, semantics, valuation or candidate components are
rendered as missing. The UI does not query a current latest substitute.

## 16. Error taxonomy and Chinese-first recovery

| Code | User message | Recovery | Preserve form |
|---|---|---|---|
| `industry_research_e2e_route_mismatch` | 当前页面与提交内容不属于同一条研究记录。 | 从研究历史重新打开精确记录。 | yes |
| `industry_research_e2e_context_not_explicit` | 当前存在多个可能的研究归属。 | 明确选择一个产业地图版本。 | yes |
| `industry_research_e2e_snapshot_stale` | 研究内容已变化，原预览不再有效。 | 保留填写内容并重新预览。 | yes |
| `industry_research_e2e_snapshot_body_mismatch` | 接受页面内容已变化，不能使用旧预览提交。 | 重新读取接受页面。 | yes |
| `industry_research_e2e_plan_version_mismatch` | 这条审核使用了不支持的计划版本。 | 返回审核并生成当前版本。 | yes |
| `industry_research_e2e_candidate_pool_mismatch` | 所选候选快照不属于这次接受的公司池。 | 移除快照或选择有效快照。 | n/a |
| `industry_research_e2e_candidate_context_mismatch` | 所选候选快照属于另一研究范围。 | 移除快照。 | n/a |
| `industry_research_e2e_output_graph_incomplete` | 本地研究成果链接不完整。 | 停止并执行完整性检查。 | n/a |
| `industry_research_e2e_commit_already_completed` | 研究成果已经完成接受。 | 打开已完成结果。 | n/a |
| `industry_research_e2e_database_unavailable` | 本地研究数据库不可用。 | 检查数据库后手动重试。 | yes |

Technical details contain IDs and lower-level owner codes.

## 17. Browser concurrency and replay

### 17.1 Two tabs

Two tabs may preview the same exact state. Only a commit whose expected latest,
snapshot content and preview fingerprint still match may write.

The later stale commit fails closed.

### 17.2 Double click

The UI disables the commit button after the first click, but correctness does
not depend on the browser.

The owner transaction and exact output graph provide server-side duplicate
protection.

### 17.3 Refresh after commit request

The browser queries the exact accepted graph before showing another commit
action.

If completed, it routes to the accepted result. If not completed, it rebuilds
the authoritative acceptance view and requires a new preview.

## 18. Accessibility and presentation requirements

- Chinese-first labels;
- keyboard-operable step navigation and primary actions;
- visible focus;
- semantic headings and landmarks;
- no color-only state;
- status text and icons together;
- comfortable and compact density;
- font-size preference respected;
- light/dark/system appearance respected;
- red-up/green-down preference irrelevant to research status;
- long company lists use expandable rows or drawers, not a mandatory very-wide
  table;
- technical details use copyable text but never expose secrets;
- error summaries announce through an accessible live region;
- preview and commit buttons have distinct wording and confirmation.

## 19. Zero-network fixture strategy

The architecture requires one production-realistic synthetic/local fixture.

Fixture facts:

```text
topic = 存储涨价受益公司
one exact Research Case
one exact Industry Map Revision
three reviewed candidate revisions
three accepted beneficiary revisions
two supported candidate-pool members
one unsupported accepted member
two exact eligible candidate snapshots
typed semantics and Company Research for two members
one explicit missing-readiness member
```

Repository tests remain zero-network and contain no Provider-valued data.

## 20. Deterministic test matrix

### 20.1 Golden tests

- topic to exact draft session;
- exact scope preview and commit;
- exact candidate review;
- exact Owner Context freeze;
- acceptance-view snapshot fingerprint stability;
- preview then commit on identical authoritative content;
- complete accepted universe of three members;
- zero candidate snapshot selected;
- explicit selection of either eligible exact snapshot;
- exact history reopen;
- writes = zero on all GET/result routes.

### 20.2 Context failure tests

- multiple contexts with no explicit selection;
- Case substitution;
- Map substitution;
- Map Revision substitution;
- same-stock but different context;
- body-supplied context not in reviewed plan.

### 20.3 Snapshot failure tests

- map mode drift;
- cutoff drift;
- recorded boundary drift;
- expected latest drift;
- reviewed fingerprint drift;
- plan-version drift;
- ordered member replacement;
- candidate-pool option replacement;
- output-default replacement;
- preview fingerprint from another snapshot.

### 20.4 Overlay failure tests

- another candidate-pool revision;
- another Research Case;
- another Map Revision;
- invisible future snapshot;
- unsupported purpose;
- no exact selected snapshot;
- newer snapshot exists during history reopen.

### 20.5 Browser and replay tests

- back after preview;
- refresh after preview;
- double commit;
- refresh during commit;
- completed transaction replay;
- stale second-tab commit.

### 20.6 Legacy and missing tests

- legacy v1 plan;
- zero supported members;
- missing typed semantics;
- missing Company Research;
- incomplete accepted output link;
- unavailable local database.

## 21. Future implementation boundary

A later Strict Implementation Issue may implement the smallest golden path by
modifying an exact reviewed subset of existing Industry Analysis adapters,
presentation files, bounded orchestration query helpers and tests.

No implementation may start merely because this architecture PR exists or is
merged. Separate explicit project-owner authorization is required.

### Candidate core additions

```text
industry_alpha/industry_research_e2e_rules.py
industry_alpha/industry_research_e2e_query.py
```

These modules may derive stages and normalize the acceptance-view snapshot. They
must not own persistence.

### Candidate existing adapters

```text
backend/api/industry_analysis.py
backend/api/industry_analysis_review.py
backend/api/industry_analysis_acceptance.py
backend/api/industry_research_result.py
```

### Candidate presentation files

```text
industry_analysis/static/workbench.*
industry_analysis/static/review_result.*
industry_analysis/static/owner_acceptance.*
industry_analysis/static/accepted_result.*
bounded shared CSS/helpers
```

### Candidate validation

```text
bounded existing/new tests
one offline demo
.github/workflows/local-tests.yml only to add the demo
```

The implementation Issue must reduce this to an exact file inventory and must
not authorize schema, migration, Provider, network, AI, recommendation,
portfolio or trading scope.

## 22. Golden path acceptance criteria

The future implementation is successful only when one user can:

1. enter `存储涨价受益公司`;
2. confirm the understood scope;
3. explicitly review three candidates under one exact Owner Context;
4. preview the exact owner-acceptance transaction;
5. commit once;
6. see all three accepted beneficiaries;
7. explicitly select one exact candidate snapshot without changing accepted
   history;
8. reopen the exact result later;
9. receive the same result under the same selectors;
10. complete the flow with zero network and zero AI.

## 23. Decisive failure acceptance criteria

The implementation must prove that:

- context inference is impossible;
- request-body replacement is rejected;
- stale preview is rejected;
- duplicate commit cannot create duplicate output;
- invalid overlay cannot hide accepted result;
- history reopen cannot drift to current latest;
- all failures preserve accepted state.

## 24. Scope exclusions

This architecture does not authorize or design:

- live THS, Tushare, AKShare or another Provider;
- credentials, HTTP transport, raw capture or Provider persistence;
- schema or migration changes;
- announcement/news acquisition;
- automatic PDF acquisition or OCR;
- automatic evidence acceptance;
- automatic research acceptance;
- new scores, recommendation, target prices or return promises;
- holdings, position sizing, portfolio optimization or trading;
- scheduler, daemon, polling, notification or push;
- release, tag or version change.

## 25. Required architecture delivery gate

A future PR must:

1. start from exact base
   `8a085f48cf99f389c810496427d2aa0292c6b6c5`;
2. change exactly the Issue-authorized architecture Markdown files;
3. remain `behind = 0`;
4. pass applicable CI on one immutable HEAD;
5. receive an independent review containing exactly:

```text
AUTHORIZED INDUSTRY RESEARCH ORDINARY-USER END-TO-END V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

6. have zero unresolved review threads;
7. receive separate explicit project-owner merge authorization.

Any new commit invalidates prior fixed-HEAD CI and review evidence.

## 26. Post-merge boundary

Merging this architecture would authorize only the architecture baseline.

It would not authorize:

- implementation branch or PR;
- architecture Issue closure;
- PR #241 modification;
- schema or migration changes;
- Provider or credential work;
- recommendation, portfolio or trading work;
- release, tag or version work.

A separately authorized Strict Implementation Issue is required.
