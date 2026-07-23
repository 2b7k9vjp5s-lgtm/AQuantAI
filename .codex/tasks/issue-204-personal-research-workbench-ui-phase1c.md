# Issue #204 — Personal Research Workbench UI Phase 1C

## Authority

- Roadmap: #137
- Accepted Industry Thesis architecture: Issue #192 / merged PR #193
- Approved UI Phase 1 architecture: Issue #198 / merged PR #199
- Completed UI Phase 1B: Issue #202 / merged PR #203
- Required base: `0b702acb89735f6185e3edf7023b32e00859f170`
- Risk: Strict implementation

## Objective

Implement the bounded complete-candidate-universe slice:

```text
exact candidate-build-ready scope revision
  -> explicit exact source confirmation
  -> deterministic proposal composition
  -> dry-run candidate preview
  -> append-only candidate revisions
  -> complete exact universe read
  -> exact review deep link
```

## Allowed behavior

- Save an exact scope revision as `candidate_build_ready` only when it has at least one exact local map or company seed.
- Read exact company seeds and exact Stage 1 frozen candidate-pool revisions under explicit dual-as-of boundaries.
- Require explicit candidate-pool revision selection; never auto-select or use a hidden latest fallback.
- Compose user-seed and frozen Stage 1 proposals without text, Provider-name, exposure or confidence inference.
- Delegate dry-run and commit persistence to `IndustryThesisCommandService.build_candidates`.
- Render every exact proposal path, including duplicate companies from different sources.
- Generate exact internal review links without requiring manual UUID entry.

## Required safety boundaries

- No selected/rejected/unresolved review write.
- No reviewed-plan result, owner acceptance or output-link write.
- No Industry Map, Stage 1, typed-semantics or Investment Candidate write.
- No schema, migration, table, dependency or front-end framework change.
- No Provider, network acquisition, news, announcement, THS, AI, scheduler or notification.
- No score, rank, valuation, portfolio, broker, order, position sizing, target price, expected return or recommendation.

## Verification

- Exact session/revision route ownership and candidate-build-ready latest-state enforcement.
- Exact source-option visibility and map-to-frozen-pool binding.
- No automatic pool selection or fallback when a map has no eligible pool.
- Deterministic seed and Stage 1 proposal composition.
- Same company through distinct exact source paths remains distinct.
- Dry-run has no persistence; commit persists the complete proposal set once.
- Repeat/stale/duplicate builds fail closed without extra rows.
- Candidate universe read returns all exact rows in deterministic source order.
- Strict malformed, unknown-field and oversized request failures.
- Browser preserves explicit choices and never automatically retries a write.
- Full regression and offline three-candidate production-boundary demo.
- Exact final HEAD CI and fresh fixed-head review before separate merge authorization.
