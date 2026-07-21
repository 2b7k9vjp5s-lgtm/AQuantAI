# Company Research and Guarded AI Consolidation Review

## Status and authority

- Authority: Issue #162.
- Related roadmap: Issue #137.
- Required base: `2e3722fdf224a58df0c870e2fa167b4f8e742b49`.
- Reviewed implemented slices:
  - Company Research Workspace v1 — PR #151;
  - Guarded AI Research Assistance v1 — PR #161.
- Related architecture work:
  - Company Research Architecture Preflight — PR #149;
  - Guarded AI Architecture Preflight — PR #159.
- Previous consolidation review: Issue #144 / PR #145.
- Work type: consolidation/refactoring characterization, documentation only.
- Released version remains `0.2.0`.
- This review authorizes no production code, API/UI behavior, schema, migration, Provider, dependency, fixture, test, release or version change.

## Executive decision

The two completed slices are coherent and bounded. No production consolidation refactor is required before the next Architecture Preflight.

Accepted consolidation decisions:

1. **Keep the Company Research workspace projection product-local.** Its exact identity, frozen-revision, cutoff, evidence and 3/14-query contracts are specific to the Company Research product surface.
2. **Keep deterministic Manifest construction separate from provider transport and model-response validation.** These modules have distinct trust and failure boundaries; merging them would reduce auditability.
3. **Do not create a generic AI framework.** One company-scoped, user-invoked draft flow does not justify an agent, provider registry, prompt framework, tool system, RAG layer or generalized AI workflow engine.
4. **Do not create a generic product-workspace framework.** Router/session/static-page/DOM similarities remain small presentation scaffolding rather than a neutral domain contract.
5. **Preserve the existing remote-network exception as narrow and explicit.** The only allowed remote request is one configured HTTPS generation request after local preview and explicit confirmation. Imports, startup, ordinary reads, preview, tests, CI and fixture demos remain network-free.
6. **Preserve ephemeral D3-only output.** No AI draft identity, revision, review state, prompt or response persistence is introduced.
7. **Synchronize the authoritative baseline now.** The current baseline still describes Guarded AI as prospective and therefore must be updated before another feature gate.
8. **Recommend one later Typed Beneficiary Evidence Semantics Architecture Preflight.** This is a candidate architecture gate only; no implementation is authorized by this review.

No consolidation implementation Issue is recommended.

## Current runtime inventory

### Company Research Workspace v1

Runtime surfaces:

- page: `GET /company-research`;
- selector: `GET /company-research/research`;
- workspace: `GET /company-research/research/{company_research_id}/workspace`;
- existing owning-domain detail routes loaded only after explicit user action.

Accepted behavior:

- requires one explicit persisted `company_research_id`;
- optional explicit `as_of_cutoff`;
- no name, stock-code, Provider-industry, free-text or model identity inference;
- no automatic first-row selection;
- selector uses exactly 3 SQL statements;
- selected workspace uses exactly 14 SQL statements;
- query count is independent of Stage 2 row growth;
- exact frozen Stage 1, stock, ingestion, claim, evidence and v0.6A-v0.6D revision provenance remains visible;
- latest cutoff-visible revisions remain separate from frozen historical revisions;
- historical mismatch remains visible and is never automatically relinked;
- safe DOM rendering uses no untrusted `innerHTML`;
- no Canonical Price, Comparison Eligibility, ranking, score, target price, expected return or recommendation state.

### Guarded AI Research Assistance v1

Runtime surfaces:

- local input preview: `GET /company-research/research/{company_research_id}/ai-draft-input`;
- explicit generation: `POST /company-research/research/{company_research_id}/ai-drafts`;
- controls embedded in the existing Company Research page.

Accepted behavior:

- consumes only the exact Company Research workspace projection;
- deterministic Manifest builder performs zero SQL, zero filesystem access and zero network access;
- canonical JSON and SHA-256 fingerprint are stable for the same accepted workspace content;
- request-time metadata is excluded from the fingerprint;
- local preview occurs before any remote transmission;
- generation requires explicit confirmation and the exact expected fingerprint;
- the server rebuilds the Manifest before adapter invocation;
- fingerprint mismatch fails with `409` before network access;
- disabled by default;
- one explicit HTTPS OpenAI-compatible profile;
- no default endpoint, provider or model;
- no retry, fallback, streaming, tools, browsing, search, retrieval or background execution;
- strict response schema, section, fingerprint and Manifest-item citation validation;
- prohibited recommendation and price-judgment language fails closed;
- result is ephemeral D3 draft assistance only;
- no accepted state or database row is created or modified.

## Accepted dependency direction

```text
accepted persisted Company Research workspace
  -> deterministic zero-I/O Manifest projection
  -> local preview and exact fingerprint
  -> explicit user confirmation
  -> one isolated HTTPS adapter request
  -> strict application-owned response validation
  -> ephemeral D3-only DOM rendering
```

Ownership remains:

| Boundary | Authoritative owner | Decision |
| --- | --- | --- |
| Company identity, cutoff, revisions, evidence and frozen history | Company Research workspace query/repository | Keep product-local and authoritative. |
| Manifest content, ordering, item IDs and fingerprint | `guarded_ai_manifest.py` | Keep deterministic and zero-I/O. |
| Provider profile and HTTPS transport | `guarded_ai_adapter.py` | Keep isolated from database and product state. |
| Confirmation, fingerprint comparison and response validation | `guarded_ai_service.py` | Keep application-owned and fail-closed. |
| Route/status translation | `backend/api/company_research.py` | Keep product-local because errors depend on route stage. |
| Rendering and user confirmation state | `company_research.js` | Keep page-local and safe-DOM only. |
| Model-generated text | D3 draft assistance | Never promote to accepted Evidence, Stage 1 or Stage 2 state. |

No model component owns identity, selection, cutoff, canonicalization, evidence qualification, evidence grade, accepted classification or workflow state.

## Query, I/O, network and persistence characterization

| Operation | SQL | Filesystem | Network | Persistent mutation |
| --- | ---: | ---: | ---: | ---: |
| Company selector | fixed 3 | 0 | 0 | 0 |
| Company workspace | fixed 14 | 0 | 0 | 0 |
| AI input preview after workspace load | Manifest adds 0 | 0 | 0 | 0 |
| AI generation before fingerprint match | Manifest adds 0 | 0 | 0 | 0 |
| AI generation after explicit confirmation and match | no additional SQL beyond the one workspace load | 0 | exactly one configured HTTPS request | 0 |
| Imports/startup/tests/CI/fixture demo | no AI-owned SQL | 0 AI files | 0 remote model requests | 0 AI state |

The Guarded AI flow does not compose per-record Stage 2 graph readers, so it does not add an N+1 query path. It reuses one already-bounded workspace projection.

There is no prompt or response retention, AI audit table, model-run table, draft revision, review status, background queue or scheduled task.

## API and error-boundary review

| Concern | Company Research | Guarded AI | Consolidation decision |
| --- | --- | --- | --- |
| Request validation | FastAPI UUID/date validation | UUID/date plus strict generation body and fingerprint | Keep route-local. Contracts differ materially. |
| Database construction | Lazy session only after validated request | Reuses the same lazy session/workspace service | No new shared abstraction needed. |
| Missing identity/cutoff visibility | `404` | Inherits the same workspace `404` | Consistent and correctly owned upstream. |
| Workspace/data integrity failure | redacted `503` | redacted `503` before Manifest/adapter | Preserve stable product-local mapping. |
| Preview conflict | not applicable | `409` only when expected fingerprint changed | AI-specific; do not generalize. |
| Input too large | not applicable | `413` before network, no truncation | AI-specific; keep local. |
| Provider rate limit | not applicable | `429` | Adapter-specific. |
| Invalid model response/citation | not applicable | `502` with no usable partial draft | Validation-specific. |
| Provider unavailable/config missing | not applicable | credential-safe `503` | Adapter-specific. |
| Timeout | not applicable | `504`, zero retry | Adapter-specific. |
| Notices | read-only research boundary | D3/ephemeral/no-tools/no-fallback boundary | Keep meanings local. |

No error inconsistency requires production refactoring.

## Repetition and keep/consolidate matrix

| Repeated pattern | Evidence | Decision now | Revisit trigger |
| --- | --- | --- | --- |
| Lazy FastAPI session factory | Similar in read-only product APIs | Keep product-local | Three or more routes require identical dependency ordering and identical error vocabulary. |
| Workspace-to-dict contract projection | Company Research and prior products serialize domain-specific contracts | Keep domain-local | A neutral contract with identical ownership and cutoff meaning reaches Definition of Ready. |
| Canonical JSON and SHA-256 | Manifest uses deterministic serialization | Keep Guarded-AI-local | A second approved non-AI domain requires the exact same content-addressed contract. |
| Provider configuration parsing | One Guarded AI profile only | Keep local | A second independently approved remote adapter with identical security and failure rules exists. |
| HTTPS transport | Standard-library one-request adapter | Keep local | Multiple approved adapters prove a stable neutral transport contract without provider relabeling. |
| Strict JSON response validation | Specific eight-section D3 schema | Keep local | Another approved AI job uses the exact same response schema and semantic boundary. |
| Prompt template handling | One fixed prompt version | Keep local | Multiple approved prompt contracts require a reviewed version registry. |
| Recommendation-language rejection | Guarded AI output safety boundary | Keep local and tested | A project-wide deterministic policy specification is separately reviewed. |
| Safe DOM helpers | Repeated small `textContent`/`replaceChildren` patterns | Keep page-local | Shared delivery can occur without a build system or semantic coupling. |
| Provider/model display | One preview card and data-use notice | Keep page-local | Multiple AI surfaces share identical approved disclosure fields. |
| Test fake adapters | Guarded AI tests inject one Protocol implementation | Keep test-local | A second approved adapter contract needs shared conformance tests. |
| Query-count assertions | Product-specific 3/14 boundary | Keep Company-Research-local | Another product shares the exact same repository and projection contract. |

The correct consolidation is architectural documentation and invariants, not a runtime framework.

## Security and semantic review

### Prompt-injection boundary

- stored evidence and research text is untrusted data;
- the adapter receives one canonical JSON Manifest, not database access;
- the system prompt forbids following instructions embedded in source text;
- no tools, browser, search, retrieval or function calls are exposed;
- citations are accepted only when they match known Manifest item IDs;
- malformed output or fabricated citations produces no usable draft.

### Credential and privacy boundary

- configuration is disabled by default;
- endpoint must be explicit HTTPS;
- provider, model, credential and data-use notice must all be explicitly present;
- URL user information and fragments are rejected;
- credential, endpoint, authorization header and raw provider response are absent from user errors;
- provider data retention/training policy is not misrepresented as a project guarantee;
- only the accepted Company Research projection is transmitted after preview and confirmation.

### Semantic boundary

- deterministic metadata and fingerprint remain application-owned;
- generated sentences remain D3 drafts;
- copying text does not create accepted evidence or research state;
- no evidence grade, identity, classification, canonical value, score, recommendation or trade action is model-owned;
- no price/return judgment becomes valid through display or non-null output.

No security or semantic blocker requires a reset.

## Test and regression-surface review

PR #161 fixed-head review recorded 24 focused tests across four layers:

- Manifest: 4;
- Adapter: 4;
- Service: 6;
- Company Research/API/page: 10.

GitHub Actions run #239 at implementation HEAD `1dc7dca75af26f491ef8e32caf31443349a0d6a8` completed successfully, including PostgreSQL initialization, full pytest, local fixture demo and cleanup.

The test split is appropriate:

1. deterministic Manifest and fingerprint tests;
2. adapter configuration/transport/failure tests with fake local I/O;
3. service confirmation/conflict/response-validation tests;
4. API status and credential-redaction tests;
5. DOM safety and explicit-selection tests;
6. repository-wide PostgreSQL regression and fixture demo.

No test consolidation is required now. A shared AI adapter conformance suite would be premature because only one approved adapter contract exists.

Test-matrix growth remains bounded but should be revisited if a second AI job or provider adapter is authorized.

## Schema, migration, dependency, release and rollback decision

| Concern | Decision |
| --- | --- |
| Schema | No change required. |
| Migration | No migration required. |
| Persistent AI state | None; remain ephemeral. |
| Runtime dependency | No change; standard-library HTTPS remains accepted for v1. |
| Provider | One explicit profile only; no registry or fallback. |
| Release/version | Remain `0.2.0`; no release action. |
| Rollback | Guarded AI is disabled by default and can be removed without data rollback because it owns no persistent state. |
| Production consolidation | Not required. |

## Architecture debt after the two slices

### Resolved or bounded

- Company Research overview query growth: bounded by exact 3/14 statements.
- AI input selection: bounded to one explicit company research identity.
- AI provenance: provider/model/adapter/prompt/fingerprint metadata is visible in the ephemeral response.
- Hidden network: prevented outside one confirmed adapter request.
- Prompt injection: bounded by data-only Manifest, no tools and strict output validation.
- AI persistence: intentionally absent.
- Provider fallback: intentionally absent.

### Still open but not blocking

- the architecture baseline is stale until this documentation PR merges;
- a second AI job would require a new Architecture Preflight and likely a new consolidation decision;
- provider cost estimation remains unavailable unless a future explicit pricing contract is reviewed;
- no generalized cancellation channel exists beyond request cancellation and late-response discard;
- typed beneficiary/customer/certification/capacity/production/order semantics remain unresolved;
- Canonical Price and Comparison Eligibility remain unresolved parallel infrastructure;
- Evidence Ingestion remains deferred.

## Next-stage input reachability

### Reachable persisted foundations

A future architecture review can rely on existing explicit identities and revisions for:

- ResearchCase and Industry Map identity;
- Stage 1 beneficiary identity, revision and current stored classification;
- candidate-pool membership and frozen map revision;
- stock and ingestion provenance;
- Evidence Ledger claims, links, grades, conflicts and missing evidence;
- Company Research and financial-transmission hypotheses;
- exact information cutoff and recorded UTC chronology.

### Missing semantics that require a new owner decision

The current runtime does not have an accepted normalized contract for:

- final beneficiary taxonomy such as direct, conditional, indirect and conceptual;
- driver subtypes and value-pool-shift classification;
- typed customer stage;
- typed certification stage;
- typed capacity and production-readiness stage;
- typed order/commercialization stage;
- deterministic mapping from evidence links to those fields;
- missing/unknown/conflicting state vocabulary for those fields;
- human-versus-rule ownership and revision lifecycle.

These meanings cannot be safely inferred from free text, stock code, Provider industry, model output or current `direct / secondary / potential` labels.

### Not recommended as the next product-domain gate

- Evidence Ingestion remains deferred because no accepted non-manual acquisition contract exists;
- Canonical Price and Comparison Eligibility remain a separate infrastructure track without Definition of Ready;
- cross-company ranking, score and investment-priority ordering remain unauthorized;
- persisted AI drafts, multi-company AI and autonomous agents are not justified by the current user job;
- Watchlist, alerts, portfolio and trading remain outside the product boundary.

## Recommended next Architecture Preflight

### Candidate name

`Typed Beneficiary Evidence Semantics v1`

### Candidate user job

> For one explicitly selected persisted Industry Map and one existing Stage 1 beneficiary identity, record and review typed beneficiary exposure and execution-evidence states with exact source, revision, cutoff, conflict and missing-data provenance, without ranking companies or inferring accepted state from free text or AI output.

### Required architecture decisions

1. exact authoritative owner and revision identity;
2. whether the feature extends Stage 1 or introduces a separate append-only semantic layer;
3. accepted beneficiary taxonomy and backward compatibility with current stored labels;
4. driver type/subtype ownership;
5. customer, certification, capacity, production and order-stage vocabularies;
6. evidence-link requirements and conflict/missing-state behavior;
7. deterministic rule versus explicit analyst ownership;
8. cutoff, recorded UTC, supersession and historical-freeze rules;
9. migration and rollback decision;
10. production-realistic offline golden path using accepted persisted evidence;
11. no LLM-owned acceptance, automatic extraction or hidden inference;
12. exact API/UI boundary and bounded tests;
13. no ranking, scoring, price, recommendation, monitoring or trading semantics.

This recommendation is not implementation authorization. The preflight must stop if the required fields cannot be sourced or owned without free-text/model inference.

## Locked exclusions for the next gate

- no Evidence Ingestion restart, PDF requirement, crawling, scraping, browsing or external search;
- no automatic evidence acquisition or accepted evidence promotion;
- no automatic company/industry identity inference;
- no AI-owned taxonomy or field acceptance;
- no generic agent, RAG, vector database or tool framework;
- no cross-company ranking or research-priority score;
- no Canonical Price or Comparison Eligibility;
- no fair value, target price, expected return, upside/downside, buy/sell/hold or recommendation state;
- no monitoring, alerts, tasks, portfolio or trading;
- no release or version change.

## Architecture baseline synchronization delta

The authoritative baseline must record:

- Guarded AI Research Assistance v1 is merged through PR #161 at main commit `2e3722fdf224a58df0c870e2fa167b4f8e742b49`;
- current runtime includes local preview and explicit confirmed ephemeral D3 generation;
- the exact 3/14 Company Research query boundary remains the only data source;
- deterministic Manifest, adapter and response validation ownership is resolved for v1;
- the second two-slice consolidation review is active under Issue #162;
- no new product implementation is currently authorized;
- after this review, Typed Beneficiary Evidence Semantics may become the next Architecture Preflight candidate;
- Evidence Ingestion remains deferred;
- Canonical Price, Comparison Eligibility, ranking and recommendations remain unauthorized.

## Final decision table

| Question | Decision |
| --- | --- |
| Production consolidation required now? | No. |
| Generic workspace framework? | No. |
| Generic AI/provider/prompt framework? | No. |
| Merge Manifest, adapter and response validation? | No; preserve separate trust boundaries. |
| Query or graph-loading blocker? | No; exact 3/14 workspace boundary remains bounded. |
| Hidden network or fallback blocker? | No; one explicit confirmed request only. |
| Persistence or accepted-state mutation? | None. |
| Schema/migration/dependency change? | None. |
| Release/version change? | None. |
| Next candidate architecture gate? | Typed Beneficiary Evidence Semantics v1. |
| Evidence Ingestion restart? | No. |
| Canonical Price / Comparison Eligibility? | Separate unresolved infrastructure track. |
| Ranking/recommendation/trading? | Excluded. |

## Completion and review gate

This document is a consolidation finding, not feature authorization.

The PR carrying this document must remain Draft/Open/unmerged until an independent reviewer verifies one fixed HEAD and confirms:

- exact three-file documentation scope;
- no production change;
- findings match the merged code and tests;
- no premature framework recommendation;
- next preflight is bounded and reachable enough for architecture work;
- all locked exclusions remain intact.

Do not start the recommended Architecture Preflight until this consolidation review is independently approved, merged and explicitly authorized by the owner.