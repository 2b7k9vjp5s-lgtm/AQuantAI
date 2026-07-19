# Issue #72 - Unified Architecture Baseline Reset

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: `#72`
- Base and required ancestor: `9cc5a0e5dda97efa6b9c7b3a43eb3b5c4ead91ec`
- Branch: `docs/architecture-baseline-reset`
- Draft PR: `[Architecture Reset] Unify project baseline and delivery gates`
- Released version remains `0.2.0`.

This task authorizes documentation and workflow-governance changes only. Issue #72 is authoritative.

Do not add or modify application code, models, migrations, repositories, commands, APIs, fixtures, demos, tests, provider behavior, dependencies, Docker, CI, launchers, frontend/UI, release/tag metadata, v0.6E behavior, v0.7 behavior, or PR #38.

The superseded Issue #70 and PR #71 remain closed without merge. Preserve their branch and review history.

## Objective

Create one accepted architecture baseline that distinguishes:

1. released software version;
2. merged capability stage;
3. current runtime and user-visible surfaces.

Synchronize project documents with merged v0.3-v0.6D capabilities, define one domain dependency direction, centralize architecture invariants, record architecture debt, and add explicit preflight, Definition-of-Ready, reset, and consolidation gates before future feature work.

## Authorized files

The complete branch diff may contain only:

- `.codex/WORKFLOW.md`
- `.codex/tasks/issue-72-architecture-reset.md`
- `README.md`
- `docs/architecture_baseline.md`
- `docs/roadmap.md`
- `docs/review.md`
- `docs/product_architecture.md`
- `docs/research_workflow.md`
- `docs/data_model.md`
- `docs/implementation_plan.md`

## Required architecture decisions

### Three-axis current-state model

Use these independent axes everywhere:

- release version: `0.2.0`;
- merged capability stage: v0.6D on `main`;
- runtime surfaces: local fixture Dashboard plus reviewed database-backed read-only Market Cockpit and Industry Alpha APIs/demos when configured.

Do not imply that merged stages are a new published release. Do not describe the repository as if only the original fixture Dashboard exists.

### Implemented dependency direction

```text
market-data evidence
  -> v0.5 evidence ledger
  -> Stage 1 beneficiary boundary
  -> v0.6A company research
  -> v0.6B expectations and valuation observations
  -> v0.6C catalysts and risks
  -> v0.6D quality judgments
```

v0.6E price judgment is superseded and not implemented. v0.7 and later are not authorized.

### Ownership boundaries

- Canonical market-price value, measurement kind, unit, currency, provider/series provenance, and decimal normalization belong to a separately reviewed market-data/evidence contract.
- Generic v0.6B valuation `observed_value` is not automatically comparison-eligible.
- A v0.6B local `daily_price` link remains provenance/context unless a future structured upstream contract explicitly permits comparison.
- “Good price” and “good timing” remain conceptual workflow goals, not current runtime entities.

### Shared architecture invariants

Define once in `docs/architecture_baseline.md` and reference them from other documents:

- local-first, personal-use, research-only, non-advisory;
- deterministic calculations outside LLM ownership;
- no network during imports, startup, tests, CI, fixture demos, or ordinary read use;
- exact revision binding and explicit selectors;
- append-only accepted research history;
- information-cutoff plus UTC chronology anti-leakage;
- visible facts, inferences, conflicts, missing evidence, and uncertainty;
- strict deterministic JSON;
- atomic rollback and deterministic concurrency behavior;
- fixture/provider contract parity;
- no mutation UI/API, broker, order, or trading behavior unless separately authorized.

### Architecture debt register

Record at least:

- current-state documentation drift;
- repeated Stage 2 identity/revision/link/repository/query/fixture patterns;
- repeated revision allocation, evidence qualification, and cutoff validation;
- growing cross-product test matrices;
- fixture-versus-production reachability risk;
- missing canonical market-price measurement semantics;
- missing formal consolidation cadence.

### Development gates

Update `.codex/WORKFLOW.md` to require:

1. Architecture Preflight before a feature Issue;
2. Definition of Ready before task synchronization or implementation;
3. a production-realistic golden path before exhaustive rejection matrices;
4. an explicit field/domain ownership table;
5. separation of architecture decision, planning, and implementation;
6. reset after two rounds of foundational blockers, or immediately on provider reachability or ownership failure;
7. consolidation review after every two domain slices;
8. recognition that green CI is necessary but not sufficient for architecture acceptance.

## Validation

Run and report:

- complete base-to-head changed-file inventory;
- `git diff --check`;
- available documentation/link or metadata checks without changing test behavior;
- unchanged `python -m pytest -q`;
- unchanged `python -m scripts.demo_research_flow`;
- final GitHub Actions result.

No new test, fixture, application, migration, or CI behavior may be added.

## Delivery and stop gate

1. Commit only the authorized documentation/task files.
2. Open Draft PR `[Architecture Reset] Unify project baseline and delivery gates` against `main`.
3. Record base/head SHA, changed files, key decisions, validation results, exclusions, and unresolved debt in the PR and Issue #72.
4. Keep the PR Draft/Open/unmerged and Issue #72 Open.
5. Stop for ChatGPT review.

Do not start Stage 2 consolidation, market-price evidence, valuation comparison eligibility, v0.6E, v0.7, or any migration from this task.