# Issue #242 Task Snapshot — Exact Owner Context in Reviewed Industry Thesis Plan

## Authority

- Authoritative Architecture Preflight Issue: #242.
- Product Roadmap: #137.
- Accepted Industry Thesis owner-acceptance architecture and implementation: #234/#235 and #236/#237.
- Accepted ordinary-user completion architecture: #238 / merged PR #239.
- Paused ordinary-user implementation: Issue #240 / Draft PR #241.
- Blocked implementation HEAD: `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.
- Project-owner authorization on 2026-07-26:

```text
Owner Context 合同架构预检
```

- Exact architecture base at branch creation: `41137ee6f017a781367b439f4119f201d05ce9cf`.
- Branch: `arch/owner-context-reviewed-plan-contract`.
- Workflow authority: `.codex/WORKFLOW.md`.
- Risk tier: **Strict Architecture Preflight** because this changes a frozen reviewed-plan contract and cross-domain acceptance authority.

## Phase boundary

This task is architecture-only.

Authorized files:

```text
.codex/tasks/issue-242-owner-context-reviewed-plan-contract-preflight.md
docs/industry_thesis_owner_context_reviewed_plan_preflight.md
```

No production code, schema, migration, fixture, executable test, API, UI, dependency, Provider, credential, network access, AI call, release, tag, version change, merge, Issue closure or resumption of PR #241 is authorized.

## Audit finding

The existing reviewed acceptance plan freezes:

- session and candidate revisions;
- selected/rejected/unresolved decisions;
- exact stock/listed-instrument identity references;
- candidate source kinds;
- candidate source-reference fingerprints;
- information and recorded-time boundaries;
- one deterministic plan fingerprint.

It does not freeze:

```text
research_case_id
industry_map_id
industry_map_revision_id
```

The ordinary-user workbench currently derives that context from Stage 1 rows reachable by frozen stock IDs. A unique reachable context remains inference rather than reviewed authority.

The source-only alternatives are invalid:

1. `existing_industry_map_revision` can carry the exact revision, but multiple companies referencing the same source produce the same candidate key because candidate identity is based on `source_kind + source_reference`.
2. `accepted_local_mapping` can distinguish companies, but its accepted source contract owns no Case/Map/Map Revision semantics.
3. Reinterpreting arbitrary source-reference keys would create a hidden unreviewed contract.

## Objective

Define the smallest deterministic reviewed-plan contract that freezes one exact Owner Context at explicit review time and makes it the only authority for later owner acceptance:

```text
exact review context selection
  -> server resolves Map Revision -> Map -> Research Case
  -> reviewed plan v2 freezes and fingerprints exact Owner Context
  -> acceptance workbench queries only that exact context
  -> core rejects any submitted context substitution
```

## Locked architecture direction

### 1. Top-level review authority

Owner Context is a top-level reviewed-plan authority, separate from candidate provenance.

Review input carries only:

```json
{
  "owner_context": {
    "industry_map_revision_id": "<exact UUID>"
  }
}
```

The server resolves and freezes:

```json
{
  "owner_context": {
    "owner_context_contract_version": "aquantai.industry-thesis-owner-context.v1",
    "map_mode": "reuse_exact_existing_map_revision",
    "research_case_id": "<resolved UUID>",
    "industry_map_id": "<resolved UUID>",
    "industry_map_revision_id": "<submitted exact UUID>"
  }
}
```

The client does not submit Case or Map identities.

### 2. Reviewed-plan version

The new active write contract is:

```text
aquantai.industry-thesis-acceptance-plan.v2
```

Version 2 requires exact `owner_context`.

Version 1 remains historical and readable but is not eligible for a new owner-acceptance write unless it already has an accepted output and the request is an exact idempotent replay.

### 3. Deterministic identity and fingerprint binding

The normalized resolved Owner Context must participate in:

- review decision seed;
- deterministic reviewed session revision ID;
- deterministic reviewed candidate revision IDs;
- acceptance-plan fingerprint;
- reviewed session `draft_graph_json` input fingerprint;
- later reviewed-plan query verification.

Two otherwise identical reviews using different Map Revisions must produce different reviewed identities and fingerprints.

### 4. Candidate provenance remains unchanged

Do not change:

- candidate source kinds;
- candidate source-reference schemas;
- candidate-key calculation;
- duplicate-source protection;
- stock identity ownership.

Candidate provenance explains why a company was proposed. Owner Context explains where accepted Stage 1 owner operations occur. These meanings remain separate.

### 5. Context options are exact persisted records

The future review surface must return bounded exact Owner Context options from persisted visible records:

```text
ResearchCase
  -> IndustryMap
  -> IndustryMapRevision
```

Eligibility:

- Map Revision exists;
- Map and Case foreign-key graph is complete;
- `information_cutoff_date <= exact thesis cutoff`;
- `recorded_at_utc <= explicit review recorded boundary`;
- no rejected/deleted/fuzzy/Provider-derived option;
- every option includes ordinary labels plus technical IDs under progressive details.

No option is selected by company overlap, candidate source, name similarity, ticker, maximum coverage, unique reachability, Provider output or AI.

The ordinary user must explicitly select and confirm one option. No hidden default is accepted.

### 6. Acceptance workbench and core enforcement

The workbench must start from fingerprint-verified `reviewed_plan.owner_context` and restrict every Stage 1 query to:

```text
case_id == reviewed owner context case
map_id == reviewed owner context map
selected_map_revision_id == reviewed owner context revision
```

Frozen stock IDs are used only to:

- confirm exact selected member identity;
- find exact reuse/append options inside the reviewed context;
- populate exact create source/code;
- reject duplicate or mismatched owner bindings.

The owner-acceptance core must compare the submitted flat DTO fields against the frozen reviewed context. HTTP validation alone is insufficient.

### 7. Existing flat owner-acceptance DTO remains unchanged

The accepted core DTO continues to contain:

```text
research_case_id
map_mode
industry_map_id
industry_map_revision_id
```

The values must come only from the reviewed plan. The UI may not edit them, and every caller is rejected on substitution.

The existing owner-acceptance plan version and output-link schema remain unchanged unless implementation proves a separate version is strictly necessary. No wrapper or parallel DTO is introduced.

### 8. Legacy behavior

#### Unaccepted v1 reviewed plan

A `reviewed_plan_ready` v1 plan without Owner Context fails closed for owner acceptance.

Recovery is an explicit re-review that appends a new v2 reviewed session/candidate revision from the exact latest candidate universe and explicit context selection. No backfill or mutation of old history is allowed.

#### Already accepted v1 output

Existing `accepted_outputs_linked` history remains readable through exact output links.

An exact idempotent replay may return the existing output only when all stored fingerprints and accepted map identities match. It must not create new owner writes or select a new context.

### 9. Migration and persistence

```text
schema migration = none
new table = none
new database column = none
history rewrite = none
backfill = none
new browser-local accepted identity = none
```

The new plan object is persisted inside the existing canonical session revision JSON and included in existing fingerprints.

### 10. Downgrade boundary

Before any v2 reviewed plan is written, code rollback is safe.

After a v2 reviewed plan exists, running an older adapter that ignores `owner_context` is semantically unsafe because it could re-enable context inference. Required operational rule:

```text
post-v2 downgrade = prohibited
safe recovery = forward fix or restore a pre-v2 database snapshot
```

The future implementation and release notes must state this semantic downgrade boundary even though no schema migration exists.

## Golden path

One production-realistic offline path must prove:

1. One exact session and candidate universe exist.
2. Three company candidates retain distinct existing candidate source references.
3. The review view lists one exact eligible Research Case / Map / Map Revision option.
4. The user explicitly selects and confirms that Map Revision.
5. Review appends a v2 reviewed plan containing one resolved Owner Context.
6. All three selected candidates coexist without candidate-key collision.
7. Acceptance view reads only Stage 1 records from the frozen context.
8. Company A reuses supported Stage 1 and exact semantic revision.
9. Company B reuses/appends draft or disputed Stage 1.
10. Company C creates/appends supported Stage 1 using the frozen stock source/code.
11. Preview produces complete count `3`, supported count `2` and a stable fingerprint with zero writes.
12. Explicit commit creates one atomic exact output graph.
13. Exact accepted result reopens all three members.
14. No Company Research, Investment Candidate, recommendation, portfolio or trading state is created.

A separate zero-supported path remains valid.

## Primary failure path

A legacy v1 reviewed plan has one same-stock Stage 1 context reachable in the database but no frozen reviewed Owner Context.

Required result:

- acceptance view fails closed;
- no context is inferred;
- no preview fingerprint is returned;
- no owner/session/pool/output write occurs;
- ordinary recovery returns to explicit re-review and context selection;
- old reviewed history remains reopenable.

## Required future implementation files

A separately authorized replacement Strict implementation may include bounded changes to:

```text
industry_alpha/industry_thesis_review.py
industry_alpha/industry_thesis_owner_acceptance.py
industry_alpha/industry_thesis_owner_acceptance_workbench.py
industry_alpha/industry_thesis_rules.py only if a neutral shared constant/normalizer is required
backend/api/industry_analysis_review.py
backend/api/industry_analysis_acceptance.py
industry_analysis/static/review_result.html
industry_analysis/static/review_result.js
industry_analysis/static/owner_acceptance.html
industry_analysis/static/owner_acceptance.js
bounded review/acceptance tests
scripts/run_industry_thesis_ordinary_user_acceptance_fixture.py
.github/workflows/local-tests.yml only when adding the required offline demo without weakening checks
```

No model, schema or migration file is expected.

## Implementation-branch decision

PR #241 must remain frozen and unmerged. It must not be resumed on its old exact base because the required reviewed-plan contract and implementation file families were not authorized by Issue #240.

After this architecture is merged and the owner separately authorizes implementation:

1. create a new Strict implementation Issue;
2. create a new branch from the then-current exact `main`;
3. reapply only the still-valid bounded ordinary-user work from PR #241;
4. add the v2 review/context contract and core enforcement;
5. open one new Draft replacement implementation PR;
6. keep PR #241 open or close it only under separate explicit owner authorization.

No rebase, force-push, silent base update or direct merge from PR #241 is allowed.

## Required validation for future implementation

At minimum:

- exact review-context option query and explicit selection;
- strict review input unknown-field rejection;
- server-only Case/Map resolution;
- v2 plan schema and version enforcement;
- Owner Context in deterministic review ID seed and fingerprints;
- different contexts produce different IDs/fingerprints;
- candidate source semantics and candidate keys remain unchanged;
- three candidates using one global context coexist;
- old v1 unaccepted plan fails closed even with one reachable Stage 1 context;
- exact v1 accepted-result reopening;
- exact idempotent v1 replay if preserved;
- context substitution rejected in core and HTTP layers;
- Map/Case FK mismatch and missing rows fail closed;
- information-cutoff and recorded-time violations fail closed;
- workbench queries only the frozen exact context;
- golden and zero-supported paths;
- preview zero writes and atomic commit;
- query ceilings retained;
- no migration/new persistence;
- zero network, Provider, credential and AI paths;
- no recommendation, target price, expected return, portfolio or trading language;
- complete repository regression and all configured offline demos.

## Locked exclusions

No candidate-key redesign, candidate source reinterpretation, schema migration, new table/column, inferred legacy backfill, fuzzy identity bridge, new Industry Map facts, Provider/network access, AI call, automatic Company Research, Investment Candidate, ranking, recommendation, target price, expected return, position sizing, research holdings, portfolio, broker, order, trading, release, tag or version change.

## Stop conditions

Stop and return for project-owner review if:

- exact context options cannot be produced from persisted records without inference;
- a migration or new database column is required;
- candidate provenance semantics must be modified;
- old reviewed history must be rewritten;
- the existing flat owner-acceptance DTO must be weakened or duplicated;
- safe implementation requires resuming or rebasing PR #241;
- any Provider/network/AI/recommendation/portfolio/trading scope appears.

## Delivery gates

1. Documentation-only diff from exact base `41137ee6f017a781367b439f4119f201d05ce9cf`.
2. One task snapshot and one focused architecture document.
3. One Draft architecture PR linked to #242, #137, #238/#239 and #240/#241.
4. Complete base-to-head inventory limited to the two authorized files.
5. Documentation/repository CI passes at one exact immutable HEAD.
6. Fresh process-independent fixed-head architecture review contains exactly:

```text
AUTHORIZED OWNER CONTEXT REVIEWED-PLAN CONTRACT PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

7. Zero unresolved review threads.
8. Separate explicit project-owner authorization before merge.
9. Any new commit invalidates prior exact-head CI and review evidence.

## Completion boundary

Architecture approval does not authorize merge, Issue closure, duplicate Issue closure, PR #241 closure, production implementation, resuming PR #241, release, tag, version change or a later roadmap phase.
