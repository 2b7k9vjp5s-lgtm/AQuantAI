# Issue #245 Task Snapshot — Owner Context v2 Replacement

## Authority

- Implementation Issue: #245.
- Product Roadmap: #137.
- Accepted architecture: Issue #242 / merged PR #244.
- Exact architecture HEAD: `8f5fea30577979bf5df3ee1b92ee84aad73b9a15`.
- Exact implementation base: `fd44ab1cb72b37c60f5958494b6b71e50d1dc074`.
- Frozen predecessor implementation: Issue #240 / Draft PR #241 at `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.
- Branch: `feat/owner-context-v2-replacement`.
- Workflow: `.codex/WORKFLOW.md`.
- Risk tier: **Strict Implementation**.

Project-owner authorization on 2026-07-26:

```text
批准启动 Owner Context v2 替代实现
```

## Objective

Implement reviewed-plan v2 with one explicit exact Owner Context and complete the ordinary-user acceptance/result path without same-stock context inference.

```text
explicit Map Revision review selection
  -> server-resolved Map and Research Case
  -> fingerprinted reviewed-plan v2
  -> exact context-bound acceptance view
  -> preview with zero writes
  -> explicit matching-fingerprint commit
  -> exact accepted-result reopening
```

## Locked contracts

```text
historical reviewed plan = aquantai.industry-thesis-acceptance-plan.v1
active reviewed plan = aquantai.industry-thesis-acceptance-plan.v2
Owner Context = aquantai.industry-thesis-owner-context.v1
owner-acceptance flat DTO = unchanged
migration/table/column/backfill/history rewrite = none
```

- Review input submits only exact `industry_map_revision_id` inside strict `owner_context`.
- Server resolves `IndustryMapRevision -> IndustryMap -> ResearchCase`.
- Owner Context participates in deterministic reviewed IDs, plan fingerprints and chronology.
- Candidate source/reference/key semantics remain unchanged.
- HTTP and core reject Case/Map/Revision/mode substitution before writes.
- Workbench queries only the exact reviewed context.
- V1 unaccepted reviewed plans fail closed and use explicit v2 re-review through the existing review command.
- Existing accepted v1 exact reads and idempotent replay remain available.
- PR #241 is read-only reference only; it is not rebased, resumed or merged.

## Authorized files

Use only the file families listed in Issue #245. No model, schema or migration file may change.

## Implementation sequence

1. Add strict Owner Context constants/normalization only where required.
2. Add exact context option projection and strict review input.
3. Write and verify reviewed-plan v2.
4. Bind context in deterministic seeds/fingerprints and chronology.
5. Add v1 fail-closed and explicit re-review behavior.
6. Enforce reviewed context in owner-acceptance core.
7. Build context-bound acceptance workbench.
8. Reapply only still-valid ordinary-user API/UI/result changes from PR #241.
9. Add three-company and zero-supported production-realistic fixture paths.
10. Run focused tests, full regression and all offline demos on one immutable HEAD.

## Decisive blocked path

Given a v1 `reviewed_plan_ready` revision and exactly one same-stock reachable Stage 1 context:

```text
acceptance capability = blocked
context inferred = none
preview fingerprint = none
writes = zero
primary action = explicit v2 re-review
```

## Required validation

- explicit exact context options and confirmation;
- strict request/unknown-field rejection;
- server-only Case/Map resolution;
- v2 plan schema, deterministic IDs and fingerprint binding;
- different contexts produce different IDs/fingerprints;
- candidate semantics unchanged;
- three candidates coexist under one context;
- v1 fail closed and bounded v2 re-review;
- accepted v1 read/idempotent replay;
- core and HTTP substitution rejection;
- graph and dual-as-of failure coverage;
- out-of-context same-stock rows excluded;
- Stage 1/semantic/pool modes and exact result/history behavior;
- preview zero writes, atomic commit and replay/conflict;
- query ceilings;
- zero migration/network/Provider/AI;
- no recommendation, portfolio or trading semantics;
- full repository pytest and every configured offline demo.

## Delivery gates

- one Draft replacement PR linked to #245, #242/#244, #240/#241 and #137;
- complete inventory inside authorized file families;
- exact fixed-HEAD CI success;
- zero unresolved threads;
- fresh process-independent review containing exactly:

```text
AUTHORIZED OWNER CONTEXT V2 REPLACEMENT IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

Merge, Issue closure, PR #241 closure, release, tag and version change require separate explicit project-owner authorization.