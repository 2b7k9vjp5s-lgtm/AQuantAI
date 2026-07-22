# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and a linked GitHub Issue controls Standard or Strict scope.

- Released software version: `0.2.0`.
- Current accepted runtime baseline: `2cb894c1547380d2e350d4200150ad50a5461236`.
- Latest merged capability: Normalized Valuation and Expectation Metrics v1 through architecture PR #184 and implementation PR #186.
- Review-identity governance is merged through PR #187.
- Canonical Price and Comparison Eligibility v1 remains the authoritative price owner through PRs #176/#178.
- Active Strict architecture gate: Issue #188, Authorized CNINFO Disclosure Acquisition v1.
- Earlier Evidence Ingestion Issue #154 / PR #155 remains closed-unmerged and is reference only; no ingestion runtime from that work reached `main`.

Documentation may advance without changing the released version. A capability or architecture merge does not itself authorize a release, source expansion, portfolio action or trading behavior.

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

future authorized acquisition
  -> exact source authorization
  -> immutable L0 raw capture
  -> source-specific L1 normalization
  -> deterministic non-accepted identity candidates
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

No current runtime surface provides fair value, target price, expected return, buy/sell/hold output, position sizing, broker execution, automated trading or external disclosure acquisition.

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
- Displays v0.6B valuation observations as narrative research context only.
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
- Slice 5 purpose is exactly `normalized_valuation_metric_v1` under `aquantai.comparison-eligibility.normalized-valuation-metric.v1`.
- Local commands are JSON-only, dry-run capable, atomic, expected-latest protected and network-free.
- Exact-ID reads require information cutoff and recorded-UTC boundaries.
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

- Records append-only structured financial observations for diluted shares, revenue, attributable net profit, EBITDA, free cash flow and net debt.
- Source kinds are exactly `actual`, `guidance`, `consensus` and `research_assumption`.
- Supported sourced observations freeze exact Company Research, claim and evidence provenance.
- Research assumptions require explicit rationale and falsification condition.
- Uses versioned Decimal arithmetic and `ROUND_HALF_EVEN` for PE, PS, EV/EBITDA and FCF yield.
- Uses one exact accepted Canonical Price and one exact eligible Slice 5 Comparison Eligibility revision.
- Enforces exact instrument, company, accounting scope, target period, currency, unit, freshness, price-age and diluted-share effective-range compatibility.
- Persists explicit non-meaningful states instead of absolute denominators, epsilon, clipping, imputation or period substitution.
- Preserves negative FCF yield as numeric with explicit state.
- Historical context requires at least eight eligible calculated observations, a 730-day eligible span, four financial period ends and unique eligible valuation dates.
- Peer membership is analyst-owned D3, preserves excluded members and requires distinct Company Research and instrument identities.
- Percentile uses deterministic midrank semantics and is not an attractiveness rank.
- Expectation gaps use exact expected/actual structured observations and preserve zero-expected percentage non-meaningfulness.
- Outputs never automatically rescore, relabel or rewrite Investment Candidate history.
- Migration `20260722_0015` creates thirteen additive append-only tables and refuses populated downgrade before any drop.
- Four local JSON-only commands and four exact-ID read APIs remain network-free and cutoff-aware.
- `/company-research/valuation-context` is explicit-ID only, safe-DOM rendered and never falls back.
- No fair value, target price, expected return, recommendation, portfolio or trading output.

### Guarded AI Research Assistance v1

- Available only inside one explicitly selected Company Research workspace.
- Deterministic immutable Manifest and SHA-256 fingerprint.
- Disabled by default with one explicit HTTPS OpenAI-compatible profile.
- Requires explicit remote-transmission confirmation.
- No retry, fallback, tools, browsing, search, retrieval or background execution.
- Strict output/citation validation and ephemeral D3 draft only.

## Active architecture candidate: Authorized CNINFO Disclosure Acquisition v1

Issue #188 defines the only active source-acquisition gate.

- Candidate source: licensed/documented CNINFO data service operated by 深圳证券信息有限公司.
- Candidate document class: public listed-company announcements and official document objects.
- Candidate mode: explicit user-initiated `licensed_api` only.
- Public-page scraping, browser request replay, undocumented endpoints and source fallback are rejected.
- Implementation remains blocked until official documentation, automated-access permission, retention rights, credential mechanism, rate limits and stable identifiers are owner-confirmed.
- Raw metadata/document bytes remain immutable L0 state.
- Source-specific normalized records remain L1.
- Candidate company/instrument matches are not accepted identity.
- Human review is required before existing Evidence Ledger acceptance.
- No scheduler, market-attention score, automatic alert or accepted-state promotion is included.

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Market-data Provider rows, series identity, ingestion status and cutoff | Market-data persistence | One explicit Provider per run/series; no fallback or row mixing |
| Canonical instrument, price, unit, currency and price eligibility | `backend.database.canonical_price*` | Exact append-only revisions and purpose-specific eligibility |
| Evidence grades, claims, links and conflicts | v0.5 Evidence Ledger | Acquisition may propose; explicit acceptance owns final state |
| Industry map, nodes, relationships and observations | v0.5B | Exact persisted identities and cutoff-visible revisions |
| Legacy beneficiary identity/classification | v0.5C Stage 1 | Preserve exact history |
| Typed beneficiary exposure and execution evidence | `industry_alpha.beneficiary_semantics_*` | Separate analyst-owned D3 profile |
| Company Research and financial hypotheses | v0.6A | Downstream records bind exact revisions |
| Narrative expectations and valuation observations | v0.6B | Research context only; no automatic numeric normalization |
| Catalyst and risk assessments | v0.6C | Not monitors, alerts or timing engines |
| Industry/company quality judgment | v0.6D | Does not generate price or recommendation state |
| Component-only company comparison | `company_comparison` | Complete universe, neutral ordering, no price arithmetic |
| Investment Candidate state and snapshots | `industry_alpha.investment_candidate_*` | Exact membership and deterministic rule results |
| Structured financial observations | `industry_alpha.normalized_financial_*` | Append-only values with exact provenance and period semantics |
| Normalized valuation arithmetic | `industry_alpha.normalized_valuation_*` | Exact price/financial revisions and versioned Decimal formulas |
| Historical/peer context | `industry_alpha.normalized_comparison_*` | Frozen membership; peer selection remains D3 |
| Structured expectation gap | `industry_alpha.normalized_expectation_*` | Exact expected/actual revisions; no hidden consensus lookup |
| Guarded AI Manifest and transport | Guarded AI modules | Explicit fingerprint/profile/confirmation; draft only |
| Future CNINFO source authorization and immutable capture | Proposed acquisition domain under Issue #188 | Contract-gated; no production owner until architecture approval |
| Future accepted disclosure evidence | Existing Evidence Ledger | Explicit human acceptance transaction only |

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
16. External-source acquisition requires exact source and access authorization.
17. Candidate entity matching is not accepted identity without reviewed acceptance.
18. Model-generated text is D3 draft assistance and cannot self-promote.
19. Guarded AI consumes only an explicit accepted Manifest and may not fetch missing evidence.
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
30. FX, corporate-action normalization and external consensus acquisition require separate authorization.
31. A comparison member cannot represent the same Company Research or instrument identity under another key.
32. Exact-ID read failures never fall back to another record.
33. Public website visibility does not authorize automated acquisition.
34. Source denial, schema drift or contract expiry fails closed without browser, proxy or alternate-source fallback.
35. Raw acquisition objects are L0 audit state and cannot directly become accepted evidence.
36. Human acceptance is required before acquisition state creates Evidence Ledger state.

## Semantic and derivation levels

### Semantic Level

- **L0 — Raw Provider/Source Data:** source output before internal normalization; audit only.
- **L1 — Source Normalized:** project fields under source-specific constraints; not automatically comparable or accepted.
- **L2 — Standardized:** standardized through an explicit accepted contract; usable only within that contract.
- **L3 — Canonical:** identity, measurement, unit, currency, market, adjustment, provenance, cutoff, chronology, decimal and missing-state contract.

Canonical Price owns L3 price state within its contract. Structured financial/valuation records remain contract-specific standardized state. Future disclosure normalization remains L1 until explicit Evidence Ledger acceptance.

### Evidence Qualification / Derivation Level

- **D0 — Direct Fact:** directly supported by an explicit source.
- **D1 — Deterministic Aggregation:** fully recorded inputs, scope, algorithm and missing treatment.
- **D2 — Rule Classification:** explicit versioned rules and responsibility boundary.
- **D3 — Analytical Judgment:** analysis or interpretation, including typed semantics, peer selection, candidate components, human acquisition review and AI drafts.

D3 does not automatically enter buy/sell guidance, target prices, return promises or trading signals.

## Capability matrix

| Capability | Reviewed boundary | Remaining boundary |
| --- | --- | --- |
| Market-data persistence | Complete-snapshot persistence and cutoff-aware reads | No hidden Provider expansion |
| Canonical Price | Listed identity, official close, provenance and purpose eligibility | No FX or hidden corporate-action normalization |
| Evidence Ledger / Industry Map | Evidence, claims, conflicts, map identities and revisions | No automatic external acceptance |
| Stage 1 beneficiary | Legacy identity/classification and pool handoff | No automatic full-market discovery |
| Typed Beneficiary Semantics | Append-only exposure/execution profiles | No automatic extraction or ranking |
| Company Research v0.6A-v0.6D | Hypotheses, narratives, catalysts, risks and quality | No automatic acceptance |
| Company Comparison | Complete-universe component comparison | No automatic peer selection |
| Investment Candidates | Transparent components, status and bounded priority | No automatic component scoring |
| Normalized Valuation / Expectation | Structured observations, formulas, comparisons and gaps | No fair value, target return, FX or hidden consensus acquisition |
| Guarded AI | Explicit ephemeral company-scoped drafts | No persisted AI state, tools or retrieval |
| CNINFO Disclosure Acquisition | Strict architecture active in Issue #188 | No implementation until exact contract entitlement is confirmed |
| Market Attention / Daily Radar | Not authorized | Requires accepted acquisition and separate architecture |

## Architecture debt register

- **D1 Current-state documentation drift — synchronized through Slice 6 preflight.**
- **D2 Repeated Stage 2 structure — bounded:** generic graph loading remains unjustified.
- **D3 Read utilities — bounded:** serializers, notices and failures remain domain-local.
- **D4 Command lifecycle/concurrency — partially shared:** semantic validation remains domain-local.
- **D5 ORM lifecycle — bounded:** append-only listener/import/metadata compatibility remains tested.
- **D6 Test-matrix growth — monitored:** acquisition must add contract fixtures without hidden network.
- **D7 Provider/source reachability — active decision:** Issue #188 requires a licensed CNINFO contract.
- **D8 Canonical market-price semantics — resolved for v1.**
- **D9 Product overview query architecture — resolved for current surfaces.**
- **D10 Consolidation cadence — 5–6 slices or concrete duplication/ownership/test-growth evidence.**
- **D11 Evidence-ingestion source/review ownership — reopened narrowly by Issue #188.**
- **D12 Guarded AI ownership — resolved for v1.**
- **D13 Typed beneficiary semantics — resolved for v1.**
- **D14 Complete-universe company comparison — resolved for v1.**
- **D15 Investment Candidate scoring/status semantics — resolved for v1.**
- **D16 Structured financial-input ownership — resolved by Issue #185 / PR #186.**
- **D17 Normalized valuation/expectation comparison semantics — resolved by Issue #185 / PR #186.**
- **D18 Authorized external evidence acquisition — active architecture decision in Issue #188.**

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
18. fixed-head review identity governance — PR #187.

Active architecture gate:

19. Authorized CNINFO Disclosure Acquisition v1 — Issue #188.

Deferred:

- production acquisition implementation until Issue #188 contract and entitlement gates are closed;
- additional financial/consensus sources;
- Market Attention and Daily Radar;
- OCR, body-text extraction and automatic evidence drafting;
- FX and corporate-action normalization.

## Current authorization state

- `main` includes PR #186 at `2cb894c1547380d2e350d4200150ad50a5461236`.
- The owner authorized the next roadmap phase with `进行下一轮开发` on 2026-07-22.
- Issue #188 authorizes architecture work only for one licensed/documented CNINFO announcement source contract.
- No production network adapter, migration, dependency, credential or live request is authorized yet.
- No undocumented endpoint, public-page scraping, browser automation or source fallback is authorized.
- No Market Attention, Daily Radar, alerting, recommendation, portfolio or trading work is authorized inside Issue #188.

## Next governed gate

Issue #188 must establish and receive process-independent fixed-head architecture approval for:

1. exact authorized source and permitted access mode;
2. contract package and entitlement evidence without exposing secrets;
3. credential isolation and host allowlist;
4. bounded user-initiated request semantics;
5. immutable metadata/document capture;
6. source-specific normalization;
7. fingerprints, duplicates, corrections and replay;
8. candidate identity versus accepted identity;
9. explicit human review and Evidence Ledger acceptance;
10. cutoff, recorded UTC and correction semantics;
11. schema/migration/downgrade candidate;
12. offline contract fixtures and zero-network default tests;
13. fail-closed access-control and contract-drift behavior;
14. explicit exclusions for scraping, generic providers and automatic accepted-state promotion.

No acquisition implementation is authorized by this baseline alone.
