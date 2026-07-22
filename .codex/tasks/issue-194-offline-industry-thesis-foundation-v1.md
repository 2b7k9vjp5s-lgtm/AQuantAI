# Issue #194 Task Snapshot — Offline Industry Thesis Orchestration Foundation v1

## Authority

- Authoritative Issue: #194.
- Product Roadmap: #137.
- Accepted architecture: Issue #192 / PR #193.
- Required base: `702a6410fecf73fb7ea428c4e37f26c9a081dd87`.
- Branch: `feat/offline-industry-thesis-foundation-v1`.
- Risk tier: **Strict**.
- Owner authorization recorded on 2026-07-22: merge PR #193 and proceed to the next development phase.

## Objective

Implement the bounded offline foundation:

```text
explicit user thesis input
  -> append-only session identity/revision
  -> deterministic local candidate proposals
  -> exact-ID dual-as-of reads
```

This slice creates no accepted Industry Map, beneficiary, Company Research, component or Investment Candidate state.

## Authorized implementation

1. migration `20260722_0016` after `20260722_0015`;
2. six additive table families accepted by PR #193;
3. strict controlled vocabularies and canonical JSON;
4. SHA-256 input/source fingerprints;
5. system-owned recorded UTC and explicit information cutoff;
6. expected-latest protected local commands:
   - `create-industry-thesis-session`;
   - `revise-industry-thesis-session`;
   - `build-industry-thesis-candidates`;
7. exact-ID session/session-revision/candidate reads under both as-of boundaries;
8. deterministic source precedence and complete proposal visibility;
9. offline golden/failure tests;
10. populated downgrade refusal before any table drop.

## Ownership boundary

The new domain owns only:

- thesis/session workflow identity and append-only revisions;
- non-accepted candidate proposal identity and append-only revisions;
- future exact output-link audit tables.

Existing owners remain authoritative for Industry Map, Stage 1 beneficiary membership, typed semantics, Company Research, Canonical Price, normalized valuation and Investment Candidate state.

Output-link tables exist only to preserve the accepted architecture schema. No output-link write service or owner-acceptance transaction is implemented in Issue #194.

## Deterministic input contract

- No hidden market default.
- Market scope is an explicit non-empty ordered strict-JSON array.
- Binary floating-point values are rejected from fingerprinted JSON.
- JSON is bounded by depth, item count and byte size.
- Canonical JSON uses sorted keys and compact ASCII encoding.
- Session fingerprints exclude system-generated IDs and recorded time.
- Candidate keys are SHA-256 over exact source kind plus exact source reference.
- Identical exact sources cannot appear twice in one build request.
- Different sources remain separate auditable candidates even when they refer to the same company label.

## Candidate sources in this slice

Allowed:

1. `accepted_local_mapping` — requires an exact persisted identity;
2. `existing_industry_map_revision` — requires one exact visible Industry Map revision;
3. `user_seed` — may remain unresolved or ambiguous.

Rejected in this slice:

- `ai_draft`;
- Provider or web-discovered candidates;
- fuzzy company-name/ticker acceptance;
- hidden source fallback.

## Chronology and concurrency

- `recorded_at_utc` is supplied only by the service clock.
- Information cutoff cannot exceed recorded UTC date.
- Session and candidate revisions cannot move cutoff or recorded time backward.
- Identity latest-revision pointers update only in the same transaction as the appended revision.
- Existing candidate sources require an explicit expected latest revision number.
- Any stale pointer or exact graph mismatch fails atomically.

## Tests required before review

- exact six-table model contract;
- canonical JSON and fingerprint reproducibility;
- float/unknown-field/hidden-market rejection;
- create/revise dry-run and commit behavior;
- stale expected-latest failure;
- deterministic three-proposal ordering;
- unresolved user seed preservation;
- exact local identity validation;
- exact Industry Map revision visibility validation;
- exact-ID dual-as-of reads;
- append-only mutation rejection;
- migration upgrade/empty round-trip;
- populated downgrade refusal before any drop;
- CLI bounded input and stable JSON output;
- full repository CI.

## Locked exclusions

No Industry Map acceptance transaction, Stage 1 beneficiary write, typed-semantics acceptance, readiness aggregation, Investment Candidate snapshot invocation, UI wizard, industry-level AI, Provider, news, announcement, THS, browser, scheduler, background worker, recommendation, target price, expected return, position sizing, portfolio, broker, order, automated trading, release, tag or version change.

## Fixed-head review gate

Before merge:

1. verify the branch merge base is exactly `702a6410fecf73fb7ea428c4e37f26c9a081dd87`;
2. verify the complete implementation diff remains inside Issue #194;
3. run full CI on the exact final HEAD;
4. perform a fresh process-independent fixed-head review;
5. record:

```text
AUTHORIZED OFFLINE INDUSTRY THESIS FOUNDATION APPROVED at fixed head <FULL_HEAD_SHA>
```

6. resolve every blocker/thread;
7. require a separate explicit project-owner merge authorization.

Any new commit invalidates prior exact-head CI/review evidence where required by `.codex/WORKFLOW.md`.
