# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and an accepted linked GitHub Issue controls a specific task.

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D plus reviewed read-only product surfaces.
- Provider-status synchronization base: `ca2a9fa0ca4daea6b7318a50851272b74c4dc115`.
- Accepted application/product baseline: `c24b61822e995ee48ae9f06e5cd1e97a47b43be2`.
- Active application implementation, migration, release or Provider authorization: none.
- Current next product gate: Company Research Workspace v1 Architecture Preflight, after this baseline synchronization is independently reviewed and merged.

Docs-only synchronization may advance `main` without changing release, capability or runtime behavior. This document records accepted current state; it does not itself authorize implementation.

## Product boundary

AQuantAI is a local-first, personal-use, research-only and non-advisory workbench. It is not a broker, order-management system, automated-trading system, investment-advice service, multi-user SaaS product or production deployment platform.

Deterministic calculations, canonicalization, selectors and workflow state belong to reviewed application code. An LLM may assist only behind an explicit adapter and may not own evidence qualification, deterministic state, execution or trading behavior.

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
```

Downstream records freeze exact accepted upstream revisions and links. They do not silently select newer records, infer missing state or rewrite historical meaning.

## Current runtime and product surfaces

When the configured database and local assets are available, the reviewed runtime contains:

1. the existing local fixture-backed Dashboard;
2. database-backed read-only Market Cockpit and Industry Alpha APIs/demos;
3. Evidence Intelligence / Research Change Feed from PR #139;
4. Industry Beneficiary Workspace v1 from PR #143.

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
- preserves exact `direct / secondary / potential` and assessment-state values;
- uses a fixed-count scalar overview path and one explicit map-detail load;
- loads full beneficiary or Stage 2 detail only after explicit user action;
- does not claim full-market exhaustive coverage and does not rank beneficiaries.

### Product reading-surface consolidation decision

Issue #144 / PR #145 completed the required review after two product/domain slices.

Accepted decisions:

- no production consolidation refactor is required before the next product preflight;
- do not create a generic workspace framework merely for router, static-page or DOM similarity;
- Evidence, Stage 1 and Stage 2 domain serializers, notices, cutoff rules and failure semantics remain domain-local;
- Evidence Intelligence and Industry Research retain their bounded product-specific overview repositories;
- existing Stage 2 list services use identity listing plus one full graph load per identity and must not be composed for a new product overview;
- a future company workspace requires one explicit company identity and a new bounded scalar aggregation boundary;
- stable runtime behavior remains unchanged by the consolidation review.

## Accepted future Provider direction

Issue #108 and PR #109 accept Hithink as a preferred future A-share Provider candidate, not an active default or implemented Provider. AKShare remains an explicit, separate implemented Provider path, and existing runs and series remain immutable and readable.

One ingestion run and one canonical series contain exactly one Provider. Silent fallback, Provider relabeling and row-level Provider mixing are prohibited. A caller may explicitly choose another reviewed run or series; persistence must not hide the distinction.

Issue #112 / PR #113 did not establish a live Hithink contract, permission or data-use acceptance. No Hithink code, dependency, runtime/default-Provider change, schema change or migration reached `main`. Hithink may be reconsidered only through a new Architecture Preflight and explicit authorization.

## Accepted canonical market-price direction

Issue #124 / PR #125 accept that standalone canonical market-price evidence has independent value for point-in-time inspection, audit and later downstream provenance. The preferred future owner is a separately reviewed market-data/evidence contract, not Stage 2 valuation or a future price-judgment domain.

Provider-normalized rows, persisted `DailyPriceRecord` rows, latest-series/cutoff-aware reads, canonical evidence, v0.6B valuation observations, Comparison Eligibility and later judgment state remain separate boundaries.

A linked `daily_price` row or a generic valuation `observed_value` is context only. It is not automatically:

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
- `industry_alpha.stage2_query_values`: required UTC normalization, date-granular visibility and text formatting for the reviewed domains;
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
| v0.5A-v0.5C | Evidence ledger, industry maps, beneficiary classifications and candidate-pool handoff | No full-market beneficiary discovery; typed roadmap taxonomy remains separate |
| v0.6A | Company research and financial-transmission hypotheses | Product overview aggregation is not yet implemented |
| v0.6B | Expectations and valuation observations with optional local price provenance | `observed_value` is not automatically comparison eligible |
| v0.6C | Catalyst and risk assessments | Not monitoring, alerts, tasks, timing or recommendation state |
| v0.6D | Industry and company quality judgments | No price, timing, ranking or formal recommendation state |
| Evidence Intelligence | Merged read-only Research Change Feed | No automated attention-to-opportunity promotion |
| Industry Research | Merged Industry Beneficiary Workspace v1 | No new taxonomy, inferred discovery or valuation filtering |
| Company Research product surface | Not implemented | Requires separate Architecture Preflight and Definition of Ready |
| v0.6E | Superseded planning only | Not implemented or authorized |
| v0.7+ | Prospective only | Requires Architecture Preflight and Definition of Ready |

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Provider rows, series identity, ingestion status and cutoff | Market-data persistence | One explicit Provider per run and series; no silent fallback, relabeling, row-level mixing or cross-run stitching |
| Canonical market-price value, measurement kind, unit, currency and decimal normalization | Future separately reviewed market-data/evidence contract | No implementation DoR; downstream code must not invent it |
| Evidence grades, claims, links and conflicts | v0.5 evidence ledger | Downstream records freeze exact revisions and links |
| Industry map, nodes, relationships and observations | v0.5B | Exact persisted identities and cutoff-visible revisions only |
| Stage 1 beneficiary classification and rationale | v0.5C | Preserve exact stored taxonomy and revision history; no inferred remapping |
| Company-research workflow and financial hypotheses | v0.6A | Downstream records bind exact revisions |
| Expectations and valuation observations | v0.6B | Stored research context only without later Comparison Eligibility |
| Catalyst and risk assessments | v0.6C | Not monitors, alerts, tasks or timing models |
| Industry/company quality outcome and evidence state | v0.6D | Does not generate price, timing or recommendation state |
| Product overview aggregation | Product-specific read repository/query | Must use explicit selectors and bounded query counts; must not alter domain meaning |
| Shared frozen-boundary mechanics | `stage2_boundary.py` | Exact accepted boundary mechanics; semantics remain local |
| Ordered scalar repository loading | `stage2_repository_rows.py` | Explicit filtering and caller-owned ordering only |
| Evidence read serialization | Owning Evidence/Stage 1/Stage 2 query module | Remains domain-local under PR #93 and PR #145 decisions |
| Revision allocation and database lock strategy | Owning command module | Remains domain-local |
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
16. Initial overview query count must remain bounded independently of displayed row count unless a reviewed task explicitly authorizes otherwise.

## Semantic Level

Semantic Level defines consumption eligibility, not quality. A level cannot be upgraded through inference, non-null fields, UI display or guesswork.

### L0 — Raw Provider Data

Direct Provider output before internal normalization.

Allowed:

- raw auditing;
- source inspection;
- adapter diagnostics.

Not automatically assumed:

- standardized meaning;
- verified unit or currency;
- cross-series comparability.

### L1 — Provider Normalized

Data normalized into project fields while retaining Provider-specific constraints.

Allowed:

- source-attributed read-only display;
- deterministic local statistics within one explicit series.

Not automatically allowed:

- cross-Provider or cross-asset comparison;
- canonical comparison;
- valuation judgment;
- investment signals.

### L2 — Standardized

Measurement kind, format, unit or another required field is standardized through an explicit accepted contract.

Allowed:

- deterministic analysis and comparison only within that contract.

Not automatically equivalent to:

- full canonical evidence;
- all-period comparability;
- all-Provider compatibility.

### L3 — Canonical

Satisfies the accepted canonical contract, including identity, unit, currency, market, adjustment semantics, Provider/series/run/row provenance, cutoff and UTC visibility, historical freeze method, decimal contract and missing-state contract.

Only L3 data satisfying the corresponding contract may enter authorized canonical comparison or subsequent Comparison Eligibility.

## Evidence Qualification / Derivation Level

### D0 — Direct Fact

A fact directly supported by an explicit source, such as an announcement, import timestamp or exact Provider-normalized value.

### D1 — Deterministic Aggregation

Produced from a fully recorded input set, scope, time window and deterministic algorithm.

D1 must disclose:

- input set;
- time window;
- deduplication rules;
- missing-value rules;
- aggregation algorithm;
- sorting rules.

### D2 — Rule Classification

Depends on explicit, versioned rules.

D2 must expose:

- rule version;
- classification source;
- human/system responsibility boundary.

### D3 — Analytical Judgment

Contains analysis, interpretation or research judgment.

D3 must be displayed separately from D0/D1 and must not automatically enter:

- buy or sell suggestions;
- target prices;
- return promises;
- trading signals;
- cross-company rankings.

## Development task classification

### Architecture Task

Full Architecture Preflight, Definition of Ready and fixed-head review are required when work changes schema, migration, Provider, data meaning, Semantic Level, revision rules, cutoff, provenance, fallback/identity/join rules, persistent state, computation contracts, rule classifications or security.

An Architecture Task must not be disguised as UI display.

### Product Task

A Product Task may use the lighter process only when it:

- reads accepted data contracts only;
- adds no persistent state;
- changes no field meaning, invariant, computation, Provider behavior, cutoff, revision or provenance;
- upgrades no Semantic Level;
- does not disguise D2/D3 as D0/D1.

Typical Product Tasks are bounded read-only pages, query composition, reading-experience optimization, accessibility and serialization display without semantic change.

## Architecture debt register

- **D1 Documentation drift — synchronized by Issue #146:** product surfaces and sequence are updated after PRs #139, #143 and #145.
- **D2 Repeated Stage 2 structure — bounded:** neutral frozen-boundary and ordered-row mechanics are shared; generic graph loading remains unjustified.
- **D3 Read utilities — reviewed:** evidence serializers and domain notices remain local.
- **D4 Command lifecycle and concurrency — partially reduced:** integrity translation and process-local locks are shared; allocation and transaction semantics remain local.
- **D5 ORM lifecycle — bounded:** accepted listener/import/mapper/metadata compatibility remains in place.
- **D6 Test-matrix growth:** shared-invariant tests and domain-semantic tests remain distinct.
- **D7 Fixture-versus-production Provider reachability — deferred:** Hithink live contract and permission are not established.
- **D8 Canonical market-price semantics — unresolved:** no canonical-price implementation DoR.
- **D9 Product overview query architecture — active next-stage concern:** a company workspace needs a bounded scalar aggregation boundary and must not compose Stage 2 N+1 list services.
- **D10 Consolidation cadence:** review after every two product/domain slices and earlier when ownership ambiguity appears; PR #145 found no production refactor necessary.

## Development gates

1. **Architecture Preflight:** problem, ownership, inputs, golden/failure paths, migration/dependency impact, conflicts, smallest slice and exclusions.
2. **Definition of Ready:** one objective, accepted contracts, ownership, reachable paths, explicit selectors/chronology, migration decision, bounded tests and stop conditions.
3. **Planning before implementation:** architecture decisions precede implementation Issue and task snapshot.
4. **Reset threshold:** reset when ownership is ambiguous, semantics depend on inference/defaults, production cannot reach the path, or authoritative documents disagree.
5. **Consolidation cadence:** review documentation, duplicated infrastructure, schema/link growth, tests, APIs and next-stage reachability.
6. **Review evidence:** green CI is necessary but not sufficient; ownership, reachability, semantics and scope must also pass.
7. **Fixed-head gate:** independent approval must name the exact reviewed HEAD before an architecture or implementation PR is merged.

## Accepted product sequence through consolidation

Completed:

1. architecture rebalance and Evidence Intelligence roadmap;
2. Evidence Intelligence Architecture Preflight;
3. Research Change Feed implementation — PR #139;
4. Industry Beneficiary Workspace v1 Architecture Preflight — PR #141;
5. Industry Beneficiary Workspace v1 implementation — PR #143;
6. product reading-surface consolidation review — PR #145;
7. current product-surface baseline synchronization — Issue #146 / its Draft PR.

Current authorization state:

- no Company Research implementation is authorized;
- no schema, migration, Provider, release or version change is authorized;
- the next product action after this synchronization is a separate Architecture Preflight.

## Recommended forward sequence

This ordering is not implementation authorization. Every item requires its own linked Issue and applicable review gate.

1. merge the current product-surface baseline synchronization;
2. Company Research Workspace v1 Architecture Preflight;
3. one bounded read-only Company Research Workspace Product Task, only if the preflight receives independent Definition-of-Ready approval;
4. separately characterize any missing typed beneficiary semantics rather than mixing them into the company workspace;
5. continue the parallel canonical-price and Comparison Eligibility infrastructure track;
6. consider cross-company research-priority comparison only after its required deterministic inputs and eligibility contracts are accepted;
7. reconsider Watchlist, monitoring or later AI assistance only through separate authorization.

## Company Research Workspace v1 as the next product gate

The candidate user job is:

> Select one explicitly persisted Stage 2 company-research identity and read, at one optional cutoff, its exact frozen Stage 1 background, financial-transmission hypotheses, expectations, valuation observations, catalysts, risks, quality judgments, conflicts, missing evidence and revision chronology in one non-advisory workspace.

Existing v0.6A-v0.6D persistence is expected to supply the candidate path through exact foreign keys from one explicit `company_research_id`.

The preflight must establish:

1. explicit selector contract and whether `map_id` is context, filter or unnecessary;
2. exact company identity and stock-provenance display;
3. fixed small query count independent of the number of downstream records;
4. latest cutoff-visible revision versus exact frozen historical revision behavior;
5. overview fields versus explicit on-demand detail;
6. handling of absent modules, multiple incompatible exact identities and integrity failures;
7. production-realistic offline fixture parity;
8. date-granular information cutoff and recorded UTC chronology;
9. 422, 404, 503 and fail-closed behavior;
10. D0-D3 and L0-L3 display qualification;
11. migration decision;
12. exact tests, exclusions and stop conditions.

The preflight must not compose these existing list services as its initial overview:

- `Stage2CompanyResearchQueryService.list_research()`;
- `Stage2ExpectationQueryService.list_expectations()`;
- `Stage2ValuationQueryService.list_valuations()`;
- `Stage2CatalystQueryService.list_catalysts()`;
- `Stage2RiskQueryService.list_risks()`;
- `Stage2IndustryJudgmentQueryService.list_judgments()`;
- `Stage2CompanyJudgmentQueryService.list_judgments()`.

Those services load one owning-domain graph per identity and remain valid for their accepted domain APIs, but they are not a bounded multi-domain product overview.

## Locked exclusions for the next product gate

The Company Research Workspace v1 preflight and any resulting first Product Task must exclude:

- Canonical Price implementation;
- Comparison Eligibility;
- computed expectation gap;
- fair value;
- target price;
- expected return;
- upside/downside percentage;
- cross-company ranking;
- total attractiveness score;
- buy/sell/hold;
- good-price or good-timing state;
- Watchlist, alerts, reminders or task lifecycle;
- portfolio or trading state;
- inferred identity from stock code, company name, Provider industry, free text, title similarity or LLM output;
- automatic relinking to newer compatible-looking revisions;
- schema, migration, Provider, release or version change unless a later separate Architecture Task explicitly authorizes it.

## Preserved canonical-price no-DoR conclusion

Canonical price remains a parallel infrastructure track and is still required for canonical comparison, price judgment and Comparison Eligibility.

Unauthorized assumptions remain:

- exchange inference from security-code prefix;
- treating null exchange as a specific market;
- defaulting currency without recorded source;
- inferring unit/currency from Provider name;
- silent fallback to another Provider;
- treating a linked daily-price row or valuation `observed_value` as automatically canonical.

No prospective item is authorized by this document alone.
