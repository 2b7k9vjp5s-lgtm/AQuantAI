# Issue #206 — Personal Research Workbench UI Phase 1D

## Authority

- Roadmap: #137
- Accepted Industry Thesis architecture: Issue #192 / merged PR #193
- Completed review backend: Issue #196 / merged PR #197
- Approved UI Phase 1 architecture: Issue #198 / merged PR #199
- Completed UI Phase 1A–1C: Issues #200, #202, #204 / merged PRs #201, #203, #205
- Required base: `381e8b308195c5861ac404e412ae7b17bd41a77e`
- Risk: Strict implementation

## Objective

```text
exact complete candidate universe
  -> explicit selected / rejected / unresolved decision for every row
  -> deterministic dry-run reviewed-plan preview
  -> atomic append-only review commit
  -> reviewed_plan_ready session revision
  -> exact result page and history reopening
```

## Required behavior

- Preserve every exact latest candidate path, including duplicate companies from different sources.
- Map 纳入后续研究 / 暂不纳入 / 待确认 exactly to selected_for_acceptance / rejected_by_user / unresolved.
- Require one explicit decision, rationale and uncertainty state for every candidate.
- Require an exact accepted identity and explicit non-unknown final exposure for selected candidates.
- Submit the complete exact universe through `IndustryThesisProposalReviewService.review_candidates`.
- Provide dry-run and commit without automatic retry or rebase.
- Read the exact verified plan through `IndustryThesisReviewedPlanQueryService.get_reviewed_plan`.
- Add the exact result page and exact history reopening link.
- State that the plan is orchestration state only and has not written formal Industry Map, Stage 1 or Investment Candidate outputs.

## Safety boundaries

- No owner acceptance, output-link, Industry Map, Stage 1, typed-semantics, Company Research, valuation or Investment Candidate write.
- No schema, migration, table, dependency or front-end framework change.
- No Provider, network, news, announcement, THS, AI, scheduler, worker or notification.
- No score, rank, recommendation, target price, expected return, position sizing, portfolio, broker or order behavior.

## Verification

- Exact route ownership and dual-as-of visibility.
- Complete-universe decision coverage.
- Selected exposure/identity validation.
- Dry-run/commit fingerprint parity.
- Atomic stale/invalid failure with browser choices preserved.
- Exact result shows selected, unresolved and rejected paths.
- History switches to exact result reopening.
- Full regression and production-route offline three-candidate review/result demo.
- Exact final HEAD CI and fresh fixed-head review before separate merge authorization.
