# Industry Thesis Intake and Research Orchestration v1

## 1. Decision status

- Authoritative Issue: #192.
- Product Roadmap: #137.
- Required base: `be18f407fb42b6caf22d339285e17f830052af91`.
- Risk tier: **Strict**.
- This document is an architecture preflight only.
- It authorizes no production code, schema migration, dependency, fixture, live AI call, Provider request, news/announcement ingestion, release, tag or version change.

## 2. Product decision

AQuantAI should support a Chinese-first local workflow in which a user enters an industry, industrial chain or investment thesis, reviews a structured industry model, establishes a complete reviewed beneficiary-company universe and then reuses the existing Company Research, valuation and Investment Candidate contracts to identify current research-priority candidates.

The workflow is intentionally independent of market news, official announcements, THS data and other external acquisition. Those sources may later improve evidence quality, timeliness and coverage, but they are optional enrichment rather than hard upstream dependencies.

The accepted v1 architecture is:

```text
user industry/thesis input
  -> append-only thesis draft revision
  -> deterministic local candidate build
  -> optional bounded AI proposal draft
  -> explicit review of driver / chain / bottleneck / value-pool / coverage
  -> explicit selected acceptance plan
  -> existing Industry Map and Stage 1 beneficiary owner writes
  -> exact orchestration-output links
  -> Company Research / valuation / component readiness inspection
  -> existing deterministic Investment Candidate snapshot
  -> complete-universe result with status and missing reasons
```

The orchestrator coordinates existing owners; it does not become a second owner of Industry Map, beneficiary, Company Research, price, valuation, component or candidate state.

## 3. Current capability and missing layer

The accepted runtime already provides:

- persisted Industry Maps, nodes, relationships, drivers, bottlenecks and value-pool observations;
- Stage 1 beneficiary identities/revisions and complete-pool handoff;
- typed beneficiary exposure and execution-evidence semantics;
- Company Research v0.6A-v0.6D;
- Company Research comparison;
- Canonical Price and purpose-specific Comparison Eligibility;
- Investment Candidate component assessments, rule versions, snapshots and statuses;
- structured financial observations, normalized valuation and expectation-gap records;
- read-only Chinese-first workspaces;
- guarded company-scoped AI draft assistance.

The missing layer is one explicit workflow identity that can:

1. preserve the user's exact thesis and scope;
2. build a candidate universe from explicit local sources;
3. record what the user reviewed and selected;
4. invoke existing domain owners without copying their fields;
5. freeze exact accepted output revisions;
6. inspect downstream readiness;
7. reproduce the same result under information-cutoff and recorded-UTC boundaries.

## 4. Core invariants

1. The complete reviewed Stage 1 beneficiary universe remains visible before and after investment-candidate analysis.
2. Valuation, price performance, popularity or market attention cannot remove a company from Stage 1.
3. Free text is draft input only.
4. LLM output is D3 proposal text only and cannot accept identity, membership, evidence, exposure, components or candidate status.
5. Exact accepted company identity is required before any accepted beneficiary write.
6. Every candidate has an inclusion path, source kind, source reference and uncertainty state.
7. Coverage is explicit; the system never claims full-market discovery from incomplete local data.
8. Missing, pending, disputed, failed and non-meaningful values are not imputed, zeroed or silently reweighted.
9. Existing owner commands and services remain authoritative for accepted state.
10. Ordinary reads, imports, startup, tests, CI and fixture demos perform no external network or AI call.
11. All accepted downstream links use exact revisions and both as-of boundaries.
12. No output is a buy/sell/hold recommendation, target price, expected return, position size or trading action.

## 5. Thesis-intake contract

### 5.1 Identity

One `industry_thesis_session_identity` represents one user research workflow, not one industry ontology identity.

Required identity fields:

- `session_id`: system UUID;
- `created_recorded_utc`: system-owned UTC;
- `created_by_kind`: `local_user` in v1;
- `state`: `active`, `completed`, `abandoned` or `retired`;
- `latest_revision_number`: expected-latest concurrency guard.

The identity does not own industry facts, company membership or investment conclusions.

### 5.2 Append-only thesis revision

One `industry_thesis_session_revision` freezes the exact user input and reviewed scope.

Required fields:

- `session_revision_id`;
- `session_id`;
- `revision_number`;
- `thesis_text_original`;
- `thesis_title_reviewed` nullable until reviewed;
- `driver_type`;
- `analysis_horizon_kind`;
- `analysis_start_date` nullable;
- `analysis_end_date` nullable;
- `market_scope_json`;
- `chain_boundary_json`;
- `exclusions_json`;
- `seed_companies_json`;
- `seed_products_json`;
- `seed_technologies_json`;
- `seed_bottlenecks_json`;
- `coverage_state`;
- `workflow_state`;
- `information_cutoff`;
- `recorded_utc`;
- `input_fingerprint_sha256`;
- `supersedes_revision_id` nullable;
- `revision_note`.

### 5.3 Controlled driver types

The accepted v1 driver vocabulary is:

- `demand_expansion`;
- `supply_contraction_or_pricing`;
- `policy_or_institutional_change`;
- `technology_substitution`;
- `event_shock`;
- `mixed`;
- `other`;
- `unknown`.

`unknown` is valid and must remain visible. A model may propose a driver type, but only an explicit user-confirmed revision may record the reviewed value.

### 5.4 Horizon contract

`analysis_horizon_kind` is one of:

- `near_term`;
- `medium_term`;
- `long_term`;
- `custom`;
- `unknown`.

Dates are optional for the named horizons and required for `custom`. The system does not infer dates from prose.

### 5.5 Market scope

Market scope is always explicit. It is an ordered strict JSON array of reviewed scope objects containing:

- `market_namespace`;
- `exchange_namespace` nullable;
- `security_type`;
- `include_status`;
- optional exact listed-instrument IDs.

The UI may suggest A shares, but persistence requires explicit confirmation. No hidden default broadens the scope.

### 5.6 Workflow states

The revision workflow state is one of:

- `draft`;
- `candidate_build_ready`;
- `awaiting_review`;
- `reviewed_plan_ready`;
- `accepted_outputs_linked`;
- `superseded`;
- `abandoned`.

State transitions require expected-latest protection and cannot mutate prior revisions.

## 6. Coverage semantics

Coverage is separate from evidence quality and candidate status.

Accepted values:

- `reviewed_local_scope`: the user explicitly reviewed the locally available scope and accepts it as the current working universe, without claiming full-market exhaustiveness;
- `partial_local_coverage`: known relevant areas or companies are missing from local mappings;
- `coverage_unknown`: the project cannot assess whether the local candidate universe is complete.

Rules:

1. `reviewed_local_scope` does not mean full-market coverage.
2. `partial_local_coverage` and `coverage_unknown` do not block drafting, but they block any UI wording that implies exhaustive discovery.
3. Coverage state is preserved in every accepted output link and downstream workspace notice.
4. External acquisition may later improve coverage only through separately accepted source contracts.

## 7. Candidate proposal model

### 7.1 Candidate identity and revisions

A proposal is non-accepted orchestration state.

`industry_thesis_candidate_identity` fields:

- `candidate_id`;
- `session_id`;
- `candidate_key` derived from source kind plus exact source reference or user-seed fingerprint;
- `created_recorded_utc`;
- `latest_revision_number`.

`industry_thesis_candidate_revision` fields:

- `candidate_revision_id`;
- `candidate_id`;
- `session_revision_id`;
- `revision_number`;
- `source_kind`;
- `source_reference_json`;
- `proposed_company_identity_id` nullable;
- `proposed_listed_instrument_id` nullable;
- `company_label_original`;
- `product_or_service_fit` nullable;
- `industry_position` nullable;
- `benefit_path_text`;
- `proposed_exposure_type`;
- `proposal_confidence`;
- `identity_state`;
- `review_state`;
- `rationale_json`;
- `uncertainty_json`;
- `manifest_fingerprint_sha256` nullable;
- `information_cutoff`;
- `recorded_utc`;
- `supersedes_revision_id` nullable.

### 7.2 Candidate source kinds and precedence

Accepted source kinds, highest precedence first:

1. `accepted_local_mapping` — exact accepted local company/product/taxonomy mapping;
2. `existing_industry_map_revision` — exact accepted Industry Map and beneficiary revision;
3. `user_seed` — explicit user-provided company, product or relationship;
4. `ai_draft` — optional bounded model proposal.

Precedence controls merge and display, not truth. Lower-precedence proposals remain visible when they disagree.

No proposal may overwrite another source's rationale or disappear because a higher-precedence source exists.

### 7.3 Identity states

- `exact_accepted_identity`;
- `candidate_identity_only`;
- `ambiguous_identity`;
- `unresolved_identity`;
- `rejected_identity`.

Only `exact_accepted_identity` is eligible for an accepted Stage 1 write.

Company name, ticker prefix, fuzzy string similarity, model output or Provider name alone cannot establish exact identity.

### 7.4 Proposal exposure types

Proposal values mirror the existing typed beneficiary vocabulary:

- `direct`;
- `conditional`;
- `indirect`;
- `conceptual`;
- `unknown`.

A proposal value is not an accepted typed beneficiary profile. The reviewed acceptance plan must explicitly choose the final value written through the existing owner.

### 7.5 Review states

- `proposed`;
- `selected_for_acceptance`;
- `rejected_by_user`;
- `unresolved`;
- `superseded`.

`selected_for_acceptance` is still orchestration state. Accepted membership exists only after the existing owner transaction succeeds and an exact output link is recorded.

## 8. Industry-chain draft

The orchestrator may preserve a draft graph but cannot own the accepted Industry Map graph.

The strict draft JSON contract contains ordered arrays for:

- driver proposals;
- chain-node proposals;
- relationship proposals;
- bottleneck proposals;
- value-pool-shift proposals;
- falsification-condition proposals;
- open verification questions.

Each proposal contains:

- stable draft key;
- source kind;
- exact source reference or Manifest fingerprint;
- proposal text;
- uncertainty state;
- user review state.

The accepted Industry Map is created or revised only through the existing v0.5B owner using an explicit reviewed plan.

## 9. Accepted-output link model

One append-only `industry_thesis_output_link_revision` proves what accepted state resulted from one reviewed plan.

Required fields:

- `output_link_revision_id`;
- `session_revision_id`;
- `accepted_industry_map_identity_id`;
- `accepted_industry_map_revision_id`;
- `accepted_candidate_pool_revision_id`;
- ordered exact beneficiary revision IDs;
- `coverage_state`;
- `acceptance_plan_fingerprint_sha256`;
- `owner_transaction_id`;
- `information_cutoff`;
- `recorded_utc`;
- `supersedes_output_link_revision_id` nullable.

This link does not copy map, beneficiary or company fields. It freezes exact owner revisions for reproduction and downstream navigation.

## 10. Persistence decision

### 10.1 Decision

A small additive persistence domain is required.

An ephemeral-only wizard would not preserve:

- the user's exact thesis and reviewed scope;
- candidate-source provenance;
- rejected and unresolved proposals;
- coverage state;
- the exact acceptance plan;
- reproducible links to accepted owner revisions;
- historical reruns under both as-of boundaries.

### 10.2 Candidate tables

A future implementation may add exactly six append-only table families:

1. `industry_thesis_session_identity`;
2. `industry_thesis_session_revision`;
3. `industry_thesis_candidate_identity`;
4. `industry_thesis_candidate_revision`;
5. `industry_thesis_output_link_identity`;
6. `industry_thesis_output_link_revision`.

Draft graph data remains strict JSON inside the session revision in v1. It does not require separate graph tables because accepted graph ownership stays in Industry Map.

### 10.3 Migration candidate

- Candidate migration: `20260722_0016` after accepted head `20260722_0015`.
- Additive only.
- No existing table or column changes.
- PostgreSQL is the production-relevant database contract.
- Supported SQLite behavior must preserve deterministic JSON text, uniqueness and revision allocation for tests/local use.
- Identity latest-revision allocation uses one transaction and row-level locking where supported.
- All foreign keys and output links commit atomically.
- A populated downgrade must refuse before dropping any thesis/orchestration table.
- This architecture PR does not create or run the migration.

## 11. User-confirmed acceptance transaction

### 11.1 Acceptance-plan input

The user-confirmed plan freezes:

- exact session revision;
- expected latest session revision number;
- reviewed thesis title and driver type;
- reviewed chain boundary;
- selected draft graph items;
- selected candidate revisions;
- exact accepted company identities;
- final exposure classifications;
- coverage state;
- information cutoff;
- plan fingerprint.

### 11.2 Owner calls

The orchestration service may coordinate existing owner services in one database transaction:

1. validate exact accepted company identities;
2. create or revise the Industry Map through the existing Industry Map owner;
3. create the complete Stage 1 candidate-pool revision through the existing beneficiary owner;
4. create/revise typed beneficiary profiles only for fields explicitly confirmed in the plan and only through the existing typed-semantics owner;
5. write the exact orchestration output-link revision;
6. commit all changes together.

The orchestrator does not implement alternative direct table writes.

### 11.3 Atomic failure

Any identity ambiguity, stale expected-latest value, duplicate company, incompatible cutoff, failed owner validation or output-link mismatch rolls back the entire transaction.

No partial map, beneficiary or link state is accepted.

## 12. Two-stage workflow

### 12.1 Stage A — complete reviewed beneficiary universe

Stage A answers:

- What is the driver type?
- Which chain/process positions matter?
- Where is the bottleneck?
- Where may the value pool migrate?
- Which companies are included in the current reviewed local scope?
- Why is each company included?
- Is exposure direct, conditional, indirect, conceptual or unknown?
- Which identity, product, customer, certification, capacity, production, order or transmission facts remain missing?

Stage A never uses valuation, price performance, popularity or candidate status as a membership filter.

### 12.2 Stage B — current research priority

Stage B reuses the existing Investment Candidate Intelligence owner and its eight dimensions:

1. industry opportunity and duration;
2. beneficiary strength;
3. earnings conversion and elasticity;
4. expectation gap;
5. valuation context;
6. catalyst readiness;
7. evidence quality;
8. risk penalty and falsification state.

The orchestrator only inspects readiness and invokes an explicit existing rule version. It does not calculate a second score.

### 12.3 Missing-data behavior

- Missing price/Comparison Eligibility: valuation remains unavailable and any existing rule gate applies.
- Missing structured financial observations: no normalized metric is invented.
- Pending verification: numeric aggregation remains prohibited under the existing contract.
- Missing Company Research: readiness reports the missing exact identity/revision.
- Partial coverage: result carries a coverage warning while preserving the accepted local pool.

## 13. Readiness inspection

The readiness read model is deterministic and network-free.

For every exact beneficiary member it reports:

- exact company and listed-instrument identity state;
- exact typed beneficiary profile state;
- latest cutoff-visible Company Research identity/revision;
- availability of the eight component inputs;
- exact Canonical Price and required purpose-specific Comparison Eligibility state;
- structured financial/valuation availability;
- catalyst/risk/falsification state;
- missing, stale, disputed, pending or failed reasons;
- whether an Investment Candidate snapshot can be created under the chosen rule version.

Readiness is not a recommendation and does not create accepted component values.

## 14. Commands

All commands are local, JSON-only, strict-schema, deterministic and dry-run capable.

### 14.1 `create-industry-thesis-session`

Creates an identity and first draft revision.

Required selectors:

- explicit market scope;
- information cutoff;
- thesis text;
- driver/horizon values or explicit `unknown`;
- optional seeds and exclusions.

Dry-run returns normalized strict JSON and input fingerprint without persistence.

### 14.2 `revise-industry-thesis-session`

Appends a revision using:

- exact session ID;
- expected latest revision number;
- explicit changed fields;
- revision note.

### 14.3 `build-industry-thesis-candidates`

Builds proposals from selected local source kinds only.

Required inputs:

- exact session revision;
- allowed candidate-source kinds;
- explicit local mapping/revision selectors;
- deterministic builder version.

No network or AI call occurs.

### 14.4 `record-industry-thesis-proposal-review`

Appends reviewed proposal states and final user choices without creating accepted owner state.

### 14.5 `accept-industry-thesis-plan`

Runs the atomic existing-owner transaction and writes output links.

Requires:

- exact reviewed session revision;
- expected latest protection;
- exact selected candidate revisions;
- exact accepted company identities;
- explicit final exposure values;
- exact acceptance-plan fingerprint;
- dry-run review before commit.

### 14.6 `inspect-industry-analysis-readiness`

Network-free exact-ID readiness read.

### 14.7 `create-industry-investment-candidate-snapshot`

A thin orchestration command that invokes the existing Investment Candidate owner with:

- exact output-link revision;
- exact candidate-pool revision;
- exact rule version;
- both as-of boundaries;
- expected owner preconditions.

It does not own scoring logic.

## 15. Read APIs

Candidate exact-ID APIs:

- `GET /industry-analysis/sessions/{session_id}`;
- `GET /industry-analysis/session-revisions/{session_revision_id}`;
- `GET /industry-analysis/session-revisions/{session_revision_id}/candidates`;
- `GET /industry-analysis/output-links/{output_link_revision_id}`;
- `GET /industry-analysis/output-links/{output_link_revision_id}/readiness`;
- `GET /industry-analysis/output-links/{output_link_revision_id}/result`.

Every read requires:

- explicit information cutoff;
- explicit recorded-UTC boundary;
- exact IDs;
- no fallback to latest compatible records;
- bounded query count and deterministic ordering;
- no network or AI call.

## 16. Chinese-first UI

### 16.1 Entry route

```text
/industry-analysis/new
```

### 16.2 Step sequence

1. **输入行业/产业命题**
   - thesis text;
   - explicit market scope;
   - horizon;
   - seeds and exclusions.

2. **审阅驱动类型与产业结构**
   - driver type;
   - chain boundary;
   - bottlenecks;
   - value-pool shifts;
   - falsification conditions.

3. **审阅完整受益公司候选池**
   - inclusion path;
   - exact identity state;
   - proposed exposure;
   - rationale and uncertainty;
   - coverage state.

4. **确认行业地图和受益公司计划**
   - explicit final selections;
   - no automatic acceptance;
   - dry-run owner changes.

5. **检查公司研究完整性**
   - Company Research;
   - typed semantics;
   - financial/price/valuation state;
   - catalysts, risks and missing reasons.

6. **生成研究候选状态**
   - explicit existing rule version;
   - deterministic snapshot;
   - no invented inputs.

7. **查看完整公司池和当前研究优先级**
   - complete Stage 1 pool always visible;
   - highlighted priority/watch members;
   - missing and exclusion reasons;
   - coverage warning;
   - exact revision/provenance navigation.

### 16.3 UI prohibitions

- no one-click AI acceptance;
- no hidden company deletion;
- no default top-N universe;
- no buy/sell/hold labels;
- no target price, expected return or position sizing;
- no trading controls;
- no ordinary-read AI or network activity.

## 17. Optional industry-level AI draft extension

### 17.1 Boundary

The offline deterministic MVP does not require AI.

A later bounded Strict implementation slice may extend guarded AI from company scope to one exact industry-thesis session. It must remain optional and disabled by default.

### 17.2 Manifest

The immutable Manifest may contain only:

- exact session revision fields approved for transmission;
- exact selected local mapping/map/beneficiary excerpts;
- explicit user seeds;
- controlled output vocabulary;
- information cutoff;
- Manifest SHA-256.

It may not browse, search, retrieve external data or infer accepted identity.

### 17.3 Output

Strict validated JSON may propose:

- driver candidates;
- chain nodes and relationships;
- bottlenecks and value-pool shifts;
- candidate company labels;
- product/service fit;
- benefit-path rationale;
- uncertainty and verification questions.

It may not output accepted evidence grades, component scores, candidate status, recommendation, target price or trading action.

### 17.4 Persistence

AI output is stored only as `ai_draft` proposal revisions with Manifest fingerprint and explicit uncertainty. It cannot become accepted state without the same explicit user review and owner transaction used for all other proposals.

## 18. Production-realistic offline golden path

Fixture scenario: one synthetic A-share industry thesis with three exact local company identities.

### 18.1 Inputs

- Thesis: demand expansion in a synthetic advanced-material supply chain.
- Market scope: explicit A-share listed-equity scope.
- Driver type: `demand_expansion`.
- Horizon: `medium_term`.
- Local mapping source: one exact accepted product/company mapping set.
- No news, announcement, Provider, browser or AI call.

### 18.2 Candidate universe

1. Company A
   - exact identity;
   - direct exposure;
   - complete typed semantics and Company Research;
   - eligible price and structured valuation inputs;
   - complete Investment Candidate components.

2. Company B
   - exact identity;
   - conditional exposure;
   - Company Research present;
   - valuation input missing.

3. Company C
   - exact identity;
   - conceptual exposure;
   - evidence insufficient and verification pending.

### 18.3 Success sequence

1. create thesis session and draft revision;
2. deterministically build three proposals;
3. review driver, chain, bottleneck, value-pool and coverage;
4. explicitly select all three companies for the Stage 1 local universe;
5. dry-run and commit the existing-owner acceptance transaction;
6. freeze exact map, candidate-pool and beneficiary revisions in the output link;
7. inspect readiness for all three members;
8. invoke the existing Investment Candidate rule version;
9. reproduce the snapshot under both as-of boundaries;
10. display all three members, with Company A eligible for a current priority/watch result, Company B carrying missing-valuation reasons and Company C carrying pending/evidence-insufficient reasons.

No member disappears from the complete pool.

## 19. Primary failure path

A proposal contains a company label produced by user prose or AI, but no exact accepted company identity can be resolved.

Required behavior:

1. proposal identity remains `ambiguous_identity` or `unresolved_identity`;
2. user may keep it visible for verification;
3. `accept-industry-thesis-plan` rejects any plan selecting it for accepted membership;
4. the entire owner transaction rolls back;
5. no Industry Map, candidate pool, beneficiary revision, typed profile, Company Research, component assessment, candidate snapshot or output link is created;
6. the error returns the exact candidate revision and identity reason without suggesting a guessed company.

## 20. Additional failure paths

### 20.1 Ambiguous thesis

A thesis with no reviewable boundary may be saved as `draft` but cannot advance to `reviewed_plan_ready` until market scope and chain boundary are explicit or explicitly `unknown` with coverage warning.

### 20.2 Empty local coverage

The deterministic builder returns zero candidates and `coverage_unknown`. The UI must request user seeds or an optional AI draft; it cannot claim no beneficiaries exist.

### 20.3 Duplicate company identity

Two proposals resolving to the same accepted company identity are preserved as source records but collapse to one selected owner member only after explicit conflict review. A plan containing duplicate selected members fails validation.

### 20.4 Stale revisions

Any session, candidate, owner or rule revision mismatch fails expected-latest validation before writes.

### 20.5 Missing price eligibility

Readiness remains valid, but valuation and any dependent candidate aggregation follow existing fail-closed rules. No Provider price or latest row is substituted.

### 20.6 AI-owned acceptance attempt

Any payload that attempts to mark AI output as accepted without explicit user selection and exact owner inputs is rejected before transaction start.

### 20.7 Universe truncation

Any requested operation that omits a reviewed Stage 1 member solely because of valuation, popularity, price performance, missing data or low component score is rejected as a universe-integrity violation.

## 21. Concurrency, chronology and determinism

- Revision numbers are allocated transactionally per identity.
- Writes require `expected_latest_revision_number`.
- Stable ordering uses explicit sequence plus UUID tie break only where required.
- Strict JSON is canonicalized before fingerprinting.
- `recorded_utc` is system-owned.
- `information_cutoff` is user-supplied and validated against linked accepted records.
- Later-recorded information cannot appear in an earlier reproduced read.
- Output links freeze exact revisions and never select a newer compatible record.
- PostgreSQL lock behavior and SQLite test behavior must be explicitly tested in implementation.

## 22. Security and privacy

- No credentials are required by the offline MVP.
- Thesis text and local research remain local unless the user explicitly invokes the optional AI draft command.
- AI transmission requires an approved profile, exact Manifest preview and explicit confirmation.
- No secrets, connection strings, API keys or raw credentials enter Issues, PRs, fixtures, database rows or errors.

## 23. Observability

Commands return strict JSON containing:

- command version;
- dry-run/commit mode;
- exact input IDs and revisions;
- input/plan fingerprint;
- coverage state;
- proposed or committed owner revisions;
- missing and failure reason codes;
- information cutoff;
- recorded UTC;
- no secret or raw AI credential data.

No background scheduler, daemon, webhook or hidden retry is included.

## 24. Implementation sequence candidate

Architecture approval should lead to separately authorized bounded implementation Issues.

### Slice 1 — Offline thesis/orchestration foundation

- migration candidate `20260722_0016`;
- session and candidate identities/revisions;
- strict JSON contracts and fingerprints;
- deterministic local candidate builder;
- local commands and exact-ID reads;
- offline golden/failure tests.

### Slice 2 — Existing-owner acceptance and readiness

- user-confirmed acceptance plan;
- atomic calls to Industry Map, Stage 1 and typed-semantics owners;
- output links;
- complete-universe readiness inspection;
- thin handoff to existing Investment Candidate snapshot command.

### Slice 3 — Chinese-first orchestration workspace

- `/industry-analysis/new` wizard;
- review, dry-run and commit views;
- full-universe result and exact provenance navigation;
- no network or AI on ordinary reads.

### Slice 4 — Optional industry-level guarded AI drafts

- separate Strict Issue;
- immutable Manifest;
- explicit remote confirmation;
- strict proposal-only JSON;
- no browsing/retrieval/tools;
- no accepted-state promotion.

Slices may be combined only if the implementation Issue proves one bounded PR remains reviewable and preserves exact ownership. Architecture approval does not automatically authorize any slice.

## 25. Alternatives rejected

### 25.1 No persistence / browser-only wizard

Rejected because reviewed inputs, rejected proposals, coverage state and accepted output links would not be reproducible.

### 25.2 New generic research graph owner

Rejected because Industry Map already owns accepted chain/map state and a generic graph would duplicate ownership.

### 25.3 AI-first automatic company discovery

Rejected because arbitrary text/model output cannot establish exact company identity, complete market coverage or accepted beneficiary membership.

### 25.4 News/announcement-required workflow

Rejected because the core industry research product must operate independently; external evidence is enrichment.

### 25.5 Direct top-N investment output

Rejected because it would collapse Stage A, hide incomplete beneficiaries and turn research prioritization into unexplained advice.

### 25.6 Generic agent/RAG/provider framework

Rejected as unnecessary infrastructure expansion and a hidden data/ownership risk.

## 26. Stop conditions

Do not authorize implementation if:

- existing owner services cannot be invoked without direct duplicate table writes;
- exact accepted company identity is unavailable for the golden path;
- a useful offline path requires external data or AI;
- coverage cannot be represented independently of evidence quality;
- free text or AI must directly create accepted map, membership, component or candidate state;
- Stage A cannot preserve the complete reviewed local universe;
- the design requires hidden defaults, fallback records, network reads or later-information leakage;
- migration downgrade cannot fail before dropping populated state;
- the workflow produces recommendation, target price, expected return, portfolio or trading behavior.

## 27. Validation requirements

The architecture PR must prove:

- exact base `be18f407fb42b6caf22d339285e17f830052af91`;
- only the authorized documentation files changed;
- no production, migration, dependency, fixture, test or network code;
- Markdown/repository CI success on the exact final HEAD;
- one fresh process-independent fixed-head review;
- zero unresolved review threads before merge;
- separate explicit owner merge authorization.

Required approval phrase:

```text
AUTHORIZED INDUSTRY THESIS ORCHESTRATION PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates the fixed-head review evidence.

## 28. Locked exclusions

No production code, migration, API/UI implementation, fixture, dependency, Provider, news ingestion, official-announcement ingestion, THS live access, web scraping, hidden browsing, automatic company-universe acceptance, automatic evidence acceptance, automatic component scoring, LLM-owned accepted state, unexplained ranking, target price, expected return, buy/sell/hold recommendation, position sizing, portfolio, broker connection, order, automated trading, release, tag or version change.

## 29. Closure decision

The Architecture Preflight is ready for implementation planning only when the exact-head review confirms:

1. the six-table maximum additive orchestration domain does not duplicate accepted business ownership;
2. the offline golden path reaches existing owner services;
3. exact identity, revision, cutoff and recorded-UTC boundaries are complete;
4. complete-universe preservation is enforced;
5. AI remains optional proposal-only assistance;
6. news, announcements and external Providers remain optional enrichment;
7. implementation can be split into bounded separately authorized slices.

Architecture merge will not itself authorize implementation.
