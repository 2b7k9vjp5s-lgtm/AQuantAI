# Issue #202 — Personal Research Workbench UI Phase 1B

## Authority

- Roadmap: #137
- Approved architecture: Issue #198 / merged PR #199
- Completed foundation UI: Issue #200 / merged PR #201
- Required base: `77255a72d03624d94a627d2c69f3d9963fab73d1`
- Risk: Strict implementation

## Objective

Implement the bounded create-and-confirm-scope slice for the Chinese personal research workbench:

```text
ordinary thesis input
  -> explicit market and cutoff confirmation
  -> optional exact local map/company selections
  -> service dry-run
  -> append-only session revision 1
  -> exact history reopening
  -> optional append-only scope revision
```

## Allowed behavior

- Exact local map and company option reads under explicit dual-as-of boundaries.
- Session create and revise endpoints delegated to accepted Industry Thesis services.
- Strict JSON, 1 MiB body limit, no automatic retry.
- Browser form preserves user input on validation/conflict.
- Exact IDs appear only in generated internal links and progressive technical details.
- Draft save is allowed without exact sources.

## Required safety boundaries

- No candidate build.
- No proposal review or reviewed-plan result implementation.
- No owner acceptance or output-link write.
- No schema, migration, table, dependency or front-end framework change.
- No Provider, network acquisition, news, announcement, THS, AI, scheduler or notification.
- No portfolio, broker, order, position sizing, target price, expected return or recommendation.

## Verification

- Local option boundaries and deterministic ordering.
- Dry-run and commit behavior for create and revise.
- Exact supersedes chain and stale expected-latest conflict.
- Strict request and body-size failures.
- Exact revision reopening without manual UUID input.
- Browser input preservation and disabled Phase 1C candidate build.
- Full regression and expanded offline demo.
- Exact final HEAD CI and fresh fixed-head review before separate merge authorization.
