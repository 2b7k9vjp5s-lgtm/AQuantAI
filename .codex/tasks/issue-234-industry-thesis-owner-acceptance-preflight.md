# Issue #234 Task Snapshot — Industry Thesis Owner Acceptance and Exact Output Links v1

## Authority

- Authoritative Issue: #234.
- Product Roadmap: #137.
- Project-owner authorization: `P0-1 — 启动 Architecture Preflight：Industry Thesis Reviewed-Plan Owner Acceptance and Exact Output Links v1` on 2026-07-25.
- Exact required base: `ada017848c01d0bf4af64951f9215f97cf10e04b`.
- Repository workflow: `.codex/WORKFLOW.md`.
- Risk tier: **Strict Architecture Preflight**.

## Phase boundary

Architecture documentation only.

Authorized files:

```text
.codex/tasks/issue-234-industry-thesis-owner-acceptance-preflight.md
docs/industry_thesis_owner_acceptance_output_links_preflight.md
docs/architecture_baseline.md
```

No production Python, migration file, API/UI implementation, fixture, executable test, workflow, dependency, Provider, network, AI, release, tag or version change.

## Objective

Define one production-reachable offline transition:

```text
reviewed_plan_ready
  -> deterministic owner-acceptance preview
  -> one atomic existing-owner transaction
  -> accepted_outputs_linked
  -> exact output-link and complete-universe reads
```

The design must preserve the complete reviewed beneficiary universe while keeping supported-only Stage 2 handoff semantics separate.

## Current facts to reconcile

1. The reviewed plan freezes candidate decisions and identity references but not all Stage 1 owner fields.
2. Stage 1 requires exact `stock_basic`, legacy beneficiary kind, assessment status, map assertion revisions, claim revisions and rationale.
3. Listed-instrument-only identity cannot silently become Stage 1 identity.
4. Typed exposure cannot be inferred into legacy beneficiary kind.
5. Stage 1 candidate-pool membership permits only `supported` revisions.
6. A typed-semantic profile needs a complete explicit owner payload.
7. Current owner command services open independent transactions.
8. Output-link tables and `accepted_outputs_linked` exist, but no writer/query/API exists.
9. Current output-link rows cannot freeze optional per-candidate semantic output links.

## Required decisions

- v1 map mode is `reuse_exact_existing_map_revision` only;
- draft graph remains non-accepted orchestration state;
- one explicit owner binding is required for each selected candidate;
- new/appended Stage 1 writes require exact `stock_basic` identity;
- legacy and typed classifications remain separate explicit inputs;
- accepted complete universe contains draft/supported/disputed Stage 1 revisions;
- supported-only candidate-pool handoff is optional and may be absent;
- owner modules expose session-bound writers; coordinator owns the outer transaction;
- accepted session revision freezes the complete owner plan and result;
- output link freezes exact map, complete beneficiary revisions, optional pool and per-candidate owner bindings;
- Company Research and Investment Candidate writes remain outside the acceptance transaction;
- ordinary reads remain exact-ID, dual-as-of and network-free.

## Migration candidate

Candidate migration:

```text
20260725_0017_industry_thesis_owner_acceptance
```

Candidate changes:

- make `accepted_candidate_pool_revision_id` nullable;
- add strict `ordered_owner_output_bindings_json`;
- enforce one output link per accepted session revision;
- refuse upgrade if legacy output-link rows cannot be deterministically backfilled;
- refuse downgrade before losing populated v1 output-link state.

No migration is created or run by this architecture task.

## Golden path

One exact existing research case and map revision; three selected exact `stock_basic` candidates:

- A: supported Stage 1, included in supported handoff;
- B: draft/disputed Stage 1, preserved only in complete universe;
- C: supported Stage 1 with incomplete typed semantics or Company Research, included in handoff but readiness incomplete.

One transaction writes/reuses owner outputs, accepted session revision and exact output link. Reopening under both as-of boundaries reproduces all three members. No candidate value is invented.

Also prove an accepted complete universe with zero supported members and no candidate-pool revision.

## Primary failure path

A selected candidate is listed-instrument-only or lacks exact Stage 1 assertion/claim bindings.

Required behavior:

- preview returns a stable blocked reason;
- commit fails before writes;
- reviewed plan remains unchanged;
- no partial beneficiary, semantic, accepted session, pool or output link is created.

## Stop conditions

Stop implementation authorization if:

- free text or draft graph must become accepted map facts;
- coordinator must duplicate another owner's validation or ORM writes;
- exact Stage 1 identity/evidence bindings cannot be supplied;
- complete universe and supported handoff cannot be separated;
- zero-supported accepted output cannot be represented honestly;
- exact idempotency or bitemporal reads require hidden latest fallback;
- network, Provider, AI, recommendation, portfolio or trading behavior is introduced.

## Validation gate

Before architecture merge:

1. verify exact base `ada017848c01d0bf4af64951f9215f97cf10e04b`;
2. verify only the three authorized documentation files changed;
3. run repository CI on the exact final HEAD;
4. perform fresh process-independent fixed-head architecture review;
5. verify zero unresolved review threads;
6. record:

```text
AUTHORIZED INDUSTRY THESIS OWNER ACCEPTANCE AND OUTPUT LINKS PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

7. require separate explicit owner merge authorization.

Any new commit invalidates prior exact-head CI and review evidence.

## Completion boundary

Architecture approval does not authorize production implementation, migration application, API/UI integration, Issue closure, release, version change or the next roadmap phase.