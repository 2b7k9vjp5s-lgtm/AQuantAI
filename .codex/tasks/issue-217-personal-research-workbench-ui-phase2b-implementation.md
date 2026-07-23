# Issue #217 — Personal Research Workbench UI Phase 2B Implementation

## Authority

- Strict implementation Issue: #217.
- Parent architecture Issue: #215.
- Accepted architecture PR: #216.
- Required exact base: `04db345c88c91a87064b319b43a07c3451b46659`.
- Project-owner authorization: `授权创建一个独立的 Strict 实现 Issue/PR，进行下一轮开发` on 2026-07-23.
- Risk tier: Strict Implementation.
- Workflow authority: `.codex/WORKFLOW.md`.
- Architecture authority: `docs/personal_research_workbench_ui_phase2b_preflight.md`.

## Objective

Implement the accepted ordinary-user usability consolidation without changing accepted research semantics:

```text
one exact dual-as-of history response
  -> sessions[0] recent-research card
  -> response-owned exact continuation path
  -> shared five-step presentation
  -> one deterministic primary action
  -> stable Chinese state explanation
  -> truthful first-use guide
```

## Locked implementation direction

- Reuse the existing `/industry-analysis/api/sessions` response for the card and history list.
- Never issue a second card request or skip the first exact visible record.
- Add only a read-only API presentation projection from exact response-owned IDs, workflow state and record-owned boundaries.
- Fail closed for `accepted_outputs_linked`, `superseded`, `abandoned`, unknown and malformed states.
- Use the exact five-step vocabulary: `研究主题 -> 确认范围 -> 候选公司 -> 人工审核 -> 研究结果`.
- Derive step state from exact route and already-loaded response; persist no UI workflow state.
- Keep exactly one visually dominant action per tested page/state.
- Use static Chinese mappings under `发生了什么 / 为什么重要 / 现在可以做什么`.
- Preserve unsaved review decisions after `409`; never retry or rebase silently.
- Make Today Market and Industry Research active consistently; keep Follow/Track and Research Portfolio unavailable.
- Keep technical identifiers and dual-as-of provenance under progressive disclosure.
- Add focused regression, query-ceiling and offline golden-path coverage.

## Authorized file families

Only the families listed in Issue #217 and the accepted Phase 2B preflight may change. In particular, existing `industry_alpha/industry_thesis_*` domain services and models are not implementation targets.

## Migration and rollback

- Schema migration: none.
- Data backfill: none.
- Persistent state: none.
- Dependency change: none.
- Rollback: revert API/static presentation changes; persisted research history remains unchanged.
- Browser-local preference keys remain unchanged and store no research identity or progress.

## Required validation

- focused API/static/query-count tests;
- continuation mapping and no-skipping tests;
- navigation and accessibility regression;
- conflict preservation test;
- empty-history versus database-failure test;
- production-realistic offline returning-user, no-skipping, new-user and navigation paths;
- full relevant regression and all existing offline demos;
- complete base-to-head file-family validation;
- process-independent fixed-head implementation review.

Required approval phrase:

`AUTHORIZED PERSONAL RESEARCH WORKBENCH UI PHASE 2B IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>`

## Stop conditions and exclusions

Stop if implementation requires persistence, schema changes, domain-service semantics, a second workflow owner, generic activity service, fuzzy/latest-compatible selection, first-record skipping, browser-local research identity, row-count-dependent queries, network/Provider/scheduler/notification/AI behavior, accepted owner writes, Daily Radar, Follow/Track, Research Portfolio, recommendation/price/trading semantics, a frontend framework, release, tag or version change.

## Delivery state

- Branch: `feat/personal-research-workbench-ui-phase2b`.
- Draft PR: to be created and linked to Issue #217.
- No merge or Issue closure is authorized by this task snapshot.
