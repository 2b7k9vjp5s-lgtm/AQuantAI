# Exact Owner Context in Reviewed Industry Thesis Plan — Architecture Preflight

## 1. Authority and status

This is the architecture contract for Issue #242.

- Product Roadmap: #137.
- Accepted predecessors: #234/#235, #236/#237 and #238/#239.
- Paused implementation: Issue #240 / Draft PR #241.
- Workflow: `.codex/WORKFLOW.md`.
- Exact architecture base: `41137ee6f017a781367b439f4119f201d05ce9cf`.
- Branch: `arch/owner-context-reviewed-plan-contract`.
- Risk: **Strict Architecture Preflight**.

Owner authorization on 2026-07-26:

```text
Owner Context 合同架构预检
```

Decision:

```text
reviewed plan historical version = aquantai.industry-thesis-acceptance-plan.v1
reviewed plan active write version = aquantai.industry-thesis-acceptance-plan.v2
owner context version = aquantai.industry-thesis-owner-context.v1
owner context authority = top-level reviewed plan
candidate provenance = unchanged
owner-acceptance flat DTO = unchanged
migration/table/column/backfill = none
legacy unaccepted v1 = fail closed, explicit v2 re-review
legacy accepted v1 = exact read and idempotent replay preserved
PR #241 = frozen, not resumed
future implementation = new Issue, branch and Draft PR
```

## 2. Contract defect

The current reviewed plan freezes candidates, decisions, exact identities, candidate source-reference fingerprints, chronology and one plan fingerprint. It does not freeze:

```text
research_case_id
industry_map_id
industry_map_revision_id
```

The current acceptance workbench derives a context from Stage 1 rows reachable through frozen stocks and accepts it when only one tuple is reachable. That is still inference:

```text
stock overlap -> reachable Stage 1 rows -> unique context
```

Required authority:

```text
explicit review selection
  -> exact persisted Map Revision
  -> server-resolved Map and Research Case
  -> fingerprinted reviewed plan
  -> context-bound owner acceptance
```

## 3. Provenance and Owner Context are separate

Candidate provenance cannot own the global context.

### `existing_industry_map_revision`

It validates one exact Map Revision, but candidate identity is based on `source_kind + source_reference`. Multiple companies using one shared revision would collide.

Adding a company discriminator only to bypass duplicate-source protection would change provenance semantics.

### `accepted_local_mapping`

It can distinguish company candidates but its accepted contract owns no Case/Map/Map Revision meaning. Interpreting arbitrary JSON keys as context would create a hidden contract.

### Locked ownership

| Meaning | Authority |
|---|---|
| Why a company was proposed | candidate source kind/reference |
| Which formal stock identity was reviewed | reviewed candidate revision |
| Where owner operations occur | reviewed-plan Owner Context |
| Which Stage 1 operation is accepted | explicit owner binding |
| Which supported members enter handoff | owner-acceptance core result |

Candidate source kinds, reference schemas, candidate-key calculation and duplicate-source protection remain unchanged.

## 4. Reviewed-plan versions

### Historical read contract

```text
aquantai.industry-thesis-acceptance-plan.v1
```

V1 records remain immutable and readable.

### Active write contract

```text
aquantai.industry-thesis-acceptance-plan.v2
```

Every new review write requires one exact Owner Context.

### Owner Context contract

```text
aquantai.industry-thesis-owner-context.v1
```

### Owner-acceptance request contract

The existing flat request remains:

```text
aquantai.industry-thesis-owner-acceptance-plan.v1
```

No wrapper, duplicate request contract or browser-owned context is introduced.

## 5. Review input

V2 review adds:

```json
{
  "owner_context": {
    "industry_map_revision_id": "<exact UUID>"
  }
}
```

Rules:

- exactly one key is accepted;
- unknown keys fail;
- the client does not submit Case, Map, map mode, labels or dates as authority;
- the service resolves all derived fields from persisted foreign keys;
- v1 input is never silently promoted.

## 6. Exact option projection

Ordinary users select from persisted options rather than typing IDs.

Recommended route:

```text
GET /industry-analysis/api/session-revisions/{session_revision_id}/owner-context-options
    ?as_of_cutoff={date}
    &as_of_recorded_at_utc={explicit UTC}
    &cursor={optional stable cursor}
    &limit={1..100}
```

The route may be folded into an existing review projection if semantics and query ceilings stay identical.

Pagination contract:

```text
default limit = 25
maximum limit = 100
stable order = case_key ASC, map_key ASC, revision_no DESC, revision_id ASC
next cursor = opaque encoding of the final stable sort tuple
```

A local text filter may narrow exact persisted options for usability. It does not create identity or authority.

Each option contains ordinary labels and technical details:

```json
{
  "industry_map_revision_id": "...",
  "ordinary_label": "研究案例 · 产业地图 · 第 N 版",
  "case_key": "...",
  "map_key": "...",
  "revision_number": 3,
  "title": "...",
  "scope": "...",
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

1. exact Map Revision exists;
2. exact parent Map exists;
3. exact parent Research Case exists;
4. FK graph is complete;
5. Map Revision cutoff does not exceed the exact thesis cutoff;
6. Map Revision recorded time does not exceed the explicit review boundary;
7. data is local and persisted;
8. no company overlap, source match, maximum coverage, unique reachability, Provider or AI selection.

Every option requires explicit selection and confirmation. A single returned option is not silently accepted.

## 7. Server-resolved frozen object

The service resolves:

```text
IndustryMapRevision -> IndustryMap -> ResearchCase
```

and freezes canonical JSON:

```json
{
  "owner_context_contract_version": "aquantai.industry-thesis-owner-context.v1",
  "map_mode": "reuse_exact_existing_map_revision",
  "research_case_id": "<resolved UUID>",
  "industry_map_id": "<resolved UUID>",
  "industry_map_revision_id": "<submitted UUID>"
}
```

It rejects missing rows, FK mismatch, malformed IDs, unsupported versions/mode and chronology violations.

## 8. Deterministic identity and fingerprint binding

Owner Context changes accepted meaning and must be included in the review decision seed before deterministic IDs are generated.

V2 seed contains at least:

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

The normalized context participates in:

- reviewed session revision UUID seed;
- reviewed candidate revision UUID seeds;
- acceptance-plan fingerprint;
- reviewed session draft-graph input fingerprint;
- reviewed-plan query verification.

Same source, decisions and context are deterministic. Different Map Revisions produce different IDs and fingerprints.

## 9. V2 plan shape

The existing plan fields remain, with required:

```json
{
  "acceptance_plan_version": "aquantai.industry-thesis-acceptance-plan.v2",
  "owner_context": {
    "owner_context_contract_version": "aquantai.industry-thesis-owner-context.v1",
    "map_mode": "reuse_exact_existing_map_revision",
    "research_case_id": "...",
    "industry_map_id": "...",
    "industry_map_revision_id": "..."
  },
  "selected_candidates": [],
  "candidate_sources": [],
  "acceptance_plan_fingerprint_sha256": "..."
}
```

The plan fingerprint covers the context.

The plan recorded boundary is the maximum visible recorded time among:

- source thesis revision;
- exact candidate revisions used by review;
- selected Map Revision.

## 10. Reviewed-plan query verification

The query service verifies:

1. exact reviewed session revision and visibility;
2. workflow state `reviewed_plan_ready`;
3. canonical plan JSON;
4. plan fingerprint and reviewed-revision binding;
5. known plan version;
6. exact candidate universe and source fingerprints;
7. exact v2 Owner Context keys and versions;
8. exact Map Revision/Map/Case graph;
9. context chronology under plan and caller boundaries.

Generic history reads may return v1. Acceptance-capable callers require v2 unless servicing an already accepted exact idempotent replay.

Recommended projection:

```json
{
  "acceptance_capability": {
    "state": "ready" | "legacy_owner_context_missing",
    "reason_code": null | "industry_thesis_owner_context_required"
  }
}
```

## 11. Legacy v1 recovery

### Unaccepted v1 `reviewed_plan_ready`

It cannot enter owner acceptance, even if one same-stock context is reachable.

Primary action:

```text
重新审核并指定研究归属
```

Recovery is a bounded extension of the existing `review_candidates` command. No second command or workflow owner is introduced.

Locked preconditions:

- source is the exact latest `reviewed_plan_ready` v1 revision;
- no accepted output exists for that reviewed revision;
- complete latest candidate decisions are explicitly resubmitted;
- one exact context is selected and confirmed;
- one new v2 reviewed session revision and new reviewed candidate revisions are appended;
- v1 history remains immutable and reopenable;
- context participates in deterministic seeds and fingerprints;
- a v2 plan cannot use this legacy-upgrade path merely to change context without a separately valid new review revision.

### Already accepted v1 output

Exact accepted history remains readable.

Exact idempotent replay is required to return the original output with zero new writes when all of the following match stored accepted state:

- reviewed session revision;
- owner-acceptance plan fingerprint;
- reviewed-plan fingerprint;
- accepted Research Case;
- accepted Map;
- accepted Map Revision.

Conflicting replay remains blocked. No new context is selected.

## 12. Core enforcement

HTTP validation is not enough. The owner-acceptance core compares:

```text
submitted research_case_id == reviewed owner context research_case_id
submitted map_mode == reviewed owner context map_mode
submitted industry_map_id == reviewed owner context industry_map_id
submitted industry_map_revision_id == reviewed owner context industry_map_revision_id
```

Mismatch fails before Stage 1, semantics, pool or output writes.

Existing stable error families remain appropriate:

```text
INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED
INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH
INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_FINGERPRINT_MISMATCH
```

## 13. Acceptance workbench

New query direction:

```text
exact reviewed revision
  -> verified v2 plan
  -> frozen Owner Context
  -> exact header
  -> context-restricted Stage 1 rows for frozen stocks
  -> assertion/claim/semantic/pool options
```

Removed direction:

```text
frozen stocks -> all reachable Stage 1 contexts -> require one
```

Every Stage 1 identity/revision query includes exact Case, Map and selected Map Revision predicates. Same-stock rows outside the context are excluded.

A loaded-graph guard may assert that all loaded rows match the reviewed context. It may not discover context.

Existing budgets remain:

```text
owner-acceptance-view <= 14 SQL statements for 3 and 20 members
accepted-result-view <= 10 SQL statements
zero per-member HTTP calls
```

## 14. UI contract

### Review

Before review submission, show:

- Research Case label;
- Map title and scope;
- exact revision number;
- cutoff and local recorded date;
- warning that later acceptance is restricted to this version;
- technical IDs under progressive details;
- explicit confirmation.

Missing selection blocks review.

### Acceptance

The frozen context is displayed as non-editable reviewed authority. No alternate selector appears. Payload substitution fails closed while ordinary form values are preserved.

### Legacy result

A v1 unaccepted result has one dominant action to explicit v2 re-review. It never links directly to commit-capable acceptance.

## 15. State matrix

| Session state | Plan | Output | Behavior |
|---|---|---|---|
| candidate build / awaiting review | none | no | explicit review requires context |
| reviewed plan ready | v2 | no | acceptance allowed when prerequisites pass |
| reviewed plan ready | v1 | no | blocked; existing-command v2 re-review |
| accepted outputs linked | v1/v2 source | yes | exact result read; exact replay only |
| superseded/abandoned | any | any | no new acceptance |
| malformed graph | any | any | fail closed |

## 16. Chronology

Review-time rules:

```text
map revision cutoff <= exact thesis cutoff
map revision recorded time <= review operation recorded time
```

Read-time rules require reviewed revision, plan boundary and context to fit both caller as-of boundaries.

No latest Map Revision fallback is allowed.

Accepted v2 output Case/Map/Map Revision must equal the reviewed context.

## 17. Persistence and migration

```text
migration = none
new table = none
new database column = none
new ORM owner = none
backfill = none
history rewrite = none
browser-owned accepted context = none
```

Owner Context is stored inside existing canonical reviewed session plan JSON.

## 18. Rollback and downgrade

Before the first v2 write, code rollback is safe.

After any v2 reviewed plan exists, older acceptance code may ignore Owner Context and re-enable inference. Schema compatibility is therefore not downgrade safety.

```text
running pre-v2 acceptance code against a database containing v2 plans = prohibited
```

Safe recovery:

1. forward fix; or
2. stop the application and restore a verified pre-v2 database snapshot.

Future implementation must fail closed on unsupported plan versions and document this semantic downgrade boundary.

## 19. Production-realistic golden path

1. One exact candidate universe has three distinct valid company provenance references and exact frozen stocks.
2. Review projection returns exact paginated context options.
3. User selects and confirms one Map Revision.
4. Server resolves Map and Case and writes one v2 reviewed plan.
5. All candidates coexist without candidate-key changes.
6. Reopen verifies context graph and fingerprint.
7. Acceptance view loads only context-local owner options.
8. A reuses supported Stage 1 plus exact semantic revision.
9. B reuses/appends draft or disputed Stage 1.
10. C creates/appends supported Stage 1 from frozen stock fields with semantic `none`.
11. User selects one global supported handoff.
12. Preview returns complete `3`, supported `2`, stable fingerprint and zero writes.
13. Explicit commit creates one atomic accepted graph.
14. Exact result reopens all three members under both boundaries.
15. No automatic Company Research, Investment Candidate, recommendation, portfolio or trading state is created.

Zero-supported acceptance remains valid and still requires explicit context.

## 20. Decisive blocked path

Given a latest v1 reviewed plan, exact frozen stocks and exactly one reachable same-stock Stage 1 context:

```text
acceptance capability = blocked
reason = industry_thesis_owner_context_required
inferred context = none
preview fingerprint = none
writes = zero
primary action = explicit v2 re-review
```

This is the decisive proof that hidden inference is removed.

## 21. Required failure coverage

Future implementation must cover:

- missing/unknown/malformed context input;
- missing Map Revision, Map or Case;
- FK mismatch;
- later cutoff or recorded time;
- plan/context tampering;
- different contexts produce different deterministic IDs/fingerprints;
- submitted Case/Map/Revision/mode substitution;
- same-stock rows outside context excluded;
- only out-of-context reuse rows exist;
- legacy v1 unaccepted plan fail-closed;
- bounded existing-command v1→v2 re-review;
- exact accepted v1 read and idempotent replay;
- conflicting replay;
- query ceilings for 3 and 20 members;
- no schema/migration/network/Provider/AI path.

## 22. Future implementation scope

A separately authorized replacement Strict implementation may include:

```text
industry_alpha/industry_thesis_review.py
industry_alpha/industry_thesis_owner_acceptance.py
industry_alpha/industry_thesis_owner_acceptance_workbench.py
industry_alpha/industry_thesis_rules.py only for a required neutral constant/normalizer
backend/api/industry_analysis_review.py
backend/api/industry_analysis_acceptance.py
industry_analysis/static/review_result.html
industry_analysis/static/review_result.js
industry_analysis/static/owner_acceptance.html
industry_analysis/static/owner_acceptance.js
bounded shared presentation helpers
bounded review/acceptance tests and fixture demo
.github/workflows/local-tests.yml only to add the demo without weakening checks
docs/architecture_baseline.md only after accepted implementation evidence
```

No model, schema or migration file is expected.

## 23. Replacement implementation decision

PR #241 remains frozen at:

```text
3116a67ec472131eea3bf3d1bd9daee884c69ee9
```

It is not resumed, rebased, force-pushed or silently updated because its Issue and exact base do not authorize this reviewed-plan/core contract change.

After this architecture is accepted, merged and separately authorized:

```text
new Strict implementation Issue
  -> new branch from then-current exact main
  -> reapply only still-valid bounded PR #241 work
  -> add reviewed-plan v2 and core binding
  -> new Draft replacement implementation PR
```

PR #241 remains open until separate owner authorization to close it as superseded.

## 24. Locked exclusions

No candidate-key redesign, candidate source reinterpretation, migration, table/column, inferred backfill, history rewrite, fuzzy identity bridge, new Industry Map facts, Provider/network/credential/AI, automatic Company Research, Investment Candidate, ranking, recommendation, target price, expected return, position sizing, research holdings, portfolio, broker, order, trading, release, tag or project-version change.

## 25. Stop conditions

Stop if:

- exact options require inference;
- a database field or migration is required;
- candidate provenance must change;
- old history must be mutated/backfilled;
- the flat DTO must be weakened or duplicated;
- PR #241 must be resumed/rebased;
- old code must run after v2 writes;
- any prohibited scope appears.

## 26. Architecture PR validation

Required:

- exact base `41137ee6f017a781367b439f4119f201d05ce9cf`;
- exactly the task snapshot and this document changed;
- coherent Markdown and internal contract;
- no executable/schema/Provider/AI/release/version file change;
- repository CI success on one exact immutable HEAD;
- zero unresolved threads;
- fresh process-independent review containing exactly:

```text
AUTHORIZED OWNER CONTEXT REVIEWED-PLAN CONTRACT PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates prior CI and review evidence.

## 27. Completion boundary

Architecture approval does not authorize merge, Issue #242 closure, duplicate Issue #243 closure, PR #241 closure/merge, replacement implementation, release, tag, project-version change or a later roadmap phase. Every such action requires separate explicit owner authorization.
