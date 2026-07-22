# AQuantAI Authoritative Architecture Baseline

## Status and authority

This document is the authoritative architecture and current-state baseline. `.codex/WORKFLOW.md` controls execution gates, and a linked GitHub Issue controls Standard or Strict scope.

- Released software version: `0.2.0`.
- Current accepted `main` baseline: `702a6410fecf73fb7ea428c4e37f26c9a081dd87`.
- Latest merged runtime capability: Normalized Valuation and Expectation Metrics v1 through PR #186.
- Latest merged product architecture: Industry Thesis Intake and Research Orchestration v1 through PR #193.
- Latest merged external-data architecture: Account-Authorized THS Structured Financial Data v1 through PR #191.
- Authorized CNINFO Disclosure Acquisition v1 architecture remains accepted through PR #189.
- Review-identity governance is merged through PR #187.
- Canonical Price and Comparison Eligibility v1 remains the authoritative price owner through PRs #176/#178.
- Active Strict implementation gate: Issue #194 / Draft PR #195, Offline Industry Thesis Orchestration Foundation v1.
- CNINFO and THS production acquisition remain implementation-blocked by their separate source/access contract gates.

Documentation may advance without changing the released version. An architecture or capability merge does not itself authorize release, source expansion, portfolio action or trading behavior. Draft PR #195 is not accepted runtime state until fixed-head review and separate owner merge authorization complete.

## Product boundary

AQuantAI is a local-first, personal-use, research-only and non-advisory A-share research workbench. It is not a broker, order-management system, automated-trading system, investment-advice service, multi-user SaaS product or production deployment platform.

Deterministic calculations, canonicalization, selectors and accepted workflow state belong to reviewed application code. An LLM may assist only behind an explicit bounded adapter and may not own evidence qualification, deterministic state, accepted research state, execution or trading behavior.

The product may identify current research-priority candidates under an explicit rule. It must preserve the complete beneficiary universe and expose every component, missing state, penalty and reason. It must not produce unexplained recommendations, target prices, expected returns, position sizes or trading actions.

## Accepted dependency direction

```text
market-data persistence
  -> v0.5 Evidence Ledger
  -> v0.5B Industry Map
  -> v0.5C Stage 1 beneficiary identities and complete candidate-pool revisions
       -> Typed Beneficiary Evidence Semantics v1
       -> v0.6A-v0.6D Company Research
  -> Canonical Price and purpose-specific Comparison Eligibility
  -> Investment Candidate Intelligence v1
  -> Normalized Valuation and Expectation Metrics v1
  -> read-only research workspaces
  -> optional company-scoped Guarded AI D3 draft assistance

accepted orchestration architecture
  -> explicit industry/thesis session revision
  -> deterministic local candidate proposals
  -> explicit user review and acceptance plan
  -> existing Industry Map / Stage 1 / typed-semantics owner writes
  -> exact orchestration output links
  -> existing readiness and Investment Candidate owners

future authorized acquisition
  -> exact source authorization and capability manifest
  -> immutable L0 raw capture
  -> source-specific L1 normalization
  -> deterministic non-accepted identity candidates
  -> explicit reviewed promotion into existing domain owners only
```

Downstream accepted records freeze exact upstream revisions and links. They do not silently select newer records, infer missing state, parse free text or rewrite historical meaning.

## Current accepted runtime and product surfaces

The accepted `main` runtime contains:

1. local fixture-backed Dashboard;
2. database-backed read-only Market Cockpit and Industry Alpha APIs/demos;
3. Evidence Intelligence / Research Change Feed;
4. Industry Beneficiary Workspace v1;
5. Company Research Workspace v1;
6. Guarded AI Research Assistance v1, disabled by default;
7. Typed Beneficiary Evidence Semantics v1;
8. Company Research Comparison Matrix v1;
9. Canonical Price and Comparison Eligibility APIs/commands;
10. Investment Candidate Intelligence APIs, commands and `/investment-candidates` workspace;
11. exact-ID normalized financial, valuation, comparison and expectation-gap APIs;
12. `/company-research/valuation-context` with exact revisions and both as-of boundaries.

Accepted `main` does not yet contain the Issue #194 industry-thesis persistence, commands or reads. No accepted runtime surface provides fair value, target price, expected return, buy/sell/hold output, position sizing, broker execution, automated trading or external Provider/disclosure acquisition.

## Accepted capability contracts

### Evidence, Industry Map and beneficiary research

- Evidence Ledger owns evidence grades, claims, links and conflicts.
- Industry Map owns accepted chain nodes, relationships, observations, drivers, bottlenecks and value-pool state.
- Stage 1 owns beneficiary identity/classification and complete candidate-pool revisions.
- Typed Beneficiary Semantics owns append-only direct/conditional/indirect/conceptual exposure and execution-evidence judgments.
- External acquisition and thesis orchestration may propose or coordinate; they do not become alternate accepted owners.

### Company Research and comparison

- Company Research v0.6A-v0.6D owns financial-transmission hypotheses, narrative expectations, valuation observations, catalysts, risks and industry/company quality judgments.
- Downstream state binds exact Company Research revisions.
- Company Comparison preserves every exact candidate-pool member under neutral deterministic ordering.
- Narrative v0.6B text is never parsed automatically into structured financial or valuation values.

### Canonical Price and Comparison Eligibility v1

- Explicit listed-instrument identity owns market, exchange namespace/code, currency, security type and listing chronology.
- Canonical prices freeze one exact accepted series contract, succeeded ingestion run and source row.
- Decimal normalization and purpose-specific eligibility are deterministic and versioned.
- Exact-ID reads require information-cutoff and recorded-UTC boundaries.
- Migration `20260722_0013` is additive and refuses populated downgrade.
- Canonical Price does not create an attractiveness judgment.

### Investment Candidate Intelligence v1

- One exact complete Stage 1 candidate-pool revision and every member are preserved.
- Eight explicit analyst-owned components feed deterministic versioned status/reason calculation.
- Missing, disputed, pending and failed values are not imputed or reweighted.
- The complete pool remains visible beneath any highlighted priority/watch members.
- Migration `20260722_0014` is additive and refuses populated downgrade.
- Candidate status is research prioritization, not investment advice.

### Normalized Valuation and Expectation Metrics v1

- Append-only structured observations cover diluted shares, revenue, attributable net profit, EBITDA, free cash flow and net debt.
- Exact Canonical Price, eligibility, accounting scope, period, currency, unit, freshness and provenance contracts are required.
- PE, PS, EV/EBITDA, FCF yield, history, peer and expectation-gap calculations are deterministic and versioned.
- Non-meaningful, negative, missing and disputed states remain explicit.
- Migration `20260722_0015` is additive and refuses populated downgrade before any drop.
- Outputs never automatically rescore or rewrite Investment Candidate history.

### Guarded AI Research Assistance v1

- Available only for one explicitly selected Company Research workspace.
- Uses an immutable Manifest and SHA-256 fingerprint.
- Disabled by default and requires explicit remote-transmission confirmation.
- No browsing, search, retrieval, tools, retry, fallback or background execution.
- Output is ephemeral D3 draft only and cannot self-promote.

### Authorized CNINFO Disclosure Acquisition architecture

- PR #189 authorizes architecture only, not a production adapter.
- Public visibility does not authorize automated acquisition.
- Raw document state remains immutable L0; source normalization remains L1.
- Candidate company/instrument matches are not accepted identity.
- Human review is required before Evidence Ledger acceptance.

### Account-Authorized THS Structured Financial Data architecture

- PR #191 authorizes architecture only, not production implementation.
- Candidate access is explicit user-initiated official account-authorized REST for local personal research.
- Provider observations remain L0/L1 until explicit promotion under existing owners.
- THS values do not automatically replace Canonical Price, official evidence or normalized financial inputs.
- Current taxonomy membership is not historical membership.
- Market attention cannot create beneficiary, candidate, recommendation or trading state.

### Industry Thesis Intake and Research Orchestration v1 architecture

PR #193 accepts the following architecture:

```text
explicit thesis input
  -> append-only thesis/session revision
  -> deterministic local candidate proposals
  -> optional later AI proposal drafts
  -> explicit reviewed acceptance plan
  -> existing owner transaction
  -> exact output links
  -> existing readiness and Investment Candidate owners
```

- Market scope, driver, horizon, chain boundary, exclusions, coverage and both as-of boundaries are explicit.
- Coverage values are `reviewed_local_scope`, `partial_local_coverage` and `coverage_unknown`; none claims full-market discovery.
- Candidate precedence is accepted local mapping, existing exact Industry Map revision, user seed, then optional later AI draft.
- Exact accepted company identity is required before any accepted Stage 1 write.
- Stage A preserves the complete reviewed local beneficiary universe.
- Stage B reuses the existing Investment Candidate owner and never introduces a second score.
- News, announcements, THS and market attention are optional enrichment, not golden-path dependencies.
- The maximum persistence boundary is six additive orchestration table families after migration `20260722_0015`.

## Active implementation candidate: Offline Industry Thesis Orchestration Foundation v1

Issue #194 / Draft PR #195 implement only the first offline slice.

Candidate implementation scope:

- migration `20260722_0016`, additive only;
- session identity and append-only session revisions;
- candidate identity and append-only candidate proposal revisions;
- output-link identity/revision tables for schema continuity only, without write service in this slice;
- strict controlled vocabularies;
- bounded canonical JSON and SHA-256 fingerprints;
- system-owned recorded UTC and explicit information cutoff;
- JSON-only dry-run-capable create/revise/build commands;
- exact-ID dual-as-of session and candidate reads;
- deterministic local source precedence;
- expected-latest protection and atomic writes;
- populated downgrade refusal;
- fully offline tests and a three-proposal golden path.

Issue #194 explicitly excludes:

- Industry Map or Stage 1 acceptance transactions;
- typed-semantics acceptance;
- Company Research/price/valuation readiness aggregation;
- Investment Candidate snapshot invocation;
- UI;
- industry-level AI;
- Provider, news, announcement, THS or web access;
- recommendation, portfolio or trading behavior.

## Field and infrastructure ownership

| Information or mechanism | Authoritative owner | Rule |
| --- | --- | --- |
| Market-data rows, Provider series and ingestion cutoff | Market-data persistence | One explicit Provider per run/series; no fallback or row mixing |
| Canonical instrument, price, currency/unit and price eligibility | Canonical Price | Exact append-only revisions and purpose-specific eligibility |
| Evidence grades, claims, links and conflicts | Evidence Ledger | Proposal is not acceptance |
| Accepted industry graph and observations | Industry Map | Exact identities and revisions |
| Complete beneficiary pool | Stage 1 | Preserve every reviewed member |
| Typed beneficiary exposure/execution evidence | Typed Beneficiary Semantics | Analyst-owned D3 accepted profile |
| Company hypotheses, narratives, catalysts, risks and quality | Company Research v0.6A-v0.6D | Exact frozen revisions |
| Candidate components, rules and snapshots | Investment Candidate | No second scoring owner |
| Structured financial and valuation records | Normalized Valuation/Expectation | Contract-specific exact inputs |
| Thesis/session and non-accepted proposal audit state | Industry Thesis Orchestration | Coordination only; no accepted business ownership |
| Accepted thesis-derived map/beneficiary state | Existing Industry Map / Stage 1 / typed-semantics owners | Explicit user plan and owner transaction only |
| Guarded AI Manifest and transport | Guarded AI | Draft only, explicit confirmation |
| External raw/source-normalized state | Source-specific acquisition domain | L0/L1 only until reviewed promotion |

## Shared architecture invariants

1. Local and non-advisory: no advice, performance promise, broker, real order or automated trading.
2. Deterministic calculations and accepted state stay outside LLM ownership.
3. Imports, startup, tests, CI, demos and ordinary reads perform no hidden external network access.
4. Exact IDs, scopes, dates, revisions and selectors are explicit.
5. Downstream accepted records freeze exact revisions and links.
6. Corrections append revisions; accepted history is not mutated through ordinary paths.
7. Information cutoff and recorded UTC both prevent later-information leakage.
8. Conflicts, missing evidence, stale state and uncertainty remain visible.
9. Identity, revision and links commit or roll back together.
10. Ordering, revision allocation, Decimal text and strict JSON are deterministic across supported databases.
11. Fixture success paths use fields reachable through reviewed production boundaries.
12. Credentials and connection details never enter source, fixtures, Issues, PRs, logs, database rows or user errors.
13. Capability merges do not change released version without a separate release decision.
14. Reading surfaces cannot upgrade semantic or derivation level.
15. Exact-ID failures never fall back to another record.
16. External acquisition requires exact source/access authorization.
17. Candidate matching is not accepted identity.
18. AI output is D3 draft and cannot self-promote.
19. No generic agent, RAG, Provider registry or hidden tool framework without separate preflight.
20. Complete beneficiary and candidate-pool universes remain visible before and after overlays.
21. Missing, disputed, pending, failed or non-meaningful values are never silently zero or neutral.
22. Purpose-specific eligibility cannot be reused under another purpose without an exact contract.
23. Provider market/financial values cannot silently become canonical or official accepted inputs.
24. Current taxonomy membership cannot masquerade as historical membership.
25. Market attention cannot directly create beneficiary, candidate, recommendation or trading state.
26. Thesis free text and proposal drafts cannot directly create accepted Industry Map or beneficiary state.
27. Coverage is explicit and separate from evidence quality and candidate status.
28. Valuation, popularity, price performance or missing data cannot remove a reviewed Stage 1 member.
29. Thesis orchestration may coordinate existing owners but cannot duplicate their accepted fields or calculations.
30. Historical reads must not reveal later identity pointers, revisions or workflow decisions.

## Semantic and derivation levels

- **L0 Raw:** immutable source output; audit only.
- **L1 Source Normalized:** source-specific project fields; not automatically comparable or accepted.
- **L2 Standardized:** standardized under an explicit accepted contract.
- **L3 Canonical:** exact identity, measurement, unit, currency, market, provenance, cutoff, chronology, decimal and missing-state contract.

Thesis candidate proposals are orchestration draft state. Persistence does not grant semantic authority.

- **D0 Direct Fact:** explicit source support.
- **D1 Deterministic Aggregation:** recorded inputs, scope, algorithm and missing treatment.
- **D2 Rule Classification:** explicit versioned deterministic rules.
- **D3 Analytical Judgment:** analyst/model interpretation requiring explicit ownership and review.

D3 does not automatically enter accepted identity, evidence, map membership, recommendation or trading state.

## Capability matrix

| Capability | Reviewed boundary | Remaining boundary |
| --- | --- | --- |
| Evidence / Industry Map | Accepted evidence and industry graph ownership | No automatic external acceptance |
| Stage 1 / Typed Semantics | Complete pool and explicit exposure/execution profiles | No automatic full-market discovery |
| Company Research / Comparison | Exact company research and complete-universe comparison | No automatic peer selection |
| Canonical Price | Official close and purpose eligibility | No hidden FX/corporate-action normalization |
| Investment Candidates | Transparent components/status/priority | No automatic component scoring |
| Normalized Valuation | Exact structured metrics, contexts and gaps | No fair value or hidden consensus acquisition |
| Guarded AI | Explicit company-scoped draft assistance | No accepted AI state/tools/retrieval |
| CNINFO / THS | Accepted architectures | Production implementation separately gated |
| Industry Thesis Orchestration | Architecture merged through PR #193 | Offline foundation active in Issue #194 / PR #195 |
| Market Attention / Daily Radar | Isolated future observations | Separate source, rule and product authorization |

## Architecture debt register

- Current-state documentation drift is synchronized through Issue #194.
- Generic graph/agent/provider frameworks remain unjustified.
- Domain-local serializers and command validation remain bounded; consolidation requires concrete duplication evidence.
- Test-matrix growth is monitored; Issue #194 adds one offline end-to-end path and migration contract.
- THS implementation remains blocked by exact account contract facts.
- Provider taxonomy chronology and market-attention isolation remain active decisions.
- Industry-level AI remains deferred until the offline orchestration foundation is accepted and proves useful.

## Accepted product sequence

Completed:

1. Evidence Intelligence / Research Change Feed — PR #139;
2. Industry Beneficiary Workspace — PR #143;
3. Company Research and comparison capabilities — PRs #151/#174;
4. Guarded AI Research Assistance — PR #161;
5. Typed Beneficiary Semantics — PR #169;
6. Canonical Price and Comparison Eligibility — PR #178;
7. Investment Candidate Intelligence — PR #182;
8. Normalized Valuation and Expectation Metrics — PR #186;
9. fixed-head review identity governance — PR #187;
10. CNINFO acquisition architecture — PR #189;
11. THS structured Provider architecture — PR #191;
12. Industry Thesis Intake and Research Orchestration architecture — PR #193.

Active implementation gate:

13. Offline Industry Thesis Orchestration Foundation v1 — Issue #194 / Draft PR #195.

Deferred:

- existing-owner acceptance and readiness orchestration;
- Chinese-first `/industry-analysis/new` UI;
- industry-level guarded AI proposals;
- production external acquisition;
- Market Attention and Daily Radar;
- external consensus, FX and accepted corporate-action normalization;
- OCR and automatic accepted evidence drafting.

## Current authorization state

- `main` includes PR #193 at `702a6410fecf73fb7ea428c4e37f26c9a081dd87`.
- Issue #192 is completed.
- The owner authorized Issue #194 implementation on 2026-07-22.
- Issue #194 authorizes only the bounded offline foundation described above.
- Draft PR #195 is unmerged candidate implementation state.
- No release, version change, external acquisition, AI call, recommendation, portfolio or trading behavior is authorized.

## Next governed gate

Before PR #195 may merge:

1. complete the Issue #194 implementation without scope expansion;
2. prove exactly six additive tables and migration `20260722_0016`;
3. prove canonical bounded JSON and stable SHA-256 fingerprints;
4. prove system-owned recorded UTC and explicit information cutoff;
5. prove expected-latest, append-only and atomic behavior;
6. prove exact local identity and Industry Map source validation;
7. prove unresolved/ambiguous candidates remain non-accepted;
8. prove exact-ID dual-as-of reads without later-information leakage;
9. prove the fully offline three-proposal golden path;
10. prove empty migration round-trip and populated downgrade refusal;
11. pass full CI on the exact final HEAD;
12. receive fresh process-independent fixed-head review;
13. resolve every review thread;
14. receive separate explicit project-owner merge authorization.

No later acceptance service, readiness aggregation, UI or AI slice is authorized by PR #195 alone.
