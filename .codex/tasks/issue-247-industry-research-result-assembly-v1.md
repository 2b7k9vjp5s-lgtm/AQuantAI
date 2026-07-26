# Issue #247 Task Snapshot — Industry Research Result Assembly v1

## Authority

- Architecture Issue: #247.
- Product Roadmap: #137.
- Exact architecture base: `2c432d1676146d5dd168907419fe2160f447e50c`.
- Merged Owner Context v2 replacement: Issue #245 / PR #246.
- Accepted Investment Candidate Intelligence: Issues #179/#181 and PRs #180/#182.
- Accepted Personal Research Workbench UI: Issues #215/#217 and PRs #216/#218.
- Frozen superseded implementation: Issue #240 / Draft PR #241 at `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.
- THS live acquisition gate: Issue #225, still blocked.
- Branch: `arch/industry-research-result-assembly-v1`.
- Workflow: `.codex/WORKFLOW.md`.
- Risk tier: **Strict Architecture Preflight**.

Project-owner instruction on 2026-07-26:

```text
继续进行下一步开发
```

## Authorized files

Only:

```text
.codex/tasks/issue-247-industry-research-result-assembly-v1.md
docs/industry_research_result_assembly_v1_preflight.md
docs/architecture_baseline.md
```

The baseline change is limited to correcting repository state after merged PR #246 and recording Issue #247 as the active architecture preflight. It must not claim this preflight is accepted before merge.

No production code, API, static UI, test, fixture, schema, migration, dependency, Provider, network, credential, AI, release, tag or version change is authorized.

## Objective

Define one ordinary-user read-only result composition after exact Owner Context v2 acceptance:

```text
exact accepted Industry Thesis output
  -> accepted conclusion and map context
  -> complete accepted beneficiary universe
  -> readiness and missing state
  -> optional explicit exact Investment Candidate snapshot overlay
  -> exact frozen downstream links
  -> reproducible exact reopening
```

The architecture must make an accepted industry analysis readable without automatically creating Company Research, candidate, valuation or recommendation state.

## Existing production owners

### Accepted research snapshot

`IndustryThesisAcceptedOutputQueryService` owns exact output/result/readiness reads for one `IndustryThesisOutputLinkRevision` under explicit information-cutoff and recorded-UTC boundaries.

It already exposes:

- reviewed and accepted session revisions;
- exact Research Case, Industry Map and Map Revision;
- ordered complete beneficiary revisions;
- supported handoff membership;
- exact semantic reuse when present;
- Company Research readiness and explicit missing states;
- zero ranking or candidate creation.

### Current candidate overlay

`InvestmentCandidateQueryService` owns exact reads for one `InvestmentCandidateSnapshotRevision`.

It already exposes:

- exact candidate-pool revision;
- complete member universe;
- existing candidate statuses and priority ordinal;
- exact component revisions and verification state;
- reason codes;
- exact Company Research, Typed Beneficiary, Canonical Price and Comparison Eligibility links when present;
- explicit dual-as-of chronology.

The result assembler may present these values but may not recompute, reinterpret or write them.

## Locked architecture decisions

### Two separate meanings

1. `accepted_research_snapshot` is immutable accepted history from one exact output-link revision.
2. `current_candidate_overlay` is optional presentation of one exact user-selected candidate snapshot.

The overlay is never written into accepted history and is never represented as having existed at acceptance time unless chronology explicitly proves it.

### Exact selectors

Required selectors:

```text
accepted_output_link_revision_id
as_of_cutoff
as_of_recorded_at_utc
optional investment_candidate_snapshot_revision_id
```

No automatic first/latest/newest/unique-reachable selection is permitted.

An overlay is eligible only when:

```text
snapshot.candidate_pool_revision_id
== accepted_output.accepted_candidate_pool_revision_id
```

and both records are visible under explicit boundaries.

### No-candidate-pool case

When accepted output has no supported handoff:

```text
accepted_candidate_pool_revision_id = null
candidate_overlay_state = unavailable_zero_supported
candidate_snapshot_options = []
```

The complete accepted result remains readable.

### No selected snapshot

When eligible snapshots exist but none is selected:

```text
candidate_overlay_state = not_selected
ranking_displayed = false
provisional_candidate_state = none
```

### Mismatch

When a supplied snapshot belongs to another exact pool:

```text
accepted_result = readable
candidate_overlay = blocked
fallback = none
writes = zero
```

### Conclusion summary

The future result may calculate bounded D1 counts from already verified exact rows:

- complete accepted member count;
- supported handoff count;
- Stage 1 assessment-status distribution;
- typed-semantics availability/status distribution;
- Company Research readiness coverage;
- candidate-status distribution only for a selected exact overlay;
- largest explicit missing-readiness category;
- coverage limitation.

It may not invent causal conclusions, forecasts, scores, recommendation language or ranking when those values are not owned by accepted records.

### Exact Industry Map context

Only the exact accepted Map Revision may be rendered. Nodes, relationships and observations must be cutoff-visible members of that revision. No newer Map Revision, free-text promotion or inferred chain element is permitted.

### Complete universe

All accepted beneficiary revisions remain visible regardless of:

- supported/draft/disputed state;
- missing typed semantics;
- missing Company Research;
- candidate status;
- demanding valuation;
- insufficient evidence.

Candidate highlights are an overlay, never a replacement universe.

### Candidate states

Reuse existing exact values only:

```text
priority_candidate
watch_candidate
awaiting_verification
pricing_demanding
evidence_insufficient
not_current_candidate
```

Reason codes, component verification, missing values and falsification state stay visible. No result-assembler rule may remap them.

### Exact downstream navigation

Navigation may use only exact revision IDs already returned by the selected snapshot or accepted readiness projection. Missing exact links remain unavailable. No compatible-looking latest fallback.

### Persistence decision

```text
new table = none
new column = none
migration = none
accepted output mutation = none
selection persistence = URL/presentation state only
candidate recomputation = none
```

### Future implementation risk

The future implementation is **Standard** only if it remains:

- read-only;
- over existing accepted models and query owners;
- explicit-selector based;
- network-free;
- non-AI;
- non-writing;
- non-recomputing;
- without ranking-rule or frozen-contract changes.

It becomes **Strict** and must return to architecture if any schema, owner write, hidden selector, candidate recomputation, accepted-history change or cross-domain contract modification is required.

## Production-realistic offline golden path

1. One accepted Owner Context v2 output freezes three beneficiary revisions and one supported candidate-pool revision.
2. Exact result displays all three members and exact Case/Map/Map Revision.
3. Readiness shows two members with semantics and Company Research and one explicit missing state.
4. Two Investment Candidate snapshot revisions exist for the same exact pool at different recorded times.
5. Eligible options are ordered deterministically and neither is automatically selected.
6. The user explicitly selects one snapshot revision.
7. Existing priority/watch/status/reason/component values are displayed while all three accepted members remain visible.
8. Reopening the same four selectors reproduces the same output.
9. No write, network call, AI call, candidate creation or score recomputation occurs.

## Decisive failure path

Given an otherwise valid snapshot revision whose exact candidate-pool revision differs:

```text
accepted result = success
candidate overlay = exact_pool_mismatch
fallback = none
write count = zero
```

The ordinary page explains the mismatch and offers only valid exact options or removal of the overlay selector.

## Required architecture validation

- branch starts at exact base `2c432d1676146d5dd168907419fe2160f447e50c`;
- exactly the three authorized documentation files change;
- no executable, dependency or configuration change;
- accepted snapshot and current overlay remain visibly separate;
- selectors and dual-as-of rules are explicit;
- zero-supported and no-selection states are complete;
- exact pool mismatch fails closed without hiding the accepted result;
- no schema, migration, Provider, network, AI, scoring or trading scope;
- zero unresolved review threads;
- fixed-head review contains exactly:

```text
AUTHORIZED INDUSTRY RESEARCH RESULT ASSEMBLY V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

## Locked exclusions

No Provider/live refresh, announcement acquisition, PDF import, evidence acceptance, Company Research creation, Investment Candidate snapshot creation, component scoring, score/rule changes, hidden latest selection, recommendation, target price, expected return, position sizing, holdings, portfolio, broker, order, trading, release, tag or version change.

## Stop conditions

Stop if:

- exact candidate options require inference;
- accepted output must be mutated;
- a persistent selector field is required;
- snapshot scores/statuses must be recomputed;
- current overlay and accepted historical meaning cannot be separated;
- PR #241 must be changed;
- Provider/network/AI/trading scope appears.

## Delivery gates

- one Draft architecture PR linked to #247, #137, #245/#246, #179/#180/#181/#182, #225 and #240/#241;
- exact fixed-HEAD validation;
- fixed-head architecture review;
- separate project-owner authorization before merge;
- separate future implementation Issue/PR after architecture merge and explicit authorization.