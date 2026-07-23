# Issue #200 Task Snapshot — Personal Research Workbench UI Phase 1A

## Authority

- Authoritative Issue: #200.
- Approved architecture: Issue #198 / merged PR #199.
- Required base: `693e580a54f83f51a3823f14528de9aa3de41cfd`.
- Branch: `feat/personal-research-workbench-ui-phase1a`.
- Risk tier: **Strict implementation**.
- Repository workflow: `.codex/WORKFLOW.md`.

## Objective

Deliver the first runnable Chinese-first workbench slice:

```text
/workbench
  -> /industry-analysis
  -> deterministic dual-as-of thesis history
  -> exact visible revision metadata
  -> browser-local display settings
```

## Authorized behavior

- Add the five-module application shell.
- Activate only 产业研究 and 系统设置.
- Serve `/industry-analysis`, `/industry-analysis/new`, and `/workbench/settings` from one static workbench asset family.
- Add a thin `/industry-analysis/api` router for bootstrap and bounded session history.
- Reuse Industry Thesis session identities and revisions; add no persistence.
- Require explicit information-cutoff and recorded-UTC boundaries.
- Keep technical identifiers in advanced details, never ordinary inputs.
- Keep the new-research page honest: scope entry is preview-only until the write slice is separately implemented.
- Store display preferences only in browser `localStorage`.

## Locked exclusions

No session or candidate writes, proposal review commit, owner acceptance, output links, migration, schema, dependency, Provider, network acquisition, scheduler, notification, AI call, credential handling, portfolio, broker, order, position sizing, recommendation, target price, expected return, release or version change.

## Required validation

- page routes and redirect;
- disabled future modules without mock values;
- deterministic bootstrap contract;
- empty and multi-session history;
- dual-as-of visibility;
- bounded deterministic ordering;
- UTC/cutoff validation before database construction;
- stable database-unavailable behavior;
- browser-only settings;
- offline demo contract;
- full repository regression;
- exact-head CI and fresh fixed-head review.

Any new commit invalidates prior exact-head evidence. Merge requires separate owner authorization.