# Issue #134 — Evidence Intelligence MVP Architecture Preflight

## Objective

Define one bounded, user-visible, read-only Evidence Intelligence slice that lets a user identify recent research changes without changing domain semantics, persistence, Provider behavior, cutoff, revision, provenance or append-only rules.

## Authority

- GitHub Issue: #134
- Base: `main` at `0136674af2c213cdc550a5605108ea67ac357616`
- Branch: `agent/issue-134-evidence-intelligence-preflight-clean`
- Task type: Architecture Preflight, docs/task only
- Release: unchanged at `0.2.0`
- Capability: unchanged at v0.6D

## Required output

Create `docs/evidence_intelligence_mvp_preflight.md` containing:

- one-sentence user job;
- exactly one first vertical slice;
- verified source-model and repository inventory;
- field Semantic/Derivation qualification matrix;
- bounded scalar-query, ordering, cursor, deduplication, missing/conflict and cutoff contracts;
- non-advisory presentation contract;
- invariance proof and task classification;
- performance/security boundary;
- validation matrix;
- exact later implementation candidates and exclusions;
- follow-on product direction for Industry Beneficiary Analysis and Investment Research Analysis without authorizing those implementations.

## Fixed decisions

- First slice: Global Research Change Feed / Evidence Timeline entry page.
- Included events: `EvidenceItem`, `ResearchCaseRevision`, `IndustryMapRevision`, and `Stage2CompanyResearchRevision` creation.
- Existing full-graph list services are not reused because they perform per-object graph loading.
- Later implementation uses one stateless, bounded, scalar read repository/query boundary.
- Read-only only; no new persistence, migration, schema, Provider, network path, AI output, score, ranking, recommendation or price judgment.
- Industry Beneficiary Analysis and Investment Research Analysis are incorporated as later separately governed slices.

## Allowed files

1. `.codex/tasks/issue-134-evidence-intelligence-mvp-preflight.md`
2. `docs/evidence_intelligence_mvp_preflight.md`

No other file may change in this preflight PR.

## Validation

- Diff contains exactly the two allowed documentation files.
- Model names, table names and fields match the current `main` repository.
- No code, tests, fixtures, API, UI, schema, migration, Provider, dependency, release or version change.
- Branch remains Draft/Open/unmerged pending independent Definition-of-Ready review.

## Stop conditions

Stop and return to Architecture Preflight if:

- a displayed field requires inference or a new semantic contract;
- a cross-domain relationship changes ownership or meaning;
- a Feed requires persistent state/materialization;
- cutoff, revision, provenance or append-only behaviour would change;
- strict valuation/price comparison is attempted without canonical price and comparison eligibility;
- beneficiary or investment research output is presented as recommendation, signal or expected return.
