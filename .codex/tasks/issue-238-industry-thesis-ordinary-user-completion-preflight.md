# Issue #238 Task Snapshot — Industry Thesis Ordinary-User Completion v1

## Authority

- Authoritative Architecture Preflight Issue: #238.
- Product Roadmap: #137.
- Accepted owner-acceptance architecture: Issue #234 / merged PR #235.
- Accepted owner-acceptance implementation: completed Issue #236 / merged PR #237.
- Accepted ordinary-user workbench foundation: #215/#216 and #217/#218.
- Today Market automatic-refresh architecture: #221 / merged PR #222.
- THS Stage C1 remains blocked by Issue #225.
- Project-owner authorization on 2026-07-25:

```text
批准，基于规划进去下一步开发
```

- Remediation authorization on 2026-07-25:

```text
修复阻断项
```

- Blocking review: PR #239 Review `4779124457` at old HEAD `dd8e7331cbe2fb18cf77b97aca647d21c03df0f3`.
- Exact architecture base: `a6da9bc8483606a67b7ca5f1329e46232d5b47be`.
- Branch: `docs/industry-thesis-ordinary-user-completion-preflight`.
- Workflow authority: `.codex/WORKFLOW.md`.
- Risk tier: **Strict Architecture Preflight**.

## Phase boundary

This task is architecture-only.

Authorized files:

```text
.codex/tasks/issue-238-industry-thesis-ordinary-user-completion-preflight.md
docs/industry_thesis_ordinary_user_completion_preflight.md
```

No production code, API, browser UI, schema, migration, fixture, executable test, dependency, Provider, credential, network access, AI call, release, tag or version change is authorized.

## Objective

Define the smallest production-reachable ordinary-user slice that completes the accepted Industry Thesis workflow:

```text
reviewed_plan_ready
  -> 查看研究结果
  -> 检查并接受研究成果
  -> confirm frozen owner bindings in ordinary Chinese
  -> deterministic dry-run preview
  -> explicit confirmation
  -> accepted_outputs_linked
  -> 查看已接受成果、完整成员和准备度
  -> exact history reopening
```

The architecture must reuse the accepted owner-acceptance core and make no accepted decision by hidden inference.

## Locked product meaning

1. The complete accepted result is the complete frozen member set for this accepted research result.
2. The supported candidate-pool handoff is a separate supported-only downstream handoff.
3. Draft and disputed accepted members remain visible.
4. Zero-supported acceptance is valid and creates no fake pool.
5. Readiness is an exact read of existing accepted owners and missing states; it creates no Company Research or Investment Candidate state.
6. Accepted research is not a recommendation, target price, expected return, position instruction or trading action.

## Review-blocker resolutions

### 1. Frozen `stock_basic` identity only

Owner acceptance does not choose among compatible identities.

For every selected reviewed candidate:

- the exact `proposed_stock_basic_record_id` frozen on the reviewed candidate is the only eligible Stage 1 stock binding;
- the page displays its ordinary label and technical ID;
- the user explicitly confirms that frozen record;
- a missing frozen record or listed-instrument-only candidate is blocked;
- any alternate identity resolution returns to a separately explicit pre-acceptance review/revision flow.

No `stock_basic_options[]`, fuzzy identity lookup or identity replacement is permitted in this slice.

### 2. Exact flat core request contract

Preview and commit use the exact flat payload accepted by `normalize_owner_acceptance_plan`.

Preview body contains exactly:

```text
reviewed_session_revision_id
expected_session_latest_revision_number
reviewed_plan_fingerprint_sha256
research_case_id
map_mode
industry_map_id
industry_map_revision_id
candidate_owner_bindings[]
candidate_pool_operation
output_title
output_scope
information_cutoff_date
revision_note
owner_acceptance_plan_version
```

Commit uses the same body plus:

```text
preview_fingerprint_sha256
```

Rules:

- no `owner_acceptance_plan` wrapper;
- no duplicated expected-latest or revision-note authority;
- route revision ID must equal body `reviewed_session_revision_id`;
- field names and meanings are preserved exactly;
- write DTOs reject unknown fields;
- the adapter may add only safe navigation links to responses, never rename away core result fields.

### 3. One global candidate-pool operation

Supported-handoff membership is derived from resulting exact Stage 1 `assessment_status == supported`; it is not editable per member.

The form includes one top-level `candidate_pool_operation` with exactly one accepted-core mode:

```text
create_supported_handoff
append_supported_handoff
reuse_exact_supported_handoff
none_no_supported_members
```

Mode contracts:

- create: deterministic technical `pool_key` from exact reviewed revision and contract version; explicit user-confirmed `title` and `scope`;
- append: exact cutoff-visible compatible pool identity and exact latest revision plus explicit `title` and `scope`;
- reuse: exact cutoff-visible pool/revision whose frozen membership already equals the supported reused Stage 1 revisions; unavailable when new Stage 1 revisions would be created/appended;
- none: available only when the resulting accepted universe has zero supported members.

The server and core remain authoritative for final membership and mismatch rejection.

### 4. Mandatory field ownership

All strict core fields have one source.

Top-level:

- `reviewed_session_revision_id`, reviewed fingerprint, expected latest, Research Case, map identity/revision and cutoff come from the exact reviewed acceptance view;
- `map_mode` is the fixed accepted constant `reuse_exact_existing_map_revision`;
- `owner_acceptance_plan_version` is the exact server-returned accepted version;
- `output_title` and `output_scope` are explicit user-confirmed form fields, optionally prefilled only from exact reviewed title/scope text;
- `revision_note` is one explicit user-entered field.

Per member:

- frozen stock record comes from `proposed_stock_basic_record_id`;
- reuse fields come from one exact compatible persisted beneficiary revision;
- create `source` and `stock_code` are exact server-returned values bound to the frozen stock record and explicitly confirmed;
- append uses the existing beneficiary identity and exact expected latest revision; `source`/`stock_code` remain identity-owned and are not resubmitted because the accepted core append payload does not contain them;
- legacy kind, assessment status, rationale, assertion revisions and claim revisions remain explicit accepted-core fields;
- semantic operation is limited to `none` or exact compatible reuse in this slice.

## Required architecture decisions

### 1. Exact routes and state mapping

Define deterministic local routes for:

- exact acceptance preparation from one `reviewed_plan_ready` revision;
- exact preview;
- explicit commit;
- exact accepted-result read;
- exact readiness read;
- exact history reopening.

Every route and request uses response-owned exact IDs and both as-of boundaries. No latest fallback, fuzzy lookup or browser-local identity reconstruction.

### 2. Ordinary-language confirmation over exact owners

For each selected reviewed candidate, display:

- the one frozen formal company/stock binding;
- Stage 1 reuse/create/append operation;
- legacy beneficiary kind and assessment status;
- assertion/claim prerequisites;
- typed-semantics none/reuse operation;
- derived supported-handoff result;
- missing and blocking states.

Internal IDs remain progressive technical details. No automatic mapping among reviewed exposure, legacy Stage 1 kind and typed semantics.

### 3. API/application adapter boundary

The future local adapter provides:

- one bounded acceptance view;
- one exact flat preview request;
- one exact flat commit request with matching preview fingerprint;
- one exact accepted output/result/readiness response.

The adapter reuses existing application services and does not duplicate owner validation or directly create ORM rows.

### 4. Preview and commit

Preview discloses:

- complete frozen member ordering;
- owner reuse/create/append operations;
- semantic operations or explicit absence;
- the one global candidate-pool operation;
- derived supported handoff membership;
- zero-supported state;
- blocking and readiness gaps;
- cutoff and visible data date.

Commit occurs only after explicit confirmation and only with the exact `preview_fingerprint_sha256`. Page load, navigation, preview and retry never commit automatically.

### 5. Conflict behavior

For stale expected-latest, moved owner boundaries, duplicate submit, conflicting replay and HTTP `409`:

- no silent retry or rebase;
- preserve selections, rationale and revision note in page memory;
- require explicit reload/re-preview;
- idempotent replay resolves to the same output;
- conflicting replay never overwrites the original accepted result.

### 6. Accepted-result presentation

First-render ordering:

1. concise accepted-state summary;
2. complete frozen member list;
3. supported-only handoff as a separate section;
4. readiness and missing/disputed/pending/failed states;
5. evidence and owner-operation details;
6. IDs, fingerprints, rule versions and chronology under technical details.

### 7. One primary action and accessibility

Define exactly one visually dominant action per tested page/state, including:

- `reviewed_plan_ready` -> `检查并接受研究成果`;
- commit-ready preview -> `确认接受研究成果`;
- `accepted_outputs_linked` -> `查看已接受成果`;
- blocked state -> one exact corrective action.

Use Chinese-first copy, keyboard navigation, explicit text states, focus management, error summaries, `aria-current` and non-color-only meaning.

### 8. Query and response budget

Deterministic ceilings:

- no per-row HTTP request;
- no N+1 database access;
- one bounded acceptance response including frozen identities, exact Stage 1/semantic options and top-level candidate-pool options;
- one preview request;
- one explicit commit request;
- one exact accepted-result response for first render.

Complete-universe meaning must not be lost through convenience pagination or first-record skipping.

### 9. Migration and persistence

```text
schema migration = none
new persisted UI workflow state = none
browser-local accepted research identity = none
```

Temporary unsaved form state may remain in page memory only. If a new persistent field or owner is required, stop and return for project-owner review.

### 10. Security and locality

- no external origins or arbitrary redirects;
- no free-text path construction;
- server-side validation of exact IDs, fingerprints and boundaries;
- strict JSON write contracts with unknown-field rejection;
- no Provider, credential, network, AI or remote transmission path.

## Production-realistic offline golden path

Use one exact `reviewed_plan_ready` session with three selected companies:

- A confirms its frozen stock binding, reuses a supported Stage 1 revision and compatible semantic revision;
- B confirms its frozen stock binding and reuses/appends a draft or disputed Stage 1 revision;
- C confirms its frozen stock binding and creates/appends a supported Stage 1 revision with exact `source`, `stock_code`, assertion and claim inputs, while choosing no semantic binding.

Top-level handoff:

- user chooses `create_supported_handoff`;
- technical `pool_key` is deterministically generated from the reviewed revision and plan version;
- user explicitly confirms pool title and scope;
- membership is derived as A and C only after owner preview validates their resulting supported revisions.

The user generates preview, explicitly confirms, receives one exact `accepted_outputs_linked` result and reopens all three in frozen order under both as-of boundaries.

No Company Research, Investment Candidate, recommendation, portfolio or trading state is automatically created.

Zero-supported path:

- every resulting Stage 1 revision is draft/disputed;
- only `none_no_supported_members` is valid;
- accepted result preserves all members and creates no fake pool.

## Primary blocked paths

### Frozen identity missing

One selected candidate lacks `proposed_stock_basic_record_id` or is listed-instrument-only.

Required behavior:

- identify the exact candidate and missing frozen prerequisite;
- expose no alternate identity choices;
- return no commit-ready fingerprint;
- route to explicit pre-acceptance correction;
- perform zero writes.

### Candidate-pool operation invalid

Supported members exist but no valid create/append/reuse operation is complete, or zero supported members are paired with a non-none mode.

Required behavior:

- show the top-level handoff error;
- keep member inputs;
- return no commit-ready fingerprint;
- perform zero writes.

No free text, name, ticker, Provider or AI inference fills either gap.

## Future implementation validation contract

Require zero-network fixture-backed coverage for:

- route/state mapping and exact-ID construction;
- frozen stock binding display and explicit confirmation;
- missing/listed-only identity blocking;
- exact flat preview and commit DTOs;
- unknown-field rejection and route/body ID mismatch;
- every mandatory field source;
- Stage 1 reuse/create/append inputs including create `source`/`stock_code`;
- candidate-pool create/append/reuse/none modes;
- derived, non-editable handoff membership;
- three-company golden path;
- zero-supported path;
- preview/commit fingerprint match;
- conflict and form preservation;
- idempotent/conflicting replay behavior;
- exact result/readiness rendering;
- dual-as-of negative visibility;
- graph-integrity failure presentation;
- one-primary-action and accessibility semantics;
- query ceilings and no N+1;
- no migration/new persistence;
- no Provider/network/credential/AI path;
- no recommendation, price target, expected return, portfolio or trading semantics.

## Locked exclusions

No production API/UI, Provider/THS/CNINFO/iFinD/Tushare/AKShare access, credentials, automatic refresh, scheduler, background worker, retry loop, notification, external network, AI call, new Industry Map facts, draft-graph promotion, fuzzy identity bridge, identity replacement during acceptance, automatic legacy/typed classification mapping, automatic Company Research, automatic Investment Candidate snapshot, recommendation, target price, expected return, position sizing, research holdings, portfolio, broker, order, trading, release, tag or version change.

## Stop conditions

Stop and return for project-owner review if:

- the success path requires hidden inference;
- owner acceptance must change the frozen stock identity;
- raw IDs must become mandatory primary inputs;
- a candidate-pool operation cannot be produced from exact owner records and explicit fields;
- a second workflow owner or new persistence is required;
- the adapter must duplicate validation or directly write ORM rows;
- a migration is required;
- exact reopening requires latest fallback;
- scope expands into Today Market source activation, announcements, Follow/Track or Research Portfolio;
- any Provider, network, AI, recommendation, portfolio or trading behavior appears.

## Delivery gates

1. Keep one architecture branch from exact base `a6da9bc8483606a67b7ca5f1329e46232d5b47be`.
2. Change only the two authorized documentation files.
3. Keep Draft PR #239 linked to #238, #137, #234/#235, #236/#237 and #215–#218.
4. Run repository checks on one new exact immutable HEAD.
5. Obtain a new process-independent fixed-head architecture review containing exactly:

```text
AUTHORIZED INDUSTRY THESIS ORDINARY-USER COMPLETION PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

6. Resolve every review thread.
7. Await separate explicit project-owner authorization before merge.
8. Any new commit invalidates prior exact-head validation and review.

Architecture approval does not authorize production implementation, merge, Issue closure, release or the next roadmap phase.