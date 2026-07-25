# Issue #240 Task Snapshot — Industry Thesis Ordinary-User Completion v1

## Authority

- Product Roadmap: #137.
- Accepted Architecture Preflight: Issue #238 / merged PR #239.
- Accepted architecture HEAD: `aba635e36db35d9babb37048e2a70e882717ca62`.
- Exact implementation base: `f5bd39c7ee720c723e275d00395cc2a281d711a1`.
- Accepted owner-acceptance core: Issue #236 / merged PR #237.
- Implementation Issue: #240.
- Project-owner authorization on 2026-07-25:

```text
按计划继续进行下一步开发
```

- Workflow authority: `.codex/WORKFLOW.md`.
- Risk tier: **Strict Implementation**.

## Branch and PR

```text
branch = feat/industry-thesis-ordinary-user-completion
base = f5bd39c7ee720c723e275d00395cc2a281d711a1
PR = Draft, linked to #240
```

No rebase, force-push, base change or silent scope expansion.

## Objective

Implement the ordinary-user completion flow over the accepted owner-acceptance core:

```text
reviewed_plan_ready
  -> 检查并接受研究成果
  -> explicit frozen owner choices
  -> deterministic preview
  -> explicit matching-fingerprint commit
  -> accepted_outputs_linked
  -> exact accepted result and readiness
  -> exact history reopening
```

## Locked implementation decisions

1. The only stock identity is each reviewed candidate's frozen `proposed_stock_basic_record_id`.
2. Missing or listed-instrument-only identity blocks acceptance; no alternative identity selector exists.
3. Preview uses the exact flat `normalize_owner_acceptance_plan` request.
4. Commit uses the unchanged plan plus only `preview_fingerprint_sha256`.
5. Stage 1 supports exact reuse/create/append; create source/code come from the frozen StockBasicRecord.
6. Typed semantics supports only `none` or exact compatible reuse.
7. One global candidate-pool operation handles create/append/reuse/zero-supported.
8. Handoff membership is derived from resulting Stage 1 `supported` status and is never editable per member.
9. Accepted result and supported-only handoff remain separate.
10. Exact reads use both cutoff and recorded-UTC boundaries; no latest fallback.
11. No schema, migration, new accepted field, server-side draft or browser-local accepted identity.
12. No Provider, network, AI, recommendation, valuation, portfolio or trading behavior.

## Authorized file families

```text
.codex/tasks/issue-240-industry-thesis-ordinary-user-completion.md
backend/api/industry_analysis.py
backend/api/industry_analysis_review.py
backend/api/industry_analysis_acceptance.py
industry_alpha/industry_thesis_owner_acceptance_workbench.py
industry_analysis/static/review_result.html
industry_analysis/static/review_result.js
industry_analysis/static/owner_acceptance.html
industry_analysis/static/owner_acceptance.js
industry_analysis/static/accepted_result.html
industry_analysis/static/accepted_result.js
bounded shared industry_analysis/static CSS/JS helpers
tests/test_industry_analysis*.py
tests/test_industry_thesis_owner_acceptance*.py
scripts/run_industry_thesis_ordinary_user_acceptance_fixture.py
.github/workflows/local-tests.yml only to add the offline demo without weakening checks
docs/architecture_baseline.md only after implementation acceptance
```

## API/application contract

### Acceptance view

One bounded exact response must return:

- reviewed session/revision/fingerprint and expected latest;
- exact Research Case, Industry Map/revision and dual-as-of boundaries;
- all selected members in frozen order;
- one frozen stock record per member or a blocking state;
- exact Stage 1 reuse/append/create reachability;
- exact assertion/claim choices;
- exact semantic reuse choices;
- one top-level candidate-pool operation catalog;
- server-owned constants and explicit output defaults.

No per-member HTTP requests. SQL ceiling: 14 statements for 3- and 20-member fixtures.

### Preview/commit

- strict JSON and unknown-field rejection;
- route/body reviewed-revision equality;
- exact flat core payload;
- stable raw core response fields;
- preview leaves zero persisted writes;
- commit requires exact preview fingerprint and explicit user action;
- stale/conflict returns 409 with no silent retry/rebase.

### Accepted result

One bounded exact response composes output, complete result and readiness:

- complete frozen member universe;
- separate supported-only handoff;
- draft/disputed visible;
- zero-supported valid with no fabricated pool;
- graph mismatch fails closed;
- exact history continuation from accepted session/output reference.

SQL ceiling: 10 statements.

## UI contract

- Chinese-first ordinary wording;
- one primary action per state;
- IDs/fingerprints under progressive details;
- explicit frozen identity confirmation;
- form state kept in page memory after 409/422/503;
- editing invalidates preview fingerprint;
- no automatic commit, retry or latest refresh;
- keyboard navigation, focus movement, error summaries, safe text rendering and `aria-current`.

## Golden paths

### Three-company

- A reuses supported Stage 1 plus semantic revision;
- B reuses/appends draft/disputed and stays complete-result-only;
- C creates/appends supported using exact frozen stock fields and semantic none;
- create supported handoff;
- preview complete=3, supported=2;
- explicit atomic commit;
- exact accepted result reopens all three in frozen order.

### Zero-supported

- all members draft/disputed;
- mode `none_no_supported_members`;
- accepted result includes every member and no pool.

## Required tests

- route/state and exact-ID mapping;
- frozen identity and missing/listed-only block;
- exact flat DTO, unknown fields and route/body mismatch;
- create source/code ownership;
- Stage 1 and semantic modes;
- pool create/append/reuse/none and conflicts;
- derived handoff membership;
- preview zero persisted writes and fingerprint stability;
- atomic commit, idempotent replay and conflicting replay;
- stale form-preservation contract;
- exact accepted-result/readiness and dual-as-of negative visibility;
- graph integrity fail closed;
- one-primary-action, accessibility and safe rendering;
- 3-/20-member query ceilings;
- zero-network import/startup/page/test/demo;
- no migration/new persistence;
- no recommendation, target price, expected return, portfolio or trading semantics;
- full repository regression and every configured offline demo.

## Stop conditions

Stop and return to architecture review if implementation requires:

- replacing the frozen stock identity;
- inferred create source/code or inferred owner semantics;
- a wrapper/adapter-owned write contract that differs from the core;
- per-member editable handoff membership;
- a second workflow owner, new persistence, migration or accepted field;
- latest fallback for exact reopening;
- direct ORM writes from the adapter;
- Provider/network/AI/recommendation/portfolio/trading scope.

## Strict gates

1. Keep the full diff inside authorized file families.
2. GitHub Actions and focused/full tests succeed on one exact immutable final HEAD.
3. All configured offline demos succeed.
4. Obtain a fresh fixed-head implementation review containing exactly:

```text
AUTHORIZED INDUSTRY THESIS ORDINARY-USER COMPLETION IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

5. Resolve all review threads.
6. Await separate explicit project-owner merge authorization.
7. Any new commit invalidates prior CI and review evidence.

Implementation approval does not authorize merge, Issue closure, Architecture Issue #238 closure, release or the next roadmap phase.
