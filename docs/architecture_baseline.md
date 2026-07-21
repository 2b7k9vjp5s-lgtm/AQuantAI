# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and an accepted linked GitHub Issue controls a specific task.

- Released software version: `0.2.0`.
- Merged capability stage: v0.6D plus reviewed read-only product surfaces.
- Provider-status synchronization base: `ca2a9fa0ca4daea6b7318a50851272b74c4dc115`.
- Accepted application/product baseline: `bcc99f20a1486d3d39c737e3fc6d102b940d863e`.
- Active application implementation, migration, release or Provider authorization: none.
- Current next roadmap gate: Slice 4 Evidence Ingestion Architecture Preflight, after this documentation synchronization is independently reviewed and merged.

Documentation synchronization may advance `main` without changing release, capability or runtime behavior. This document records accepted current state; it does not itself authorize implementation.

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
4. Industry Beneficiary Workspace v1 from PR #143;
5. Company Research Workspace v1 from PR #151.

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

### Product reading-surface consolidation decision

Issue #144 / PR #145 completed the required review after Evidence Intelligence and Industry Beneficiary Workspace v1.

Accepted decisions:

- no production consolidation refactor was required before Company Research;
- do not create a generic workspace framework merely for router, static-page or DOM similarity;
- Evidence, Stage 1 and Stage 2 domain serializers, notices, cutoff rules and failure semantics remain domain-local;
- each reading surface retains its bounded product-specific overview repository/query boundary;
- existing Stage 2 list services remain valid owning-domain reads but are not composed into multi-domain overview pages;
- stable schemas remained unchanged.

Only one additional product/domain slice, Company Research Workspace v1, has completed since PR #145. The next Architecture Preflight may proceed without another consolidation pause. Consolidation is required again after the next domain/product slice or earlier if ownership ambiguity appears.

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
| v0.5A-v0.5C | Evidence ledger, industry maps, beneficiary classifications and candidate-pool handoff | No full-market beneficiary discovery; typed roadmap taxonomy remains separate |
| v0.6A | Company research and financial-transmission hypotheses | No automatic research generation or accepted-evidence promotion |
| v0.6B | Expectations and valuation observations with optional local price provenance | `observed_value` is not automatically comparison eligible |
| v0.6C | Catalyst and risk assessments | Not monitoring, alerts, tasks, timing or recommendation state |
| v0.6D | Industry and company quality judgments | No price, timing, ranking or formal recommendation state |
| Evidence Intelligence | Merged read-only Research Change Feed | No automated attention-to-opportunity promotion |
| Industry Research | Merged Industry Beneficiary Workspace v1 | No new taxonomy, inferred discovery or valuation filtering |
| Company Research | Merged Company Research Workspace v1 | No cross-company ranking, computed expectation gap or price-attractiveness judgment |
| Evidence Ingestion | Not implemented | Requires a separate Architecture Preflight and Definition of Ready |
| Guarded AI assistance | Prospective only | Requires explicit adapter, review state and separate authorization |
| v0.6E / v0.7+ | Superseded or prospective planning only | Not implemented or authorized |

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
| Product overview aggregation | Product-specific read repository/query | Explicit selectors, bounded query counts and no domain-meaning change |
| Shared frozen-boundary mechanics | `stage2_boundary.py` | Exact accepted boundary mechanics; semantics remain local |
| Ordered scalar repository loading | `stage2_repository_rows.py` | Explicit filtering and caller-owned ordering only |
| Evidence read serialization | Owning Evidence/Stage 1/Stage 2 query module | Remains domain-local under PR #93 and PR #145 decisions |
| Revision allocation and database lock strategy | Owning command module | Remains domain-local |
| Future ingestion raw capture, normalization, deduplication and review state | Not yet assigned | Must be resolved by Slice 4 Architecture Preflight before implementation |
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

## Semantic Level

Semantic Level defines consumption eligibility, not quality. A level cannot be upgraded through inference, non-null fields, UI display or guesswork.

### L0 — Raw Provider Data

Direct Provider output before internal normalization. Allowed for raw auditing, source inspection and adapter diagnostics. It is not automatically standardized, unit-verified, currency-verified or cross-series comparable.

### L1 — Provider Normalized

Data normalized into project fields while retaining Provider-specific constraints. Allowed for source-attributed read-only display and deterministic local statistics within one explicit series. It is not automatically canonical, comparison eligible or suitable for investment signals.

### L2 — Standardized

Measurement kind, format, unit or another required field is standardized through an explicit accepted contract. Deterministic analysis is allowed only within that contract. L2 is not automatically full canonical evidence or universally comparable.

### L3 — Canonical

Satisfies an accepted canonical contract including identity, unit, currency, market, adjustment semantics, Provider/series/run/row provenance, cutoff and UTC visibility, historical freeze method, decimal contract and missing-state contract. Only L3 data satisfying the relevant contract may enter authorized canonical comparison or later Comparison Eligibility.

## Evidence Qualification / Derivation Level

### D0 — Direct Fact

A fact directly supported by an explicit source, such as an announcement, import timestamp or exact Provider-normalized value.

### D1 — Deterministic Aggregation

Produced from a fully recorded input set, scope, time window and deterministic algorithm. D1 discloses inputs, time window, deduplication, missing-value handling, algorithm and sorting.

### D2 — Rule Classification

Depends on explicit versioned rules. D2 exposes rule version, classification source and human/system responsibility boundary.

### D3 — Analytical Judgment

Contains analysis, interpretation or research judgment. D3 remains separate from D0/D1 and does not automatically enter buy/sell suggestions, target prices, return promises, trading signals or cross-company rankings.

## Development task classification

### Architecture Task

Full Architecture Preflight, Definition of Ready and fixed-head review are required when work changes schema, migration, Provider, data meaning, Semantic Level, revision rules, cutoff, provenance, fallback/identity/join rules, persistent state, computation contracts, rule classifications, external-network boundaries or security.

An Architecture Task must not be disguised as UI display.

### Product Task

A Product Task may use the lighter process only when it reads accepted contracts, adds no persistent state, changes no field meaning/invariant/computation/Provider/cutoff/revision/provenance, upgrades no Semantic Level and does not disguise D2/D3 as D0/D1.

Typical Product Tasks are bounded read-only pages, query composition, reading-experience optimization, accessibility and serialization display without semantic change.

## Architecture debt register

- **D1 Documentation drift — synchronized by Issue #152:** Company Research runtime and the next roadmap gate are updated after PRs #149 and #151.
- **D2 Repeated Stage 2 structure — bounded:** neutral frozen-boundary and ordered-row mechanics are shared; generic graph loading remains unjustified.
- **D3 Read utilities — reviewed:** evidence serializers and domain notices remain local.
- **D4 Command lifecycle and concurrency — partially reduced:** integrity translation and process-local locks are shared; allocation and transaction semantics remain local.
- **D5 ORM lifecycle — bounded:** accepted listener/import/mapper/metadata compatibility remains in place.
- **D6 Test-matrix growth:** shared-invariant tests and domain-semantic tests remain distinct.
- **D7 Fixture-versus-production Provider reachability — deferred:** Hithink live contract and permission are not established.
- **D8 Canonical market-price semantics — unresolved:** no canonical-price implementation DoR.
- **D9 Product overview query architecture — resolved for current surfaces:** Company Research uses a bounded 3/14 query boundary and does not compose Stage 2 N+1 list services.
- **D10 Consolidation cadence:** PR #145 found no production refactor necessary; the next review occurs after one more product/domain slice or earlier if ownership ambiguity appears.
- **D11 Evidence-ingestion source and review ownership — next preflight concern:** official-source authorization, immutable raw storage, deduplication, candidate matching and human acceptance are unresolved.

## Development gates

1. **Architecture Preflight:** problem, ownership, inputs, golden/failure paths, migration/dependency/network impact, conflicts, smallest slice and exclusions.
2. **Definition of Ready:** one objective, accepted contracts, ownership, reachable paths, selectors/chronology, migration decision, bounded tests and stop conditions.
3. **Planning before implementation:** architecture decisions precede implementation Issue and task snapshot.
4. **Reset threshold:** reset when ownership is ambiguous, semantics depend on inference/defaults, production cannot reach the path, or authoritative documents disagree.
5. **Consolidation cadence:** review documentation, duplicated infrastructure, schema/link growth, tests, APIs and next-stage reachability after every two domain/product slices.
6. **Review evidence:** green CI is necessary but not sufficient; ownership, reachability, semantics and scope must also pass.
7. **Fixed-head gate:** independent approval must name the exact reviewed HEAD before an architecture or implementation PR is merged.

## Accepted product sequence

Completed:

1. architecture rebalance and Evidence Intelligence roadmap;
2. Evidence Intelligence Architecture Preflight;
3. Research Change Feed implementation — PR #139;
4. Industry Beneficiary Workspace v1 Architecture Preflight — PR #141;
5. Industry Beneficiary Workspace v1 implementation — PR #143;
6. product reading-surface consolidation review — PR #145;
7. product-surface baseline synchronization — PR #147;
8. Company Research Workspace v1 Architecture Preflight — PR #149;
9. Company Research Workspace v1 implementation — PR #151.

Current authorization state:

- no Evidence Ingestion implementation or task synchronization is authorized;
- no external source, schema, migration, Provider, dependency, release or version change is authorized;
- the next roadmap action after this synchronization is a separate Evidence Ingestion Architecture Preflight.

## Recommended forward sequence

This ordering is not implementation authorization. Every item requires its own linked Issue and applicable review gate.

1. merge the Company Research baseline synchronization;
2. Slice 4 Evidence Ingestion Architecture Preflight for one explicitly authorized official source;
3. one bounded ingestion implementation task only if the preflight receives independent Definition-of-Ready approval;
4. perform the next consolidation review after that product/domain slice before expanding further;
5. separately characterize missing typed beneficiary semantics;
6. continue the parallel canonical-price and Comparison Eligibility infrastructure track;
7. consider guarded AI research assistance only through a separate Architecture Preflight after deterministic ingestion/review boundaries exist;
8. reconsider Watchlist, monitoring, ranking or later investment-priority comparison only through separate authorization.

## Slice 4 Evidence Ingestion as the next architecture gate

The candidate user job is:

> Import one explicitly authorized official source into an immutable, auditable review queue, deterministically identify duplicates and possible company/industry links, and require explicit human acceptance before creating or linking accepted Evidence Ledger records.

The Architecture Preflight must establish:

1. exactly one official source, authorization and data-use boundary;
2. fetch/import trigger and explicit external-network boundary;
3. immutable raw capture identity, storage owner, retention and redaction rules;
4. source-specific normalization contract without cross-Provider fallback or mixing;
5. deterministic fingerprint and duplicate semantics;
6. explicit information time, fetched/imported time and recorded UTC chronology;
7. candidate company/industry matching output and confidence semantics;
8. the boundary between candidate match and accepted identity;
9. human-review states, transitions and authorization ownership;
10. accepted EvidenceItem and claim-link creation boundaries;
11. evidence-grade responsibility and prohibition on automatic accepted grading;
12. production-realistic offline golden path and most important failure path;
13. schema, migration, dependency, rollback and credential impact;
14. exact tests, exclusions, stop conditions and fixture parity.

The smallest candidate slice must stop before multi-source orchestration, scheduled crawling, generalized scraping, automatic identity acceptance or AI-owned evidence qualification.

## Locked exclusions for the next gate

The Evidence Ingestion Architecture Preflight and any later first implementation must not assume authorization for:

- more than one official source;
- hidden network access during import, startup, tests, CI, fixture demos or ordinary reads;
- silent Provider fallback, relabeling or row-level Provider mixing;
- automatic accepted company/industry identity from free text, stock-code heuristics, title similarity or LLM output;
- automatic accepted EvidenceItem creation without explicit reviewed rules and human action;
- automatic evidence-grade assignment;
- AI self-promotion to D0, D1 or accepted D2 state;
- mutation of existing accepted revisions or links;
- ranking, target price, expected return, buy/sell/hold or recommendation behavior;
- monitoring, alerts, portfolio or trading state;
- Canonical Price or Comparison Eligibility implementation;
- release or version changes.

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
