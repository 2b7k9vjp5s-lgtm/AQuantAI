# Issue #198 Task Snapshot — Chinese Personal Investment Research Workbench UI Phase 1

## Authority

- Authoritative Issue: #198.
- Product Roadmap: #137.
- Required base: `1ce3abace07d00e60fd911f9cc4f96a768f47a06`.
- Owner authorization recorded on 2026-07-23: enter the next development step and preserve the approved five-module UI and subsequent capability plan for later implementation.
- Repository workflow: `.codex/WORKFLOW.md`.
- Risk tier: **Strict architecture** because the preflight defines one cross-domain product read model over thesis orchestration, beneficiary, evidence, company research, price, valuation and investment-candidate contracts, and because later phases contain Provider, scheduler and portfolio triggers that must remain explicitly gated.

## Phase boundary

This task authorizes **Product / Architecture Preflight for UI Phase 1 — Research Workbench only**.

Authorized work:

- inspect accepted product and domain contracts;
- define the Phase 1 application shell, routes, user jobs and navigation;
- define page-level read models and exact reuse of existing services;
- define the manual industry-research workflow from ordinary Chinese input through scope confirmation, candidate review and reviewed-plan display;
- define evidence presentation and ordinary-versus-advanced metadata policy;
- define loading, empty, stale, partial, conflict and failure states;
- define responsive, accessibility and local-first behavior;
- define one production-realistic offline three-candidate fixture/demo scenario;
- define missing backend seams without implementing them;
- synchronize the authoritative architecture baseline;
- open one Draft architecture PR and obtain exact-head CI and process-independent review.

Not authorized:

- production HTML, CSS, JavaScript, TypeScript, Python, API or UI implementation;
- schema, migration or table changes;
- fixtures or executable tests;
- dependency or build-system changes;
- Provider, network, news, announcement, THS, browser or market-data acquisition;
- scheduler, background worker, notification or automatic refresh implementation;
- AI calls, new model adapters, credentials or AI-owned accepted state;
- Industry Map, Stage 1, typed semantics, output-link, Company Research, price, valuation, Investment Candidate or portfolio owner writes;
- observation/simulated portfolio ledger;
- broker, order, position-sizing, target-price, expected-return, recommendation, release, tag or version change.

## Authorized file family

The architecture PR may change only:

1. `.codex/tasks/issue-198-personal-research-workbench-ui-phase1-preflight.md`;
2. `docs/personal_research_workbench_ui_phase1_preflight.md`;
3. `docs/architecture_baseline.md`.

Any production, migration, workflow, dependency, fixture, test or unrelated documentation file is outside scope.

## Product objective

Define a Chinese-first, local-first and ordinary-user-friendly Research Workbench that hides technical identifiers while preserving exact revisions, provenance and dual-as-of semantics internally.

The Phase 1 user path is:

```text
application shell
  -> enter a fuzzy industry / concept / thesis in ordinary Chinese
  -> confirm interpreted scope and explicit market/cutoff
  -> create or continue an exact local thesis session
  -> build the complete local candidate universe
  -> review every candidate as include / do not include now / unresolved
  -> display one reviewed plan with complete pool, reasons, uncertainty and evidence
  -> save and reopen from research history
```

The workflow must be useful without news, announcements, external Provider data, scheduler or AI.

## Required architecture decisions

### 1. Application shell and routes

Define the five top-level navigation areas while implementing only the Phase 1 research surfaces:

- 今日市场;
- 产业研究;
- 关注与跟踪;
- 研究组合;
- 系统设置.

Inactive future areas must use honest unavailable/coming-later states and must not fabricate data.

Define exact Phase 1 routes, route parameters and navigation return behavior.

### 2. Ordinary-user input contract

The primary user must not enter UUIDs, revision numbers, fingerprints or database URLs.

The UI must collect or confirm:

- thesis text;
- market scope;
- driver type or unknown;
- horizon;
- chain boundary;
- exclusions;
- optional seed companies/products/technologies/bottlenecks;
- information cutoff.

No hidden default may broaden market scope or claim full-market discovery.

### 3. Scope-confirmation contract

Before candidate build, show the system interpretation and require explicit confirmation or editing. Free text and AI proposals remain draft input only.

### 4. Read-model ownership

Map every visible field to an existing authoritative owner or mark it unavailable. Prefer thin composition over copied business state.

At minimum inventory:

- thesis session/revision and reviewed-plan services;
- Industry Map and complete Stage 1 beneficiary reads;
- Typed Beneficiary Semantics;
- Company Research;
- Evidence Ledger/source links;
- Investment Candidate status/reasons when exact state already exists;
- Canonical Price and valuation context only when exact eligible records exist.

### 5. Candidate review contract

The primary candidate actions are:

- `纳入后续研究` -> `selected_for_acceptance`;
- `暂不纳入` -> `rejected_by_user`;
- `待确认` -> `unresolved`.

The UI must preserve the complete candidate universe and must not hide rejected or unresolved rows.

### 6. Evidence presentation

Define a right-side evidence drawer or equivalent detail surface that visually separates:

- source facts;
- deterministic calculations;
- analyst judgments;
- AI drafts.

Show source, information date/cutoff, recorded time, conflict/missing/stale state and exact technical metadata through progressive disclosure.

### 7. Ordinary versus advanced metadata

Ordinary mode shows readable labels, freshness, coverage and reasons. Advanced details expose exact IDs, revision numbers, fingerprints and raw error codes without making them normal inputs.

### 8. User-visible states

Define consistent behavior for:

- initial loading;
- long local operation;
- no research sessions;
- no local candidates;
- partial or unknown coverage;
- stale expected-latest conflict;
- ambiguous identity;
- incomplete review universe;
- not-visible historical boundary;
- unavailable downstream company/price/valuation state;
- local database unavailable;
- feature not yet implemented.

No failure may fall back to a newer record, another company or inferred identity.

### 9. Responsive and accessibility behavior

Desktop-first shell with:

- fixed left navigation;
- global top bar;
- central workspace;
- optional right evidence drawer.

Define tablet/card fallback, keyboard traversal, visible focus, semantic labels, non-color-only status cues and readable dense tables.

### 10. Offline golden path

The production-realistic demo must reuse the existing three-candidate thesis flow:

1. create one A-share thesis session;
2. confirm scope and cutoff;
3. build three exact local candidates;
4. display direct, conditional and conceptual/uncertain benefit paths;
5. select one, reject one and leave one unresolved;
6. save the reviewed plan;
7. reopen it from history using exact IDs internally;
8. show all three candidates, evidence/uncertainty and coverage state;
9. perform no network or AI call.

### 11. Primary failure path

When an identity is ambiguous, a candidate is omitted from the complete review universe, or the expected latest revision is stale, the save must fail atomically. The UI must retain the user's unsaved decisions, identify the affected rows and offer an explicit reload/review path. It must not silently overwrite or rebase decisions.

### 12. Missing backend seams

The preflight must distinguish:

- existing services directly reusable;
- composition/read adapters that may be implemented in Phase 1;
- owner writes intentionally unavailable in Phase 1;
- future dependencies belonging to Today Market, Daily Radar, Follow/Track or Research Portfolio.

## Working architecture direction

Prefer:

- server-rendered or existing-stack-compatible Chinese-first pages rather than a new front-end framework unless repository inspection proves otherwise;
- thin page/view-model composition over a new UI database domain;
- existing exact-ID services behind ordinary-user session/history selection;
- explicit local actions with clear progress rather than background jobs;
- one evidence drawer contract shared only where semantics truly match;
- compact defaults and progressive disclosure;
- read-only placeholders for future modules, not mock market or portfolio data.

## Stop conditions

Stop and return to Issue #198 if:

- ordinary operation requires users to copy technical IDs;
- Phase 1 requires a new Provider, scheduler, notification system or portfolio ledger;
- a visible field lacks an authoritative owner and would need inference from free text;
- UI composition would silently choose latest compatible-looking records instead of exact revisions;
- candidate review cannot preserve the complete universe;
- useful offline manual research cannot be completed without AI or network access;
- implementation would require a new front-end framework, API family or persistence boundary not justified by the preflight;
- future modules would need to show fabricated placeholder values rather than honest unavailable states.

## Validation and review gates

Before architecture merge:

1. verify branch base is exactly `1ce3abace07d00e60fd911f9cc4f96a768f47a06`;
2. verify the complete diff contains only the three authorized documentation files;
3. run repository documentation/CI checks on the exact final HEAD;
4. perform a fresh process-independent review against that exact HEAD;
5. record the exact approval phrase:

```text
AUTHORIZED PERSONAL RESEARCH WORKBENCH UI PHASE 1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

6. keep the PR Draft/Open until the fixed-head review is complete;
7. require a separate explicit project-owner merge authorization.

Any new commit invalidates prior exact-head review evidence.

## Completion boundary

Completion of this preflight may authorize one separately scoped UI Phase 1 implementation Issue only after exact-head architecture approval and separate owner authorization. It does not authorize UI production code by itself.
