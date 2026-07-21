# Issue #162 — Company Research and Guarded AI Consolidation Review

## Authority

- Work type: consolidation/refactoring characterization, documentation only.
- Required base: `2e3722fdf224a58df0c870e2fa167b4f8e742b49`.
- Linked Issue: #162.
- Related roadmap: #137.
- Reviewed implemented slices:
  - Company Research Workspace v1 — PR #151;
  - Guarded AI Research Assistance v1 — PR #161.

## Objective

Characterize the two completed slices, synchronize the authoritative baseline and decide whether any production consolidation is required before another Architecture Preflight.

## Exact authorized files

1. `.codex/tasks/issue-162-company-research-guarded-ai-consolidation-review.md`;
2. `docs/company_research_guarded_ai_consolidation_review.md`;
3. `docs/architecture_baseline.md`.

No other file may change.

## Required review

Record:

- runtime and product-surface inventory;
- Company Research selector/workspace query boundaries;
- deterministic Manifest ownership and zero-I/O behavior;
- adapter configuration, network, timeout, retry and fallback boundaries;
- strict output validation, D3-only semantics and ephemeral state;
- API/status/error consistency;
- repeated router, service, contract, serializer, DOM and test patterns;
- keep/consolidate decisions with explicit revisit triggers;
- test/regression-surface characterization;
- schema, migration, dependency, Provider, release and rollback decision;
- next-stage field ownership and production reachability;
- one bounded next Architecture Preflight candidate or an explicit pause.

## Expected default

Unless evidence proves otherwise:

- no production refactor;
- keep Company Research projection, Manifest, adapter and response validation as separate bounded modules;
- no generic workspace, AI-agent, provider, prompt, RAG or product-page framework;
- no second AI job or persisted draft state;
- synchronize the baseline to the merged Guarded AI capability and active consolidation gate;
- recommend only a later Typed Beneficiary Evidence Semantics Architecture Preflight;
- keep Evidence Ingestion deferred and Canonical Price / Comparison Eligibility unauthorized.

## Validation

Verify:

```text
base = 2e3722fdf224a58df0c870e2fa167b4f8e742b49
changed files = exactly 3 authorized documentation files
no production code or behavior changes
```

GitHub Actions may run repository tests for regression evidence, but this task adds no application behavior or test requirement.

## Stop conditions

Stop if the review requires production refactoring, a shared runtime abstraction, provider expansion, a second AI job, persistent drafts, schema/migration/dependency work, live ingestion, Canonical Price, Comparison Eligibility, ranking, scoring, recommendation, alerts, portfolio or trading state.

## Completion gate

Create one Draft PR and keep it Draft/Open/unmerged. Record exact base/head, changed files, findings and CI. Stop after author review and independent fixed-head consolidation review. Do not merge or start the recommended next preflight without explicit owner authorization.