# Issue #208 — Personal Research Workbench UI Phase 2A Preflight

## Authority

- Product roadmap: #137
- Five-module product direction: Issue #198 / merged PR #199
- Completed UI Phase 1A–1D: Issues #200, #202, #204, #206 / merged PRs #201, #203, #205, #207
- Required base: `98a67c36f5cd968f17898038c786d3720b793dab`
- Owner direction: `按计划进行下一步开发` on 2026-07-23
- Risk tier: Strict Product / Architecture Preflight

## Objective

Define an honest local-only Today Market first slice:

```text
explicit persisted equity series
  + optional explicit benchmark series
  + optional explicit sector series
  + information cutoff and recorded-UTC boundary
  -> existing deterministic Market Cockpit calculation
  -> Chinese-first Today Market local snapshot
```

## Accepted preflight decisions

- Canonical page route: `/today-market`.
- `/workbench` continues to enter `/industry-analysis` in Phase 2A.
- 今日市场, 产业研究 and 系统设置 are active; 关注与跟踪 and 研究组合 remain disabled.
- Existing `MarketCockpitService`, repositories and calculators remain the only market calculation owners.
- Add a bounded local series catalog with at most 20 equity, benchmark and sector options per family.
- Labels are deterministic projections of validated canonical selector fields; they do not create full-market meaning.
- Every series selection is explicit; no first/newest automatic selection or name-based compatibility inference.
- Catalog and snapshot reads require information-cutoff and explicit recorded-UTC boundaries.
- The future read adapter filters successful complete runs by both information and local recording chronology.
- Supported content is selected-universe price behavior, liquidity, optional benchmark, optional sector, provenance, scope, completeness and alignment.
- Unsupported breadth, anomaly, event/cause, market-attention and remote-refresh sections remain explicit unavailable states.
- THS live implementation remains blocked by its separate account-contract gate.
- Use no schema, migration, dependency, Provider, network, scheduler, notification or AI call.
- Reuse FastAPI plus static HTML/CSS/vanilla JavaScript.
- One offline production-boundary golden path and recorded-UTC invisibility failure path are required.

## Architecture deliverables

- this task snapshot;
- `docs/personal_research_workbench_ui_phase2a_preflight.md`;
- bounded current-state correction in `docs/architecture_baseline.md`;
- Draft architecture PR #209 from the exact required base;
- fixed-head checks and Product / Architecture review.

## Candidate future implementation boundary

The architecture document authorizes a later linked implementation Issue to modify only the exact listed Today Market API/view-model/static/test/demo families and bounded recorded-UTC compatibility seams in existing Market Cockpit repositories/service. Any schema, Provider, network or additional product meaning requires a new Issue amendment or preflight.

## Locked exclusions

No production code in this preflight; no schema, migration, table, dependency, Provider adapter, credential, live request, remote refresh, scheduler, background worker, notification, news/announcement ingestion, market-attention acquisition, full-market claim, cause inference, AI call, accepted-state mutation, Investment Candidate mutation, recommendation, target price, expected return, position sizing, portfolio, broker, order, automated trading, release, tag or version change.

## Delivery state

- Issue: #208
- Branch: `docs/personal-research-workbench-ui-phase2a-preflight`
- Draft PR: #209
- Changed files: exactly this task snapshot, the detailed Phase 2A preflight and the authoritative architecture baseline
- The PR remains Draft and unmerged until fixed-head checks, review and separate owner authorization are complete.
- Required fixed-head approval phrase:

`AUTHORIZED PERSONAL RESEARCH WORKBENCH UI PHASE 2A PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`
