# Issue #171 — Company Research Priority Comparison v1 Architecture Preflight

## Authority

- Issue: #171
- Related roadmap: #137
- Required base: `1c176994320bda72f57805676d5e39d48d45d057`
- Branch: `docs/company-research-priority-comparison-preflight`
- Risk tier: Strict
- Work type: Architecture Preflight and Definition of Ready, documentation only
- Owner authorization: chat message `审核完成，继续` on 2026-07-21
- Released version remains `0.2.0`

## Objective

Define the smallest safe side-by-side company research comparison over one explicit persisted Stage 1 candidate-pool revision, preserving every member of that exact unranked universe and displaying accepted component state without a total score, ordering, price-attractiveness claim or recommendation.

## Required architecture decisions

1. Exact comparison selector and frozen universe identity.
2. Exact membership, beneficiary, map and cutoff semantics.
3. Deterministic Company Research attachment without first/latest guessing.
4. Typed Beneficiary semantic selection and historical mismatch behavior.
5. Component ownership across Stage 1 and v0.6A-v0.6D.
6. Missing, disputed, stale, conflicting and not-applicable treatment.
7. Component-only versus D2 classification, score or ranking decision.
8. Canonical Price / Comparison Eligibility boundary.
9. Fixed-count query plan independent of universe size.
10. D0-D3 presentation and non-advisory wording.
11. Golden path, failure path, migration decision and rollback.
12. Candidate implementation file families, tests and stop conditions.

## Candidate decision to validate

- selector: one explicit `candidate_pool_revision_id`;
- comparison universe: every exact `Stage1CandidatePoolMembership` in that revision;
- deterministic neutral ordering only;
- unique Stage 2 Company Research identity may attach only through exact candidate-pool membership;
- Typed Beneficiary profile may attach only when it references the exact frozen beneficiary revision;
- component matrix presents accepted stored state and explicit missingness;
- no total score, research-priority rank, valuation comparison or recommendation;
- no schema or migration for v1;
- later implementation may be Standard only if the preflight proves all Strict triggers are excluded.

## Authorized files

Exactly:

1. `.codex/tasks/issue-171-company-research-priority-comparison-preflight.md`
2. `docs/company_research_priority_comparison_preflight.md`

No other file is authorized.

## Locked exclusions

- no production code, API/UI behavior, schema or migration in this preflight;
- no external network, Provider, ingestion, browsing, crawling or scraping;
- no AI-owned comparison, score, ranking or accepted state;
- no Canonical Price or Comparison Eligibility implementation;
- no fair value, target price, expected return, upside/downside or buy/sell/hold state;
- no monitoring, alerts, tasks, portfolio or trading;
- no generic comparison, rule-engine, agent, RAG, vector or provider framework;
- no release or version change.

## Validation

- exact two-file documentation diff;
- accepted model and ownership inventory verified against current `main`;
- one production-realistic offline golden path and one fail-closed path;
- no hidden identity, revision, price or AI inference;
- GitHub Actions success at one fixed head;
- independent fixed-head architecture approval.

## Completion gate

Keep the PR Draft/Open/unmerged. Do not create or merge implementation work until the fixed architecture head is independently approved and the owner explicitly advances it.
