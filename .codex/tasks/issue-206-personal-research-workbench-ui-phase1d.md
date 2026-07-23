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

## Implemented slice

- Added an isolated Phase 1D API/page router for exact review views, strict complete-universe review writes and exact reviewed-plan reads.
- Added a non-persistent review/result projection that validates exact session ownership, latest candidate pointers, workflow state, plan fingerprint and reviewed candidate bindings.
- Upgraded the existing candidate page from the Phase 1C placeholder to explicit three-state review while retaining the authorized scope/candidate-build flow.
- Added dry-run/signature parity in the browser: any form change invalidates the checked payload and disables commit.
- Added an exact read-only result page showing selected, unresolved and rejected source paths without representing selection as accepted membership.
- Updated research history progressive enhancement to reopen exact review or exact result links under the user-selected dual-as-of boundary.
- Updated bootstrap and candidate responses to report the active Phase 1D review/read capabilities while keeping accepted-output authority disabled.
- Added production-route and domain-level regression coverage plus an offline three-candidate golden-path demo.

## Deterministic and failure behavior

- Every exact latest candidate revision must appear exactly once in a review request.
- Duplicate candidate decisions fail with 409; missing or extra candidates fail with 422.
- Rejected and unresolved decisions cannot carry final exposure overrides.
- Selected decisions require one authoritative identity and explicit non-unknown final exposure.
- Dry-run performs zero writes and freezes the same deterministic reviewed session/candidate IDs and plan fingerprint as commit.
- One stale session or candidate expected-latest value aborts the complete transaction.
- The exact result URL uses the reviewed-candidate recorded boundary, not the earlier reviewed-session timestamp.
- Ambiguous transport failure is never retried automatically; browser choices remain present for explicit verification.

## Safety boundaries

- No owner acceptance, output-link, Industry Map, Stage 1, typed-semantics, Company Research, valuation or Investment Candidate write.
- No schema, migration, table, dependency or front-end framework change.
- No Provider, network, news, announcement, THS, AI, scheduler, worker or notification.
- No score, rank, recommendation, target price, expected return, position sizing, portfolio, broker or order behavior.

## Verification

- Exact route ownership and dual-as-of visibility.
- Complete-universe decision coverage and duplicate-path preservation.
- Selected exposure/identity validation and rejected/unresolved override refusal.
- Strict JSON, content-type, body-size and unknown-field handling.
- Duplicate review 409 versus incomplete review 422 mapping.
- Dry-run/commit fingerprint parity across invocation clocks and decision order.
- Atomic stale/invalid failure with browser choices preserved.
- Exact result shows selected, unresolved and rejected paths and verifies the stored plan fingerprint.
- History switches to exact result reopening without user-entered IDs.
- Full repository regression and production-route offline three-candidate review/result demo.
- Demo asserts zero Industry Map, Stage 1 and output-link writes.
- Exact final HEAD CI and fresh fixed-head review before separate merge authorization.

## Delivery state

- Implementation branch: `feat/personal-research-workbench-ui-phase1d`
- Draft PR: #207
- Final fixed-head SHA, successful CI run/job and fixed-head review are recorded on the PR after the branch stops changing.
- The PR remains Draft until all Strict gates pass and remains unmerged until the project owner separately authorizes merge.
