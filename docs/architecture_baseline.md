# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and a linked GitHub Issue controls Standard or Strict scope.

- Released software version: `0.2.0`.
- Current accepted `main` baseline: `be18f407fb42b6caf22d339285e17f830052af91`.
- Latest merged runtime capability: Normalized Valuation and Expectation Metrics v1 through architecture PR #184 and implementation PR #186.
- Latest merged external-data architecture decision: Account-Authorized THS Structured Financial Data v1 through PR #191.
- Authorized CNINFO Disclosure Acquisition v1 architecture remains accepted through PR #189.
- Review-identity governance is merged through PR #187.
- Canonical Price and Comparison Eligibility v1 remains the authoritative price owner through PRs #176/#178.
- Active Strict architecture gate: Issue #192, Industry Thesis Intake and Research Orchestration v1.
- CNINFO automated acquisition remains implementation-blocked pending a separately accepted source/access contract.
- THS production implementation remains blocked pending exact non-secret account capability, host, endpoint, limit, retention and revision facts.
- Earlier Evidence Ingestion Issue #154 / PR #155 remains closed-unmerged and reference only.

Documentation may advance without changing the released version. An architecture or capability merge does not itself authorize implementation, release, source expansion, portfolio action or trading behavior.

## Product boundary

AQuantAI is a local-first, personal-use, research-only and non-advisory A-share research workbench. It is not a broker, order-management system, automated-trading system, investment-advice service, multi-user SaaS product or production deployment platform.

Deterministic calculations, canonicalization, selectors and accepted workflow state belong to reviewed application code. An LLM may assist only behind an explicit bounded adapter and may not own evidence qualification, deterministic state, accepted research state, execution or trading behavior.

The product may identify current research-priority candidates under an explicit rule. It must preserve the complete beneficiary universe and expose every component, missing state, penalty and reason. It must not produce unexplained recommendations, target prices, expected returns, position sizes or trading actions.

## Accepted dependency direction

```text
market-data persistence
  -> v0.5 Evidence Ledger
  -> v0.5B Industry Map
  -> v0.5C Stage 1 beneficiary identities and revisions
       -> Typed Beneficiary Evidence Semantics v1
       -> v0.6A Company Research and financial-transmission hypotheses
       -> v0.6B narrative expectations and valuation observations
       -> v0.6C catalyst and risk assessments
       -> v0.6D industry/company quality judgments
  -> Canonical Price and Comparison Eligibility v1
       -> purpose-specific normalized-valuation price eligibility
  -> Investment Candidate Intelligence Layer v1
  -> Normalized Valuation and Expectation Metrics v1
       -> structured financial observations
       -> PE / PS / EV-EBITDA / FCF-yield calculations
       -> frozen historical and analyst-owned peer context
       -> structured numeric expectation gaps
       -> additive links to exact Investment Candidate component revisions
  -> read-only product workspaces
       -> Evidence Intelligence / Research Change Feed
       -> Industry Beneficiary Workspace
       -> Company Research Workspace
       -> Company Research Comparison Matrix
       -> Company Research Valuation Context
       -> Investment Candidate Workspace
  -> optional company-scoped Guarded AI D3 draft assistance

active architecture candidate
  -> explicit industry/thesis intake session
  -> deterministic local candidate proposals
  -> explicit user review and acceptance plan
  -> existing Industry Map and Stage 1 owner writes
  -> exact orchestration output links
  -> existing readiness and Investment Candidate owners

future authorized acquisition
  -> exact source authorization and capability manifest
  -> immutable L0 raw capture
  -> source-specific L1 normalization
  -> deterministic non-accepted identity candidates
  -> explicit reviewed promotion into existing domain owners only

future disclosure evidence
  -> separately governed official announcement/PDF acquisition or import
  -> exact source/document provenance
  -> explicit human review
  -> existing Evidence Ledger accepted state
```

Downstream accepted records freeze exact accepted upstream revisions and links. They do not silently select newer records, infer missing state, parse free text or rewrite historical meaning.

## Current runtime and product surfaces

When the configured database and local assets are available, the reviewed runtime contains:

1. local fixture-backed Dashboard;
2. database-backed read-only Market Cockpit and Industry Alpha APIs/demos;
3. Evidence Intelligence / Research Change Feed;
4. Industry Beneficiary Workspace v1;
5. Company Research Workspace v1;
6. Guarded AI Research Assistance v1, disabled by default;
7. Typed Beneficiary Evidence Semantics v1 detail inside Industry Research;
8. Company Research Comparison Matrix v1;
9. exact-ID Canonical Price and Comparison Eligibility APIs plus local write commands;
10. Investment Candidate Intelligence v1 APIs, commands and Chinese-first `/investment-candidates` workspace;
11. exact-ID normalized financial, valuation, comparison and expectation-gap APIs;
12. Chinese-first read-only `/company-research/valuation-context` requiring explicit revision IDs and both as-of boundaries.

No current runtime surface provides industry-thesis intake/orchestration, fair value, target price, expected return, buy/sell/hold output, position sizing, broker execution, automated trading or external Provider/disclosure acquisition.

## Accepted capability contracts

### Evidence Intelligence / Research Change Feed

- Chinese-first read-only surface for recent evidence and research changes.
- Explicit time window, cutoff, provenance and deterministic ordering.
- No opportunity ranking or recommendation.
- Navigation reuses accepted owning-domain contracts.

### Industry Beneficiary Workspace v1

- Requires explicit persisted Industry Map selection.
- Shows the complete cutoff-visible Stage 1 beneficiary set for the selected map.
- Preserves exact legacy beneficiary and typed-semantic values.
- Does not claim full-market exhaustive coverage and never ranks beneficiaries.

### Typed Beneficiary Evidence Semantics v1

- Separate append-only profile for one exact Stage 1 beneficiary.
- Exact beneficiary, map, observation, claim and evidence revisions.
- Exposure taxonomy `direct / conditional / indirect / conceptual`.
- Closed execution-evidence vocabularies and analyst-owned D3 judgments.
- No automatic legacy mapping, extraction, ranking or recommendation.

### Company Research Workspace v1

- Requires one explicit persisted Company Research identity.
- Shows exact frozen v0.6A-v0.6D and provenance state.
- Keeps latest cutoff-visible and exact frozen historical revisions separate.
- Displays v0.6B valuation observations as narrative context only.
- Never parses v0.6B free text into structured financial or valuation values.

### Company Research Comparison Matrix v1

- Requires one exact candidate-pool revision and both as-of boundaries.
- Preserves every exact frozen member.
- Attaches exact Company Research and Typed Semantics state.
- Uses neutral deterministic ordering.
- Excludes numeric valuation comparison, priority scoring and advice.

### Canonical Price and Comparison Eligibility v1

- Explicit listed-instrument identity owns market, exchange namespace/code, currency, security type and listing chronology.
- Accepted price-series revisions freeze exact instrument, Provider, dataset, series key, adjustment and decimal contracts.
- Canonical prices freeze one exact succeeded market-data ingestion run and one exact daily-price row.
- Official-close values use deterministic Decimal normalization with disclosed source-float fidelity.
- Comparison Eligibility is separate append-only D2 state with explicit purpose and reason codes.
- Normalized-valuation purpose is exactly `normalized_valuation_metric_v1` under `aquantai.comparison-eligibility.normalized-valuation-metric.v1`.
- Local commands are JSON-only, dry-run capable, atomic, expected-latest protected and network-free.
- Exact-ID reads require information-cutoff and recorded-UTC boundaries.
- Migration `20260722_0013` creates nine additive tables with populated downgrade refusal.
- Canonical Price does not itself create an attractiveness judgment.

### Investment Candidate Intelligence Layer v1

- Preserves one complete exact Stage 1 candidate-pool revision and all members.
- Records eight explicit analyst-owned D3 components.
- Deterministically calculates weighted score, risk deduction, status, reason codes and bounded priority under an explicit rule version.
- Missing, disputed, pending and failed states are never imputed or reweighted.
- Pending and failed verification prohibit numeric aggregation.
- Exposes the complete pool beneath highlighted priority/watch candidates.
- Local commands and exact-ID reads remain network-free.
- Migration `20260722_0014` creates eight additive append-only tables and refuses populated downgrade.
- Candidate status is research prioritization, not buy/sell/hold advice.

### Normalized Valuation and Expectation Metrics v1

- Records append-only structured observations for diluted shares, revenue, attributable net profit, EBITDA, free cash flow and net debt.
- Source kinds are `actual`, `guidance`, `consensus` and `research_assumption`.
- Supported sourced observations freeze exact Company Research, claim and evidence provenance.
- Research assumptions require explicit rationale and falsification condition.
- Uses versioned Decimal arithmetic and `ROUND_HALF_EVEN` for PE, PS, EV/EBITDA and FCF yield.
- Uses one exact accepted Canonical Price and one exact eligible Comparison Eligibility revision.
- Enforces exact instrument, company, accounting scope, target period, currency, unit, freshness, price age and diluted-share effective-range compatibility.
- Persists explicit non-meaningful states instead of absolute denominators, epsilon, clipping, imputation or period substitution.
- Historical context requires at least eight eligible observations, a 730-day eligible span, four financial period ends and unique eligible valuation dates.
- Peer membership is analyst-owned D3 and preserves excluded members.
- Percentile uses deterministic midrank semantics and is not an attractiveness rank.
- Expectation gaps use exact expected/actual observations and preserve zero-expected percentage non-meaningfulness.
- Outputs never automatically rescore or rewrite Investment Candidate history.
- Migration `20260722_0015` creates thirteen additive append-only tables and refuses populated downgrade before any drop.
- Four local JSON-only commands and four exact-ID read APIs remain network-free and cutoff-aware.
- No fair value, target price, expected return, recommendation, portfolio or trading output.

### Guarded AI Research Assistance v1

- Available only inside one explicitly selected Company Research workspace.
- Deterministic immutable Manifest and SHA-256 fingerprint.
- Disabled by default with one explicit HTTPS OpenAI-compatible profile.
- Requires explicit remote-transmission confirmation.
- No retry, fallback, tools, browsing, search, retrieval or background execution.
- Strict output/citation validation and ephemeral D3 draft only.

### Authorized CNINFO Disclosure Acquisition v1 architecture

PR #189 defines an accepted disclosure-acquisition architecture but authorizes no production adapter.

- Candidate company/instrument matches are not accepted identity.
- Raw metadata/document bytes remain immutable L0 when implemented.
- Source-specific records remain L1 until explicit Evidence Ledger acceptance.
- Human review is required before accepted evidence state.
- No scheduler, automatic alert, evidence promotion, recommendation or trading behavior is included.
- Future automated or webpage acquisition requires a separately reviewed personal-use source/access contract; public visibility alone is not sufficient authorization.

### Account-Authorized THS Structured Financial Data v1 architecture

PR #191 defines an accepted external Provider architecture but authorizes no production implementation.

- Candidate source: official account-authorized 同花顺 / HiThink Financial Data API.
- Candidate access: explicit user-initiated personal, local, non-commercial research.
- Candidate transport: documented REST API only.
- Candidate families: instrument identity, daily market, company actions, financial statements, industry/concept taxonomy and market-attention observations.
- Source authorization begins `pending_review` until exact account contract facts are confirmed without secrets.
- Provider observations remain L0/L1 until explicit reviewed promotion under existing owners.
- THS market values do not automatically replace Canonical Price.
- THS financial values do not automatically become official evidence or normalized financial inputs.
- Current taxonomy membership is not historical membership.
- Market attention cannot create beneficiary, evidence-grade, candidate, recommendation or trading state.
- No scheduler, background worker, hidden fallback or read-triggered network is included.

## Active architecture candidate: Industry Thesis Intake and Research Orchestration v1

Issue #192 defines the only active product-orchestration architecture gate.

Candidate boundary:

- one explicit user-entered industry/theme thesis and exact local session revision;
- explicit market scope, driver type/horizon, chain boundary, exclusions and information cutoff;
- deterministic candidate proposals from exact local mappings, existing exact maps/beneficiaries and user seeds;
- optional industry-level AI proposals only as later disabled-by-default D3 drafts;
- explicit coverage state: reviewed local scope, partial local coverage or unknown coverage;
- exact accepted company identity before any Stage 1 write;
- explicit user-selected acceptance plan;
- existing Industry Map, beneficiary and typed-semantics owners remain authoritative;
- exact output links to accepted map/pool/beneficiary revisions;
- readiness inspection and thin handoff to the existing Investment Candidate owner;
- complete Stage 1 universe remains visible before and after Stage B overlays;
- news, announcements, THS and market attention remain optional enrichment.

Candidate persistence is a maximum six-table additive orchestration domain after `20260722_0015`; no migration is authorized by Issue #192.

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Market-data Provider rows, series identity, ingestion status and cutoff | Market-data persistence | One explicit Provider per run/series; no fallback or row mixing |
| Canonical instrument, price, unit, currency and price eligibility | `backend.database.canonical_price*` | Exact append-only revisions and purpose-specific eligibility |
| Evidence grades, claims, links and conflicts | v0.5 Evidence Ledger | Acquisition may propose; explicit acceptance owns final state |
| Industry map, nodes, relationships and observations | v0.5B Industry Map | Exact persisted identities and cutoff-visible revisions |
| Legacy beneficiary identity/classification and complete pool | v0.5C Stage 1 | Preserve exact history and universe integrity |
| Typed beneficiary exposure and execution evidence | `industry_alpha.beneficiary_semantics_*` | Separate analyst-owned D3 profile |
| Company Research and financial hypotheses | v0.6A | Downstream records bind exact revisions |
| Narrative expectations and valuation observations | v0.6B | Context only; no automatic numeric normalization |
| Catalyst and risk assessments | v0.6C | Not monitors, alerts or timing engines |
| Industry/company quality judgment | v0.6D | Does not generate price or recommendation state |
| Component-only company comparison | `company_comparison` | Complete universe, neutral ordering, no price arithmetic |
| Investment Candidate state and snapshots | `industry_alpha.investment_candidate_*` | Exact membership and deterministic rule results |
| Structured financial observations | `industry_alpha.normalized_financial_*` | Append-only values with exact provenance and period semantics |
| Normalized valuation arithmetic | `industry_alpha.normalized_valuation_*` | Exact price/financial revisions and versioned Decimal formulas |
| Historical/peer context | `industry_alpha.normalized_comparison_*` | Frozen membership; peer selection remains D3 |
| Structured expectation gap | `industry_alpha.normalized_expectation_*` | Exact expected/actual revisions; no hidden consensus lookup |
| Guarded AI Manifest and transport | Guarded AI modules | Explicit fingerprint/profile/confirmation; draft only |
| CNINFO source authorization and disclosure capture | Accepted architecture in PR #189 | Production path remains separately gated |
| Future accepted disclosure evidence | Existing Evidence Ledger | Explicit human acceptance transaction only |
| THS source authorization, raw capture and source normalization | Accepted architecture in PR #191 | Contract-gated, source-specific and disabled by default |
| Thesis session, proposal and exact output-link audit state | Candidate orchestration domain in Issue #192 | Non-accepted coordination state only |
| Accepted thesis-derived map and beneficiary state | Existing Industry Map / Stage 1 / typed-semantics owners | Explicit user plan and owner transaction only |
| Thesis-derived research priority | Existing Investment Candidate owner | Existing exact rule version; no second scoring owner |

## Shared architecture invariants

1. Local and non-advisory: no advice, performance promise, broker, real order or automated trading.
2. Deterministic calculations and accepted state stay outside LLM ownership.
3. Imports, startup, tests, CI, fixture demos and ordinary reads perform no hidden external network access.
4. Exact IDs, scopes, dates, revisions and selectors are explicit.
5. Downstream accepted records freeze exact revisions and links.
6. Corrections append revisions; accepted history is not mutated through ordinary paths.
7. Information cutoff and recorded UTC both prevent later-information leakage.
8. Conflicts, missing evidence, stale state and uncertainty remain visible.
9. Identity, revision and links commit or roll back together.
10. Ordering, revision allocation, decimal text and strict JSON are deterministic across supported databases.
11. Fixture success paths use fields reachable through reviewed production boundaries.
12. Credentials and raw connection details never enter source, fixtures, Issues, PRs, logs or user errors.
13. Capability merges do not change released version without a separate release decision.
14. A reading surface cannot upgrade Semantic or Derivation Level through display or inference.
15. Overview query counts remain bounded independently of displayed row count unless reviewed.
16. External-source acquisition requires exact source and access authorization.
17. Candidate entity matching is not accepted identity without reviewed acceptance.
18. Model-generated text is D3 draft assistance and cannot self-promote.
19. Guarded AI consumes only an explicit Manifest and may not fetch missing evidence.
20. No generic AI-agent, Provider registry, RAG or tool framework without separate preflight.
21. Legacy and typed beneficiary classifications may disagree; disagreement remains visible.
22. No research-priority result may collapse components into an unexplained total.
23. Existing Provider-normalized price rows are not canonical unless bound through Canonical Price.
24. Complete beneficiary and candidate-pool universes remain visible before and after overlays.
25. Missing, disputed, pending, failed or non-meaningful values are never silently zero or neutral.
26. Purpose-specific Comparison Eligibility cannot be reused for another purpose without an exact contract.
27. Existing v0.6B free text is not parsed into structured metrics.
28. Peer membership, valuation attractiveness and accepted component scores cannot be inferred by AI or metadata.
29. No automatic rescore or rewrite of Investment Candidate history from newer normalized context.
30. FX, accepted corporate-action normalization and external consensus acquisition require separate authorization.
31. A comparison member cannot represent the same Company Research or instrument identity under another key.
32. Exact-ID read failures never fall back to another record.
33. Public website visibility does not by itself authorize automated acquisition.
34. Source denial, schema drift or contract expiry fails closed without hidden fallback.
35. Raw acquisition objects are L0 audit state and cannot directly become accepted evidence.
36. Human acceptance is required before acquisition state creates Evidence Ledger state.
37. Provider account capability must be explicit; public documentation does not prove account entitlement.
38. Provider market observations cannot silently replace Canonical Price.
39. Provider financial values cannot silently become official evidence or normalized inputs.
40. Current taxonomy membership cannot be represented as historical without effective-date support.
41. Market-attention observations cannot directly create beneficiary, candidate, recommendation or trading state.
42. Thesis free text and proposal drafts cannot directly create accepted Industry Map or beneficiary state.
43. Coverage completeness is explicit and separate from evidence quality and candidate status.
44. Valuation, popularity, price performance or missing data cannot remove a reviewed Stage 1 member.
45. Thesis orchestration may coordinate existing owners but cannot duplicate their accepted fields or calculations.

## Semantic and derivation levels

### Semantic Level

- **L0 — Raw Provider/Source Data:** source output before internal normalization; audit only.
- **L1 — Source Normalized:** project fields under source-specific constraints; not automatically comparable or accepted.
- **L2 — Standardized:** standardized through an explicit accepted contract; usable only within that contract.
- **L3 — Canonical:** identity, measurement, unit, currency, market, adjustment, provenance, cutoff, chronology, decimal and missing-state contract.

Canonical Price owns L3 price state within its contract. Structured financial/valuation records remain contract-specific standardized state. Disclosure and THS normalization remain L1 until explicit existing-owner acceptance. Thesis candidate proposals are orchestration drafts and do not gain semantic authority through persistence.

### Evidence Qualification / Derivation Level

- **D0 — Direct Fact:** directly supported by an explicit source.
- **D1 — Deterministic Aggregation:** fully recorded inputs, scope, algorithm and missing treatment.
- **D2 — Rule Classification:** explicit versioned rules and responsibility boundary.
- **D3 — Analytical Judgment:** analysis or interpretation, including typed semantics, peer selection, candidate components, human acquisition review and AI drafts.

D3 does not automatically enter accepted identity, evidence, map membership, buy/sell guidance, target prices, return promises or trading signals.

## Capability matrix

| Capability | Reviewed boundary | Remaining boundary |
| --- | --- | --- |
| Market-data persistence | Complete-snapshot persistence and cutoff-aware reads | No hidden Provider expansion |
| Canonical Price | Listed identity, official close, provenance and purpose eligibility | No FX or hidden corporate-action normalization |
| Evidence Ledger / Industry Map | Evidence, claims, conflicts, map identities and revisions | No automatic external acceptance |
| Stage 1 beneficiary | Legacy identity/classification and complete-pool handoff | No automatic full-market discovery |
| Typed Beneficiary Semantics | Append-only exposure/execution profiles | No automatic extraction or ranking |
| Company Research v0.6A-v0.6D | Hypotheses, narratives, catalysts, risks and quality | No automatic acceptance |
| Company Comparison | Complete-universe component comparison | No automatic peer selection |
| Investment Candidates | Transparent components, status and bounded priority | No automatic component scoring |
| Normalized Valuation / Expectation | Structured observations, formulas, comparisons and gaps | No fair value, target return, FX or hidden consensus acquisition |
| Guarded AI | Explicit ephemeral company-scoped drafts | No persisted accepted AI state, tools or retrieval |
| CNINFO Disclosure Acquisition | Architecture accepted through PR #189 | Production acquisition remains separately gated |
| THS Structured Provider | Architecture accepted through PR #191 | No implementation until exact account contract facts and separate authorization |
| Industry Thesis Orchestration | Strict architecture active in Issue #192 | No implementation until fixed-head approval and separate authorization |
| Market Attention / Daily Radar | Source observations remain isolated candidates | Separate product/rule authorization required |

## Architecture debt register

- **D1 Current-state documentation drift — active in PR for Issue #192:** synchronize `main`, accepted THS architecture and the new orchestration gate.
- **D2 Repeated Stage 2 structure — bounded:** generic graph loading remains unjustified.
- **D3 Read utilities — bounded:** serializers, notices and failures remain domain-local.
- **D4 Command lifecycle/concurrency — partially shared:** semantic validation remains domain-local.
- **D5 ORM lifecycle — bounded:** append-only listener/import/metadata compatibility remains tested.
- **D6 Test-matrix growth — monitored:** new orchestration must add one offline end-to-end path without hidden network.
- **D7 External Provider reachability — blocked:** THS implementation awaits exact account contract facts.
- **D8 Canonical market-price semantics — resolved for v1; Provider promotion remains separately gated.**
- **D9 Product overview query architecture — resolved for current surfaces.**
- **D10 Consolidation cadence — 5–6 implemented slices or concrete duplication/ownership/test-growth evidence.**
- **D11 Evidence-ingestion source/review ownership — architecture accepted; production acquisition remains gated.**
- **D12 Guarded AI company-scope ownership — resolved for v1.**
- **D13 Typed beneficiary semantics — resolved for v1.**
- **D14 Complete-universe company comparison — resolved for v1.**
- **D15 Investment Candidate scoring/status semantics — resolved for v1.**
- **D16 Structured financial-input ownership — resolved by PR #186.**
- **D17 Normalized valuation/expectation semantics — resolved by PR #186.**
- **D18 Account-authorized THS architecture — resolved by PR #191; implementation facts remain blocked.**
- **D19 Provider taxonomy chronology — active:** current snapshots must not masquerade as historical membership.
- **D20 Market-attention isolation — active:** attention remains separate from beneficiary and candidate quality.
- **D21 Industry-thesis entry/orchestration — active in Issue #192:** define reproducible draft, review, owner handoff and coverage semantics.
- **D22 Industry-level AI assistance — deferred:** optional proposal-only extension after offline orchestration proves useful.

## Accepted product sequence

Completed:

1. Evidence Intelligence / Research Change Feed — PR #139;
2. Industry Beneficiary Workspace v1 — PR #143;
3. first reading-surface consolidation — PR #145;
4. Company Research Workspace v1 — PR #151;
5. Guarded AI Research Assistance v1 — PR #161;
6. Company Research and Guarded AI consolidation — PR #163;
7. risk-tiered governance workflow — PR #167;
8. Typed Beneficiary Evidence Semantics architecture — PR #165;
9. Typed Beneficiary Evidence Semantics implementation — PR #169;
10. Company Research Comparison Matrix architecture — PR #172;
11. Company Research Comparison Matrix implementation — PR #174;
12. Canonical Price and Comparison Eligibility architecture — PR #176;
13. Canonical Price and Comparison Eligibility implementation — PR #178;
14. Investment Candidate Intelligence architecture — PR #180;
15. Investment Candidate Intelligence implementation — PR #182;
16. Normalized Valuation and Expectation Metrics architecture — PR #184;
17. Normalized Valuation and Expectation Metrics implementation — PR #186;
18. fixed-head review identity governance — PR #187;
19. Authorized CNINFO Disclosure Acquisition architecture — PR #189;
20. Account-Authorized THS Structured Financial Data architecture — PR #191.

Active architecture gate:

21. Industry Thesis Intake and Research Orchestration v1 — Issue #192.

Deferred:

- production CNINFO/webpage/PDF acquisition until its own accepted implementation contract;
- THS production implementation until exact account contract facts and separate authorization;
- external consensus sources;
- Market Attention scoring and Daily Radar product behavior;
- OCR and automatic accepted evidence drafting;
- FX and accepted corporate-action normalization;
- industry-level guarded AI drafting until the offline orchestration foundation is approved and separately authorized.

## Current authorization state

- `main` includes PR #191 at `be18f407fb42b6caf22d339285e17f830052af91`.
- Issue #190 is completed; PR #191 authorizes THS architecture only.
- The owner authorized the next development step on 2026-07-22 as Issue #192 architecture work.
- Issue #192 authorizes architecture documentation only for industry-thesis intake and orchestration.
- No production code, migration, dependency, API/UI implementation, fixture or AI call is authorized yet.
- No news, announcement, THS, Provider or web acquisition is required by the orchestration golden path.
- No automatic company acceptance, evidence acceptance, component scoring, recommendation, portfolio or trading behavior is authorized.

## Next governed gate

Issue #192 and its Draft architecture PR must establish and receive process-independent fixed-head approval for:

1. exact thesis/session identity and append-only revision contract;
2. explicit market scope, driver, horizon, chain boundary, exclusions and both as-of boundaries;
3. deterministic candidate-source precedence and provenance;
4. coverage semantics independent of evidence quality;
5. exact company identity and duplicate/ambiguity failure behavior;
6. draft, selection and accepted-owner boundaries;
7. complete Stage 1 universe preservation;
8. atomic handoff to existing Industry Map, beneficiary and typed-semantics owners;
9. exact orchestration output links;
10. readiness inspection and thin handoff to the existing Investment Candidate owner;
11. a maximum six-table additive migration candidate with populated downgrade refusal;
12. JSON-only dry-run commands and exact-ID reads;
13. Chinese-first `/industry-analysis/new` workflow;
14. one fully offline three-company golden path;
15. fail-closed ambiguous identity, stale revision, missing-price and AI-owned acceptance paths;
16. optional industry-level AI as a later disabled-by-default proposal-only slice;
17. locked exclusions for external acquisition, recommendation, portfolio and trading behavior.

No production implementation is authorized by this baseline or Issue #192 alone.
