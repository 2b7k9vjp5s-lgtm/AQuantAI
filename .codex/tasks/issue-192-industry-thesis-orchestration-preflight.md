# Issue #192 Task Snapshot — Industry Thesis Intake and Research Orchestration v1

## Authority

- Authoritative Issue: #192.
- Product Roadmap: #137.
- Required base: `be18f407fb42b6caf22d339285e17f830052af91`.
- Owner authorization recorded on 2026-07-22: continue and start the next development step after PR #191 merged; the requested product path is user industry/theme input -> beneficiary-company analysis -> current investment-research candidates, without making news or official announcements hard dependencies.
- Repository workflow: `.codex/WORKFLOW.md`.
- Risk tier: **Strict** because this architecture coordinates accepted Industry Map and beneficiary ownership, deterministic Investment Candidate state, possible additive persistence and bounded AI draft behavior.

## Phase boundary

This task authorizes **architecture preflight only**.

Authorized work:

- inspect accepted domain contracts and current runtime boundaries;
- define the thesis-intake and orchestration architecture;
- define candidate-source precedence and coverage semantics;
- define exact draft/review/acceptance boundaries;
- define an additive persistence candidate if required;
- define commands, reads, UI flow, golden path and failure paths;
- synchronize the authoritative architecture baseline;
- open one Draft architecture PR and obtain exact-head CI and process-independent review.

Not authorized:

- production Python, API or UI implementation;
- database migration or schema application;
- fixtures or executable tests;
- dependency changes;
- Provider, news, announcement, THS or web acquisition;
- live AI calls or new credentials;
- automatic company membership, evidence acceptance, component scoring or candidate-state mutation;
- release, tag or version change.

## Authorized file family

The architecture PR may change only:

1. `.codex/tasks/issue-192-industry-thesis-orchestration-preflight.md`;
2. `docs/industry_thesis_orchestration_preflight.md`;
3. `docs/architecture_baseline.md`.

Any production, migration, workflow, dependency, fixture, test or unrelated documentation file is outside scope.

## Product problem

The accepted runtime already owns:

- persisted Industry Maps and Stage 1 beneficiary revisions;
- complete-universe Industry Beneficiary Workspace reads;
- typed beneficiary exposure and execution evidence;
- Company Research v0.6A-v0.6D;
- company comparison;
- Canonical Price and purpose-specific Comparison Eligibility;
- Investment Candidate component assessments, deterministic snapshots and statuses;
- structured financial, valuation and expectation-gap records;
- guarded company-scoped AI draft assistance.

The missing layer is one governed entry and orchestration path. A user cannot currently enter a phrase such as `存储芯片`, `电子特气` or `创新药`, review a structured industry thesis, establish a complete local-scope beneficiary universe and continue into the existing investment-candidate workflow without manually navigating unrelated identities and commands.

## Architecture objective

Define one local-first workflow:

```text
explicit user thesis input
  -> append-only thesis draft revision
  -> deterministic local candidate build
  -> optional bounded AI proposal draft
  -> explicit user review of driver / chain / bottleneck / value-pool / coverage
  -> explicit selected company and exposure plan
  -> existing Industry Map and Stage 1 owner writes
  -> exact orchestration-output links
  -> Company Research and component readiness inspection
  -> existing deterministic Investment Candidate snapshot command
  -> full-universe result with priority/watch/incomplete reasons
```

The success path must remain usable with no news, announcement, market-attention or external Provider acquisition configured.

## Required decisions

The architecture document must close the following decisions.

### 1. Exact thesis-intake contract

At minimum define:

- user-entered thesis/theme text;
- explicit market scope;
- explicit driver type or `unknown`;
- analysis horizon;
- optional chain boundary and exclusions;
- optional seed companies, products, technologies and bottlenecks;
- information cutoff;
- system-owned recorded UTC;
- deterministic input fingerprint.

Free text is draft input and cannot itself become an accepted Industry Map, beneficiary classification, component assessment or candidate status.

### 2. Minimal orchestration ownership

Decide whether reproducibility requires a small append-only orchestration domain. It must not duplicate:

- Industry Map ownership;
- Stage 1 beneficiary ownership;
- typed beneficiary semantics;
- Company Research;
- Canonical Price;
- normalized valuation;
- Investment Candidate components, rules or snapshots.

### 3. Candidate-source precedence

Candidate proposals must preserve exact source kind and provenance in this order:

1. accepted local company/product/taxonomy mappings;
2. exact existing Industry Map and beneficiary revisions;
3. explicit user seeds;
4. optional bounded AI draft proposals.

No source may silently claim full-market coverage.

### 4. Coverage and identity behavior

The architecture must distinguish at least:

- reviewed local-scope coverage;
- known partial local coverage;
- unknown coverage.

An ambiguous or duplicate company identity fails closed. Company-name or security-code guessing is not accepted identity.

### 5. Draft, selection and accepted-state boundary

Separate:

- thesis draft;
- chain and driver draft;
- candidate proposal draft;
- user-selected acceptance plan;
- existing-owner accepted Industry Map and beneficiary revisions;
- exact output links;
- deterministic downstream Investment Candidate snapshot.

AI output may never cross this boundary without an explicit deterministic user-confirmed write through existing owners.

### 6. Two-stage research method

Stage A preserves every reviewed beneficiary in scope and records direct, conditional, indirect or conceptual exposure plus unknown/missing states.

Stage B reuses the existing eight Investment Candidate dimensions and preserves missing, pending, disputed and failed values. No valuation or price-performance filter may remove a company from Stage A.

### 7. Offline-first and optional AI

The production-realistic golden path must be fully offline using exact local records and user input.

An industry-level AI draft extension may be architected as optional, disabled by default and separately implementable. It must use an immutable Manifest, explicit remote confirmation, strict JSON validation and no browsing, tools, retrieval or self-promotion.

### 8. Commands, reads and UI

Define:

- JSON-only dry-run-capable local commands;
- exact-ID reads with information-cutoff and recorded-UTC boundaries;
- expected-latest protection for writes;
- one Chinese-first workflow beginning at `/industry-analysis/new`;
- readiness and missing-input inspection;
- deterministic handoff to an existing Investment Candidate rule version.

Ordinary reads must never call AI or any external network.

### 9. Migration and rollback candidate

If new persistence is required, define:

- the minimum additive identities/revisions/links;
- exact foreign-key and uniqueness ownership;
- PostgreSQL and supported SQLite behavior;
- concurrency and atomicity;
- populated downgrade refusal;
- no migration execution in this architecture task.

### 10. Tests

Define a fully offline three-company golden path and fail-closed tests for:

- ambiguous thesis input;
- empty/unknown local coverage;
- duplicate or ambiguous company identity;
- stale or mismatched exact revisions;
- missing price eligibility;
- attempted AI-owned acceptance;
- attempted removal of incomplete beneficiaries from the complete Stage 1 pool.

## Working architecture direction

The preflight should prefer:

- a small append-only thesis/orchestration domain for audit and reproducibility;
- exact links into existing owning domains rather than copied business fields;
- one user-confirmed acceptance transaction that calls existing owner services;
- deterministic offline candidate building as the MVP;
- optional industry-level guarded AI drafting as a later bounded Strict implementation slice;
- no requirement for news or announcement ingestion.

## Production-realistic golden path

The architecture must prove, without network access:

1. one explicit A-share industry thesis revision;
2. one reviewed driver and chain boundary;
3. three exact local company identities;
4. one direct beneficiary with complete research inputs;
5. one conditional beneficiary with missing valuation input;
6. one conceptual or insufficient-evidence company pending verification;
7. explicit user selection and acceptance through existing Industry Map/beneficiary owners;
8. exact orchestration links to accepted revisions;
9. readiness inspection preserving all three members;
10. one deterministic Investment Candidate snapshot showing different statuses and reasons without inventing missing values.

## Primary failure path

When a candidate is supported only by ambiguous free text or an AI proposal without exact accepted company identity and explicit user selection, acceptance must fail atomically. No Industry Map, beneficiary pool, Company Research, component assessment or Investment Candidate history may be mutated.

## Stop conditions

Stop and return to Issue #192 if:

- accepted ownership would need to be duplicated in the orchestration domain;
- the workflow requires news, announcements, live Provider data or hidden browsing to produce any useful result;
- the offline success path cannot reach existing owner services;
- arbitrary free text or AI output must directly create accepted membership or scores;
- Stage A completeness would be replaced by top-N discovery or valuation filtering;
- exact identity, revision, cutoff or recorded-UTC boundaries cannot be preserved;
- the design requires a generic agent, RAG, Provider fallback or automatic research loop.

## Validation and review gates

Before architecture merge:

1. verify branch base is exactly `be18f407fb42b6caf22d339285e17f830052af91`;
2. verify the complete diff contains only the authorized documentation files;
3. run repository documentation/CI checks on the exact final HEAD;
4. perform a fresh process-independent review against that exact HEAD;
5. record the exact approval phrase:

```text
AUTHORIZED INDUSTRY THESIS ORCHESTRATION PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

6. keep the PR Draft/Open until the fixed-head review is complete;
7. require a separate explicit project-owner merge authorization.

Any new commit invalidates prior CI/review evidence where the workflow requires exact-head validation.

## Completion boundary

Architecture approval will authorize only the documented contract. It will not itself authorize production implementation, migration, AI calls, external data acquisition, release, version change or merge of a future implementation PR.
