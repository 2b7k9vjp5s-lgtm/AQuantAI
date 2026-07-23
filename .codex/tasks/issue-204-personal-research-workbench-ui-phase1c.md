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

## Delivered behavior

- An exact saved scope revision may be explicitly advanced from `draft` to `candidate_build_ready` through the existing append-only revision command.
- Exact stored company seeds are validated against one canonical StockBasic or ListedInstrument authority and copied from canonical identity fields.
- Exact selected Industry Map revisions expose only frozen Stage 1 candidate-pool revisions that are bound to that exact map and visible under both as-of boundaries.
- No pool is auto-selected and maps with no eligible pool produce an explicit no-source state with no fallback.
- Candidate proposals are composed deterministically as `user_seed` or `existing_industry_map_revision` sources.
- Stage 1 source references freeze exact map revision, pool revision, membership and beneficiary revision IDs.
- Pool member counts are computed only after full exact graph and visibility validation.
- The same company through different exact source paths remains separate; no ranking, filtering or deduplication is performed.
- Dry-run and commit delegate to the accepted candidate transaction/revision service.
- The exact candidate page renders the complete local universe and keeps three-state review disabled for Phase 1D.
- Existing history and save-success surfaces generate exact candidate-page links without manual UUID entry.
- Workbench bootstrap keeps the Phase 1B scope shell contract while declaring the active Phase 1C candidate-universe slice and capabilities.

## Required safety boundaries

- No selected/rejected/unresolved review write.
- No reviewed-plan result, owner acceptance or output-link write.
- No Industry Map, Stage 1, typed-semantics or Investment Candidate write.
- No schema, migration, table, dependency or front-end framework change.
- No Provider, network acquisition, news, announcement, THS, AI, scheduler or notification.
- No score, rank, valuation, portfolio, broker, order, position sizing, target price, expected return or recommendation.

## Verification inventory

- Exact session/revision route ownership and candidate-build-ready latest-state enforcement.
- Exact company identity authority and canonical label/code projection.
- Exact source-option visibility and map-to-frozen-pool binding.
- No automatic pool selection or fallback when a map has no eligible pool.
- Later pools do not leak across the recorded-time boundary.
- Full frozen member graph is validated before its count or proposal data is exposed.
- Deterministic seed and Stage 1 proposal composition.
- Same company through distinct exact source paths remains distinct.
- Dry-run has no persistence; commit persists the complete proposal set once.
- Repeat/stale/duplicate builds fail closed without extra rows.
- Candidate-universe read returns all exact rows in deterministic source order.
- Strict malformed, unknown-field and oversized request failures.
- Browser preserves explicit choices and never automatically retries a write.
- Full regression plus existing demos and offline three-candidate production-boundary demo.

## Current gate

Implementation is complete on Draft PR #205. It remains unmerged pending exact final HEAD CI, fresh fixed-head review with no unresolved blockers, and separate project-owner merge authorization.
