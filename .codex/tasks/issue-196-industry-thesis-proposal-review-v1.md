# Issue #196 Task Snapshot — Industry Thesis Proposal Review and Acceptance Plan v1

## Authority

- Authoritative Issue: #196.
- Product Roadmap: #137.
- Accepted architecture: Issue #192 / merged PR #193.
- Completed foundation: Issue #194 / merged PR #195.
- Required base: `058fd4e6dab99e3aaab506f9c746b10a87a584a4`.
- Branch: `feat/industry-thesis-proposal-review-v1`.
- Risk tier: **Strict**.
- Owner authorization recorded on 2026-07-22: merge PR #195 and start this next implementation phase.

## Objective

Implement the bounded offline review layer:

```text
exact session revision + complete exact candidate revision set
  -> explicit selected / rejected / unresolved decisions
  -> append-only reviewed candidate revisions
  -> deterministic acceptance-plan preview and SHA-256 fingerprint
  -> reviewed_plan_ready session revision
```

This slice creates no accepted Industry Map, Stage 1 beneficiary, typed-semantics, output-link, Company Research, valuation, component or Investment Candidate state.

## Authorized implementation

1. Reuse migration `20260722_0016` tables only; no schema or migration change.
2. Add local JSON-only, dry-run-capable candidate-review command.
3. Require exact session revision and exact candidate revisions.
4. Require expected-latest guards for the session and every candidate.
5. Append reviewed candidate revisions atomically.
6. Support only `selected_for_acceptance`, `rejected_by_user` and `unresolved` decisions.
7. Require exact accepted persisted identity for every selected candidate.
8. Preserve rejected and unresolved candidates in the complete universe.
9. Generate canonical deterministic acceptance-plan preview plus SHA-256 fingerprint.
10. Append a session revision with `workflow_state = reviewed_plan_ready` only after complete valid review.
11. Add exact-ID, dual-as-of reviewed-plan reads.
12. Add SQLite/PostgreSQL tests and an offline three-candidate fixture demo.

## Acceptance-plan minimum contract

- exact session identity and reviewed session revision ID;
- explicit cutoff and recorded-UTC boundary;
- coverage state;
- ordered selected, rejected and unresolved candidate revision IDs;
- exact persisted identity IDs for selected candidates;
- explicit final proposed exposure type for selected candidates;
- source kind and source-reference fingerprint;
- rule/version identifier;
- canonical JSON and SHA-256 fingerprint.

## Fail-closed rules

- one stale session or candidate expected-latest value aborts the transaction;
- incomplete candidate coverage cannot become `reviewed_plan_ready`;
- ambiguous, unresolved, rejected or candidate-only identities cannot be selected;
- missing candidates cannot disappear;
- duplicate selected company identities are explicit conflicts unless a reviewed deterministic rule proves the same candidate identity/revision;
- chronology and information cutoff cannot move backward;
- no fuzzy match, ticker-prefix inference, provider-name inference, AI inference or hidden market default;
- dry-run performs full validation without writes.

## File families authorized

- `.codex/tasks/issue-196-industry-thesis-proposal-review-v1.md`;
- `industry_alpha/industry_thesis_*`;
- one bounded local command script under `scripts/`;
- focused `tests/test_industry_thesis_*` files;
- `docs/architecture_baseline.md` only if needed to reflect accepted/active state.

## Locked exclusions

No migration, schema change, Industry Map write, Stage 1 beneficiary write, typed-semantics acceptance, output-link write, owner-acceptance transaction, readiness aggregation, Investment Candidate snapshot invocation, UI, AI, Provider, news, announcement, THS, browser, scheduler, background worker, recommendation, target price, expected return, position sizing, portfolio, broker, order, automated trading, release, tag or version change.

## Validation gate

Before fixed-head review:

1. verify merge base is exactly `058fd4e6dab99e3aaab506f9c746b10a87a584a4`;
2. verify complete base-to-head inventory remains within Issue #196;
3. run focused SQLite and PostgreSQL tests;
4. run full repository CI and offline fixture demo;
5. record exact final HEAD and required approval phrase;
6. resolve every blocker/thread;
7. require separate explicit project-owner merge authorization.

Required approval phrase:

```text
AUTHORIZED INDUSTRY THESIS PROPOSAL REVIEW APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates exact-head review evidence.