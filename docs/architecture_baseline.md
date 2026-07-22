# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and a linked GitHub Issue controls the scope of Standard or Strict work.

- Released software version: `0.2.0`.
- Slice 5 implementation base: `c7627a76cd7e571c7eee6485d18550113e40d4cf`.
- Latest merged runtime capability before Slice 5: Investment Candidate Intelligence Layer v1 through architecture PR #180 and implementation PR #182.
- Normalized Valuation and Expectation Metrics v1 is defined by architecture Issue #183 / merged PR #184 and implemented under Issue #185 / PR #186.
- Canonical Price and Comparison Eligibility v1 remains the authoritative price owner through architecture PR #176 and implementation PR #178.
- Evidence Ingestion remains deferred after Issue #154 / closed-unmerged PR #155; no ingestion runtime capability reached `main`.
- PR #186 remains subject to green final-head CI, fixed-head review, independent approval and explicit owner merge authorization.

Documentation may advance with a capability PR without changing the released software version. A capability merge does not itself authorize a release, Provider expansion, portfolio action or trading behavior.

## Product boundary

AQuantAI is a local-first, personal-use, research-only and non-advisory workbench. It is not a broker, order-management system, automated-trading system, investment-advice service, multi-user SaaS product or production deployment platform.

Deterministic calculations, canonicalization, selectors and accepted workflow state belong to reviewed application code. An LLM may assist only behind an explicit bounded adapter and may not own evidence qualification, deterministic state, accepted research state, execution or trading behavior.

The product may identify current research-priority candidates under an explicit rule, but it must preserve the complete beneficiary universe and expose every component, missing state, penalty and reason. It must not produce unexplained recommendations, target prices, expected returns, position sizes or trading actions.

## Implemented dependency direction

```text
market-data persistence
  -> v0.5 Evidence Ledger
  -> v0.5B Industry Map
  -> v0.5C Stage 1 beneficiary identity and revisions
       -> Typed Beneficiary Evidence Semantics v1
       -> v0.6A Company Research and financial-transmission hypotheses
       -> v0.6B narrative expectations and valuation observations
       -> v0.6C catalyst and risk assessments
       -> v0.6D industry and company quality judgments
  -> Canonical Price and Comparison Eligibility v1
       -> purpose-specific normalized-valuation price eligibility
  -> Investment Candidate Intelligence Layer v1
  -> Normalized Valuation and Expectation Metrics v1
       -> structured financial observations
       -> PE / PS / EV-EBITDA / FCF-yield calculations
       -> frozen historical and analyst-owned peer context
       -> structured numeric expectation gaps
       -> additive links to new Investment Candidate component revisions
  -> read-only product workspaces
       -> Evidence Intelligence / Research Change Feed
       -> Industry Beneficiary Workspace
       -> Company Research Workspace
       -> Company Research Comparison Matrix
       -> Company Research Valuation Context
       -> Investment Candidate Workspace
  -> optional company-scoped Guarded AI D3 draft assistance
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

No current runtime surface provides fair value, target price, expected return, buy/sell/hold output, position sizing, broker execution or automated trading.

## Accepted capability contracts

### Evidence Intelligence / Research Change Feed

- Chinese-first read-only surface for recent evidence and research changes;
- explicit time window, cutoff, provenance and deterministic ordering;
- no opportunity ranking or recommendation;
- navigation reuses accepted owning-domain contracts.

### Industry Beneficiary Workspace v1

- requires explicit persisted Industry Map selection;
- shows the complete cutoff-visible Stage 1 beneficiary set for the selected map;
- preserves exact legacy beneficiary and typed-semantic values;
- does not claim full-market exhaustive coverage;
- never ranks beneficiaries.

### Typed Beneficiary Evidence Semantics v1

- separate append-only profile for one exact Stage 1 beneficiary;
- exact beneficiary, map, observation, claim and evidence revisions;
- exposure taxonomy `direct / conditional / indirect / conceptual`;
- closed execution-evidence vocabularies;
- analyst-owned D3 judgments with deterministic validation;
- no automatic legacy mapping, extraction, ranking or recommendation.

### Company Research Workspace v1

- requires one explicit persisted Company Research identity;
- shows exact frozen v0.6A-v0.6D and provenance state;
- keeps latest cutoff-visible and exact frozen historical revisions separate;
- displays v0.6B valuation observations as narrative research context only;
- never parses v0.6B free text into structured financial or valuation values.

### Company Research Comparison Matrix v1

- requires one exact candidate-pool revision and both as-of boundaries;
- preserves every exact frozen member;
- attaches exact Company Research and Typed Semantics state;
- uses neutral deterministic ordering;
- excludes numeric valuation comparison, priority scoring and advice.

### Canonical Price and Comparison Eligibility v1

- explicit listed-instrument identity owns market, exchange namespace/code, currency, security type and listing chronology;
- accepted price-series revisions freeze exact instrument, Provider, dataset, series key, adjustment and decimal contracts;
- canonical prices freeze one exact succeeded ingestion run and one exact daily-price row;
- official-close values use deterministic Decimal normalization with disclosed source-float fidelity;
- Comparison Eligibility is separate append-only D2 state with explicit purpose and reason codes;
- the Slice 5 purpose is exactly `normalized_valuation_metric_v1` under rule `aquantai.comparison-eligibility.normalized-valuation-metric.v1`;
- the Slice 5 purpose requires an accepted, unadjusted, official-close, currency-per-share price for the exact requested trade date;
- local commands are JSON-only, dry-run capable, atomic, expected-latest protected and network-free;
- exact-ID reads require information cutoff and recorded-UTC boundaries;
- migration `20260722_0013` creates nine additive tables with populated downgrade refusal;
- Canonical Price does not itself create an attractiveness judgment.

### Investment Candidate Intelligence Layer v1

- preserves one complete exact Stage 1 candidate-pool revision and all members;
- records eight explicit analyst-owned D3 components;
- deterministically calculates weighted score, risk deduction, status, reason codes and bounded priority under an explicit rule version;
- missing, disputed, pending and failed states are never imputed or reweighted;
- pending and failed verification prohibit numeric aggregation;
- exposes the complete pool beneath highlighted priority/watch candidates;
- local commands and exact-ID reads remain network-free;
- migration `20260722_0014` creates exactly eight additive append-only tables and refuses populated downgrade;
- candidate status is research prioritization, not buy/sell/hold advice.

### Normalized Valuation and Expectation Metrics v1

- records append-only structured financial observations for exactly:
  - `diluted_shares_outstanding`;
  - `revenue`;
  - `net_profit_attributable`;
  - `ebitda`;
  - `free_cash_flow`;
  - `net_debt`;
- source kinds are exactly `actual`, `guidance`, `consensus` and `research_assumption`;
- supported sourced observations freeze exact Company Research, claim and evidence provenance;
- supported research assumptions require explicit rationale and falsification condition;
- uses versioned Decimal arithmetic and `ROUND_HALF_EVEN` for PE, PS, EV/EBITDA and FCF yield;
- uses one exact accepted Canonical Price and one exact eligible Slice 5 Comparison Eligibility revision;
- enforces exact instrument, company, accounting scope, target period, currency, unit, freshness, price-age and diluted-share effective-range compatibility;
- persists explicit non-meaningful states instead of absolute denominators, epsilon, clipping, imputation or period substitution;
- preserves negative FCF yield as a numeric calculated result with explicit state;
- historical context requires frozen membership, at least eight calculated observations, 730 calendar days and four financial period ends;
- peer context is analyst-owned D3 membership, preserves every excluded member and requires distinct Company Research and listed-instrument identities;
- percentile uses deterministic midrank semantics and does not create an attractiveness rank;
- expectation gaps use exact expected and actual structured observations and preserve zero-expected percentage non-meaningfulness;
- normalized outputs never automatically rescore, relabel or rewrite Investment Candidate history;
- migration `20260722_0015` creates exactly thirteen additive append-only tables and refuses populated downgrade before any drop;
- four local JSON-only commands support strict fields, dry-run, expected-latest protection and zero hidden network;
- four exact-ID read APIs require information cutoff and explicit UTC recorded boundaries;
- `/company-research/valuation-context` is read-only, explicit-ID only, safe-DOM rendered and never falls back to another record;
- no fair value, target price, expected return, recommendation, portfolio or trading output is produced.

### Guarded AI Research Assistance v1

- available only inside one explicitly selected Company Research workspace;
- deterministic immutable Manifest and SHA-256 fingerprint;
- disabled by default with one explicit HTTPS OpenAI-compatible profile;
- explicit remote-transmission confirmation;
- no retry, fallback, tools, browsing, search, retrieval or background execution;
- strict output and citation validation;
- ephemeral D3 draft only, with no accepted-state persistence.

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Provider rows, series identity, ingestion status and cutoff | Market-data persistence | One explicit Provider per run/series; no fallback or row mixing |
| Canonical instrument, price, unit, currency and price eligibility | `backend.database.canonical_price*` plus bounded Slice 5 eligibility extension | Exact append-only revisions and purpose-specific eligibility |
| Evidence grades, claims, links and conflicts | v0.5 Evidence Ledger | Downstream records freeze exact revisions and links |
| Industry map, nodes, relationships and observations | v0.5B | Exact persisted identities and cutoff-visible revisions |
| Legacy beneficiary identity/classification | v0.5C Stage 1 | Preserve exact history |
| Typed beneficiary exposure and execution evidence | `industry_alpha.beneficiary_semantics_*` | Separate analyst-owned D3 profile |
| Company Research and financial hypotheses | v0.6A | Downstream records bind exact revisions |
| Narrative expectations and valuation observations | v0.6B | Research context only; no automatic numeric normalization |
| Catalyst and risk assessments | v0.6C | Not monitors, alerts or timing engines |
| Industry/company quality judgment | v0.6D | Does not generate price or recommendation state |
| Component-only company comparison | `company_comparison` | Complete universe, neutral ordering, no price arithmetic |
| Investment Candidate state and snapshots | `industry_alpha.investment_candidate_*` | Exact frozen membership and deterministic rule results |
| Structured financial observations | `industry_alpha.normalized_financial_*` | Explicit append-only values with exact provenance and period semantics |
| Normalized valuation arithmetic | `industry_alpha.normalized_valuation_*` | Exact price/financial revisions and versioned Decimal formulas |
| Historical and peer comparison context | `industry_alpha.normalized_comparison_*` | Frozen membership; peer selection remains analyst-owned D3 |
| Structured numeric expectation gap | `industry_alpha.normalized_expectation_*` | Exact expected/actual revisions; no hidden consensus lookup |
| Guarded AI Manifest and transport | Guarded AI modules | Explicit fingerprint/profile/confirmation; draft only |
| Future ingestion raw capture and review state | Deferred / not assigned | Requires source authorization and new Architecture Preflight |

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
15. Overview query counts remain bounded independently of displayed row count unless explicitly reviewed.
16. External-source ingestion requires explicit source authorization.
17. Candidate entity matching is not accepted identity without reviewed acceptance.
18. Model-generated text is D3 draft assistance and cannot self-promote.
19. Guarded AI consumes only an explicit accepted Manifest and may not fetch missing evidence.
20. No generic AI-agent, provider registry, RAG or tool framework without separate preflight.
21. Legacy and typed beneficiary classifications may disagree; disagreement remains visible.
22. No research-priority result may collapse components into an unexplained total.
23. Existing Provider-normalized price rows are not canonical unless bound through Canonical Price.
24. Complete beneficiary and candidate-pool universes remain visible before and after downstream overlays.
25. Missing, disputed, pending, failed or non-meaningful values are never silently zero or neutral.
26. Purpose-specific Comparison Eligibility cannot be reused as a different purpose without an exact reviewed contract.
27. Existing v0.6B free text is not parsed into structured financial, valuation or expectation metrics.
28. Peer membership, valuation attractiveness and accepted component scores cannot be inferred by AI or metadata.
29. No automatic rescore or rewrite of Investment Candidate history from newer normalized context.
30. FX, corporate-action normalization and external consensus acquisition require separate authorization.
31. A comparison member cannot represent the same Company Research or listed-instrument identity under a different member key.
32. Exact-ID read failures never fall back to a newer, older or different record.

## Semantic and derivation levels

### Semantic Level

- **L0 — Raw Provider Data:** source output before internal normalization; audit only.
- **L1 — Provider Normalized:** project fields with Provider-specific constraints; not automatically comparable.
- **L2 — Standardized:** standardized through an explicit accepted contract; usable only within that contract.
- **L3 — Canonical:** identity, measurement, unit, currency, market, adjustment, provenance, cutoff, chronology, decimal and missing-state contract.

Canonical Price owns L3 price state within its accepted contract. Structured financial and normalized metric records remain contract-specific standardized state; display or non-null storage does not promote them to L3.

### Evidence Qualification / Derivation Level

- **D0 — Direct Fact:** directly supported by an explicit source.
- **D1 — Deterministic Aggregation:** fully recorded inputs, scope, algorithm and missing treatment.
- **D2 — Rule Classification:** explicit versioned rules and responsibility boundary.
- **D3 — Analytical Judgment:** analysis or interpretation, including typed beneficiary semantics, peer selection, Investment Candidate component assessments and AI drafts.

D3 does not automatically enter buy/sell guidance, target prices, return promises or trading signals.

## Capability matrix

| Capability | Reviewed boundary | Remaining boundary |
| --- | --- | --- |
| Market-data persistence | Complete-snapshot persistence and cutoff-aware reads | No hidden Provider expansion |
| Canonical Price | Listed identity, official close, exact provenance and purpose eligibility | No FX or hidden corporate-action normalization |
| Evidence Ledger / Industry Map | Evidence, claims, conflicts, map identities and revisions | No external automated acquisition |
| Stage 1 beneficiary | Legacy identity/classification and candidate-pool handoff | No automatic full-market discovery |
| Typed Beneficiary Semantics | Append-only exposure and execution-evidence profiles | No automatic extraction or ranking |
| Company Research v0.6A-v0.6D | Hypotheses, narrative expectations/valuation, catalysts, risks and quality | No automatic acceptance |
| Company Comparison | Complete-universe component comparison | No automatic peer selection |
| Investment Candidates | Transparent components, deterministic status and bounded priority | No automatic component scoring |
| Normalized Valuation / Expectation | Structured observations, versioned formulas, frozen comparisons and expectation gaps | No fair value, target return, FX or hidden consensus acquisition |
| Guarded AI | Explicit ephemeral company-scoped draft assistance | No persisted AI state, tools or retrieval |
| Evidence Ingestion | Deferred | Requires explicit source authorization |
| Market Attention / Daily Radar | Not authorized | Requires acquisition and separate architecture |

## Architecture debt register

- **D1 Current-state documentation drift — resolved through the Slice 5 implementation baseline.**
- **D2 Repeated Stage 2 structure — bounded:** generic graph loading remains unjustified.
- **D3 Read utilities — bounded:** serializers, notices and failure semantics remain domain-local.
- **D4 Command lifecycle and concurrency — partially shared:** transactions and semantic validation remain domain-local.
- **D5 ORM lifecycle — bounded:** append-only listener/import/metadata compatibility remains tested.
- **D6 Test-matrix growth — monitored:** Slice 5 uses focused semantic tests plus shared migration invariants.
- **D7 Provider reachability — deferred:** live source contracts are not established.
- **D8 Canonical market-price semantics — resolved for v1.**
- **D9 Product overview query architecture — resolved for current surfaces.**
- **D10 Consolidation cadence — 5–6 slices or concrete duplication/ownership/test-growth evidence.**
- **D11 Evidence-ingestion source/review ownership — deferred.**
- **D12 Guarded AI ownership — resolved for v1.**
- **D13 Typed beneficiary semantics — resolved for v1.**
- **D14 Complete-universe company comparison — resolved for v1.**
- **D15 Investment Candidate scoring/status semantics — resolved for v1.**
- **D16 Structured financial-input ownership — resolved for v1 by Issue #185 / PR #186.**
- **D17 Normalized valuation/expectation comparison semantics — resolved for v1 by Issue #185 / PR #186.**
- **D18 Authorized external financial/evidence acquisition — deferred pending source decisions.**

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
16. Normalized Valuation and Expectation Metrics architecture — PR #184.

Active merge gate:

17. Normalized Valuation and Expectation Metrics implementation — Issue #185 / PR #186.

Deferred:

- Evidence Ingestion Issue #154 / closed-unmerged PR #155;
- authorized financial and evidence acquisition until exact source decisions exist;
- Market Attention and Daily Radar until authorized acquisition exists.

## Current authorization state

- PR #184 is merged on implementation base `c7627a76cd7e571c7eee6485d18550113e40d4cf`.
- Issue #185 authorizes the bounded Strict Slice 5 implementation in PR #186.
- PR #186 may merge only after final-head CI, complete inventory, author fixed-head review, independent fixed-head approval and separate explicit owner authorization.
- No Provider, ingestion, FX, corporate-action, hidden consensus, fair-value, target-price, expected-return, portfolio or trading work is authorized inside PR #186.
- Evidence Ingestion remains deferred.

## Next governed architecture gate

After Slice 5 is merged, the next useful product work is authorized acquisition, beginning with an explicit source decision rather than a crawler or generic Provider framework.

A future Strict Architecture Preflight must establish:

1. exact authorized source and permitted access method;
2. immutable raw capture ownership;
3. source-specific normalization and schema boundaries;
4. fingerprints, deduplication and replay behavior;
5. company/instrument candidate matching versus accepted identity;
6. human review before Evidence Ledger or structured-financial acceptance;
7. cutoff, recorded UTC and correction semantics;
8. credentials, rate limits, errors and network isolation;
9. fixture and offline test equivalents;
10. explicit exclusions for hidden fallback, uncontrolled crawling and automatic accepted-state promotion.

No acquisition implementation is authorized by this baseline alone.
