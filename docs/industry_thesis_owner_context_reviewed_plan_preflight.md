# Exact Owner Context in Reviewed Industry Thesis Plan — Architecture Preflight

## 1. Status, authority and decision

This document is the architecture contract for Issue #242.

Authority:

- Product Roadmap: #137;
- accepted Industry Thesis owner-acceptance architecture and implementation: #234/#235 and #236/#237;
- accepted ordinary-user completion architecture: #238 / merged PR #239;
- paused implementation: Issue #240 / Draft PR #241;
- workflow: `.codex/WORKFLOW.md`;
- exact architecture base: `41137ee6f017a781367b439f4119f201d05ce9cf`;
- branch: `arch/owner-context-reviewed-plan-contract`.

Project-owner authorization on 2026-07-26:

```text
Owner Context 合同架构预检
```

Decision:

```text
architecture_status = proposed_for_fixed_head_review
risk = strict
reviewed_plan_active_write_version = aquantai.industry-thesis-acceptance-plan.v2
owner_context_contract_version = aquantai.industry-thesis-owner-context.v1
owner_context_authority = top_level_reviewed_plan
candidate_provenance_semantics = unchanged
owner_acceptance_flat_dto = unchanged
schema_migration = none
new_table = none
new_database_column = none
legacy_unaccepted_v1 = fail_closed_and_re_review
legacy_accepted_output = exact_read_preserved
pr_241 = frozen_not_resumed
future_implementation = new_issue_new_branch_new_draft_pr
```

The missing Owner Context is a reviewed-contract ownership defect, not a query-selection bug. The fix is to freeze one exact persisted context during explicit review, include it in deterministic identities and fingerprints, and enforce it again in the owner-acceptance core.

## 2. Problem statement

The current reviewed acceptance plan freezes selected candidate revisions and source-reference fingerprints, but it does not freeze the exact cross-domain owner destination:

```text
Research Case
Industry Map
Industry Map Revision
```

The ordinary-user acceptance projection currently finds Stage 1 beneficiary rows for the selected frozen stocks and accepts the context when exactly one Case/Map/Map Revision tuple is reachable.

That behavior is fail-closed on ambiguity but remains hidden inference:

```text
frozen stock overlap
  -> currently reachable Stage 1 rows
  -> unique context
  -> accepted as Owner Context
```

The required authority is instead:

```text
explicit review selection
  -> exact persisted Map Revision
  -> server-resolved Map and Research Case
  -> fingerprinted reviewed plan
  -> owner operations restricted to that exact context
```

## 3. Why candidate source provenance cannot own the context

### 3.1 `existing_industry_map_revision`

This source kind already validates one exact `industry_map_revision_id` and its chronology. It cannot serve as the global context contract for a multi-company candidate universe because candidate identity keys are derived from:

```text
source_kind + source_reference
```

Multiple company proposals referencing the same Map Revision therefore collide as one candidate source.

Adding a company discriminator to this source reference solely to avoid collision would change candidate provenance meaning and weaken duplicate-source protection.

### 3.2 `accepted_local_mapping`

This source kind supports distinct company mappings and exact stock identities, but its accepted contract does not own or validate Case/Map/Map Revision fields.

Treating arbitrary keys inside its open JSON reference as Owner Context would create an undocumented semantic side channel.

### 3.3 Separation of meanings

The architecture therefore preserves this boundary:

| Meaning | Owner |
|---|---|
| Why this company candidate exists | candidate `source_kind` and `source_reference` |
| Which formal stock identity was reviewed | reviewed candidate revision |
| Where Stage 1 owner operations occur | top-level reviewed-plan `owner_context` |
| What Stage 1 operation is accepted | explicit owner-acceptance binding |
| Which supported members enter handoff | owner-acceptance core derived result |

No one field is overloaded to own two meanings.

## 4. Contract versions

### 4.1 Reviewed acceptance plan

The current version remains historical:

```text
aquantai.industry-thesis-acceptance-plan.v1
```

The new active write version is:

```text
aquantai.industry-thesis-acceptance-plan.v2
```

Version 2 requires one valid top-level `owner_context`.

Version 1 records remain immutable and readable. New review writes must not create v1 plans after the v2 implementation is enabled.

### 4.2 Owner Context object

The nested object has its own explicit version:

```text
aquantai.industry-thesis-owner-context.v1
```

This allows the reviewed-plan version and the context schema to evolve independently only through later governed architecture work.

### 4.3 Owner-acceptance request

The existing flat owner-acceptance request remains unchanged:

```text
aquantai.industry-thesis-owner-acceptance-plan.v1
```

No wrapper, duplicate request model or browser-owned context DTO is introduced.

## 5. Review input contract

The exact proposal-review request adds one required top-level object for v2:

```json
{
  "session_revision_id": "...",
  "expected_session_latest_revision_number": 4,
  "acceptance_plan_version": "aquantai.industry-thesis-acceptance-plan.v2",
  "owner_context": {
    "industry_map_revision_id": "..."
  },
  "decisions": [],
  "revision_note": "..."
}
```

Rules:

- `owner_context` accepts exactly one key: `industry_map_revision_id`;
- unknown keys are rejected;
- the client does not submit `research_case_id`, `industry_map_id`, `map_mode`, titles, labels or dates as authority;
- the revision ID must be an explicit UUID;
- the review service resolves every other field from persisted foreign keys;
- v1 historical payloads are never silently promoted to v2.

## 6. Review-context option projection

An ordinary user must not type a UUID. A future bounded review projection returns exact eligible persisted options.

Recommended local API shape:

```text
GET /industry-analysis/api/session-revisions/{session_revision_id}/owner-context-options
    ?as_of_cutoff={date}
    &as_of_recorded_at_utc={explicit UTC}
```

The exact route may be integrated into the existing candidate-review response if that stays within deterministic query ceilings. The semantic contract is the same.

Each option contains:

```json
{
  "industry_map_revision_id": "...",
  "ordinary_label": "研究案例 · 产业地图 · 第 N 版",
  "case": {
    "case_key": "...",
    "title": "optional cutoff-visible title"
  },
  "industry_map": {
    "map_key": "...",
    "revision_number": 3,
    "title": "...",
    "scope": "..."
  },
  "information_cutoff_date": "YYYY-MM-DD",
  "recorded_at_utc": "...",
  "technical_details": {
    "research_case_id": "...",
    "industry_map_id": "...",
    "industry_map_revision_id": "..."
  }
}
```

Eligibility requires:

1. exact `IndustryMapRevision` exists;
2. exact parent `IndustryMap` exists;
3. exact parent `ResearchCase` exists;
4. the foreign-key graph is consistent;
5. Map Revision information cutoff does not exceed the exact Industry Thesis cutoff;
6. Map Revision recorded time does not exceed the explicit review boundary;
7. option data comes only from persisted local records;
8. no company overlap, source-reference matching, maximum coverage or unique reachability is used.

The UI requires an explicit selection and an explicit confirmation such as:

```text
确认将本次审核结果归属到这个研究案例和产业地图版本
```

There is no accepted hidden default. A visually highlighted single option still requires explicit confirmation.

## 7. Server-resolved frozen object

The review service resolves the submitted Map Revision and constructs:

```json
{
  "owner_context_contract_version": "aquantai.industry-thesis-owner-context.v1",
  "map_mode": "reuse_exact_existing_map_revision",
  "research_case_id": "<resolved from IndustryMap.case_id>",
  "industry_map_id": "<resolved from IndustryMapRevision.map_id>",
  "industry_map_revision_id": "<submitted exact revision>"
}
```

The normalized object uses canonical key ordering and string UUIDs before fingerprinting.

The service rejects:

- missing Map Revision;
- missing Map;
- missing Research Case;
- Map Revision pointing to a different Map than resolved;
- Map pointing to a different Case than resolved;
- later information cutoff;
- later recorded time;
- malformed or noncanonical identifiers;
- any unsupported context contract or map mode.

## 8. Deterministic review identity

The current review creates deterministic session and candidate revision IDs from a decision fingerprint. Owner Context changes accepted meaning and therefore must participate in that seed.

Version 2 decision seed contains at least:

```json
{
  "acceptance_plan_version": "aquantai.industry-thesis-acceptance-plan.v2",
  "owner_context": {},
  "session_id": "...",
  "source_session_revision_id": "...",
  "next_session_revision_number": 5,
  "decisions": []
}
```

Required properties:

- same exact source revision, same decisions and same context produce the same deterministic IDs in dry-run and commit;
- a different Map Revision produces different reviewed session and candidate revision IDs;
- context selection cannot be changed without appending a new reviewed revision;
- context is not copied from display text or candidate source references.

## 9. Reviewed-plan v2 shape

The v2 acceptance plan contains the existing fields plus the required object:

```json
{
  "acceptance_plan_version": "aquantai.industry-thesis-acceptance-plan.v2",
  "session_id": "...",
  "source_session_revision_id": "...",
  "reviewed_session_revision_id": "...",
  "information_cutoff_date": "YYYY-MM-DD",
  "recorded_at_utc_boundary": "...",
  "coverage_state": "...",
  "owner_context": {
    "owner_context_contract_version": "aquantai.industry-thesis-owner-context.v1",
    "map_mode": "reuse_exact_existing_map_revision",
    "research_case_id": "...",
    "industry_map_id": "...",
    "industry_map_revision_id": "..."
  },
  "selected_candidates": [],
  "rejected_candidate_revision_ids": [],
  "unresolved_candidate_revision_ids": [],
  "candidate_sources": [],
  "acceptance_plan_fingerprint_sha256": "..."
}
```

The plan fingerprint covers `owner_context`.

The plan recorded boundary becomes the maximum cutoff-visible recorded time among:

- source Industry Thesis session revision;
- exact candidate revisions used by the review;
- selected Owner Context Map Revision.

The reviewed session revision itself is recorded after that boundary under the existing append-only chronology rule.

## 10. Reviewed-plan query verification

`IndustryThesisReviewedPlanQueryService` remains the read owner for one exact reviewed plan and must verify v2 context before returning an acceptance-capable projection.

Verification order:

1. exact reviewed session revision exists and is visible;
2. workflow state is `reviewed_plan_ready`;
3. stored plan is canonical JSON;
4. plan fingerprint and reviewed revision binding match;
5. plan version is recognized;
6. candidate universe and source fingerprints match exact reviewed candidate rows;
7. v2 Owner Context object has exactly the accepted keys and versions;
8. exact Map Revision / Map / Case graph exists and matches the frozen IDs;
9. context chronology is within both the plan boundary and caller as-of boundaries.

The generic reviewed-result page may still render a historical v1 plan. Acceptance-capable callers must require v2.

Recommended query result metadata:

```json
{
  "acceptance_capability": {
    "state": "ready" | "legacy_owner_context_missing",
    "reason_code": null | "industry_thesis_owner_context_required"
  }
}
```

This is a read projection only and does not mutate old history.

## 11. Legacy reviewed-plan recovery

### 11.1 Unaccepted v1 plan

A latest `reviewed_plan_ready` v1 record cannot enter owner acceptance.

Ordinary-user result:

```text
这条审核结果尚未冻结研究案例和产业地图版本，不能继续接受成果。
```

Primary action:

```text
重新审核并指定研究归属
```

Recovery appends new history; it never edits the v1 plan.

The future review service may accept an exact latest legacy `reviewed_plan_ready` source only through an explicit v1-to-v2 re-review mode with these constraints:

- the source is the exact latest session revision;
- no accepted output exists for it;
- its complete latest candidate universe is reloaded;
- all decisions are explicitly resubmitted and cover the complete universe;
- one exact Owner Context is explicitly selected;
- new reviewed candidate revisions and one v2 reviewed session revision are appended;
- the old v1 reviewed revision remains immutable and reopenable;
- repeated upgrade of a v2 plan is rejected unless ordinary review meaning changes through a separately valid new revision.

This may be implemented as a bounded extension of the existing review command or a dedicated re-review command. It must not become a second workflow owner.

### 11.2 Already accepted v1 output

An existing exact `accepted_outputs_linked` result remains readable through its stored output link, Case, Map, Map Revision and accepted owner bindings.

No re-review or backfill is required.

An exact idempotent replay may return the already accepted output only when:

- reviewed revision matches;
- owner-acceptance plan fingerprint matches the stored output;
- reviewed-plan fingerprint matches;
- accepted Case/Map/Map Revision match the stored output link;
- no new owner write is attempted.

A conflicting replay remains blocked.

## 12. Owner-acceptance core enforcement

The web adapter is not the sole security or integrity boundary.

The core coordinator must compare the normalized flat request against the fingerprint-verified reviewed-plan v2 object:

```text
normalized.research_case_id == reviewed_plan.owner_context.research_case_id
normalized.map_mode == reviewed_plan.owner_context.map_mode
normalized.industry_map_id == reviewed_plan.owner_context.industry_map_id
normalized.industry_map_revision_id == reviewed_plan.owner_context.industry_map_revision_id
```

Mismatch returns a stable fail-closed error before Stage 1, semantics, pool or output writes.

Recommended existing public code mapping:

```text
INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH
```

A stale or fingerprint mismatch remains:

```text
INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_FINGERPRINT_MISMATCH
```

A missing v2 context remains:

```text
INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED
```

No owner call may supply a different valid-looking context merely because it contains the same stocks.

## 13. Acceptance workbench projection

The future query path is:

```text
exact reviewed revision
  -> verified v2 acceptance plan
  -> frozen owner_context
  -> exact header query for Case/Map/Map Revision
  -> exact Stage 1 rows inside that context and selected stock set
  -> exact assertion/claim/semantic/pool options
```

The following current pattern is removed:

```text
selected stocks
  -> all reachable Stage 1 contexts
  -> require one context
```

All Stage 1 identity/revision queries include the exact context predicates. Stock matching is only a member predicate inside that context.

The adapter-level loaded-graph guard may remain only as an integrity assertion:

```text
all loaded Stage 1 rows must equal reviewed owner_context
```

It may not discover or choose the context.

The existing query ceilings remain:

```text
owner-acceptance-view <= 14 SQL statements for 3 and 20 members
accepted-result-view <= 10 SQL statements
zero per-member HTTP calls
```

## 14. Candidate and fixture semantics

Candidate sources remain production-realistic and distinct.

The ordinary-user golden fixture may continue using distinct accepted local mapping references per company, provided those references satisfy the accepted source contract. It adds one separate explicit review-level Map Revision selection.

Required fixture shape:

```text
candidate A provenance = existing accepted source A
candidate B provenance = existing accepted source B
candidate C provenance = existing accepted source C
review Owner Context = one exact shared Map Revision
```

This proves multi-company coexistence without changing candidate-key semantics.

A fixture must not place context IDs inside an otherwise unvalidated source reference and then treat them as authority.

## 15. Review and acceptance UI behavior

### 15.1 Review result / decision surface

The explicit Owner Context control appears before final review submission.

The surface shows:

- Research Case label;
- Industry Map title and scope;
- exact revision number;
- information cutoff and local recorded date;
- warning that later acceptance will be limited to this exact context;
- technical IDs under `<details>` or equivalent;
- one explicit confirmation.

Missing selection blocks review submission.

### 15.2 Acceptance surface

The acceptance page displays the frozen context as non-editable reviewed authority.

It does not expose an alternative context selector.

Technical IDs remain progressive details. Any payload context substitution is rejected and form values are preserved.

### 15.3 Legacy recovery

A v1 reviewed result shows one primary action to re-review and specify context. It never links directly to a commit-capable acceptance page.

## 16. Exact state matrix

| State | Plan version | Output exists | Acceptance action |
|---|---:|---:|---|
| `candidate_build_ready` / `awaiting_review` | none | no | explicit review requires context |
| `reviewed_plan_ready` | v2 | no | acceptance allowed when exact prerequisites pass |
| `reviewed_plan_ready` | v1 | no | blocked; explicit v2 re-review |
| `accepted_outputs_linked` | v1 or v2 source | yes | exact result read; no new selection |
| `superseded` | any | any | exact history read only where supported |
| `abandoned` | any | any | no acceptance |
| malformed / graph incomplete | any | any | fail closed |

## 17. Chronology and provenance

### 17.1 Review-time boundary

The selected Map Revision must satisfy:

```text
map_revision.information_cutoff_date <= thesis_revision.information_cutoff_date
map_revision.recorded_at_utc <= review_operation_recorded_at_utc
```

The exact context row is included in the source recorded boundary used by the v2 plan.

### 17.2 Read-time boundary

A reviewed v2 plan is visible only when:

```text
reviewed_revision.information_cutoff_date <= requested as_of_cutoff
reviewed_revision.recorded_at_utc <= requested as_of_recorded_at_utc
map_revision.information_cutoff_date <= requested as_of_cutoff
map_revision.recorded_at_utc <= requested as_of_recorded_at_utc
plan.recorded_at_utc_boundary <= requested as_of_recorded_at_utc
```

No current latest Map Revision fallback is allowed.

### 17.3 Accepted output

The accepted output continues to persist exact Case/Map/Map Revision fields. These must equal the reviewed v2 context for new outputs.

## 18. Persistence and migration

Decision:

```text
migration = none
new table = none
new database column = none
new ORM owner = none
backfill = none
history rewrite = none
```

The context is stored in the existing canonical reviewed session `draft_graph_json` acceptance-plan preview.

No browser state becomes accepted authority. Browser form state remains temporary and is discarded or preserved only according to existing UI conflict behavior.

## 19. Rollback and downgrade

### 19.1 Before first v2 write

Code rollback is safe because no persisted record depends on the new semantic contract.

### 19.2 After first v2 write

Older code may parse the generic plan while ignoring Owner Context and could re-enable same-stock context inference. Therefore schema compatibility does not equal semantic downgrade safety.

Required operational rule:

```text
running pre-v2 acceptance code against a database containing v2 reviewed plans is prohibited
```

Safe recovery options:

1. roll forward with a corrective patch; or
2. stop the application and restore a verified database snapshot taken before the first v2 reviewed-plan write.

Implementation validation must include a static/runtime version guard appropriate to local deployment so that unsupported reviewed-plan versions fail closed rather than fall through to legacy inference.

## 20. Production-realistic golden path

Prerequisites:

- one exact Industry Thesis candidate universe;
- three distinct selected company candidates with exact frozen stock identities;
- one exact visible Research Case, Industry Map and Map Revision;
- exact Stage 1 assertions/claims and optional semantic revision inside that context.

Path:

1. User opens exact candidate review.
2. Server returns bounded exact Owner Context options.
3. User explicitly selects one Map Revision and confirms it.
4. Review request submits only that revision ID plus complete candidate decisions.
5. Server resolves Map and Case, validates chronology and builds normalized context.
6. Decision fingerprint includes context.
7. Commit appends one v2 reviewed session revision and reviewed candidate revisions.
8. Reopening verifies the exact context graph and fingerprint.
9. Acceptance view loads Stage 1 options only inside the reviewed context.
10. Company A reuses supported Stage 1 plus exact semantic revision.
11. Company B reuses/appends draft or disputed Stage 1.
12. Company C creates/appends supported Stage 1 with exact frozen stock fields and semantic `none`.
13. User selects one global supported-handoff operation.
14. Preview returns complete `3`, supported `2`, stable fingerprint and zero writes.
15. Explicit commit creates one atomic accepted session/output/pool graph.
16. Exact result reopens all three in frozen order under both boundaries.
17. No automatic Company Research, Investment Candidate, recommendation, portfolio or trading state is created.

Zero-supported path:

- explicit context still required;
- all final Stage 1 states are draft/disputed;
- pool mode is `none_no_supported_members`;
- exact commit and complete-result reopening succeed without a fabricated pool.

## 21. Primary blocked path

Given:

- a latest v1 `reviewed_plan_ready` plan;
- all selected candidates have exact stocks;
- the database happens to contain exactly one Stage 1 context for those stocks;
- no reviewed Owner Context exists.

Required result:

```text
acceptance_capability = blocked
reason = industry_thesis_owner_context_required
inferred_context = none
preview_fingerprint = none
writes = zero
primary_action = explicit v2 re-review
```

This test is the decisive proof that the architecture defect is closed.

## 22. Additional failure matrix

Future tests must cover:

- review context omitted;
- malformed UUID;
- unknown owner-context field;
- Map Revision missing;
- Map missing;
- Case missing;
- FK graph mismatch;
- later information cutoff;
- later recorded time;
- stored v2 context tampered without fingerprint update;
- stored context and fingerprint both tampered but FK graph invalid;
- same decisions with two different contexts produce different deterministic IDs;
- submitted owner-acceptance Case substitution;
- submitted Map substitution;
- submitted Map Revision substitution;
- submitted map mode substitution;
- Stage 1 row for same stock but different context is excluded;
- only different-context Stage 1 rows exist, so reuse/append unavailable while create may remain explicit if assertions/claims permit;
- legacy v1 unaccepted plan fails closed;
- legacy v1 accepted result remains readable;
- exact idempotent replay returns original output without writes;
- conflicting replay remains blocked;
- query ceilings remain constant for 3 and 20 members;
- no network or Provider import appears;
- no schema/migration artifact appears.

## 23. Security, locality and non-advisory boundary

- local persisted records only;
- no external origin, Provider call or credential path;
- strict JSON and unknown-field rejection;
- exact UUID and chronology validation;
- safe text rendering;
- no arbitrary redirect or free-text path construction;
- AI cannot choose or modify Owner Context;
- no recommendation, target price, expected return, position sizing, portfolio, broker, order or trading semantics.

## 24. Future implementation scope

A later separately authorized Strict implementation Issue may permit bounded changes to:

```text
industry_alpha/industry_thesis_review.py
industry_alpha/industry_thesis_owner_acceptance.py
industry_alpha/industry_thesis_owner_acceptance_workbench.py
industry_alpha/industry_thesis_rules.py only for a necessary neutral constant/normalizer
backend/api/industry_analysis_review.py
backend/api/industry_analysis_acceptance.py
industry_analysis/static/review_result.html
industry_analysis/static/review_result.js
industry_analysis/static/owner_acceptance.html
industry_analysis/static/owner_acceptance.js
bounded shared presentation helpers only when necessary
bounded Industry Thesis review/acceptance tests
scripts/run_industry_thesis_ordinary_user_acceptance_fixture.py
.github/workflows/local-tests.yml only to add the offline demo without weakening checks
docs/architecture_baseline.md only after accepted fixed-head implementation evidence
```

No model, schema or migration file is expected.

## 25. Replacement implementation decision

PR #241 remains a frozen blocked implementation record at exact HEAD:

```text
3116a67ec472131eea3bf3d1bd9daee884c69ee9
```

It must not receive the new contract work because:

- its Issue does not authorize changes to the review core and owner-acceptance core;
- its exact base predates this architecture;
- adding the contract would silently expand scope;
- rebasing or silently updating its branch is prohibited;
- its prior fixed-head CI and review evidence are already blocked and would be invalidated.

After this architecture is accepted and merged, and only after separate project-owner authorization:

```text
new Strict implementation Issue
  -> new branch from then-current exact main
  -> reapply still-valid bounded PR #241 work
  -> implement reviewed-plan v2 Owner Context
  -> new Draft replacement implementation PR
```

PR #241 remains open until the owner separately authorizes closure as superseded. No automatic close or merge occurs.

## 26. Validation contract for the architecture PR

This architecture PR is documentation-only. Required checks:

- complete base-to-head inventory contains exactly the task snapshot and this document;
- Markdown structure and internal references are coherent;
- exact base and branch are recorded;
- candidate provenance and Owner Context ownership are not conflated;
- reviewed-plan v2, legacy behavior and downgrade rules are explicit;
- golden and primary blocked paths are production-reachable;
- no executable, schema, Provider, AI, release or version file changed;
- repository documentation/CI checks pass on one exact immutable HEAD.

## 27. Strict fixed-head review

The process-independent architecture reviewer must re-read:

- Issue #242;
- Roadmap #137;
- `.codex/WORKFLOW.md`;
- this document and task snapshot;
- the exact base-to-head diff;
- current CI evidence;
- PR #241 blocker context.

Approval requires zero blocking findings and the exact phrase:

```text
AUTHORIZED OWNER CONTEXT REVIEWED-PLAN CONTRACT PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates prior CI and review evidence.

## 28. Locked exclusions

No candidate-key redesign, candidate source reinterpretation, migration, table, database column, backfill, history rewrite, inferred legacy upgrade, fuzzy identity bridge, new Industry Map fact creation, Provider/network access, credential, AI call, automatic classification, automatic Company Research, Investment Candidate, scoring, recommendation, target price, expected return, position sizing, research holdings, portfolio, broker, order, trading, release, tag or project-version change.

## 29. Stop conditions

Stop and return for project-owner review if implementation would require:

- context selection from stock overlap or unique reachability;
- candidate source semantic changes;
- a migration or new database field;
- mutation/backfill of old reviewed plans;
- a second workflow owner;
- a wrapper or weakened owner-acceptance DTO;
- resuming, rebasing or silently updating PR #241;
- unsafe operation of old acceptance code after v2 writes;
- any Provider/network/AI/recommendation/portfolio/trading behavior.

## 30. Completion boundary

Architecture fixed-head approval does not authorize:

- merge;
- closing Issue #242;
- closing duplicate Issue #243;
- closing or merging PR #241;
- starting the replacement implementation Issue;
- production code;
- release, tag or version change;
- a later roadmap phase.

Every such action requires its own explicit project-owner authorization.
