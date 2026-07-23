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

## Required decisions

- Activate 今日市场 without changing the accepted five-module shell ownership.
- Reuse `MarketCockpitService`; do not create a second market-calculation owner.
- Define a bounded local series catalog with explicit selection and no automatic newest/first fallback.
- Close information-cutoff, recorded-UTC, effective-session and mixed-alignment semantics.
- Define supported price/liquidity, benchmark, sector, provenance and warning sections.
- Mark unsupported breadth, anomaly, event, market-attention and live-refresh sections unavailable.
- Keep THS live implementation blocked by its account-contract gate.
- Use no schema, migration, dependency, Provider, network, scheduler, notification or AI call.
- Reuse FastAPI plus static HTML/CSS/vanilla JavaScript.
- Define exact future implementation routes, file families, tests and offline demo.

## Architecture deliverables

- this task snapshot;
- `docs/personal_research_workbench_ui_phase2a_preflight.md`;
- bounded current-state correction in `docs/architecture_baseline.md`;
- one Draft architecture PR from the exact required base;
- fixed-head checks and Product / Architecture review.

## Locked exclusions

No production code in this preflight; no schema, migration, table, dependency, Provider adapter, credential, live request, remote refresh, scheduler, background worker, notification, news/announcement ingestion, market-attention acquisition, full-market claim, cause inference, AI call, accepted-state mutation, Investment Candidate mutation, recommendation, target price, expected return, position sizing, portfolio, broker, order, automated trading, release, tag or version change.

## Delivery state

- Issue: #208
- Branch: `docs/personal-research-workbench-ui-phase2a-preflight`
- Draft PR: created after the initial architecture document is committed
- Required fixed-head approval phrase:

`AUTHORIZED PERSONAL RESEARCH WORKBENCH UI PHASE 2A PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`
