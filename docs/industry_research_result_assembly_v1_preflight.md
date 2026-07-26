# Industry Research Result Assembly and Exact Candidate Overlay v1 — Architecture Preflight

## 1. Status and authority

This document is the Strict Architecture Preflight for Issue #247.

- Product Roadmap: #137.
- Exact base: `2c432d1676146d5dd168907419fe2160f447e50c`.
- Accepted Owner Context v2 replacement: Issue #245 / merged PR #246.
- Accepted Industry Thesis owner-acceptance core: Issues #234/#236 and merged PRs #235/#237.
- Accepted Investment Candidate Intelligence: Issues #179/#181 and merged PRs #180/#182.
- Accepted Personal Research Workbench UI: Issues #215/#217 and merged PRs #216/#218.
- Frozen superseded PR: #241 at `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.
- THS live source remains separately blocked by Issue #225.
- Workflow: `.codex/WORKFLOW.md`.
- Risk: **Strict Architecture Preflight**.

Project-owner authorization on 2026-07-26:

```text
继续进行下一步开发
```

This preflight changes no executable contract. It defines how existing exact accepted/read-only owners may be composed for an ordinary-user result surface.

## 2. Product problem

PR #246 closes the write-capable path from one exact reviewed plan to one exact accepted output graph. The runtime can now preserve:

- exact accepted Research Case;
- exact accepted Industry Map Revision;
- complete ordered accepted beneficiary revisions;
- supported-only candidate-pool handoff;
- exact semantic reuse where selected;
- accepted-result and readiness reads;
- exact history reopening.

The existing accepted-result page is intentionally narrow. It does not yet answer the ordinary user’s complete post-research questions:

- What was accepted?
- What is the exact industry-chain context?
- Which companies remain in the complete beneficiary universe?
- Which research materials are present or missing?
- Has the user separately created a current Investment Candidate snapshot for this exact pool?
- What are the current priority/watch/verification states, and why?

The product already has an Investment Candidate owner with exact snapshots and transparent reasons. The missing capability is composition, not another score or accepted owner.

## 3. Existing authoritative owners

### 3.1 Accepted Industry Thesis output

`IndustryThesisAcceptedOutputQueryService` owns exact accepted output verification.

The exact output link freezes:

```text
reviewed_session_revision_id
accepted_session_revision_id
research_case_id
accepted_industry_map_identity_id
accepted_industry_map_revision_id
optional accepted_candidate_pool_revision_id
ordered beneficiary revision IDs
ordered owner-output bindings
reviewed-plan fingerprint
owner-acceptance fingerprint
owner transaction ID
information cutoff
recorded UTC
```

`get_result()` owns the complete accepted member projection. `get_readiness()` owns explicit readiness and missing-state projection. These reads do not compute candidate scores or create downstream state.

### 3.2 Industry Map

The existing Industry Map owner owns exact map identities, revisions, revision memberships, nodes, relationships and observations. A result assembler may query the accepted exact Map Revision under the caller’s dual-as-of boundaries. It cannot select another revision or infer facts from thesis text.

### 3.3 Stage 1 and Typed Beneficiary Semantics

The accepted output freezes exact beneficiary revisions and optional exact semantic profile revisions. Their status and absence remain authoritative. A read surface cannot remap legacy classification into typed semantics.

### 3.4 Company Research

Accepted readiness already determines whether exact compatible Company Research exists for the frozen beneficiary and candidate-pool context. An exact selected Investment Candidate snapshot may freeze a Company Research Revision for a member. These are separate facts:

- readiness says whether research is available for later handoff;
- a candidate snapshot freezes the exact revision used by that snapshot.

The result assembler must not replace one with the other or choose a newer revision.

### 3.5 Investment Candidate Intelligence

`InvestmentCandidateQueryService.get_snapshot_revision()` owns exact snapshot output for one supplied revision ID and explicit dual-as-of boundaries.

The snapshot freezes:

```text
candidate_pool_revision_id
purpose_code
rule_version
complete members
candidate status
priority ordinal
reason codes
component revisions
verification states
falsification states
Company Research revision links
Typed Beneficiary revision links
Canonical Price revision links
Comparison Eligibility revision links
```

The assembler is a reader only. It does not own score calculation, status precedence, reason semantics, verification meaning or snapshot selection.

## 4. Core architecture decision

The ordinary result has two visibly separate layers.

### Layer A — Accepted research snapshot

Authority:

```text
one exact IndustryThesisOutputLinkRevision
```

Meaning:

> This is the immutable research result the user explicitly accepted at the recorded boundary.

It includes the complete accepted beneficiary universe and accepted handoff/readiness state. It is the stable historical record.

### Layer B — Current candidate overlay

Authority:

```text
zero or one explicitly selected exact InvestmentCandidateSnapshotRevision
```

Meaning:

> This is a separately recorded candidate-priority snapshot selected for comparison with the accepted research result.

It is not written into Layer A. It may be recorded after acceptance. Its own cutoff, recorded time, rule version and exact revision remain visible.

### Prohibited collapsed meaning

The page must never imply:

- candidate status was part of the accepted output when it was not;
- a newer candidate snapshot rewrote accepted history;
- missing candidate state means a negative recommendation;
- the accepted result is incomplete because no candidate snapshot was selected;
- candidate highlights are the complete beneficiary universe.

## 5. Route and selector contract

### 5.1 Canonical selectors

A future page/API must own or receive exactly:

```text
session_id
accepted_session_revision_id or output_link_revision_id
as_of_cutoff
as_of_recorded_at_utc
optional investment_candidate_snapshot_revision_id
```

The accepted-output revision remains the canonical graph authority. A session/accepted-revision route may server-resolve its one exact output link using existing accepted graph validation; it may not select among ambiguous links.

### 5.2 Reproducible navigation

The URL or equivalent explicit navigation state must preserve:

```text
accepted output identity
selected candidate snapshot identity, when present
information cutoff
recorded UTC
```

Reloading never changes the selected snapshot.

### 5.3 No automatic snapshot selection

Prohibited selectors include:

- latest snapshot;
- newest visible snapshot;
- first option;
- only reachable snapshot;
- closest recorded time;
- maximum member overlap;
- same stock codes;
- matching company names;
- matching Provider/source;
- same rule version without exact revision identity.

Even one eligible option requires explicit selection.

## 6. Candidate overlay eligibility

An exact candidate snapshot is eligible only when all conditions hold:

```text
accepted_output.accepted_candidate_pool_revision_id is not null
snapshot.candidate_pool_revision_id
  == accepted_output.accepted_candidate_pool_revision_id
snapshot visible at as_of_cutoff
snapshot visible at as_of_recorded_at_utc
snapshot purpose_code is supported by existing candidate owner
snapshot rule_version is displayable without reinterpretation
```

Complete-universe equality is not recalculated by the assembler as a competing owner. The Investment Candidate snapshot owner already validates exact persisted pool membership when writing and verifies the exact snapshot graph when reading.

The assembler may verify that the returned snapshot still declares the exact accepted pool revision. It must fail closed if not.

## 7. Exact option projection

### 7.1 Need for a bounded option query

The current Investment Candidate query requires an exact snapshot revision ID. The ordinary page therefore needs a new read-only option projection restricted to one exact candidate-pool revision and caller boundaries.

The future implementation may add a bounded read-only query method/API because `.codex/WORKFLOW.md` classifies new read-only APIs over accepted models as Standard when no Strict trigger appears.

### 7.2 Stable ordering

Recommended deterministic order:

```text
recorded_at_utc DESC
information_cutoff_date DESC
revision_no DESC
snapshot_revision_id ASC
```

No ordering field creates selection authority.

### 7.3 Bounded pagination

Recommended contract:

```text
default limit = 20
maximum limit = 100
cursor = recorded_at_utc + information_cutoff_date + revision_no + snapshot_revision_id
```

The option label may include ordinary-language recorded date, cutoff date, rule version and status counts. Technical IDs remain progressive details.

### 7.4 Empty option state

```text
candidate_overlay_state = unavailable
reason = no_exact_snapshot_for_accepted_pool
```

This does not change accepted-result validity.

## 8. Read model

A future result assembly response should keep owner projections nested rather than flattening them into a new canonical contract.

Recommended shape:

```json
{
  "result_contract_version": "aquantai.industry-research-result-assembly.v1",
  "accepted_snapshot": {
    "output_link_revision_id": "<uuid>",
    "accepted_session_revision_id": "<uuid>",
    "research_case": {},
    "industry_map": {},
    "complete_members": [],
    "supported_handoff": {},
    "readiness": {},
    "information_cutoff_date": "YYYY-MM-DD",
    "recorded_at_utc": "...Z"
  },
  "candidate_overlay": {
    "state": "not_selected|unavailable|selected|blocked",
    "snapshot_revision_id": null,
    "snapshot": null,
    "blocked_reason": null
  },
  "conclusion_cards": [],
  "coverage_notice": "...",
  "writes_performed": false
}
```

The assembly contract is presentation/read semantics. It is not persisted accepted state.

## 9. Conclusion cards

The first screen should show 5–8 concise deterministic cards.

Allowed card families:

1. **研究范围** — exact Case and Map Revision label/scope.
2. **完整受益公司** — exact accepted member count.
3. **进入后续研究** — supported handoff count or zero-supported state.
4. **受益状态** — closed Stage 1 assessment-status counts.
5. **证据语义覆盖** — exact semantic available/missing/status counts.
6. **公司研究准备度** — ready/missing counts from accepted readiness.
7. **当前候选状态** — status counts only from selected exact candidate snapshot.
8. **最大缺口** — deterministic largest explicit readiness reason category, with stable tie break.
9. **覆盖边界** — accepted coverage notice.

Use at most eight cards. A card must disclose its source layer: accepted snapshot or current overlay.

### Stable tie break for largest missing category

If counts tie, use a closed reviewed ordering such as:

```text
typed_semantics_missing
company_research_missing
investment_candidate_not_created_by_acceptance
canonical_price_not_evaluated_by_acceptance
structured_valuation_not_evaluated_by_acceptance
other exact reason code lexicographically
```

This is presentation ordering, not evidence severity or investment priority.

### Prohibited cards

- invented core driver;
- generated industry stage;
- inferred value-pool movement;
- earnings forecast;
- expected upside;
- attractiveness rating;
- buy/sell/hold;
- target price;
- portfolio action.

Those require authoritative accepted inputs and separate governed owners.

## 10. Industry-chain context

The result may display:

- exact accepted Map title and scope;
- exact revision number and boundaries;
- exact revision-member nodes;
- exact revision-member relationships;
- exact revision-member observations;
- accepted assertion status and evidence/provenance links already owned by the map.

Rules:

- require exact revision membership;
- enforce both as-of boundaries;
- preserve rejected/missing states according to existing Map read contracts;
- deterministic ordering by existing position/key/revision identity;
- no latest revision fallback;
- no thesis-text extraction;
- no browser-generated chain facts;
- no AI completion.

## 11. Complete beneficiary presentation

The full list is the accepted snapshot’s ordered member list.

Every row should preserve:

- original reviewed company label;
- exact stock identity when available;
- reviewed proposal exposure;
- exact beneficiary kind and assessment status;
- rationale summary;
- exact semantic state or missing state;
- supported-handoff inclusion and reason;
- readiness reasons;
- selected candidate status/reasons only when exact overlay member matches the same beneficiary revision.

### Overlay join key

Use:

```text
beneficiary_revision_id
```

not stock code, beneficiary identity alone, company name or row position.

### Complete-universe protection

The accepted list remains the outer collection. Candidate snapshot members may enrich matching exact revisions, but they may not:

- remove accepted members;
- add members outside the accepted complete result;
- reorder accepted history as if the candidate priority were accepted order;
- conceal non-current or evidence-insufficient members.

Candidate highlights may be a separate bounded section while the complete list remains visible below.

## 12. Candidate overlay presentation

When selected, the overlay may show:

- purpose and rule version;
- snapshot cutoff and recorded time;
- candidate-status counts;
- up to three existing `priority_candidate` / `watch_candidate` members ordered by persisted priority ordinal and existing exact tie behavior;
- every member’s status, reason codes and component states;
- verification questions/material flags;
- falsification state;
- exact downstream links.

The assembler does not recalculate final score or priority ordinal. It displays exact stored values.

### Missing values

Missing score, component, price, valuation or research state remains explicit. Never convert missing to zero, neutral or low priority.

## 13. Chronology

### Accepted snapshot chronology

The exact accepted output and all frozen members must be visible under:

```text
information_cutoff_date <= as_of_cutoff
recorded_at_utc <= as_of_recorded_at_utc
```

### Overlay chronology

The exact selected candidate snapshot and component revisions must also be visible under the same caller boundary.

The UI displays the overlay’s own cutoff and recorded time separately from acceptance time.

### Historical wording

Use:

- “已接受研究结果” for Layer A;
- “所选候选快照” or “当前选择的研究优先级快照” for Layer B.

Do not use “当时的候选结论” unless the selected snapshot’s recorded time is at or before accepted recorded time and the product explicitly chooses to present that historical relationship.

## 14. State matrix

| Accepted result | Accepted pool | Eligible snapshots | User selection | Result |
| --- | --- | --- | --- | --- |
| valid | null | none | none | complete result + `unavailable_zero_supported` |
| valid | exact pool | none | none | complete result + `unavailable` |
| valid | exact pool | one/many | none | complete result + `not_selected` |
| valid | exact pool | one/many | matching exact snapshot | complete result + selected overlay |
| valid | exact pool | one/many | snapshot from another pool | complete result + blocked overlay |
| invalid/corrupt | any | any | any | fail closed; no assembled result |

The accepted result is never hidden merely because the optional overlay is absent or invalid.

## 15. Error and recovery semantics

Recommended ordinary states:

```text
accepted_result_not_visible
accepted_result_graph_incomplete
candidate_snapshot_not_selected
candidate_snapshot_unavailable
candidate_snapshot_not_visible
candidate_snapshot_exact_pool_mismatch
candidate_snapshot_graph_incomplete
local_database_unavailable
```

Recovery actions:

- remove invalid overlay selector;
- return to stable eligible options;
- reopen exact accepted history;
- inspect technical details;
- fix local database/integrity issue.

No automatic retry, latest fallback or selector substitution.

## 16. Query architecture

The future implementation should compose existing batch-capable query owners and add only bounded exact option/map projections.

Performance targets:

- no per-member Company Research or candidate component query loop;
- fixed or bounded query count independent of accepted member count for overview/list projection;
- one 3-member production-realistic path;
- one 20-member query-ceiling path;
- candidate options bounded by pagination;
- technical detail expansion may use an explicit separate exact-ID request.

If existing owners force an N+1 result assembly, implementation may add domain-local batch read helpers without changing owner meaning. A generic cross-domain repository is not justified by this slice.

## 17. Persistence, rollback and downgrade

```text
schema change = none
migration = none
new accepted JSON field = none
history rewrite = none
backfill = none
selection database state = none
```

The architecture PR is documentation only and can be reverted without data impact.

A future Standard implementation can be rolled back safely because it adds read-only adapters and presentation. Accepted output and candidate snapshot data remain independently readable through existing exact-ID APIs.

If implementation discovers a need to persist selection or modify frozen output contracts, stop and open a new Strict architecture decision. Do not smuggle mutable overlay state into accepted history.

## 18. Security and network boundary

- local database reads only;
- no Provider/network access;
- no credentials;
- no startup refresh;
- no browser external request;
- no AI call;
- no hidden telemetry;
- no automatic downstream command.

Static tests must prohibit external URL fetch, WebSocket, EventSource and remote assets.

## 19. Future implementation classification

### Standard implementation is authorized as a candidate when

- new result and option APIs are read-only;
- models/schema are unchanged;
- existing exact query owners remain authoritative;
- candidate calculations are not changed;
- selectors are explicit;
- no accepted-state mutation;
- no Provider/network/AI;
- no recommendation/trading semantics.

### Return to Strict architecture when

- a new persisted selector or result snapshot is required;
- accepted output JSON/schema must change;
- candidate snapshot ownership or rules change;
- automatic latest or compatibility inference is proposed;
- a write command/recomputation is added;
- a cross-domain canonical contract changes;
- Provider/network/AI appears.

The expected outcome of this preflight is a later **Standard read-only implementation Issue/PR**, but that future Issue requires architecture merge and separate owner authorization.

## 20. Golden path

Fixture state:

- one exact Owner Context v2 accepted output;
- three accepted beneficiary revisions in deterministic order;
- A and B supported, C draft/disputed;
- exact supported candidate-pool revision contains A and B;
- A and B have exact semantics and Company Research;
- C exposes exact missing readiness;
- two candidate snapshot revisions exist for the same A/B pool;
- each candidate snapshot preserves the complete A/B pool and exact components.

Execution:

1. Open exact accepted result using explicit dual-as-of boundaries.
2. Verify all three accepted members and exact Map Revision.
3. Show deterministic accepted summary cards.
4. Query exact eligible candidate snapshot options for the accepted pool.
5. Show both options in stable order with no default selection.
6. User selects one exact snapshot revision.
7. Verify snapshot pool equals accepted pool.
8. Join overlay only by exact beneficiary revision IDs.
9. Highlight existing priority/watch members.
10. Keep C in complete accepted members with no fabricated candidate status.
11. Expose exact reasons, components, verification and downstream revision links.
12. Reopen the same URL and reproduce all values.
13. Assert zero writes and zero external network.

## 21. Decisive failure path

Fixture includes an exact candidate snapshot for another pool.

Request supplies that snapshot ID against the accepted output.

Expected:

```text
accepted_snapshot.state = readable
candidate_overlay.state = blocked
candidate_overlay.blocked_reason = exact_pool_mismatch
candidate_overlay.snapshot = null
fallback_snapshot = null
writes = zero
```

The page keeps the accepted conclusion, chain and complete beneficiary universe visible and explains how to remove the invalid selector or choose a valid exact option.

## 22. Required future tests

- exact accepted output/session/route ownership;
- strict dual-as-of boundaries;
- exact Map Revision membership and no latest fallback;
- candidate option stable ordering/cursor/limits;
- no one-option default;
- zero-supported pool state;
- no eligible snapshot state;
- explicit matching snapshot selection;
- exact pool mismatch while accepted result remains readable;
- snapshot not visible/corrupt failures;
- exact beneficiary-revision join;
- complete accepted universe preservation;
- persisted priority/status/reason/component display without recomputation;
- exact downstream links and missing links;
- deterministic conclusion counts/tie breaks;
- 3-member golden path;
- 20-member query ceiling;
- zero database writes;
- zero hidden network;
- history reopening and URL reproducibility;
- ordinary Chinese errors and progressive technical details;
- full relevant regression and offline demo.

## 23. Locked exclusions

No:

- Provider or live refresh;
- announcement/news/social acquisition;
- PDF import or OCR;
- evidence acceptance;
- map fact creation;
- Stage 1 authoring;
- semantic authoring;
- Company Research creation;
- candidate snapshot creation;
- component scoring or rule changes;
- automatic latest selection;
- recommendation, target price or expected return;
- position sizing, holdings, portfolio, broker, order or trading;
- release, tag or version change.

## 24. Stop conditions

Stop and return for project-owner review if:

- exact candidate snapshot options require fuzzy or hidden inference;
- accepted output must be mutated;
- a new field/table/migration is required;
- candidate scores/statuses must be recomputed;
- accepted and current meanings cannot be separated;
- exact map context cannot be rendered through accepted revision membership;
- PR #241 must be resumed/rebased/modified;
- any Provider/network/AI/trading path appears.

## 25. Delivery gates

Architecture PR must have:

- exact base `2c432d1676146d5dd168907419fe2160f447e50c`;
- exactly three authorized documentation files;
- no executable/dependency changes;
- Markdown and repository-link validation;
- no unresolved threads;
- fixed-head review containing exactly:

```text
AUTHORIZED INDUSTRY RESEARCH RESULT ASSEMBLY V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Architecture approval does not authorize merge. Merge requires separate explicit project-owner authorization. A future Standard implementation requires its own Issue/PR and separate authorization after architecture merge.