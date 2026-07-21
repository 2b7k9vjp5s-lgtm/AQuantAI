# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and a linked GitHub Issue controls the scope of Standard or Strict work.

- Released software version: `0.2.0`.
- Accepted application/product baseline: `e59e40ce9b45d9a0d2a22a897edcbc9dcd10704e`.
- Latest merged capability: Typed Beneficiary Evidence Semantics v1 through architecture PR #165 and implementation PR #169.
- Active application implementation, migration, Provider, release or version authorization: none.
- Evidence Ingestion remains deferred after Issue #154 / closed-unmerged PR #155; no ingestion runtime capability reached `main`.
- Canonical Price and Comparison Eligibility remain separate infrastructure tracks without implementation Definition of Ready.
- Owner authorization on 2026-07-21 advances the roadmap to the next Strict architecture gate only: Company Research Priority Comparison v1.
- No comparison, score, ranking, recommendation, price judgment or next-phase implementation is authorized until that architecture gate is independently approved.

Documentation may advance `main` without changing release or runtime behavior. This document records accepted current state; it does not itself authorize production implementation.

## Product boundary

AQuantAI is a local-first, personal-use, research-only and non-advisory workbench. It is not a broker, order-management system, automated-trading system, investment-advice service, multi-user SaaS product or production deployment platform.

Deterministic calculations, canonicalization, selectors and workflow state belong to reviewed application code. An LLM may assist only behind an explicit bounded adapter and may not own evidence qualification, deterministic state, accepted research state, execution or trading behavior.

## Implemented dependency direction

```text
market-data evidence
  -> v0.5 Evidence Ledger
  -> v0.5B Industry Map
  -> v0.5C Stage 1 beneficiary identity and revisions
       -> Typed Beneficiary Evidence Semantics v1
       -> v0.6A Company Research and financial-transmission hypotheses
  -> v0.6B expectations and valuation observations
  -> v0.6C catalyst and risk assessments
  -> v0.6D industry and company quality judgments
  -> read-only product workspaces
  -> optional company-scoped Guarded AI D3 draft assistance
```

Typed Beneficiary Evidence Semantics extends one exact Stage 1 beneficiary through a separate append-only profile. It does not rewrite the Stage 1 beneficiary contract and does not automatically relink frozen Stage 2 records.

Downstream accepted records freeze exact accepted upstream revisions and links. They do not silently select newer records, infer missing state or rewrite historical meaning.

## Current runtime and product surfaces

When the configured database and local assets are available, the reviewed runtime contains:

1. local fixture-backed Dashboard;
2. database-backed read-only Market Cockpit and Industry Alpha APIs/demos;
3. Evidence Intelligence / Research Change Feed;
4. Industry Beneficiary Workspace v1;
5. Company Research Workspace v1;
6. Guarded AI Research Assistance v1, disabled by default;
7. Typed Beneficiary Evidence Semantics v1 detail inside Industry Research.

### Evidence Intelligence / Research Change Feed

- Chinese-first read-only surface for recent evidence and research changes;
- explicit time window, cutoff, provenance and deterministic ordering;
- no opportunity ranking, score, recommendation or trading state;
- detail navigation reuses accepted owning-domain contracts.

### Industry Beneficiary Workspace v1

- Chinese-first read-only `/industry-research` workspace;
- requires explicit persisted Industry Map selection;
- shows the complete cutoff-visible persisted Stage 1 beneficiary set for the selected map;
- preserves exact stored legacy beneficiary and assessment values;
- loads full beneficiary, typed-semantic or Stage 2 detail only after explicit user action;
- does not claim full-market exhaustive coverage and does not rank beneficiaries.

### Typed Beneficiary Evidence Semantics v1

- separate append-only profile identity for one exact existing Stage 1 beneficiary;
- immutable revisions freeze exact beneficiary revision, selected map revision, driver observation revision and accepted claim revisions;
- taxonomy version is `aquantai.typed-beneficiary-evidence-semantics.v1`;
- exposure taxonomy is exactly `direct / conditional / indirect / conceptual`;
- legacy Stage 1 `direct / secondary / potential` is preserved and never automatically mapped;
- driver, offering, customer, certification, capacity, production and order vocabularies are closed;
- positive assertions require already-frozen claim revisions and attributable A/B/C evidence paths;
- `missing`, `disputed` and `not_applicable` remain distinct;
- all accepted semantic values are explicit analyst-owned D3 judgments;
- deterministic code validates identity, chronology, vocabulary and evidence sufficiency but does not infer values from text, Provider metadata, company name, security code or AI output;
- local CLI is the only write path; API and page are read-only;
- writes are atomic and append-only with expected-latest conflict protection;
- migration `20260721_0012` performs no backfill and refuses populated downgrade before any drop;
- no network, LLM, ranking, score, valuation, recommendation, alert, portfolio or trading behavior.

### Company Research Workspace v1

- Chinese-first read-only `/company-research` workspace;
- requires one explicit persisted `company_research_id` and never silently selects the first row;
- selector uses exactly 3 SQL statements and selected workspace uses exactly 14 SQL statements;
- shows exact frozen Stage 1, stock, ingestion and v0.6A-v0.6D revision provenance;
- keeps latest cutoff-visible revisions separate from exact frozen historical revisions;
- displays historical revision mismatch and never automatically relinks it;
- loads full owning-domain claim/evidence detail only after explicit user action;
- uses safe DOM methods and no untrusted `innerHTML`;
- presents valuation observations and optional L1 local-price provenance only;
- does not create Canonical Price, Comparison Eligibility, fair value, target price, expected return, ranking, score or recommendation state.

### Guarded AI Research Assistance v1

- available only inside one explicitly selected Company Research workspace;
- local preview projects an immutable deterministic Manifest and exact SHA-256 fingerprint;
- Manifest projection performs zero SQL, filesystem or network I/O beyond the completed workspace read;
- generation requires explicit remote-transmission confirmation and exact expected fingerprint;
- disabled by default with one explicit HTTPS OpenAI-compatible profile;
- no default provider, endpoint or model;
- no retry, fallback, streaming, tools, browsing, search, retrieval, embeddings or background execution;
- strict application-owned response, section, fingerprint and Manifest-item citation validation;
- prohibited recommendation and price-judgment language fails closed;
- output is ephemeral D3 draft assistance only;
- no prompt, model response, draft identity, revision, review state or accepted-domain mutation is persisted.

## Consolidation decisions

The accepted consolidation reviews remain binding:

- no generic product-workspace framework merely for router, page or DOM similarity;
- no generic AI-agent, provider registry, prompt, RAG, vector database or tool framework;
- domain serializers, notices, cutoff rules and failure semantics remain domain-local;
- Company Research projection, deterministic AI Manifest, provider transport and response validation remain separate bounded responsibilities;
- Typed Beneficiary semantics remains a separate Stage 1 extension rather than modifying the accepted Stage 1 contract;
- no new consolidation review is required until 5–6 implemented slices accumulate or concrete duplication/ownership/test-growth evidence appears.

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Provider rows, series identity, ingestion status and cutoff | Market-data persistence | One explicit Provider per run and series; no silent fallback, relabeling or row-level mixing |
| Canonical market-price value, unit, currency and comparison eligibility | Future separately reviewed market-data/evidence contract | No implementation DoR; downstream code must not invent it |
| Evidence grades, claims, links and conflicts | v0.5 Evidence Ledger | Downstream records freeze exact revisions and links |
| Industry map, nodes, relationships and observations | v0.5B | Exact persisted identities and cutoff-visible revisions only |
| Legacy beneficiary identity/classification and rationale | v0.5C Stage 1 | Preserve exact `direct / secondary / potential` values and revision history |
| Typed beneficiary exposure and execution-evidence profile | `industry_alpha.beneficiary_semantics_*` | Separate append-only D3 profile; no automatic legacy mapping or hidden inference |
| Typed semantic write transaction | `beneficiary_semantics_commands.py` | CLI-only, atomic, expected-latest and append-only |
| Typed semantic read projection | `beneficiary_semantics_query.py` and read-only API | Explicit beneficiary selector and exact revision/evidence provenance |
| Company-research workflow and financial hypotheses | v0.6A | Downstream records bind exact revisions |
| Expectations and valuation observations | v0.6B | Stored research context only without Comparison Eligibility |
| Catalyst and risk assessments | v0.6C | Not monitors, alerts, tasks or timing models |
| Industry/company quality outcome and evidence state | v0.6D | Does not generate price, timing or recommendation state |
| Product overview aggregation | Product-specific read repository/query | Explicit selectors, bounded query counts and no domain-meaning change |
| Company Research AI input projection | `guarded_ai_manifest.py` | Deterministic zero-I/O Manifest, stable item IDs and SHA-256 fingerprint |
| Guarded AI profile and HTTPS request | `guarded_ai_adapter.py` | One disabled-by-default explicit profile, one request, no retry or fallback |
| Guarded AI confirmation and output validation | `guarded_ai_service.py` | Exact fingerprint, strict schema/citations and D3-only result |
| Future ingestion raw capture and review state | Deferred / not assigned | Restart requires a new explicit source decision and Architecture Preflight |
| Research-priority comparison, score or ordering | Unassigned pending next Strict Architecture Preflight | Must not be inferred from recency, evidence count, price context or AI output |

## Shared architecture invariants

1. Local and non-advisory: no advice, performance promise, broker, real order or automated trading.
2. Deterministic calculations and accepted state stay outside LLM ownership.
3. Imports, startup, tests, CI, fixture demos and ordinary reads perform no hidden external network access.
4. Exact IDs, series keys, scopes, dates, revisions and selectors are explicit.
5. Downstream accepted records freeze exact revisions and links.
6. Corrections append revisions; accepted history is not mutated through ordinary paths.
7. Information cutoff and recorded UTC chronology both prevent later-information leakage.
8. Conflicts, contradictions, missing evidence and uncertainty remain visible.
9. Identity, revision and links commit or roll back together.
10. Ordering, revision allocation, decimal text and strict JSON are deterministic across supported databases.
11. Fixture success paths use contracts reachable through reviewed production boundaries.
12. Mutations, notifications, tasks and portfolio state require separate authorization.
13. Credentials and raw connection details never enter source, fixtures, Issues, PRs, logs or user errors.
14. Capability, product-surface and consolidation merges do not change released version without a separate release decision.
15. A product reading surface cannot upgrade Semantic Level or Derivation Level through display, non-null fields or inference.
16. Initial overview query count remains bounded independently of displayed row count unless explicitly reviewed.
17. External-source ingestion requires explicit source authorization and may not appear as hidden runtime or test network access.
18. Candidate entity matching is not accepted identity; human review is required before accepted evidence linkage unless a reviewed deterministic contract says otherwise.
19. Model-generated text is D3 draft assistance and cannot self-promote to accepted D0, D1, D2 or domain state.
20. Guarded AI may consume only an explicit Manifest of accepted persisted inputs and may not fetch missing evidence or mutate accepted records.
21. A remote Guarded AI request requires local preview, explicit confirmation, exact expected fingerprint and one explicit provider/model profile.
22. Unknown model citations, malformed output, fingerprint mismatch and prohibited recommendation/price language fail closed.
23. No generic AI-agent, provider registry, prompt framework, RAG layer or tool system without a separate Architecture Preflight.
24. Typed beneficiary values remain analyst-owned D3 judgments; closed vocabularies and evidence checks do not convert them into D2 rules.
25. Legacy and typed beneficiary classifications may disagree; disagreement is visible history, not an automatic correction or mapping.
26. No research-priority comparison may collapse industry benefit, company execution, evidence quality, valuation context and risk into an unexplained total.

## Semantic and derivation levels

### Semantic Level

- **L0 — Raw Provider Data:** source output before internal normalization; audit only.
- **L1 — Provider Normalized:** project fields with Provider-specific constraints; not automatically comparable.
- **L2 — Standardized:** standardized through an explicit accepted contract; usable only within that contract.
- **L3 — Canonical:** identity, measurement, unit, currency, market, adjustment, provenance, cutoff, chronology, decimal and missing-state contract. No current price implementation has reached L3.

A level cannot be upgraded through inference, non-null fields, UI display, AI output or guesswork.

### Evidence Qualification / Derivation Level

- **D0 — Direct Fact:** directly supported by an explicit source.
- **D1 — Deterministic Aggregation:** fully recorded inputs, scope, algorithm and missing treatment.
- **D2 — Rule Classification:** explicit versioned rules and responsibility boundary.
- **D3 — Analytical Judgment:** analysis or interpretation, including typed beneficiary semantics and AI drafts.

D3 does not automatically enter buy/sell guidance, target prices, return promises, trading signals or cross-company rankings.

## Capability matrix

| Capability | Merged boundary | Remaining boundary |
| --- | --- | --- |
| Market-data persistence | Complete-snapshot PostgreSQL persistence, ingestion attempts, canonical series and cutoff-aware reads | Canonical market-price evidence still has no implementation DoR |
| Market Cockpit | Read-only selected-scope breadth/risk, context, liquidity and descriptive price behavior | No official full-market, valuation, signal or recommendation claims |
| Evidence Ledger / Industry Map | Evidence, claims, conflicts, map identities and exact revisions | No external automated evidence acquisition |
| Stage 1 beneficiary | Legacy beneficiary identity/classification and candidate-pool handoff | No automatic full-market beneficiary discovery |
| Typed Beneficiary Semantics | Merged append-only exposure and execution-evidence profiles | No automatic mapping, extraction, ranking or recommendation |
| Company Research v0.6A-v0.6D | Financial hypotheses, expectations, valuation observations, catalysts, risks and quality judgments | No automatic acceptance, price judgment or recommendation |
| Evidence Intelligence | Merged read-only Research Change Feed | No attention-to-opportunity promotion |
| Industry Research | Merged beneficiary workspace plus explicit typed-semantic detail | No cross-company research-priority comparison |
| Company Research | Merged exact company workspace | No cross-company ranking, computed expectation gap or price-attractiveness judgment |
| Guarded AI | Merged company-scoped preview and explicit ephemeral D3 generation | No second AI job, persisted draft, tools, retrieval or accepted-state mutation |
| Evidence Ingestion | Not implemented and deferred | Requires explicit source authorization and restart Architecture Preflight |
| Research Priority Comparison | Not implemented | Requires next Strict Architecture Preflight |
| Canonical Price / Comparison Eligibility | Not implemented | Separate Architecture Preflight required |

## Architecture debt register

- **D1 Documentation drift — resolved by this sync:** baseline now records PR #165 and PR #169.
- **D2 Repeated Stage 2 structure — bounded:** neutral mechanics are shared; generic graph loading remains unjustified.
- **D3 Read utilities — reviewed:** evidence serializers and domain notices remain local.
- **D4 Command lifecycle and concurrency — partially reduced:** integrity translation and process-local locks are shared; allocation and transactions remain local.
- **D5 ORM lifecycle — bounded:** accepted listener/import/mapper/metadata compatibility remains in place.
- **D6 Test-matrix growth — bounded:** shared-invariant and domain-semantic tests remain distinct.
- **D7 Fixture-versus-production Provider reachability — deferred:** Hithink live contract and permission are not established.
- **D8 Canonical market-price semantics — unresolved:** no canonical-price implementation DoR.
- **D9 Product overview query architecture — resolved for current surfaces:** bounded query boundaries remain product-local.
- **D10 Consolidation cadence — reset:** new risk-tiered cadence is 5–6 slices or concrete duplication/ownership evidence.
- **D11 Evidence-ingestion source and review ownership — deferred.**
- **D12 Guarded AI ownership — resolved for v1.**
- **D13 Typed beneficiary evidence semantics — resolved for v1:** ownership, taxonomy, evidence, revision, migration and UI boundaries are implemented.
- **D14 Research-priority comparison semantics — unresolved:** component ownership, comparison eligibility, missing treatment and non-advisory presentation require a Strict Architecture Preflight.

## Accepted product sequence

Completed:

1. Evidence Intelligence / Research Change Feed — PR #139;
2. Industry Beneficiary Workspace v1 — PR #143;
3. first reading-surface consolidation — PR #145;
4. Company Research Workspace v1 — PR #151;
5. Guarded AI Research Assistance v1 — PR #161;
6. Company Research and Guarded AI consolidation — PR #163;
7. risk-tiered governance workflow — PR #167;
8. Typed Beneficiary Evidence Semantics v1 Architecture Preflight — PR #165;
9. Typed Beneficiary Evidence Semantics v1 implementation — PR #169.

Deferred:

- Evidence Ingestion Issue #154 / closed-unmerged PR #155;
- no ingestion implementation, migration, dependency, source adapter or runtime behavior reached `main`.

## Current authorization state

- Typed Beneficiary Evidence Semantics v1 is merged and Issue #168 is completed.
- No active production implementation, schema, migration, Provider, external-network, AI-transmission, release or version change is authorized.
- Owner authorization advances only the next roadmap architecture phase.
- The next gate is a Strict Architecture Preflight for Company Research Priority Comparison v1.
- No implementation task may merge before independent fixed-head architecture and implementation reviews.
- Evidence Ingestion remains deferred.
- Canonical Price and Comparison Eligibility remain separate and unauthorized.
- Buy/sell/hold, target price, expected return, portfolio and trading remain prohibited.

## Next Strict architecture gate: Company Research Priority Comparison v1

Candidate user job:

> For one explicit persisted Industry Map or candidate-pool revision, review multiple exact company-research records side by side across industry benefit, typed execution evidence, financial transmission, expectations, catalysts, risks, quality judgments, conflicts and freshness, without hiding the complete beneficiary universe or issuing investment recommendations.

The Architecture Preflight must decide:

1. exact comparison identity, selector and frozen input revisions;
2. whether the first slice is component-only comparison, categorical research status, deterministic score or no computed ordering;
3. ownership of industry certainty, beneficiary execution, financial transmission, expectations, catalyst, risk, evidence quality and freshness components;
4. separation of industry-benefit certainty from investment-attractiveness research judgment;
5. missing, disputed, stale and not-applicable treatment;
6. rule version, weights, penalties and explanation if any D2 classification or score is proposed;
7. whether any price or valuation comparison requires Canonical Price and Comparison Eligibility and therefore must be excluded or stopped;
8. cutoff, recorded UTC, supersession and historical-freeze behavior;
9. query-count and complete-universe visibility requirements;
10. explicit D0/D1/D2/D3 presentation and non-advisory language;
11. production-realistic offline golden path and fail-closed path;
12. schema/migration decision, rollback and downgrade behavior;
13. exact API/UI, tests, exclusions and stop conditions.

The preflight must stop if:

- comparison requires hidden company, industry, price, currency or unit inference;
- a total score cannot expose deterministic inputs and missing treatment;
- price attractiveness cannot be separated from non-canonical price context;
- complete beneficiary-universe visibility would be lost;
- output would function as buy/sell/hold guidance or conceal conflicts.

## Locked exclusions for the next gate

- no external evidence acquisition, crawling, scraping, browsing or hidden network;
- no automatic accepted evidence promotion;
- no automatic company, industry, market, exchange, currency or price identity inference;
- no AI-owned score, ranking, taxonomy or accepted field state;
- no generic agent, RAG, vector database, tools or provider framework;
- no fair value, target price, expected return, upside/downside or buy/sell/hold state;
- no monitoring, alerts, tasks, portfolio or trading;
- no release or version change.

## Preserved Canonical Price no-DoR conclusion

Canonical Price remains a parallel infrastructure track and is required before canonical price comparison, price judgment or Comparison Eligibility.

Unauthorized assumptions remain:

- exchange inference from security-code prefix;
- treating null exchange as a specific market;
- defaulting currency without recorded source;
- inferring unit or currency from Provider name;
- silent fallback to another Provider;
- treating a linked daily-price row, valuation `observed_value` or AI output as automatically canonical.

No prospective implementation is authorized by this document alone.
