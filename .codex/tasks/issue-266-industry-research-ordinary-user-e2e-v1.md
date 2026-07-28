# Issue #266 Task Snapshot — Industry Research Ordinary-User End-to-End Completion v1

## Authority

Project-owner instruction on 2026-07-28:

```text
根据项目设计，进行下一步开发
```

Authoritative context:

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
default_branch = main
exact_base = 8a085f48cf99f389c810496427d2aa0292c6b6c5
architecture_issue = #266
parent_roadmap = #137
ths_contract_issue = #225 / closed / completed / blocked_quota_contract
branch = arch/industry-research-ordinary-user-e2e-v1
risk_tier = Strict Architecture Preflight
workflow = .codex/WORKFLOW.md
```

Accepted foundations that this architecture must reuse:

- Personal Research Workbench and exact history reopening: #215/#216 and #217/#218;
- Owner Context v2 replacement: #242/#243 and #245/merged PR #246;
- Industry Research Result Assembly and Exact Candidate Overlay v1: #247/merged PR #248 and #249/merged PR #250;
- Investment Candidate Intelligence: #179/#180 and #181/#182;
- current accepted Industry Thesis review, owner-acceptance and accepted-output owners on `main`.

PR #241 remains closed, unmerged, permanently frozen and read-only at
`3116a67ec472131eea3bf3d1bd9daee884c69ee9`. Issue #240 is superseded.
Neither is an authority for this slice.

## Authorized architecture files

Initial Draft architecture PR may change only:

```text
.codex/tasks/issue-266-industry-research-ordinary-user-e2e-v1.md
docs/industry_research_ordinary_user_e2e_v1_preflight.md
```

`docs/architecture_baseline.md` is intentionally deferred until this architecture
has an accepted fixed HEAD and a separately authorized synchronization step.
No production code, API, UI, test, fixture, workflow, dependency, schema,
migration, Provider, network, credential, AI, release, tag or version file is
authorized by this task.

## Objective

Freeze one deterministic, Chinese-first ordinary-user flow over the existing
owners:

```text
ordinary-language topic
  -> explicit scope confirmation
  -> exact session and revision
  -> deterministic candidate universe
  -> explicit candidate review
  -> exact reviewed plan with frozen Owner Context
  -> exact owner-acceptance view
  -> preview
  -> explicit commit
  -> immutable accepted output
  -> complete beneficiary universe
  -> optional explicit exact candidate overlay
  -> exact history reopening
```

The end-to-end layer is orchestration and presentation only. It does not become
a new persisted owner and may not rewrite any accepted domain state.

## Locked architecture decisions

### 1. Contract identity

```text
presentation_contract_version =
  aquantai.industry-research-ordinary-user-e2e.v1

acceptance_view_snapshot_contract_version =
  aquantai.industry-thesis-owner-acceptance-view-snapshot.v1
```

The presentation contract may derive an ordinary-user stage from exact owner
states. It is not persisted accepted state.

### 2. Derived end-to-end stages

```text
topic_entry
scope_draft
scope_confirmed
candidate_review
reviewed_plan_ready
acceptance_preview_ready
acceptance_commit_ready
accepted_result
history_reopen
blocked_recovery
```

The stage is derived from exact session, reviewed-plan, acceptance and output
records. No new workflow-state column or orchestration table is introduced.

### 3. No hidden authority

Prohibited:

```text
latest fallback
maximum-coverage inference
same-stock context inference
first-row selection
silent legacy backfill
automatic candidate snapshot selection
request-body substitution
cross-case composition
cross-map composition
current-latest Company Research substitution
```

Case, Map and Map Revision authority comes only from the exact reviewed Owner
Context. If unique authority cannot be proven, fail closed and return the user
to explicit review.

### 4. Query and command classification

Read-only queries:

- workbench bootstrap and exact history;
- exact session revision;
- candidate review view;
- Owner Context options;
- reviewed-plan result;
- owner-acceptance view;
- accepted-output/assembled-result;
- exact candidate snapshot options;
- exact history reopening.

Explicit preview commands:

- session create/revise dry run;
- candidate review dry run;
- owner-acceptance preview.

Explicit commit commands:

- session create/revise commit;
- candidate review commit;
- owner-acceptance commit.

GET, page load, browser refresh, history navigation, detail expansion and
candidate-overlay selection for display perform zero writes, zero network and
zero AI calls.

### 5. Exact acceptance-view snapshot

The owner-acceptance GET must expose one normalized authoritative snapshot:

```text
snapshot_contract_version
reviewed_session_revision_id
expected_session_latest_revision_number
reviewed_plan_fingerprint_sha256
research_case_id
map_mode
industry_map_id
industry_map_revision_id
information_cutoff_date
owner_acceptance_plan_version
ordered exact member bindings
candidate-pool operation options
output metadata defaults
snapshot_content_sha256
```

`snapshot_content_sha256` is calculated from canonical normalized snapshot
content, not only top-level IDs.

Preview must compare route, request and freshly rebuilt authoritative snapshot
field by field. Commit must compare all preview inputs again and require:

```text
preview_fingerprint_sha256
acceptance_view_snapshot_content_sha256
```

A body replacement that preserves top-level IDs but changes members, operation
options, output defaults or ordering must fail closed before any owner write.

### 6. Preview and commit chronology

Preview is non-persistent. It returns a deterministic preview fingerprint over:

```text
exact authoritative snapshot
normalized submitted owner bindings
candidate-pool operation
output title and scope
revision note
dual-as-of boundaries
plan versions
```

Commit accepts only a preview fingerprint produced from the same exact content.
A completed owner transaction is replayed through the existing owner result;
duplicate submit must never create a second accepted graph.

### 7. Complete universe and candidate overlay

The accepted complete beneficiary list is the outer collection.

The optional candidate layer is:

```text
zero or one explicitly selected
InvestmentCandidateSnapshotRevision
```

Eligibility requires exact equality with the accepted candidate-pool revision
and visibility under the exact dual-as-of boundaries.

Join key:

```text
beneficiary_revision_id
```

The overlay may enrich matching rows. It may not filter, add, remove, rewrite or
canonically reorder the accepted universe.

### 8. Exact history route

Canonical accepted-result route remains anchored by:

```text
session_id
accepted_session_revision_id
as_of_cutoff
as_of_recorded_at_utc
optional investment_candidate_snapshot_revision_id
```

The server resolves exactly one output-link revision from the accepted graph.
Ambiguous or incomplete output links fail closed.

Reloading the same selectors reproduces the same accepted result. A newer
candidate snapshot, Company Research revision, Map Revision or reviewed plan is
never silently substituted.

### 9. Ordinary-user interaction

Minimum visible stages:

```text
输入主题
确认范围
生成候选公司
逐项人工审核
预览接受结果
确认接受研究成果
查看完整研究结果
重开历史结果
```

Each page has one dominant primary action. Technical IDs, hashes and database
details remain under progressive technical disclosure.

The result hierarchy is:

1. 5–8 key conclusion cards from accepted deterministic facts;
2. exact industry-chain and value-pool context;
3. complete accepted beneficiary universe;
4. optional exact candidate overlay;
5. earnings transmission, expectation, valuation, catalysts, risks and missing
   facts only when owned by accepted linked records;
6. evidence, provenance and technical details.

### 10. Recovery rules

- stale session or candidate revision: preserve user input and reload exact
  current owner state;
- missing Owner Context: return to explicit context selection;
- legacy v1 reviewed plan: require explicit v2 re-review;
- acceptance snapshot mismatch: discard preview authority, preserve form and
  rebuild the authoritative view;
- duplicate completed commit: reopen the exact accepted result;
- candidate snapshot mismatch: keep accepted result readable and remove only the
  overlay;
- incomplete accepted graph: stop and require local integrity review;
- browser back/refresh during preview: preview is recreated from the current
  exact authoritative snapshot;
- browser refresh during commit: query exact owner transaction/result before
  allowing retry.

### 11. Persistence and dependency decision

```text
new table = none
new column = none
migration = none
new dependency = none
external network = none
AI call = none
accepted owner mutation = only through existing commands
orchestration persistence = none
```

### 12. Future implementation file-family candidate

A future separately authorized Strict Implementation Issue may justify a bounded
family such as:

```text
backend/api/industry_analysis.py
backend/api/industry_analysis_review.py
backend/api/industry_analysis_acceptance.py
backend/api/industry_research_result.py
backend/main.py only if a bounded route registration change is required

industry_alpha/industry_research_e2e_rules.py
industry_alpha/industry_research_e2e_query.py
existing owner-acceptance workbench/query files only for the reviewed
snapshot-fingerprint contract

industry_analysis/static/workbench.html
industry_analysis/static/workbench.js
industry_analysis/static/review_result.html
industry_analysis/static/review_result.js
industry_analysis/static/owner_acceptance.html
industry_analysis/static/owner_acceptance.js
industry_analysis/static/accepted_result.html
industry_analysis/static/accepted_result.js
bounded shared industry-analysis CSS/helpers

bounded industry-analysis, owner-acceptance and result-assembly tests
one offline production-realistic demo
.github/workflows/local-tests.yml only to add the demo without weakening checks
```

This inventory is a candidate only. The implementation Issue must inspect current
files again and authorize an exact subset.

## Production-realistic offline golden path

1. Enter `存储涨价受益公司`.
2. Explicitly confirm one scope and one exact session revision.
3. Explicitly select one exact Owner Context containing one Research Case and one
   Industry Map Revision.
4. Review three candidate revisions.
5. Accept all three into the complete beneficiary universe; two are supported
   for one exact candidate-pool revision and one remains outside the supported
   handoff.
6. Rebuild the exact acceptance-view snapshot and preview.
7. Commit using the same snapshot content hash and preview fingerprint.
8. Show all three accepted beneficiaries.
9. List two eligible candidate snapshots for the exact pool without default
   selection.
10. Explicitly select one snapshot; exactly two matching rows receive overlay
    fields.
11. Reopen the same accepted result and selected overlay from the exact URL with
    zero writes, zero network and zero AI.

## Decisive failure matrix

The architecture and future tests must fail closed for:

1. multiple reachable contexts with no explicit frozen authority;
2. Case/Map/Map Revision substitution;
3. map mode, cutoff, reviewed fingerprint, expected latest or plan-version drift;
4. acceptance-view body replacement with unchanged top-level IDs;
5. changed ordered member bindings or candidate-pool operation options;
6. preview fingerprint from another snapshot;
7. candidate snapshot from another pool, Case or Map context;
8. legacy reviewed plan without exact Owner Context;
9. incomplete beneficiary readiness;
10. missing or stale exact Company Research link;
11. exact history reopen while newer snapshots exist;
12. duplicate submit after completed commit;
13. browser back/refresh during preview or commit;
14. incomplete accepted output graph.

Every failure preserves existing accepted state.

## Required validation

Before merge consideration:

- branch starts from exact base
  `8a085f48cf99f389c810496427d2aa0292c6b6c5`;
- Base-to-HEAD changes exactly the two authorized Markdown files;
- `behind = 0`;
- no executable or configuration changes;
- applicable CI succeeds on the exact immutable HEAD;
- independent review contains exactly:

```text
AUTHORIZED INDUSTRY RESEARCH ORDINARY-USER END-TO-END V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

- unresolved review threads = 0;
- merge requires separate explicit project-owner authorization.

Any new commit invalidates prior fixed-HEAD CI and review evidence.

## Locked exclusions

No live THS, Tushare, AKShare or another Provider; no credentials, HTTP
transport, raw capture, Provider persistence, schema, migration, announcement
acquisition, OCR, automatic evidence acceptance, automatic research acceptance,
new scoring, recommendation, target price, expected return, holdings, position
sizing, portfolio optimization, trading, background task, scheduler,
notification, release, tag or version change.

## Stop conditions

Stop and return for owner review if:

- a new persisted orchestration owner appears necessary;
- exact context cannot be proven without inference;
- accepted owners must be rewritten;
- schema or migration is required;
- current/latest fallback is proposed;
- candidate states must be recomputed;
- PR #241 must be changed or copied wholesale;
- Provider, network, AI, recommendation, portfolio or trading scope appears.

## Delivery gates

- one Draft architecture PR linked to #266 and #137;
- exact fixed-HEAD CI;
- fixed-head independent architecture review;
- zero unresolved threads;
- separate explicit owner authorization before Ready/merge;
- separate Strict Implementation Issue after architecture acceptance.
