# Issue #164 — Typed Beneficiary Evidence Semantics v1 Architecture Preflight

## Authority

- Issue: #164
- Related roadmap: #137
- Predecessor consolidation: Issue #162 / merged PR #163
- Required base: `13099ce1988dec05eaf674732fce3acb7f5fa080`
- Branch: `docs/typed-beneficiary-evidence-semantics-preflight`
- Work type: Architecture Preflight and Definition of Ready, documentation only
- Released version remains `0.2.0`

## Objective

Define the smallest safe append-only semantic layer for one explicitly selected existing Stage 1 beneficiary so an analyst can record typed exposure and execution-evidence states with exact revisions, claims, cutoff, UTC, conflicts and missing-data provenance.

## Required user job

For one explicit persisted `map_id` and one exact existing `beneficiary_id`, record and review typed beneficiary exposure, industry-driver and execution-evidence states without ranking companies and without inferring accepted values from free text, Provider metadata, stock identifiers or AI output.

## Required decisions

1. Select the authoritative owner and immutable revision identity.
2. Decide separate semantic layer versus modifying v0.5C Stage 1.
3. Preserve raw `direct / secondary / potential` without automatic mapping.
4. Define the exact v1 exposure taxonomy and taxonomy version.
5. Define industry-driver types/subtypes and exact map-observation linkage.
6. Define typed product/service, customer, certification, capacity, production and order states.
7. Define exact claim-revision links and supported/disputed/missing/not-applicable behavior.
8. Define analyst responsibility representation without authentication claims.
9. Separate deterministic validation from analyst-owned D3 judgment.
10. Define cutoff, UTC, supersession, history and downstream-freeze rules.
11. Define one migration, downgrade, rollback and production-realistic offline golden path.
12. Define candidate command/API/read-only UI boundaries and bounded tests.
13. Stop if any accepted value requires hidden inference or unavailable ownership.

## Authorized files

Exactly:

1. `.codex/tasks/issue-164-typed-beneficiary-evidence-semantics-preflight.md`
2. `docs/typed_beneficiary_evidence_semantics_preflight.md`

No other file is authorized.

## Locked exclusions

- no production code, API/UI behavior, schema or migration in this preflight;
- no Evidence Ingestion restart, PDF, crawling, scraping, browsing or external search;
- no AI/LLM-owned taxonomy, extraction, acceptance or evidence promotion;
- no automatic identity selection or mapping from name, code, Provider industry or free text;
- no generic rule engine, agent framework, RAG, vector database or embeddings;
- no cross-company comparison, ranking, score or investment-priority total;
- no Canonical Price, Comparison Eligibility, fair value, target price, expected return or recommendation;
- no monitoring, alerts, tasks, portfolio or trading;
- no dependency, Provider, release or version change.

## Acceptance criteria

- documentation-only exact two-file diff;
- current v0.5A/v0.5B/v0.5C ownership and gap inventory is accurate;
- a separate append-only semantic layer is either accepted with complete lifecycle rules or rejected with an explicit stop;
- exact taxonomies and state vocabularies are defined;
- evidence, conflict, missing, chronology and immutable history rules are complete;
- migration/downgrade/rollback and implementation candidate are bounded;
- no production behavior change;
- GitHub Actions succeeds at one fixed head;
- independent reviewer records exact fixed-head Definition-of-Ready approval.

## Stop conditions

Stop without implementation authorization if:

- typed values cannot be bound to an explicit existing beneficiary identity and revision;
- positive states cannot bind exact accepted claim revisions;
- the design requires parsing free text, Provider industry, stock code or model output;
- Stage 1 or Stage 2 history would require mutation or automatic relinking;
- migration downgrade would require deleting or rewriting accepted history;
- the first slice expands into ranking, valuation, monitoring, ingestion or AI acceptance.

## Completion gate

Create a Draft PR containing only the two authorized documentation files. Record exact Base/HEAD, changed-file inventory and CI. Keep Draft/Open/unmerged. Do not create an implementation Issue, migration or production code until independent fixed-head approval and explicit owner authorization.