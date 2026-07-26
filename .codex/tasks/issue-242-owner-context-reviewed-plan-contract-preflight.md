# Issue #242 Task Snapshot — Exact Owner Context in Reviewed Industry Thesis Plan

## Authority

- Architecture Issue: #242.
- Product Roadmap: #137.
- Accepted predecessors: #234/#235, #236/#237 and #238/#239.
- Paused implementation: Issue #240 / Draft PR #241.
- Frozen blocked implementation HEAD: `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.
- Owner authorization on 2026-07-26:

```text
Owner Context 合同架构预检
```

- Exact architecture base: `41137ee6f017a781367b439f4119f201d05ce9cf`.
- Branch: `arch/owner-context-reviewed-plan-contract`.
- Workflow: `.codex/WORKFLOW.md`.
- Risk: **Strict Architecture Preflight**.

## Authorized scope

Only:

```text
.codex/tasks/issue-242-owner-context-reviewed-plan-contract-preflight.md
docs/industry_thesis_owner_context_reviewed_plan_preflight.md
```

No production code, schema, migration, fixture, executable test, API, UI, Provider, network, credential, AI, release, tag, project-version change, merge, Issue closure or PR #241 resumption is authorized.

## Audit finding

The current reviewed plan freezes candidates, decisions, exact identities, candidate source kinds, source-reference fingerprints, chronology and one plan fingerprint. It does not freeze:

```text
research_case_id
industry_map_id
industry_map_revision_id
```

The ordinary-user workbench therefore still derives Owner Context from Stage 1 rows reachable by frozen stock IDs. A unique reachable context is still inference.

Candidate provenance cannot safely carry the missing authority:

- a shared `existing_industry_map_revision` reference collides under the current `source_kind + source_reference` candidate-key contract;
- `accepted_local_mapping` owns no accepted Case/Map/Map Revision semantics;
- arbitrary source-reference reinterpretation would be a hidden contract.

## Locked architecture decision

### Reviewed-plan versions

```text
historical read version = aquantai.industry-thesis-acceptance-plan.v1
active write version = aquantai.industry-thesis-acceptance-plan.v2
owner context version = aquantai.industry-thesis-owner-context.v1
```

Version 2 requires one exact top-level Owner Context.

### Review input

The review request submits only:

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
  "owner_context_contract_version": "aquantai.industry-thesis-owner-context.v1",
  "map_mode": "reuse_exact_existing_map_revision",
  "research_case_id": "<resolved UUID>",
  "industry_map_id": "<resolved UUID>",
  "industry_map_revision_id": "<submitted UUID>"
}
```

The client cannot submit Case or Map identities as authority.

### Explicit option projection

The future review surface returns exact cutoff-visible persisted Case/Map/Map Revision options. Options use stable cursor pagination with:

```text
default limit = 25
maximum limit = 100
stable order = case_key, map_key, revision_no DESC, revision_id
```

Text filtering may narrow already exact persisted options for usability, but never creates identity or context authority.

Every option requires explicit user selection and confirmation. No single-option hidden default is accepted.

### Fingerprints and deterministic IDs

The normalized resolved Owner Context participates in:

- review decision seed;
- deterministic reviewed session revision ID;
- deterministic reviewed candidate revision IDs;
- acceptance-plan fingerprint;
- reviewed session input fingerprint;
- reviewed-plan query verification.

Different exact contexts must produce different IDs and fingerprints.

### Candidate provenance

Do not change candidate source kinds, source-reference schemas, candidate-key calculation, duplicate-source protection or stock identity ownership.

Candidate provenance answers why a company was proposed. Owner Context answers where accepted owner operations occur.

### Acceptance enforcement

The workbench starts only from fingerprint-verified `reviewed_plan.owner_context` and restricts Stage 1 records to the exact Case/Map/Map Revision.

Frozen stocks are used only for exact member validation and context-local reuse/create/append options. Stock overlap, maximum coverage and unique reachability never select context.

The owner-acceptance core must reject any flat DTO Case/Map/Map Revision/map-mode value that differs from the frozen reviewed context. HTTP-only validation is insufficient.

The existing flat owner-acceptance DTO and `aquantai.industry-thesis-owner-acceptance-plan.v1` remain unchanged.

## Legacy behavior

### Unaccepted v1 reviewed plan

A v1 `reviewed_plan_ready` record without Owner Context fails closed for acceptance, even when exactly one same-stock Stage 1 context is reachable.

Recovery is locked to a bounded extension of the existing `review_candidates` command, not a second command owner:

- source must be the exact latest `reviewed_plan_ready` v1 revision;
- no accepted output may exist;
- complete latest candidate decisions must be explicitly resubmitted;
- one exact Owner Context must be explicitly selected;
- command writes one new v2 reviewed session revision and reviewed candidate revisions;
- old v1 history remains immutable and reopenable;
- v2-to-v2 context-only upgrade is rejected unless a separately valid review revision changes accepted meaning.

### Already accepted v1 output

Existing v1-sourced `accepted_outputs_linked` results remain exactly readable.

Exact idempotent replay is required to return the original accepted output with zero new writes when reviewed revision, owner-plan fingerprint, reviewed-plan fingerprint and accepted Case/Map/Map Revision all match. Conflicting replay remains blocked.

## Chronology

At review time:

```text
map revision cutoff <= exact thesis cutoff
map revision recorded time <= review operation recorded time
```

The v2 plan recorded boundary is the maximum visible recorded time across the source thesis revision, reviewed candidate source revisions and selected Map Revision.

At read time, the reviewed revision, plan boundary and exact context must all be visible under both caller boundaries. No latest fallback is permitted.

## Persistence and downgrade

```text
migration = none
new table = none
new database column = none
backfill = none
history rewrite = none
browser-owned accepted context = none
```

The context is stored in the existing canonical reviewed session plan JSON.

Before the first v2 write, code rollback is safe. After any v2 reviewed plan exists, pre-v2 acceptance code is semantically unsafe because it may ignore the context and re-enable inference.

```text
post-v2 downgrade = prohibited
safe recovery = forward fix or restore verified pre-v2 database snapshot
```

## Golden path

1. Three candidates retain distinct valid existing provenance references.
2. Review view returns exact paginated Owner Context options.
3. User explicitly selects one Map Revision.
4. Review resolves Case/Map and writes one v2 plan.
5. All three candidates coexist without candidate-key changes.
6. Acceptance view reads only the frozen context.
7. A reuses supported Stage 1 and exact semantic revision.
8. B reuses/appends draft or disputed Stage 1.
9. C creates/appends supported Stage 1 using exact frozen stock fields.
10. Preview returns complete `3`, supported `2`, stable fingerprint and zero writes.
11. Explicit commit creates one atomic exact output graph.
12. Exact result reopens all members.
13. No automatic Company Research, Investment Candidate, recommendation, portfolio or trading state is created.

A zero-supported path remains valid and still requires explicit context.

## Decisive blocked path

Given a legacy v1 reviewed plan and one reachable same-stock Stage 1 context:

```text
acceptance = blocked
inferred context = none
preview fingerprint = none
writes = zero
primary action = explicit v2 re-review
```

## Future implementation scope

A separately authorized replacement Strict implementation may include bounded changes to:

```text
industry_alpha/industry_thesis_review.py
industry_alpha/industry_thesis_owner_acceptance.py
industry_alpha/industry_thesis_owner_acceptance_workbench.py
industry_alpha/industry_thesis_rules.py only for a required neutral shared constant/normalizer
backend/api/industry_analysis_review.py
backend/api/industry_analysis_acceptance.py
industry_analysis/static/review_result.html
industry_analysis/static/review_result.js
industry_analysis/static/owner_acceptance.html
industry_analysis/static/owner_acceptance.js
bounded related tests and fixture demo
.github/workflows/local-tests.yml only to add the demo without weakening checks
```

No model, schema or migration file is expected.

## Replacement implementation decision

PR #241 remains frozen, Draft and unmerged. It is not resumed, rebased, force-pushed or silently updated.

After architecture merge and separate owner authorization:

1. create a new Strict implementation Issue;
2. create a new branch from then-current exact `main`;
3. reapply only still-valid bounded PR #241 work;
4. implement reviewed-plan v2 and core context binding;
5. open one new Draft replacement implementation PR;
6. leave PR #241 open until the owner separately authorizes closure as superseded.

## Required future tests

At minimum:

- exact paginated context options and explicit confirmation;
- strict input and unknown-field rejection;
- server-only Case/Map resolution;
- v2 schema/version enforcement;
- context included in deterministic IDs and fingerprints;
- different contexts produce different IDs/fingerprints;
- candidate provenance unchanged;
- three candidates share one global context without collision;
- legacy v1 unaccepted plan fails closed despite one reachable context;
- bounded existing-command v1→v2 re-review;
- exact v1 accepted-result read and idempotent replay;
- context substitution rejected in core and HTTP layers;
- missing/corrupt/later Map/Case graph fails closed;
- workbench excludes same-stock rows outside frozen context;
- golden and zero-supported paths;
- preview zero writes, atomic commit and conflict behavior;
- query ceilings retained;
- no migration, network, Provider, credential or AI path;
- no recommendation, target price, expected return, portfolio or trading language;
- complete regression and all configured offline demos.

## Locked exclusions and stop conditions

No candidate-key redesign, source reinterpretation, migration, table/column, inferred backfill, fuzzy identity bridge, new Industry Map facts, Provider/network/AI, automatic Company Research, Investment Candidate, ranking, recommendation, target price, expected return, position sizing, portfolio, broker, order, trading, release, tag or version change.

Stop if exact options require inference, a database field is required, old history must be rewritten, the flat DTO must be weakened/duplicated, PR #241 must be resumed/rebased, or any prohibited scope appears.

## Delivery gates

- exact base `41137ee6f017a781367b439f4119f201d05ce9cf`;
- exactly the two authorized documentation files;
- Draft PR linked to #242, #137, #238/#239 and #240/#241;
- exact immutable HEAD CI success;
- zero unresolved threads;
- process-independent review containing exactly:

```text
AUTHORIZED OWNER CONTEXT REVIEWED-PLAN CONTRACT PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

- separate owner authorization before merge.

Architecture approval does not authorize merge, Issue closure, duplicate Issue closure, PR #241 closure, production implementation, release, tag, version change or a later roadmap phase.
