# Issue #215 — Personal Research Workbench UI Phase 2B Preflight

## Authority

- Parent product roadmap: Issue #210.
- Broader product roadmap: Issue #137.
- Strict Architecture Preflight Issue: #215.
- Required exact base: `2780442efa0a6c110bf7887c68cf2919ea3cc443`.
- Project-owner direction: `进行下一步开发` on 2026-07-23, interpreted only as authorization to create the architecture branch, documentation and Draft PR for Issue #215.
- Risk tier: Strict Architecture Preflight.
- Workflow authority: `.codex/WORKFLOW.md`.

## Objective

Define one bounded presentation-layer consolidation over the accepted Personal Research Workbench:

```text
exact dual-as-of research history
  -> one exact recent-research continuation card
  -> shared five-step workflow indicator
  -> one deterministic primary action per state
  -> ordinary-user Chinese state explanation
  -> first-use guidance
```

The preflight improves continuity and comprehension only. It creates no new research, market, evidence, valuation, Provider, alert, portfolio or trading capability.

## Accepted preflight direction

- Reuse `GET /industry-analysis/api/sessions` as the sole recent-history owner; do not create a generic activity service or persisted recent-item table.
- Use one bounded history response for both the recent-research card and the history list; no per-card fetches.
- The first returned session is the exact latest visible session under the requested information-cutoff and recorded-UTC boundaries because the existing query orders by recorded time descending and exact session identity ascending.
- Displaying the card does not navigate automatically, write state, advance boundaries or fall back to another compatible-looking record.
- Continue links are built only from exact response-owned session/revision identifiers and both response-owned chronology boundaries.
- Use the exact five-step vocabulary: `研究主题 -> 确认范围 -> 候选公司 -> 人工审核 -> 研究结果`.
- Derive the active/completed/unavailable step from the exact route and already loaded accepted response state; do not persist presentation progress or add a second workflow owner.
- Define one visually dominant action for each participating route/state. History, reload, back and technical-detail actions remain secondary.
- Ordinary-user state explanations use three stable presentation fields: `发生了什么`, `为什么重要`, `现在可以做什么`.
- Technical IDs, fingerprints and dual-as-of details remain available through progressive disclosure and are never required as ordinary inputs.
- Correct navigation so Today Market is active on every workbench surface while Follow/Track and Research Portfolio remain honestly unavailable.
- When no exact visible research exists, show the three-step first-use guide and keep any fixture/demo entry explicitly labelled.
- Preserve unsaved review decisions on conflicts; never silently retry, rebase or select a newer record.
- Use no schema, migration, Provider, network, scheduler, notification, AI call, portfolio state, release, tag or version change.

## Architecture deliverables

- this task snapshot;
- `docs/personal_research_workbench_ui_phase2b_preflight.md`;
- one Draft architecture PR linked to Issue #215;
- documentation/link validation and complete base-to-head scope inspection;
- applicable process-independent fixed-head architecture review.

A focused `docs/architecture_baseline.md` synchronization may be added to this same architecture PR only when it accurately records the active/accepted Phase 2B gate and does not claim implementation.

## Candidate future implementation boundary

A later separately authorized implementation Issue may modify only bounded presentation and existing-owner read paths:

- `industry_analysis/static/**`;
- `today_market/static/**` only for navigation-shell consistency;
- `backend/api/industry_analysis.py` only for a focused read-only projection correction already owned by the workbench history adapter, if the existing response cannot express an exact link;
- `industry_alpha/industry_thesis_workbench.py` only for bounded presentation projection fields derived from already owned state, not new workflow semantics;
- focused workbench tests and one offline ordinary-user golden-path demo;
- `.github/workflows/local-tests.yml` only to run that demo without weakening checks.

No new table, domain service, generic activity layer, framework or persistent presentation state is authorized.

## Locked exclusions

No production code in this preflight. No schema, migration, Provider, remote refresh, network request, scheduler, background worker, notification, news/announcement ingestion, market-attention feature, followed-entity state, research/simulated portfolio, new AI call, accepted evidence/map/beneficiary/company/candidate write, target price, expected return, recommendation, position size, broker, order, automated trading, mobile redesign, release, tag or version change.

## Delivery state

- Issue: #215.
- Branch: `docs/personal-research-workbench-ui-phase2b-preflight`.
- Draft PR: to be created from the exact required base.
- Architecture files: exactly this task snapshot and the detailed Phase 2B preflight, with an optional focused baseline synchronization in the same PR.
- The PR remains Draft and unmerged until exact-head validation, independent review, resolved threads and separate project-owner merge authorization are complete.
- Required fixed-head approval phrase:

`AUTHORIZED PERSONAL RESEARCH WORKBENCH UI PHASE 2B PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`
