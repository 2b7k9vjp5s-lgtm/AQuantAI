# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and a linked GitHub Issue controls Standard or Strict scope.

- Released software version: `0.2.0`.
- Latest merged product capability: Owner Context v2 and ordinary-user acceptance replacement through architecture PR #244 and implementation PR #246, merge commit `2c432d1676146d5dd168907419fe2160f447e50c`.
- THS Stage C0 capability merge commit: `d899115e571d393ec45ff9740df4d21cd5c7133f` through implementation PR #231.
- Personal Research Workbench UI Phase 2B remains accepted through architecture PR #216 and implementation PR #218.
- Personal Research Workbench UI Phase 2A Today Market remains accepted through architecture PR #209 and implementation PR #212.
- Personal Research Workbench UI Phase 1A–1D remains accepted through architecture PR #199 and implementation PRs #201, #203, #205 and #207.
- Industry Thesis intake, proposal review, exact Owner Context v2, owner acceptance and exact output links are accepted through PRs #193, #195, #197, #235, #237, #239, #244 and #246.
- Normalized Valuation and Expectation Metrics v1 remains accepted through architecture PR #184 and implementation PR #186.
- Account-Authorized THS Structured Financial Data v1 architecture remains accepted through PR #191; Today Market source selection and contract evidence were narrowed through PRs #220, #222, #224 and #226.
- THS Stage C0 offline contract and request-planning foundation is accepted through architecture PR #229 and implementation PR #231.
- Authorized CNINFO Disclosure Acquisition v1 architecture remains accepted through PR #189.
- Review-identity governance is merged through PR #187.
- Canonical Price and Comparison Eligibility v1 remains the authoritative price owner through PRs #176/#178.
- Issue #225 remains the sole live THS contract gate. Live Stage C1 is blocked by unresolved account quota, completion, correction/revision/late-data and API-key lifecycle facts.
- Issues #227, #230, #242 and #245 remain open until separately authorized for closure; their linked architecture or implementation PRs are merged.
- Frozen superseded Draft PR #241 remains open and read-only at `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.
- Issue #247 is the active Strict Architecture Preflight for readable accepted industry-research result assembly and an optional explicitly selected exact Investment Candidate snapshot overlay.
- CNINFO automated acquisition remains implementation-blocked pending a separately accepted source/access contract.
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

accepted Industry Thesis orchestration and owner-acceptance flow
  -> explicit industry/thesis intake session and append-only revisions
  -> deterministic exact local candidate proposals
  -> explicit selected / rejected / unresolved review
  -> explicit exact Map Revision selection
  -> server-resolved Research Case and Industry Map
  -> fingerprinted reviewed-plan v2 and Owner Context
  -> reviewed_plan_ready session revision
  -> exact context-bound acceptance preview
  -> explicit matching-fingerprint atomic commit
  -> accepted_outputs_linked session revision and exact output links
  -> complete accepted result and readiness reads
  -> optional later explicit Investment Candidate handoff under its existing owner

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

merged Personal Research Workbench UI Phase 2B
  -> exact recent-research continuation from the existing dual-as-of session response
  -> shared five-step industry-research presentation
  -> one deterministic primary action per tested state
  -> stable ordinary-Chinese state explanations
  -> truthful first-use guidance
  -> no second workflow owner or new persisted UI state

accepted THS Stage C0 offline foundation
  -> immutable reviewed source-specific contract
  -> explicit closed readiness values and blocked reasons
  -> reserved synthetic selector namespace
  -> deterministic non-executable dry-run planning
  -> secret-free request/schema fingerprints and redaction
  -> strict synthetic response validation
  -> no transport, credential, persistence or Provider-valued fixture path

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
13. local JSON-only Industry Thesis session/candidate commands, exact dual-as-of reads, proposal review, reviewed-plan v1/v2 reads, Owner Context validation, owner-acceptance preview/commit and exact accepted-output reads;
14. Chinese-first `/industry-analysis` Personal Research Workbench with scope creation/revision, complete candidate construction, complete three-state review, explicit exact Owner Context selection, exact acceptance authoring, preview/commit, accepted-result and history reopening;
15. exact context-bound Stage 1 reuse/append/create and candidate-pool create/append/reuse/zero-supported ordinary-user controls;
16. browser-local `/workbench/settings` for presentation-only preferences;
17. Chinese-first local-only `/today-market`, exact local-series catalog and snapshot API requiring explicit information-cutoff and recorded-UTC boundaries;
18. source-specific `datasource.ths_structured_provider` Stage C0 contract/readiness/planning/validation package, structurally offline and non-executable.

No current runtime provides the Issue #247 assembled conclusion/chain/current-candidate-overlay result, daily news/announcement radar, followed-entity alerts, observation/simulated portfolio, fair value, target price, expected return, buy/sell/hold output, position sizing, broker execution, automated trading or live external Provider/disclosure acquisition.

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

PR #191 defines the accepted external Provider architecture. PRs #220, #222, #224 and #226 narrow the controlled-refresh, Today Market source and contract-evidence decisions without authorizing live production access.

- Candidate source: official account-authorized 同花顺 / HiThink Financial Data API.
- Candidate access: explicit user-initiated personal, local, non-commercial research.
- Candidate transport: documented REST API only when a later live stage is separately authorized.
- Candidate families: instrument identity, daily market, company actions, financial statements, industry/concept taxonomy and market-attention observations.
- Local normalized research storage and derived local outputs are supported by reviewed official repository evidence; public Provider-valued fixtures remain prohibited without explicit redistribution permission.
- Source authorization and account limits remain fail-closed until exact applicable non-secret facts are reviewed.
- Provider observations remain L0/L1 until explicit reviewed promotion under existing owners.
- THS market values do not automatically replace Canonical Price.
- THS financial values do not automatically become official evidence or normalized financial inputs.
- Current taxonomy membership is not historical membership.
- Market attention cannot create beneficiary, evidence-grade, candidate, recommendation or trading state.
- No scheduler, background worker, hidden fallback or read-triggered network is included.

### THS Stage C0 Offline Contract and Request-Planning Foundation

PR #229 defines and PR #231 implements the accepted source-specific offline foundation for `a_share_index_daily_history`.

- Owns one immutable reviewed host/method/path/query/response contract and its canonical fingerprint.
- Owns closed readiness statuses and stable technical/ordinary-Chinese blocked reasons.
- Accepts only reserved `SYNTH.IDX.*` selectors with explicit millisecond bounds and a maximum ten-calendar-year window.
- Produces deterministic ordered dry-run plans, request fingerprints and schema fingerprints without credentials, account IDs, request IDs or runtime clocks.
- Strictly validates synthetic standard envelopes and index-history rows and rejects unknown fields, wrong types and non-ascending dates.
- Static and dynamic guards prohibit HTTP, DNS, socket, subprocess, environment-secret and database access.
- Every Stage C0 plan has `synthetic_only=true` and `remote_executable=false`, including when all hypothetical readiness inputs are marked confirmed.
- Stage C0 owns no transport, credential reference, raw capture, persistence, API, UI, Today Market publication or downstream accepted-state write.
- Live Stage C1 remains blocked by Issue #225 under `blocked_quota_contract`.

### Industry Thesis Intake, Review and Owner Acceptance

PRs #193, #195 and #197 define and implement the accepted offline intake, persistence, candidate and proposal-review foundation. PRs #235/#237 add reviewed-plan owner acceptance and exact output links. PR #239 defines the ordinary-user completion contract. PRs #244/#246 replace same-stock context inference with explicit reviewed-plan v2 Owner Context and complete the ordinary-user acceptance/result path.

- One append-only session identity and revision history owns the exact user thesis, explicit market scope, driver/horizon, chain boundary, exclusions, seeds, coverage and both as-of boundaries.
- Candidate proposals are non-accepted orchestration state sourced only from exact accepted local mappings, exact existing Industry Map revisions or explicit user seeds in the current implementation.
- AI draft candidates remain rejected in the implemented builder and require a later separately authorized slice.
- Candidate identities and revisions preserve exact source references, identity state, exposure proposal, rationale, uncertainty and review state.
- Proposal review requires the complete exact latest candidate universe and explicit selected/rejected/unresolved decisions.
- Selected candidates require exactly one authoritative persisted identity and explicit non-unknown exposure.
- Active reviewed writes use `aquantai.industry-thesis-acceptance-plan.v2` with one `aquantai.industry-thesis-owner-context.v1` exact Map Revision selected by the user and Case/Map resolved by the server.
- Owner Context participates in deterministic reviewed IDs, plan fingerprints and chronology. Candidate provenance and key semantics remain unchanged.
- Unaccepted v1 reviewed plans fail closed and require explicit v2 re-review; already accepted v1 exact reads and idempotent replay remain supported.
- Owner-acceptance preview is zero-write. Commit requires the exact matching preview fingerprint and one atomic existing-owner transaction.
- HTTP and core both reject submitted Case/Map/Revision/mode substitution before owner writes.
- Exact Stage 1 reuse/append/create, semantic none/exact reuse and candidate-pool create/append/reuse/zero-supported are explicit ordinary-user operations.
- The frozen complete accepted result remains separate from the supported-only candidate-pool handoff.
- Exact result, output and readiness reads require information-cutoff and recorded-UTC boundaries and never fall back to newer records.
- Migrations `20260722_0016` and `20260725_0017` own additive orchestration/output-link persistence and refuse unsafe populated downgrade. Owner Context v2 requires no new table, column, migration, backfill or history rewrite.
- Full tests, production-boundary offline demos, query ceilings and zero-network guards are merged.
- Acceptance creates no automatic Company Research, Investment Candidate, valuation, recommendation, portfolio or trading state.

### Personal Research Workbench UI Phase 1

PR #199 defines the architecture; PRs #201, #203, #205 and #207 implement the accepted offline workbench slices. PR #246 extends the same product flow through explicit Owner Context acceptance and exact accepted-result reopening.

- Chinese-first five-module shell using FastAPI and static HTML/CSS/vanilla JavaScript.
- `/workbench` enters 产业研究; `/industry-analysis` provides history and ordinary-language intake.
- Explicit scope confirmation precedes any session write.
- Exact local maps, mappings, company/instrument records and explicit seeds are the deterministic candidate sources.
- Fuzzy text never establishes accepted identity or full-market coverage.
- Candidate construction preserves the complete local-scope universe and duplicate company paths from different exact sources.
- Review requires explicit selected/rejected/unresolved decisions for every exact latest candidate.
- Dry-run and commit use the same deterministic reviewed plan and fingerprint.
- Exact result/history reopening uses explicit dual-as-of boundaries and no hidden latest fallback.
- Reviewed-plan v2 acceptance requires explicit exact Map Revision and explicit per-member owner operations.
- Browser conflicts preserve unsaved decisions and never silently retry or rebase.
- Technical IDs and fingerprints are progressive details, not ordinary inputs.
- Browser-local settings contain presentation preferences only.
- No Provider, scheduler, notification, hidden AI call, portfolio ledger or trading behavior is included.

### Personal Research Workbench UI Phase 2B — Ordinary-User Usability Consolidation

PR #216 defines and PR #218 implements the accepted presentation-only consolidation over the existing industry-research workflow.

- Reuses the exact dual-as-of `GET /industry-analysis/api/sessions` response for the recent-research card and history list.
- Always represents `sessions[0]`; it never skips a newer stopped/non-continuable record to show an older convenient record.
- Exact continuation paths are response-owned and bind the exact session/revision identity and recorded boundaries.
- Uses the shared five-step vocabulary `研究主题 -> 确认范围 -> 候选公司 -> 人工审核 -> 研究结果`.
- Derives presentation state from exact routes and already-loaded responses with no persisted UI progress or second workflow owner.
- Uses one visually dominant primary action and stable Chinese `发生了什么 / 为什么重要 / 现在可以做什么` explanations.
- Shows a truthful first-use guide only when the database is available and no exact history is visible.
- Preserves unsaved candidate-review decisions after conflicts; no silent retry, rebase or record substitution.
- Adds no schema, migration, Provider, network, notification, portfolio or trading behavior.

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
| Investment Candidate state and snapshots | `industry_alpha.investment_candidate_*` | Exact membership and deterministic rule results; no second scoring owner |
| Structured financial observations | `industry_alpha.normalized_financial_*` | Append-only values with exact provenance and period semantics |
| Normalized valuation arithmetic | `industry_alpha.normalized_valuation_*` | Exact price/financial revisions and versioned Decimal formulas |
| Historical/peer context | `industry_alpha.normalized_comparison_*` | Frozen membership; peer selection remains D3 |
| Structured expectation gap | `industry_alpha.normalized_expectation_*` | Exact expected/actual revisions; no hidden consensus lookup |
| Guarded AI Manifest and transport | Guarded AI modules | Explicit fingerprint/profile/confirmation; draft only |
| CNINFO source authorization and disclosure capture | Accepted architecture in PR #189 | Production path remains separately gated |
| Future accepted disclosure evidence | Existing Evidence Ledger | Explicit human acceptance transaction only |
| THS reviewed public contract, readiness, synthetic selectors and dry-run planning | `datasource.ths_structured_provider` Stage C0 | Offline-only; no transport, credential, persistence or Provider-valued fixture |
| THS live source authorization, raw capture and source normalization | Future source-specific Stage C1 under accepted PR #191 architecture | Issue #225 contract-gated, disabled and unauthorized |
| Thesis session, proposal and reviewed-plan audit state | `industry_alpha.industry_thesis_*` | Append-only coordination state; v2 freezes exact Owner Context |
| Accepted thesis output identity, exact bindings and readiness | `industry_alpha.industry_thesis_owner_acceptance*` | Exact accepted output links, complete universe and dual-as-of reads |
| Accepted thesis-derived map and beneficiary state | Existing Industry Map / Stage 1 / typed-semantics owners | Explicit context-bound user plan and atomic owner transaction only |
| Thesis-derived research priority | Existing Investment Candidate owner | Existing exact rule version; no result-assembler score or status calculation |
| UI page labels, grouping, navigation and optional exact overlay selection | Non-persistent workbench adapters | Presentation/URL state only; cannot create product meaning or rewrite accepted history |
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
55. Accepted Industry Thesis history and an optional current candidate overlay are separate meanings and must remain visibly separate.
56. An optional candidate overlay requires one explicitly selected exact snapshot revision and never auto-selects latest, first or uniquely reachable state.
57. Candidate overlays join accepted results only by exact beneficiary revision and exact candidate-pool revision, never by stock/name overlap.

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
| Investment Candidates | Transparent components, status and bounded priority | No automatic component scoring or hidden snapshot selection |
| Normalized Valuation / Expectation | Structured observations, formulas, comparisons and gaps | No fair value, target return, FX or hidden consensus acquisition |
| Guarded AI | Explicit ephemeral company-scoped drafts | No persisted accepted AI state, tools or retrieval |
| CNINFO Disclosure Acquisition | Architecture accepted through PR #189 | Production acquisition remains separately gated |
| THS Structured Provider | Architecture/source-contract evidence accepted through PRs #191/#220/#222/#224/#226; offline Stage C0 merged through PRs #229/#231 | Live Stage C1 remains blocked by Issue #225; no credential, transport, persistence or source activation authorized |
| Industry Thesis Orchestration and Acceptance | Reviewed-plan v2, explicit Owner Context, atomic owner acceptance, exact output links, complete accepted result and readiness merged through PR #246 | Issue #247 readable conclusion/chain/exact current-candidate overlay architecture; no automatic downstream creation |
| Personal Research Workbench UI Phase 1/2B | Scope intake, complete candidate review, explicit Owner Context acceptance, exact accepted result/history and ordinary-user usability merged through PRs #207/#218/#246 | No Provider, alerts or portfolio; richer assembled result remains under Issue #247 preflight |
| Today Market UI Phase 2A | Local-series catalog, dual-as-of snapshot and ordinary-user page merged through PR #212 | No Provider refresh, full-market breadth, anomaly/cause engine, event feed or market-attention data |
| Market Attention / Daily Radar | Source observations remain isolated candidates | Separate Provider, ingestion and product authorization required |
| Follow / Track | No accepted followed-entity or alert state | Separate persistence, change-rule and notification architecture required |
| Research Portfolio | Existing research/price foundations only | Separate observation/simulated ledger and corporate-action architecture required |

## Architecture debt register

- **D1 Current-state documentation drift — corrected through merged PR #246 state in Issue #247 preflight.**
- **D2 Repeated Stage 2 structure — bounded:** generic graph loading remains unjustified.
- **D3 Read utilities — bounded:** serializers, notices and failures remain domain-local.
- **D4 Command lifecycle/concurrency — partially shared:** semantic validation remains domain-local.
- **D5 ORM lifecycle — bounded:** append-only listener/import/metadata compatibility remains tested.
- **D6 Test-matrix growth — monitored:** each UI or source-contract slice adds one production-boundary offline path without hidden network.
- **D7 External Provider reachability — partially resolved:** THS Stage C0 is implemented offline; live Stage C1 remains blocked by Issue #225.
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
- **D18 Account-authorized THS architecture — source contract and Stage C0 are resolved; applicable live account facts remain blocked under Issue #225.**
- **D19 Provider taxonomy chronology — active:** current snapshots must not masquerade as historical membership.
- **D20 Market-attention isolation — active:** attention remains separate from beneficiary and candidate quality.
- **D21 Industry-thesis entry/orchestration/acceptance — resolved through PR #246; readable assembled conclusion and exact current-candidate overlay are active under Issue #247.**
- **D22 Industry-level AI assistance — deferred:** optional proposal-only extension after the deterministic product loop is complete.
- **D23 Personal workbench composition — Phase 1 resolved through PR #207, Phase 2B usability through PR #218, Phase 2A Today Market through PR #212 and acceptance completion through PR #246.**
- **D24 Free-text discovery gap — explicit:** automatic fuzzy discovery remains later governed assistance.
- **D25 Local market series discoverability — resolved through PR #212 with a bounded exact catalog and no auto-selection.**
- **D26 Market snapshot bitemporality — resolved through PR #212 using recorded-UTC visibility without changing calculation ownership.**
- **D27 Accepted/current result separation — active:** Issue #247 must prevent a selected current candidate snapshot from rewriting accepted historical meaning.

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
30. Personal Research Workbench UI Phase 2A Today Market implementation — PR #212;
31. Personal Research Workbench UI Phase 2B architecture — PR #216;
32. Personal Research Workbench UI Phase 2B ordinary-user usability implementation — PR #218;
33. Controlled THS Data Refresh MVP architecture — PR #220;
34. Today Market Automatic Daily Refresh architecture — PR #222, with the initial Tushare source choice prospectively superseded by PR #224;
35. Today Market THS source synchronization architecture — PR #224;
36. THS official local-retention, synthetic-fixture and retry-reference evidence synchronization — PR #226;
37. THS Stage C0 offline foundation architecture — PR #229;
38. THS Stage C0 offline foundation implementation — PR #231;
39. Industry Thesis reviewed-plan owner-acceptance and exact-output-link architecture — PR #235;
40. Industry Thesis owner-acceptance core implementation — PR #237;
41. Industry Thesis ordinary-user completion architecture — PR #239;
42. exact Owner Context reviewed-plan contract architecture — PR #244;
43. Owner Context v2 replacement and ordinary-user acceptance/result implementation — PR #246.

Active governed architecture:

44. Industry Research Result Assembly and Exact Candidate Overlay v1 — Issue #247 / branch `arch/industry-research-result-assembly-v1`.

Owner-approved planned order after this preflight, each requiring its own governed authorization:

45. bounded Standard read-only result-assembly implementation only after Issue #247 architecture merge and separate authorization;
46. parallel closure of applicable THS live-account facts under Issue #225;
47. THS Stage C1 source-specific live foundation only after Issue #225 reaches an implementation-ready outcome;
48. index/industry/concept strength and Today Market bounded automatic refresh;
49. current full-market snapshot and breadth only under an accepted completion/quota contract;
50. manual official-PDF import and explicit Evidence Ledger review;
51. announcement evidence packs and later authorized enrichment;
52. historical full-market, corporate-action and advanced anomaly work only after their separate contracts exist.

Deferred:

- production CNINFO/webpage/PDF acquisition until its own accepted implementation contract;
- THS live production implementation until Issue #225 closes exact applicable quota, completion, revision and key-lifecycle facts and a separate implementation Issue is authorized;
- expansion of Stage C0 into unrelated endpoint families without a concrete product dependency;
- external consensus sources;
- Market Attention scoring and Daily Radar product behavior;
- OCR and automatic accepted evidence drafting;
- FX and accepted corporate-action normalization;
- industry-level guarded AI drafting until a separately accepted proposal-only slice;
- followed-entity alerts and portfolio ledgers;
- full-market breadth, stock anomaly/cause and live refresh beyond accepted source contracts.

## Current authorization state

- Main contains Owner Context v2 replacement merge commit `2c432d1676146d5dd168907419fe2160f447e50c` from PR #246.
- PR #246 was validated at exact head `eefa47212195e117f9cf159c0f96d21ce5479383` by Local Tests #893 and fixed-head review `4781714011` before owner-authorized merge.
- Issue #247 authorizes exactly one Strict documentation-only architecture preflight branch and Draft PR for result assembly.
- PR #241 remains frozen, Draft and unmerged at `3116a67ec472131eea3bf3d1bd9daee884c69ee9`.
- THS Stage C0 capability merge commit is `d899115e571d393ec45ff9740df4d21cd5c7133f` from PR #231.
- Personal Research Workbench UI Phase 2B is merged through PR #218; Phase 2A Today Market remains merged through PR #212.
- Stage C0 remains structurally offline:

```text
synthetic_only = true
remote_executable = false
network = prohibited
credentials = prohibited
persistence = prohibited
provider_valued_fixtures = prohibited
```

- Issue #225 remains open and controls the live THS gate:

```text
live_stage_c1_gate = blocked_pending_provider_response
production_live_network_authorized = false
```

- Issues #227, #230, #242 and #245 remain open until separately authorized for completion closure.
- No production implementation is authorized by Issue #247.
- No live Provider, news, announcement, browser acquisition, scheduler, notification, new AI call or portfolio ledger is authorized.
- No automatic Company Research, Investment Candidate, valuation or portfolio owner write is authorized by the result-assembly preflight.
- No recommendation, target price, expected return, position size, broker, order or automated trading behavior is authorized.
- No release, tag or version change is authorized.

## Next governed gate

The active mainline gate is the Strict documentation-only Architecture Preflight in Issue #247:

```text
Industry Research Result Assembly
and Exact Candidate Overlay v1
```

The preflight must prove that one immutable accepted Industry Thesis output can be composed with exact Industry Map context, complete accepted beneficiaries and readiness, plus an optional explicitly selected exact Investment Candidate snapshot for the same candidate-pool revision. Accepted historical meaning and the selected current overlay must remain separate. No latest/default snapshot, score recomputation, owner write, schema or migration is permitted.

If the architecture is accepted and separately authorized for implementation, the expected implementation tier is Standard read-only work over existing accepted models. Any need for persistence, accepted-contract change, hidden selector, candidate recomputation, Provider/network or AI returns the work to Strict architecture.

Issue #225 continues independently as the sole THS live-contract evidence gate. No Stage C1 implementation Issue, credential boundary, HTTP client, source activation or live request may be created until that gate reaches an accepted implementation-ready outcome and the project owner separately authorizes the implementation slice.

Roadmap Issue #137 records the owner-approved execution order. A materially different feature instruction must be identified as a plan deviation and confirmed before creating its Issue, branch, PR or code. Necessary fixes and validation within an already authorized slice are not roadmap deviations.

## Industry Thesis owner-acceptance accepted-state synchronization

This section records the accepted owner-acceptance state produced by architecture PR #235 and implementation PR #237 and refined by Owner Context architecture PR #244 and replacement implementation PR #246. It supersedes older statements that describe owner acceptance, exact output links or ordinary-user acceptance as future, missing, deferred or unauthorized.

- The deterministic Industry Thesis workflow can advance an exact `reviewed_plan_ready` revision to one append-only `accepted_outputs_linked` revision only through an explicit strict owner-acceptance plan.
- Active reviewed writes use `aquantai.industry-thesis-acceptance-plan.v2` with one exact `aquantai.industry-thesis-owner-context.v1` frozen in the reviewed plan.
- Review submits only exact `industry_map_revision_id`; the server resolves exact Industry Map and Research Case.
- Owner Context participates in deterministic reviewed IDs, plan fingerprints and chronology.
- Preview and commit use the same normalized owner plan and SHA-256 fingerprint; commit requires the exact matching preview fingerprint.
- One outer transaction coordinates session-bound Stage 1 and Typed Beneficiary Semantics owner ports. The coordinator does not open nested owner transactions and does not duplicate owner validation.
- HTTP and core both reject Case/Map/Map Revision/mode substitution before owner work.
- Exact existing Research Case, Industry Map, reviewed session, reviewed candidates and owner revisions remain explicit. No free text, company label, draft graph, Provider field or AI result is promoted by inference.
- The frozen complete accepted result remains separate from the supported-only Stage 1 candidate-pool handoff. Draft and disputed members remain visible in the complete result; rejected members are blocked.
- A valid zero-supported acceptance freezes the complete accepted members, stores a null candidate-pool revision and creates no empty or fabricated pool.
- Candidate-pool exact reuse is available only when the final supported Stage 1 Revision UUID set exactly equals a frozen pool Revision membership set.
- Candidate-pool append explicitly exposes and confirms the selected pool Revision title and scope; it does not submit hidden create defaults.
- The accepted session revision and output-link revision freeze the exact reviewed revision, accepted revision, Research Case, Industry Map revision, optional candidate-pool revision, ordered owner bindings, reviewed-plan fingerprint, owner-plan fingerprint, transaction ID, information cutoff and recorded-UTC boundary.
- Identical replay is deterministic and idempotent; conflicting replay, stale expected-latest state, incomplete owner bindings and graph corruption fail closed.
- Exact JSON-only output, complete-result and readiness reads require explicit information-cutoff and recorded-UTC visibility and never fall back to a newer or substitute record.
- Unaccepted reviewed-plan v1 records fail closed and require explicit v2 re-review. Existing accepted v1 exact reads and idempotent replay remain supported when all frozen identities/fingerprints match.
- Migration `20260725_0017` changes only the Industry Thesis output-link schema, supports nullable zero-supported handoff, refuses ambiguous populated legacy upgrade and refuses lossy populated downgrade. Owner Context v2 adds no migration, table, column, backfill or history rewrite.
- The core and ordinary-user surface are local and offline. They add no Provider access, credential path, scheduler, retry loop, background worker, notification, hidden AI call, automatic Company Research creation, Investment Candidate scoring, recommendation, target price, expected return, portfolio, broker, order or trading behavior.
- Issue #247 is the next separately governed product gate for a readable accepted result and optional explicit exact candidate snapshot overlay.
- This capability synchronization does not change released version `0.2.0` and does not itself authorize release, Issue closure or any later slice.