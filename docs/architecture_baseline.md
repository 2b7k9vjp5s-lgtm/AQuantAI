# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and an accepted linked GitHub Issue controls a specific task.

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D plus reviewed read-only product surfaces and bounded Guarded AI Research Assistance v1.
- Accepted application/product baseline: `2e3722fdf224a58df0c870e2fa167b4f8e742b49`.
- Active application implementation, migration, release or Provider authorization: none.
- Evidence Ingestion status: deferred by owner decision after Issue #154 / closed-unmerged PR #155; no ingestion runtime capability reached `main`.
- Guarded AI status: Architecture Preflight merged through PR #159 and bounded implementation merged through PR #161.
- Current required gate: mandatory consolidation review under Issue #162 after Company Research Workspace v1 and Guarded AI Research Assistance v1.
- No later product/domain implementation or Architecture Preflight is authorized until Issue #162 is independently approved, merged and explicitly advanced by the owner.

Documentation synchronization may advance `main` without changing release, capability or runtime behavior. This document records accepted current state; it does not itself authorize implementation.

## Product boundary

AQuantAI is a local-first, personal-use, research-only and non-advisory workbench. It is not a broker, order-management system, automated-trading system, investment-advice service, multi-user SaaS product or production deployment platform.

Deterministic calculations, canonicalization, selectors and workflow state belong to reviewed application code. An LLM may assist only behind an explicit bounded adapter and may not own evidence qualification, deterministic state, execution or trading behavior.

## Implemented dependency direction

```text
market-data evidence
  -> v0.5 evidence ledger
  -> Stage 1 industry map and beneficiary boundary
  -> v0.6A company research and financial-transmission hypotheses
  -> v0.6B expectations and valuation observations
  -> v0.6C catalyst and risk assessments
  -> v0.6D industry and company quality judgments
  -> read-only product surfaces over exact persisted boundaries
  -> optional company-scoped Guarded AI D3 draft assistance
```

Downstream accepted records freeze exact accepted upstream revisions and links. They do not silently select newer records, infer missing state or rewrite historical meaning.

Guarded AI consumes only an explicit deterministic Manifest projected from one accepted Company Research workspace. It cannot choose records, query the database, browse, search, retrieve missing evidence or mutate accepted state.

## Current runtime and product surfaces

When the configured database and local assets are available, the reviewed runtime contains:

1. the existing local fixture-backed Dashboard;
2. database-backed read-only Market Cockpit and Industry Alpha APIs/demos;
3. Evidence Intelligence / Research Change Feed from PR #139;
4. Industry Beneficiary Workspace v1 from PR #143;
5. Company Research Workspace v1 from PR #151;
6. Guarded AI Research Assistance v1 from PR #161, disabled by default.

### Evidence Intelligence / Research Change Feed

- Chinese-first read-only product surface for recent evidence and research changes;
- bounded event-source scalar query plan;
- explicit time window, cutoff, provenance and deterministic ordering;
- no opportunity ranking, score, recommendation or trading state;
- detail navigation reuses accepted owning-domain contracts.

### Industry Beneficiary Workspace v1

- Chinese-first read-only `/industry-research` workspace;
- requires an explicit persisted industry-map selection;
- shows the complete cutoff-visible persisted Stage 1 beneficiary set for that selected map;
- preserves exact stored beneficiary and assessment values;
- uses a fixed-count scalar overview path and one explicit map-detail load;
- loads full beneficiary or Stage 2 detail only after explicit user action;
- does not claim full-market exhaustive coverage and does not rank beneficiaries.

### Company Research Workspace v1

- Chinese-first read-only `/company-research` workspace;
- requires one explicit persisted `company_research_id` and never silently selects the first row;
- does not infer identity from stock code, company name, Provider industry, free text, title similarity or LLM output;
- selector uses exactly 3 SQL statements;
- selected workspace uses exactly 14 SQL statements;
- query count is independent of hypothesis, expectation, valuation, catalyst, risk, judgment, claim and evidence row growth;
- shows exact frozen Stage 1, stock, ingestion and v0.6A-v0.6D revision provenance;
- keeps latest cutoff-visible revisions separate from exact frozen historical revisions;
- displays historical revision mismatch and never automatically relinks it;
- loads full owning-domain claim/evidence detail only after explicit user action;
- uses safe DOM methods and no untrusted `innerHTML`;
- presents valuation observations and optional L1 local-price provenance only;
- does not create Canonical Price, Comparison Eligibility, fair value, target price, expected return, ranking, score or recommendation state.

### Guarded AI Research Assistance v1

- available only inside one explicitly selected Company Research workspace;
- local preview route projects an immutable deterministic Manifest and exact SHA-256 fingerprint;
- Manifest projection performs zero SQL, filesystem or network I/O beyond the already completed workspace read;
- request-time generation metadata is excluded from the fingerprint;
- generation requires explicit remote-transmission confirmation and the exact expected fingerprint;
- the server reloads the one Company Research workspace and rebuilds the Manifest before adapter invocation;
- fingerprint mismatch returns `409` before network access;
- disabled by default with one explicit HTTPS OpenAI-compatible profile;
- no default provider, endpoint or model;
- no retry, provider/model fallback, streaming, tools, browsing, search, retrieval, embeddings or background execution;
- strict application-owned response schema, section, fingerprint and Manifest-item citation validation;
- prohibited recommendation and price-judgment language fails closed;
- output is ephemeral D3 draft assistance only;
- no prompt, model response, draft identity, revision, review state or accepted-domain mutation is persisted.

### Product reading-surface consolidation decision

Issue #144 / PR #145 completed the first required review after Evidence Intelligence and Industry Beneficiary Workspace v1.

Accepted decisions remain:

- no production consolidation refactor was required before Company Research;
- do not create a generic workspace framework merely for router, static-page or DOM similarity;
- Evidence, Stage 1 and Stage 2 domain serializers, notices, cutoff rules and failure semantics remain domain-local;
- each reading surface retains its bounded product-specific overview repository/query boundary;
- existing Stage 2 list services remain valid owning-domain reads but are not composed into multi-domain overview pages;
- stable schemas remain unchanged.

### Company Research and Guarded AI consolidation gate

Company Research Workspace v1 and Guarded AI Research Assistance v1 are the next two implemented product/domain slices after PR #145. Mandatory consolidation review is active under Issue #162.

The candidate consolidation finding is:

- no production refactor;
- keep the Company Research workspace projection product-local;
- keep deterministic Manifest construction separate from provider transport and response validation;
- do not create a generic AI-agent, provider, prompt, RAG or product-page framework;
- preserve the one company-scoped, explicit-confirmation, ephemeral D3 job;
- consider Typed Beneficiary Evidence Semantics only as a later Architecture Preflight candidate.

These findings are not accepted until the Issue #162 Draft PR receives independent fixed-head review and owner authorization.

## Accepted future Provider direction

Issue #108 and PR #109 accept Hithink as a preferred future A-share Provider candidate, not an active default or implemented Provider. AKShare remains an explicit, separate implemented Provider path, and existing runs and series remain immutable and readable.

One ingestion run and one canonical series contain exactly one Provider. Silent fallback, Provider relabeling and row-level Provider mixing are prohibited. A caller may explicitly choose another reviewed run or series; persistence must not hide the distinction.

Issue #112 / PR #113 did not establish a live Hithink contract, permission or data-use acceptance. No Hithink code, dependency, runtime/default-Provider change, schema change or migration reached `main`. Hithink may be reconsidered only through a new Architecture Preflight and explicit authorization.

The Guarded AI provider profile is a separate optional model-transport configuration. It does not become a market-data Provider and may not relabel, mix or supply market evidence.

## Accepted canonical market-price direction

Issue #124 / PR #125 accept that standalone canonical market-price evidence has independent value for point-in-time inspection, audit and later downstream provenance. The preferred future owner is a separately reviewed market-data/evidence contract, not Stage 2 valuation or a future price-judgment domain.

Provider-normalized rows, persisted `DailyPriceRecord` rows, latest-series/cutoff-aware reads, canonical evidence, v0.6B valuation observations, Comparison Eligibility and later judgment state remain separate boundaries.

A linked `daily_price` row, a generic valuation `observed_value` or AI-generated text is context only. It is not automatically:

- canonical current price;
- comparison eligible;
- a normalized valuation multiple;
- fair value;
- target price;
- expected return;
- upside or downside.

No canonical-price implementation has Definition of Ready. Provider measurement semantics, explicit unit/currency, historical freezing, decimal limits, exact Provider/series/run/row selection, chronology, missing-state vocabulary, migration and rollback remain unresolved. Comparison Eligibility remains a later, separate deterministic contract.

## Accepted neutral Stage 2 infrastructure boundaries

The following neutral boundaries are accepted:

- `industry_alpha.stage2_boundary`: exact shared frozen-boundary mechanics;
- `industry_alpha.stage2_repository_rows`: stateless ordered scalar row loading;
- `industry_alpha.stage2_query_values`: required UTC normalization, date-granular visibility and text formatting for reviewed domains;
- `industry_alpha.stage2_integrity`: SQLAlchemy `IntegrityError` translation only;
- `industry_alpha.stage2_revision_locks`: guarded process-local `(kind, UUID) -> RLock` registry only;
- `industry_alpha.orm_append_only`: neutral append-only ORM mutation scan only.

Domain semantics remain local. Repository graph assembly, optional-ID normalization, missing-parent policy, link selection, evidence serialization, claim projection, notices, aggregate errors, command transactions, row locks, revision-number allocation, supersession and retry policy remain with their owning domains unless a later characterization proves a neutral shared contract.

The current implementable path does not include v0.6E price judgment, timing judgment, Watchlist tasks, Paper Portfolio, simulated trades, portfolio analysis or Quant Core workflow state.

## Capability matrix

| Capability | Merged boundary | Remaining boundary |
| --- | --- | --- |
| v0.3 market-data persistence | Complete-snapshot PostgreSQL persistence, ingestion attempts, canonical series and cutoff-aware reads | Canonical market-price evidence still has no implementation DoR |
| v0.4A-v0.4E Market Cockpit | Read-only selected-scope breadth/risk, context, liquidity and descriptive price behavior | No official full-market, valuation, regime, signal or recommendation claims |
| v0.5A-v0.5C | Evidence ledger, industry maps, beneficiary classifications and candidate-pool handoff | No full-market beneficiary discovery; typed beneficiary semantics remain separate |
| v0.6A | Company research and financial-transmission hypotheses | No automatic research acceptance or evidence promotion |
| v0.6B | Expectations and valuation observations with optional local price provenance | `observed_value` is not automatically comparison eligible |
| v0.6C | Catalyst and risk assessments | Not monitoring, alerts, tasks, timing or recommendation state |
| v0.6D | Industry and company quality judgments | No price, timing, ranking or formal recommendation state |
| Evidence Intelligence | Merged read-only Research Change Feed | No automated attention-to-opportunity promotion |
| Industry Research | Merged Industry Beneficiary Workspace v1 | No new taxonomy, inferred discovery or valuation filtering |
| Company Research | Merged Company Research Workspace v1 | No cross-company ranking, computed expectation gap or price-attractiveness judgment |
| Guarded AI assistance | Merged company-scoped preview and explicit ephemeral D3 generation | No second AI job, persisted draft, tools, retrieval, accepted-state mutation or fallback |
| Evidence Ingestion | Not implemented; Issue #154 / PR #155 deferred unmerged | Requires a new explicit restart Architecture Preflight; manual PDF import is not a current product prerequisite |
| Typed Beneficiary Evidence Semantics | Prospective architecture candidate only | Field ownership, taxonomy, evidence requirements, revision, migration and UI remain unresolved |
| v0.6E / v0.7+ | Superseded or prospective planning only | Not implemented or authorized |

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Provider rows, series identity, ingestion status and cutoff | Market-data persistence | One explicit Provider per run and series; no silent fallback, relabeling, row-level mixing or cross-run stitching |
| Canonical market-price value, measurement kind, unit, currency and decimal normalization | Future separately reviewed market-data/evidence contract | No implementation DoR; downstream code must not invent it |
| Evidence grades, claims, links and conflicts | v0.5 evidence ledger | Downstream records freeze exact revisions and links |
| Industry map, nodes, relationships and observations | v0.5B | Exact persisted identities and cutoff-visible revisions only |
| Stage 1 beneficiary classification and rationale | v0.5C | Preserve exact stored taxonomy and revision history; no inferred remapping |
| Future typed beneficiary/customer/certification/capacity/production/order semantics | Unassigned pending Architecture Preflight | Must not be inferred from free text, Provider industry, security code or model output |
| Company-research workflow and financial hypotheses | v0.6A | Downstream records bind exact revisions |
| Expectations and valuation observations | v0.6B | Stored research context only without later Comparison Eligibility |
| Catalyst and risk assessments | v0.6C | Not monitors, alerts, tasks or timing models |
| Industry/company quality outcome and evidence state | v0.6D | Does not generate price, timing or recommendation state |
| Product overview aggregation | Product-specific read repository/query | Explicit selectors, bounded query counts and no domain-meaning change |
| Company Research AI input projection | `guarded_ai_manifest.py` | Deterministic zero-I/O Manifest, stable item IDs and SHA-256 fingerprint |
| Guarded AI profile and HTTPS request | `guarded_ai_adapter.py` | One explicit disabled-by-default profile, one request, no retry or fallback |
| Guarded AI confirmation and output validation | `guarded_ai_service.py` | Exact fingerprint comparison, strict schema/citations and D3-only result |
| Guarded AI UI state | Company Research page script | Explicit preview and confirmation; safe DOM; no credential or endpoint display |
| Shared frozen-boundary mechanics | `stage2_boundary.py` | Exact accepted boundary mechanics; semantics remain local |
| Ordered scalar repository loading | `stage2_repository_rows.py` | Explicit filtering and caller-owned ordering only |
| Evidence read serialization | Owning Evidence/Stage 1/Stage 2 query module | Remains domain-local under PR #93 and PR #145 decisions |
| Revision allocation and database lock strategy | Owning command module | Remains domain-local |
| Future ingestion raw capture, normalization, deduplication and review state | Deferred / not assigned | Issue #154 / PR #155 remain design history only; restart requires a new explicit source decision and Architecture Preflight |
| “Good price” and “good timing” | Conceptual future workflow | Not current runtime entities |

## Shared architecture invariants

1. Local and non-advisory: no advice, performance promise, broker, real order or automated trading.
2. Deterministic calculations and state stay outside LLM ownership.
3. Imports, startup, tests, CI, fixture demos and ordinary reads perform no hidden external network access.
4. Exact IDs, series keys, scopes, dates and revisions are explicit.
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
16. Initial overview query count remains bounded independently of displayed row count unless a reviewed task explicitly authorizes otherwise.
17. External-source ingestion requires explicit source authorization and may not appear as hidden runtime or test network access.
18. Candidate entity matching is not accepted identity; human review is required before accepted EvidenceItem or claim linkage unless a later reviewed deterministic contract explicitly says otherwise.
19. Model-generated text is D3 draft assistance unless an independently reviewed deterministic contract says otherwise; it cannot self-promote to D0, D1, accepted D2 or accepted domain state.
20. Guarded AI may consume only an explicit Manifest of accepted persisted inputs and may not browse, crawl, search, infer hidden identity, fetch missing evidence or mutate accepted records as a fallback.
21. A remote Guarded AI request requires local preview, explicit confirmation, an exact expected fingerprint and one explicit provider/model profile.
22. Unknown model citations, malformed output, fingerprint mismatch and prohibited recommendation/price language fail closed with no usable partial draft.
23. No generic AI-agent, provider registry, prompt framework, RAG layer or tool system may be introduced without a separate Architecture Preflight.

## Semantic Level

Semantic Level defines consumption eligibility, not quality. A level cannot be upgraded through inference, non-null fields, UI display, AI output or guesswork.

### L0 — Raw Provider Data

Direct Provider output before internal normalization. Allowed for raw auditing, source inspection and adapter diagnostics. It is not automatically standardized, unit-verified, currency-verified or cross-series comparable.

### L1 — Provider Normalized

Data normalized into project fields while retaining Provider-specific constraints. Allowed for source-attributed read-only display and deterministic local statistics within one explicit series. It is not automatically canonical, comparison eligible or suitable for investment signals.

### L2 — Standardized

Measurement kind, format, unit or another required field is standardized through an explicit accepted contract. Deterministic analysis is allowed only within that contract. L2 is not automatically full canonical evidence or universally comparable.

### L3 — Canonical

Satisfies an accepted canonical contract including identity, unit, currency, market, adjustment semantics, Provider/series/run/row provenance, cutoff and UTC visibility, historical freeze method, decimal policy and missing-state behavior. No current price implementation has reached this level.

## Evidence Qualification / Derivation Level

### D0 — Direct Fact

A fact directly supported by an explicit source, such as an announcement, import timestamp or exact Provider-normalized value.

### D1 — Deterministic Aggregation

Produced from a fully recorded input set, scope, time window and deterministic algorithm. D1 discloses inputs, time window, deduplication, missing-value handling, algorithm and sorting.

### D2 — Rule Classification

Depends on explicit versioned rules. D2 exposes rule version, classification source and human/system responsibility boundary.

### D3 — Analytical Judgment

Contains analysis, interpretation or research judgment. D3 remains separate from D0/D1 and does not automatically enter buy/sell suggestions, target prices, return promises, trading signals or cross-company rankings.

Model-generated summaries, contradiction prompts, missing-evidence prompts, research questions and review checklists are D3 drafts. Their source Manifest, cutoff and model/adapter provenance remain visible, and they do not become accepted Evidence Ledger or Stage 1/Stage 2 state through display, citation or user convenience.

## Development task classification

### Architecture Task

Full Architecture Preflight, Definition of Ready and fixed-head review are required when work changes schema, migration, Provider, data meaning, Semantic Level, revision rules, cutoff, provenance, fallback/identity/join rules, persistent state, computation contracts, rule classifications, external-network boundaries or security.

An Architecture Task must not be disguised as UI display.

### Product Task

A Product Task may use the lighter process only when it reads accepted contracts, adds no persistent state, changes no field meaning/invariant/computation/Provider/cutoff/revision/provenance, upgrades no Semantic Level and does not disguise D2/D3 as D0/D1.

Typical Product Tasks are bounded read-only pages, query composition, reading-experience optimization, accessibility and serialization display without semantic change.

## Architecture debt register

- **D1 Documentation drift — active synchronization:** Issue #162 synchronizes the merged Guarded AI capability and current consolidation gate.
- **D2 Repeated Stage 2 structure — bounded:** neutral frozen-boundary and ordered-row mechanics are shared; generic graph loading remains unjustified.
- **D3 Read utilities — reviewed:** evidence serializers and domain notices remain local.
- **D4 Command lifecycle and concurrency — partially reduced:** integrity translation and process-local locks are shared; allocation and transaction semantics remain local.
- **D5 ORM lifecycle — bounded:** accepted listener/import/mapper/metadata compatibility remains in place.
- **D6 Test-matrix growth — bounded:** shared-invariant tests and domain-semantic tests remain distinct; a second AI job would trigger renewed review.
- **D7 Fixture-versus-production Provider reachability — deferred:** Hithink live contract and permission are not established.
- **D8 Canonical market-price semantics — unresolved:** no canonical-price implementation DoR.
- **D9 Product overview query architecture — resolved for current surfaces:** Company Research uses a bounded 3/14 query boundary and does not compose Stage 2 N+1 list services.
- **D10 Consolidation cadence — active:** Issue #162 is required after Company Research Workspace v1 and Guarded AI v1.
- **D11 Evidence-ingestion source and review ownership — deferred:** Issue #154 / PR #155 remain unmerged design history; no current product path depends on manual PDF import.
- **D12 Guarded AI ownership — resolved for v1:** Company Research projection, deterministic Manifest, adapter transport, response validation and ephemeral D3 rendering have explicit owners.
- **D13 Typed beneficiary evidence semantics — unresolved:** final taxonomy, typed execution evidence, ownership, revision and migration require a separate Architecture Preflight.

## Development gates

1. **Architecture Preflight:** problem, ownership, inputs, golden/failure paths, migration/dependency/network impact, conflicts, smallest slice and exclusions.
2. **Definition of Ready:** one objective, accepted contracts, ownership, reachable paths, selectors/chronology, migration decision, bounded tests and stop conditions.
3. **Planning before implementation:** architecture decisions precede implementation Issue and task snapshot.
4. **Reset threshold:** reset when ownership is ambiguous, semantics depend on inference/defaults, production cannot reach the path, or authoritative documents disagree.
5. **Consolidation cadence:** review documentation, duplicated infrastructure, schema/link growth, tests, APIs and next-stage reachability after every two implemented domain/product slices.
6. **Review evidence:** green CI is necessary but not sufficient; ownership, reachability, semantics and scope must also pass.
7. **Fixed-head gate:** independent approval must name the exact reviewed HEAD before an architecture, consolidation or implementation PR is merged.

## Accepted product sequence

Completed:

1. architecture rebalance and Evidence Intelligence roadmap;
2. Evidence Intelligence Architecture Preflight;
3. Research Change Feed implementation — PR #139;
4. Industry Beneficiary Workspace v1 Architecture Preflight — PR #141;
5. Industry Beneficiary Workspace v1 implementation — PR #143;
6. first product reading-surface consolidation review — PR #145;
7. product-surface baseline synchronization — PR #147;
8. Company Research Workspace v1 Architecture Preflight — PR #149;
9. Company Research Workspace v1 implementation — PR #151;
10. Company Research baseline synchronization — PR #153;
11. owner-approved Evidence Ingestion deferral and route synchronization — PR #157;
12. Guarded AI Research Assistance v1 Architecture Preflight — PR #159;
13. Guarded AI Research Assistance v1 implementation — PR #161.

Active documentation gate:

- Company Research and Guarded AI consolidation review — Issue #162.

Deferred design work:

- Evidence Ingestion Architecture Preflight — Issue #154 / closed-unmerged PR #155;
- no ingestion implementation, migration, dependency, source adapter or runtime behavior reached `main`.

Current authorization state:

- Issue #162 documentation-only consolidation review is the only active gate;
- no new application implementation, Provider, schema, migration, dependency, release or version change is authorized;
- no second AI job, persisted AI state, provider registry, agent, tools, retrieval or background work is authorized;
- Evidence Ingestion remains deferred;
- Canonical Price, Comparison Eligibility, ranking, scoring, target price, expected return and recommendation state remain unauthorized.

## Recommended forward sequence

This ordering is not implementation authorization. Every item requires its own linked Issue and applicable review gate.

1. complete Issue #162 documentation-only consolidation review and independent fixed-head approval;
2. merge its three-file documentation PR only after owner authorization;
3. if the accepted review retains the current finding, open a separate Typed Beneficiary Evidence Semantics Architecture Preflight;
4. create no implementation task until that preflight establishes exact field ownership, source reachability, revision and migration decisions;
5. reconsider Evidence Ingestion only through a new explicit restart decision that avoids manual PDF upload as a required workflow;
6. continue the parallel Canonical Price and Comparison Eligibility infrastructure track only through separate Architecture Preflight;
7. reconsider any second AI job, persisted draft, monitoring, comparison or ranking only through separate authorization.

## Candidate next architecture gate: Typed Beneficiary Evidence Semantics v1

This candidate is not authorized until Issue #162 is accepted and the owner explicitly advances it.

Candidate user job:

> For one explicitly selected persisted Industry Map and one existing Stage 1 beneficiary identity, record and review typed beneficiary exposure and execution-evidence states with exact source, revision, cutoff, conflict and missing-data provenance, without ranking companies or inferring accepted state from free text or AI output.

The Architecture Preflight must establish:

1. authoritative owner and append-only revision identity;
2. whether the capability extends Stage 1 or uses a separate semantic layer;
3. accepted beneficiary taxonomy and compatibility with current `direct / secondary / potential` labels;
4. driver type and subtype ownership;
5. customer, certification, capacity, production and order-stage vocabularies;
6. exact evidence-link requirements;
7. missing, unknown and conflicting-state behavior;
8. deterministic rule versus explicit analyst ownership;
9. cutoff, recorded UTC, supersession and historical-freeze rules;
10. migration and rollback decision;
11. production-realistic offline golden and failure paths;
12. no free-text, Provider-name, security-code or LLM acceptance inference;
13. exact API/UI, tests, exclusions and stop conditions.

The preflight must stop if required fields cannot be sourced or owned without hidden inference.

## Locked exclusions for the next gate

- no Evidence Ingestion restart, PDF requirement, crawling, scraping, browsing or external search;
- no automatic evidence acquisition or accepted evidence promotion;
- no automatic company/industry identity inference;
- no AI-owned taxonomy or accepted field state;
- no generic agent, RAG, vector database, tools or provider framework;
- no cross-company ranking, score or research-priority ordering;
- no Canonical Price or Comparison Eligibility;
- no fair value, target price, expected return, upside/downside, buy/sell/hold or recommendation state;
- no monitoring, alerts, tasks, portfolio or trading;
- no release or version change.

## Preserved canonical-price no-DoR conclusion

Canonical price remains a parallel infrastructure track and is still required for canonical comparison, price judgment and Comparison Eligibility.

Unauthorized assumptions remain:

- exchange inference from security-code prefix;
- treating null exchange as a specific market;
- defaulting currency without recorded source;
- inferring unit/currency from Provider name;
- silent fallback to another Provider;
- treating a linked daily-price row, valuation `observed_value` or AI output as automatically canonical.

No prospective item is authorized by this document alone.