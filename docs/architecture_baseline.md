# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and a linked GitHub Issue controls Standard or Strict scope.

- Released software version: `0.2.0`.
- Current accepted `main` baseline: `1f9edfc0719c9d512ed95c2330db78dadea17eea`.
- Latest merged product capability: Personal Research Workbench UI Phase 2A through architecture PR #209 and implementation PR #212.
- Personal Research Workbench UI Phase 1A–1D remains accepted through architecture PR #199 and implementation PRs #201, #203, #205 and #207.
- Industry Thesis orchestration foundation and proposal review remain accepted through PRs #193, #195 and #197.
- Normalized Valuation and Expectation Metrics v1 remains accepted through architecture PR #184 and implementation PR #186.
- Latest merged external-data architecture decision: Account-Authorized THS Structured Financial Data v1 through PR #191.
- Authorized CNINFO Disclosure Acquisition v1 architecture remains accepted through PR #189.
- Review-identity governance is merged through PR #187.
- Canonical Price and Comparison Eligibility v1 remains the authoritative price owner through PRs #176/#178.
- No product or architecture phase is currently authorized. Roadmap Issue #210 is planning only and does not start Phase 2B.
- Issue #213 is a Light project-state housekeeping task only; it is not a product gate.
- CNINFO automated acquisition remains implementation-blocked pending a separately accepted source/access contract.
- THS production implementation remains blocked pending exact non-secret account capability, host, endpoint, limit, retention and revision facts.
- Earlier Evidence Ingestion Issue #154 / PR #155 remains closed-unmerged and reference only.

Documentation may advance without changing the released version. An architecture or capability merge does not itself authorize implementation, release, source expansion, portfolio action or trading behavior.

## Product boundary

AQuantAI is a local-first, personal-use, research-only and non-advisory A-share research workbench. It is not a broker, order-management system, automated-trading system, investment-advice service, multi-user SaaS product or production deployment platform.

Deterministic calculations, canonicalization, selectors and accepted workflow state belong to reviewed application code. An LLM may assist only behind an explicit bounded adapter and may not own evidence qualification, deterministic state, accepted research state, execution or trading behavior.

The product may identify current research-priority candidates under an explicit rule. It must preserve the complete beneficiary universe and expose every component, missing state, penalty and reason. It must not produce unexplained recommendations, target prices, expected returns, position sizes or trading actions.

The target personal-product shell contains five modules:

1. 今日市场;
2. 产业研究;
3. 关注与跟踪;
4. 研究组合;
5. 系统设置.

Only separately approved phases may activate those modules. Disabled future modules must not display fabricated data.

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
       -> Market Cockpit
       -> Today Market
  -> optional company-scoped Guarded AI D3 draft assistance

accepted Industry Thesis orchestration foundation
  -> explicit industry/thesis intake session and append-only revisions
  -> deterministic exact local candidate proposals
  -> explicit selected / rejected / unresolved review
  -> deterministic reviewed-plan preview and fingerprint
  -> reviewed_plan_ready session revision
  -> future existing-owner acceptance transaction and exact output links
  -> future readiness and Investment Candidate handoff

merged Personal Research Workbench UI Phase 1
  -> Chinese-first five-module shell
  -> ordinary-language thesis intake with explicit scope confirmation
  -> deterministic local source selection
  -> complete local-scope candidate universe
  -> complete selected / rejected / unresolved review
  -> exact reviewed-plan result and history reopening
  -> browser-local display settings

merged Personal Research Workbench UI Phase 2A
  -> explicit persisted local equity series
  -> optional explicit persisted benchmark and sector series
  -> explicit information-cutoff and recorded-UTC boundaries
  -> existing Market Cockpit deterministic calculation owner
  -> Chinese-first Today Market local snapshot
  -> unsupported breadth, anomaly, event and refresh states shown honestly

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
12. Chinese-first read-only `/company-research/valuation-context` requiring explicit revision IDs and both as-of boundaries;
13. local JSON-only Industry Thesis session/candidate commands, exact dual-as-of reads, proposal review and reviewed-plan reads;
14. Chinese-first `/industry-analysis` Personal Research Workbench with scope creation/revision, complete candidate construction, complete three-state review, exact reviewed-plan result and history reopening;
15. browser-local `/workbench/settings` for presentation-only preferences;
16. Chinese-first local-only `/today-market`, exact local-series catalog and snapshot API requiring explicit information-cutoff and recorded-UTC boundaries.

No current runtime provides the thesis owner-acceptance transaction or output links, daily news/announcement radar, followed-entity alerts, observation/simulated portfolio, fair value, target price, expected return, buy/sell/hold output, position sizing, broker execution, automated trading or external Provider/disclosure acquisition.

The existing `/market-cockpit` remains a separate read-only technical surface. `/today-market` is the ordinary-user workbench surface for explicit persisted local equity, optional benchmark/sector context and dual-as-of visibility. Neither surface performs remote refresh or upgrades an exact selected series into full-market coverage.

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

### Industry Thesis Intake and Research Orchestration foundation

PRs #193, #195 and #197 define and implement the accepted offline orchestration foundation.

- One append-only session identity and revision history owns the exact user thesis, explicit market scope, driver/horizon, chain boundary, exclusions, seeds, coverage and both as-of boundaries.
- Candidate proposals are non-accepted orchestration state sourced only from exact accepted local mappings, exact existing Industry Map revisions or explicit user seeds in the current implementation.
- AI draft candidates remain rejected in the implemented builder and require a later separately authorized slice.
- Candidate identities and revisions preserve exact source references, identity state, exposure proposal, rationale, uncertainty and review state.
- Proposal review requires the complete exact latest candidate universe and explicit selected/rejected/unresolved decisions.
- Selected candidates require exactly one authoritative persisted identity and explicit non-unknown exposure.
- The reviewed plan is deterministic, input-order-independent, fingerprinted and dual-as-of readable.
- Dry-run/commit plan parity is independent of invocation time.
- Normal historical invisibility returns not-visible rather than false graph corruption.
- The implemented state stops at `reviewed_plan_ready`.
- No Industry Map, Stage 1, typed-semantics, output-link, Company Research, price, valuation or Investment Candidate owner write occurs.
- Migration `20260722_0016` owns six additive append-only orchestration table families and refuses populated downgrade.
- Full tests and a production-boundary three-candidate offline demo are merged.

### Personal Research Workbench UI Phase 1

PR #199 defines the architecture; PRs #201, #203, #205 and #207 implement the accepted offline workbench slices.

- Chinese-first five-module shell using FastAPI and static HTML/CSS/vanilla JavaScript.
- `/workbench` enters 产业研究; `/industry-analysis` provides history and ordinary-language intake.
- Explicit scope confirmation precedes any session write.
- Exact local maps, mappings, company/instrument records and explicit seeds are the deterministic candidate sources.
- Fuzzy text never establishes accepted identity or full-market coverage.
- Candidate construction preserves the complete local-scope universe and duplicate company paths from different exact sources.
- Review requires explicit selected/rejected/unresolved decisions for every exact latest candidate.
- Dry-run and commit use the same deterministic reviewed plan and fingerprint.
- Exact result/history reopening uses explicit dual-as-of boundaries and no hidden latest fallback.
- Browser conflicts preserve unsaved decisions and never silently retry or rebase.
- Technical IDs and fingerprints are progressive details, not ordinary inputs.
- `reviewed_plan_ready` is orchestration state, not accepted Industry Map, Stage 1, typed-semantics, output-link or Investment Candidate state.
- Browser-local settings contain presentation preferences only.
- No Provider, scheduler, notification, AI call, portfolio ledger or trading behavior is included.

### Personal Research Workbench UI Phase 2A — Today Market

PR #209 defines the accepted architecture; PR #212 implements the local-only Today Market slice.

- 今日市场 is active at `/today-market` while `/workbench` continues to enter 产业研究.
- Only exact successful complete local equity, benchmark and sector series are eligible.
- The ordinary-user local-series catalog uses deterministic labels, explicit selection and no first/newest auto-selection.
- Catalog and snapshot reads require explicit information-cutoff and recorded-UTC boundaries.
- Existing Market Cockpit repositories, calculators and service remain the only deterministic market calculation owner.
- Today Market adds only a bounded read-only catalog, chronology adapter, projection and static presentation.
- The page shows selected-universe price behavior, liquidity, benchmark, sector, provenance, scope, completeness and alignment state.
- An exact selected series is never represented as full-market coverage.
- Unsupported breadth, stock anomaly, event/cause, market-attention and remote-refresh sections remain unavailable.
- No network, Provider, credential, scheduler, notification, AI or write action occurs.
- No schema, migration, dependency or new front-end framework was introduced.

The detailed route/API contracts remain recorded in `docs/personal_research_workbench_ui_phase2a_preflight.md` and Issue #211.

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Market-data Provider rows, series identity, ingestion status and cutoff | Market-data persistence | One explicit Provider per run/series; no fallback or row mixing |
| Market Cockpit price/liquidity/benchmark/sector calculations | Existing Market Cockpit repositories, calculators and service | Today Market may present but cannot recalculate or upgrade scope |
| Today Market labels, grouping and unsupported notices | `backend.api.today_market` and `today_market/static` | Non-persistent presentation only; selected local scope is never full-market identity |
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
| Thesis session, proposal and reviewed-plan audit state | `industry_alpha.industry_thesis_*` | Non-accepted append-only coordination state |
| Accepted thesis-derived map and beneficiary state | Existing Industry Map / Stage 1 / typed-semantics owners | Future explicit user plan and owner transaction only |
| Thesis-derived research priority | Existing Investment Candidate owner | Existing exact rule version; no second scoring owner |
| UI page labels, grouping and navigation | Non-persistent workbench adapters | Presentation only; cannot create product meaning |
| Browser-local appearance/density preferences | Browser local storage | No credentials or research state |

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
46. A UI label, group, count or visual emphasis cannot create identity, evidence quality, beneficiary status or research priority.
47. Ordinary users must not be required to enter technical identifiers that the selected local record already owns.
48. Disabled future modules must not display sample values as if they were live product state.
49. Filtering candidate rows cannot alter the complete universe submitted for review.
50. UI write conflicts preserve unsaved user decisions and require explicit reload/review; they never silently rebase.
51. An exact selected local market series is not full-market coverage unless its accepted selector contract explicitly owns that scope.
52. Market, benchmark and sector series are never auto-selected or treated as compatible from names, recency or Provider equality.
53. A Today Market page cannot claim historical reproducibility unless information-cutoff and recorded-UTC visibility are both enforced.
54. Unsupported breadth, anomaly, event and refresh capabilities remain explicit unavailable states rather than fabricated values.

## Semantic and derivation levels

### Semantic Level

- **L0 — Raw Provider/Source Data:** source output before internal normalization; audit only.
- **L1 — Source Normalized:** project fields under source-specific constraints; not automatically comparable or accepted.
- **L2 — Standardized:** standardized through an explicit accepted contract; usable only within that contract.
- **L3 — Canonical:** identity, measurement, unit, currency, market, adjustment, provenance, cutoff, chronology, decimal and missing-state contract.

Canonical Price owns L3 price state within its contract. Structured financial/valuation records remain contract-specific standardized state. Disclosure and THS normalization remain L1 until explicit existing-owner acceptance. Market Cockpit source observations remain within their source-series contract and do not gain Canonical Price authority through Today Market display. Thesis candidate proposals and UI view models are orchestration/presentation state and do not gain semantic authority through persistence or display.

### Evidence Qualification / Derivation Level

- **D0 — Direct Fact:** directly supported by an explicit source.
- **D1 — Deterministic Aggregation:** fully recorded inputs, scope, algorithm and missing treatment.
- **D2 — Rule Classification:** explicit versioned rules and responsibility boundary.
- **D3 — Analytical Judgment:** analysis or interpretation, including typed semantics, peer selection, candidate components, human acquisition review and AI drafts.

D3 does not automatically enter accepted identity, evidence, map membership, buy/sell guidance, target prices, return promises or trading signals.

## Capability matrix

| Capability | Reviewed boundary | Remaining boundary |
| --- | --- | --- |
| Market-data persistence | Complete-snapshot persistence, cutoff-aware reads and optional recorded-UTC visibility for Today Market | No hidden Provider expansion or full-market identity inference |
| Market Cockpit | Exact selected-series price/liquidity plus optional benchmark/sector context | Technical surface only; no full-market claim, anomaly/event cause or remote refresh |
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
| Industry Thesis Orchestration | Session/candidate/reviewed-plan foundation merged through PR #197 | No owner-acceptance transaction or output links |
| Personal Research Workbench UI Phase 1 | Scope intake, candidate build, complete review, exact result/history and settings merged through PR #207 | No accepted owner handoff, Provider, alerts or portfolio |
| Today Market UI Phase 2A | Local-series catalog, dual-as-of snapshot and ordinary-user page merged through PR #212 | No Provider refresh, full-market breadth, anomaly/cause engine, event feed or market-attention data |
| Market Attention / Daily Radar | Source observations remain isolated candidates | Separate Provider, ingestion, scheduler and product authorization required |
| Follow / Track | No accepted followed-entity or alert state | Separate persistence, change-rule and notification architecture required |
| Research Portfolio | Existing research/price foundations only | Separate observation/simulated ledger and corporate-action architecture required |

## Architecture debt register

- **D1 Current-state documentation drift — synchronized through Issue #213 after PR #212.**
- **D2 Repeated Stage 2 structure — bounded:** generic graph loading remains unjustified.
- **D3 Read utilities — bounded:** serializers, notices and failures remain domain-local.
- **D4 Command lifecycle/concurrency — partially shared:** semantic validation remains domain-local.
- **D5 ORM lifecycle — bounded:** append-only listener/import/metadata compatibility remains tested.
- **D6 Test-matrix growth — monitored:** each UI phase adds one production-boundary offline path without hidden network.
- **D7 External Provider reachability — blocked:** THS implementation awaits exact account contract facts.
- **D8 Canonical market-price semantics — resolved for v1; Provider promotion remains separately gated.**
- **D9 Product overview query architecture — resolved for current surfaces; Today Market has an explicit independent ceiling.**
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
- **D21 Industry-thesis entry/orchestration — offline browser workflow resolved through PR #207; owner acceptance remains later.**
- **D22 Industry-level AI assistance — deferred:** optional proposal-only extension after the offline workbench proves useful.
- **D23 Personal workbench composition — Phase 1 resolved through PR #207; Phase 2A Today Market resolved through PR #212.**
- **D24 Free-text discovery gap — explicit:** automatic fuzzy discovery remains later governed assistance.
- **D25 Local market series discoverability — resolved through PR #212 with a bounded exact catalog and no auto-selection.**
- **D26 Market snapshot bitemporality — resolved through PR #212 using recorded-UTC visibility without changing calculation ownership.**

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
20. Account-Authorized THS Structured Financial Data architecture — PR #191;
21. Industry Thesis Intake and Research Orchestration architecture — PR #193;
22. Industry Thesis offline persistence/command/query foundation — PR #195;
23. Industry Thesis proposal review and deterministic reviewed plan — PR #197;
24. Personal Research Workbench UI Phase 1 architecture — PR #199;
25. Personal Research Workbench UI Phase 1A shell/history/settings — PR #201;
26. Personal Research Workbench UI Phase 1B scope create/revise — PR #203;
27. Personal Research Workbench UI Phase 1C complete candidate universe — PR #205;
28. Personal Research Workbench UI Phase 1D complete review and exact result — PR #207;
29. Personal Research Workbench UI Phase 2A architecture — PR #209;
30. Personal Research Workbench UI Phase 2A Today Market implementation — PR #212.

No product or architecture phase is currently active.

Planned later product phases, each separately governed and not yet authorized:

31. Personal Research Workbench UI Phase 2B ordinary-user usability consolidation described by roadmap Issue #210;
32. Today Market Provider-backed refresh and broader exact market contracts after source authorization;
33. Daily Industry Radar with authorized news/announcement ingestion and scheduler;
34. Follow and Track with followed-entity/change/notification contracts;
35. Research Portfolio, observation first and simulated ledger later;
36. advanced model/Provider settings with credential security and explicit role boundaries.

Deferred:

- production CNINFO/webpage/PDF acquisition until its own accepted implementation contract;
- THS production implementation until exact account contract facts and separate authorization;
- external consensus sources;
- Market Attention scoring and Daily Radar product behavior;
- OCR and automatic accepted evidence drafting;
- FX and accepted corporate-action normalization;
- industry-level guarded AI drafting until a separately accepted proposal-only slice;
- owner acceptance/output links from a reviewed thesis plan;
- followed-entity alerts and portfolio ledgers;
- full-market breadth, stock anomaly/cause and live refresh beyond the exact Phase 2A local contract.

## Current authorization state

- `main` includes Personal Research Workbench UI Phase 2A PR #212 at `1f9edfc0719c9d512ed95c2330db78dadea17eea`.
- Issues #208 and #211 are completed; PRs #209 and #212 define and implement the accepted local-only Today Market slice.
- Historical connectivity Issue #37 and unmerged Draft PR #38 are retired through authorized housekeeping Issue #213.
- Issue #210 remains a roadmap plan only. It does not authorize a Phase 2B architecture Issue, branch, code change or PR.
- No product architecture or implementation phase is active.
- No Provider, news, announcement, THS, browser acquisition, scheduler, notification, new AI call or portfolio ledger is authorized.
- No remote refresh, full-market claim, anomaly/cause engine, accepted evidence, Investment Candidate or portfolio owner write is authorized by current housekeeping.
- No recommendation, target price, expected return, position size, broker, order or automated trading behavior is authorized.
- No release, tag or version change is authorized.

## Next governed gate

There is no automatically active next phase.

A future Phase 2B may begin only after the project owner separately authorizes one Strict architecture-preflight Issue against the then-current exact `main`. That architecture work must remain within the five bounded usability improvements described in roadmap Issue #210, establish exact existing-route/API reuse, file families, state mappings, golden/failure paths and stop conditions, and obtain applicable fixed-head review and separate merge authorization.

Roadmap Issue #210, this baseline and housekeeping Issue #213 do not themselves authorize Phase 2B architecture or implementation.

Provider-backed Today Market refresh, Daily Industry Radar, Follow and Track, Research Portfolio, external acquisition and any new AI/credential boundary each require their own separate governed authorization.
