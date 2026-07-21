# Typed Beneficiary Evidence Semantics v1 Architecture Preflight

## Status and authority

- Authority: Issue #164.
- Related roadmap: Issue #137.
- Required base: `13099ce1988dec05eaf674732fce3acb7f5fa080`.
- Predecessor consolidation: Issue #162 / merged PR #163.
- Work type: Architecture Preflight and Definition of Ready, documentation only.
- Released version remains `0.2.0`.
- This document authorizes no production code, API/UI behavior, schema, migration, Provider, dependency, fixture, test, release or version change.

## Executive decision

Typed Beneficiary Evidence Semantics v1 **reaches architecture Definition of Ready as a later separately authorized implementation candidate** under the following design:

1. Add a **separate append-only semantic profile layer** linked to one existing `Stage1Beneficiary` identity.
2. Do not alter, backfill, reinterpret or replace existing v0.5C beneficiary identities or revisions.
3. Preserve raw `direct / secondary / potential` as the exact legacy Stage 1 analytical state.
4. Add the new `direct / conditional / indirect / conceptual` exposure taxonomy only inside the new versioned semantic layer.
5. Require every semantic revision to freeze one exact existing beneficiary revision and selected map revision.
6. Require positive typed assertions to bind exact claim revisions already frozen by that beneficiary revision.
7. Keep Evidence Ledger claims, evidence grades, relations, conflicts and chronology authoritative; the new layer owns no evidence item.
8. Treat every accepted typed value as an explicit analyst-owned D3 judgment. Deterministic code validates identity, chronology, vocabulary and evidence sufficiency but never invents a value.
9. Use an explicit local command as the only v1 write surface. Browser/API surfaces remain read-only.
10. Add one new migration with no backfill and a downgrade preflight that refuses to delete populated semantic history.

The implementation must stop if it cannot satisfy these boundaries without free-text, Provider, stock-code or model inference.

## One-sentence user job

For one explicitly selected persisted Industry Map and one exact existing Stage 1 beneficiary identity, an analyst can record and later review typed exposure, driver and execution-evidence states with exact beneficiary/map revisions, claim links, cutoff, UTC, conflict and missing-data provenance, without ranking companies or inferring accepted state from free text or AI output.

## Why a separate layer is required

The current v0.5C beneficiary revision already has an accepted meaning and is frozen by downstream Stage 2 records. It owns:

- exact beneficiary identity, case, map, source and stock code;
- exact selected map revision and stock row;
- raw `beneficiary_kind` in `direct / secondary / potential`;
- `assessment_status`;
- rationale;
- information cutoff, recorded UTC and supersession;
- exact map-assertion and claim-revision links;
- candidate-pool membership and downstream handoff.

Changing that revision contract would create four unacceptable risks:

1. historical Stage 2 foreign keys would appear to point at a changed semantic contract;
2. old `direct / secondary / potential` values would require a fabricated mapping;
3. new typed fields would force backfill or nullable mixed-version rows into an accepted table;
4. a later semantic correction could appear to rewrite the original Stage 1 judgment.

The new layer therefore extends research history without mutating it.

## Existing authoritative source inventory

| Object | Current owner | Available foundation | Limitation resolved by this slice |
| --- | --- | --- | --- |
| Research case | v0.5A Evidence Ledger | case identity and immutable revisions | No typed beneficiary execution state. |
| Claim/evidence graph | v0.5A Evidence Ledger | exact claim revisions, support/contradiction/context links, A/B/C/D grades, conflicts and missing evidence | New layer may reference exact claims but may not create or reinterpret evidence. |
| Industry map | v0.5B | map identity/revisions, nodes, relationships, `driver / bottleneck / value_pool_shift` observations | `driver` has no accepted type/subtype. |
| Stage 1 beneficiary | v0.5C | explicit company identity and immutable beneficiary revisions | Raw three-value taxonomy only; no typed execution fields. |
| Candidate pool | v0.5C | exact unranked frozen membership | Not a typed evidence profile and not a ranking source. |
| Company research | v0.6A-v0.6D | exact Stage 1 handoff and downstream research revisions | Existing records must not automatically relink to new semantic revisions. |
| Industry Research page | Product surface | explicit map selection and complete persisted beneficiary rows | May later load the new profile only after explicit row action. |

## Ownership and identity

### Stable identity

Candidate table: `stage1_beneficiary_semantic_profiles`.

One profile identity exists for at most one exact `stage1_beneficiary_id`:

- `id` UUID primary key;
- `beneficiary_id` UUID, unique, required, `ON DELETE RESTRICT`;
- `created_at_utc` timezone-aware UTC, required.

The profile identity does not own company identity. Company, case, map, source and stock code remain owned by the referenced Stage 1 beneficiary.

### Immutable revisions

Candidate table: `stage1_beneficiary_semantic_profile_revisions`.

Each revision contains:

- `id` UUID primary key;
- `profile_id` UUID, required;
- `revision_no` positive integer, unique per profile;
- `beneficiary_revision_id` UUID, required and frozen;
- `selected_map_revision_id` UUID, required and equal to the frozen value on the beneficiary revision;
- `taxonomy_version` exact constant `aquantai.typed-beneficiary-evidence-semantics.v1`;
- `overall_status`: `draft / supported / disputed / rejected`;
- `summary` explicit analyst text;
- `recorded_by` explicit local analyst responsibility label;
- `information_cutoff_date` date, required;
- `recorded_at_utc` timezone-aware UTC, required;
- `supersedes_revision_id` nullable exact prior profile revision.

A semantic revision freezes one exact beneficiary revision. It never follows a later Stage 1 revision automatically.

### Analyst responsibility label

`recorded_by` is required, trimmed, non-empty and bounded to 100 characters.

It is:

- a local responsibility/audit label;
- not authentication;
- not authorization;
- not a verified legal identity;
- not derived from Git author, operating-system account or environment variables.

A future identity/authentication contract may replace or supplement it only through a separate Architecture Preflight.

## Typed assertion model

Candidate table: `stage1_beneficiary_semantic_assertions`.

Each assertion belongs to one immutable profile revision and contains:

- `id` UUID primary key;
- `profile_revision_id` UUID, required;
- `assertion_key` stable explicit key, unique within the revision;
- `field_kind` from the exact v1 list;
- `state_code` valid for that field kind;
- `evidence_state`: `supported / disputed / missing / not_applicable`;
- `subject_text` optional bounded explicit text where allowed;
- `rationale` required bounded analyst text;
- `map_observation_revision_id` nullable and allowed only for `driver`;
- `position` non-negative deterministic display order.

This is not open-ended EAV. The field list, state-code matrix, required cardinality and validation behavior are versioned and closed for v1.

### Required cardinality per profile revision

A revision must contain:

- exactly one `exposure` assertion;
- at least one `driver` assertion;
- at least one `offering` assertion;
- exactly one each of `customer`, `certification`, `capacity`, `production` and `order`.

Additional unreviewed field kinds are rejected.

## Exposure taxonomy

Taxonomy version: `aquantai.typed-beneficiary-evidence-semantics.v1`.

Exact exposure state codes:

- `direct` — supported evidence connects the company’s explicit offering or capability to the identified driver, bottleneck or value-pool path through a primary revenue, cost or strategic value-capture mechanism.
- `conditional` — the economic benefit depends on one or more explicit unresolved execution conditions such as qualification, certification, capacity, production, customer adoption or order conversion.
- `indirect` — the company is exposed through a second-order demand, cost, substitution or ecosystem effect rather than the primary identified value-capture path.
- `conceptual` — thematic association exists, but accepted evidence does not yet establish an executable company-level economic transmission path.

Rules:

- no automatic mapping from legacy `direct / secondary / potential`;
- legacy and new values are displayed side by side;
- disagreement is a historical/semantic fact, not an integrity error;
- exposure values are D3 analyst judgments, not scores or probabilities;
- values have no numeric ordering.

## Industry-driver vocabulary

Every driver assertion must link one exact cutoff-visible `IndustryMapObservationRevision` whose persisted `observation_kind` is `driver` and which is already frozen by the selected beneficiary revision.

Exact driver types and allowed subtypes:

### `demand_expansion`

- `end_demand_growth`
- `capacity_expansion`
- `mix_upgrade`
- `replacement_cycle`

### `supply_contraction`

- `capacity_exit`
- `supply_disruption`
- `input_shortage`
- `compliance_constraint`
- `price_repair`

### `policy_institutional_change`

- `subsidy_or_fiscal_support`
- `procurement_or_localization`
- `access_or_approval`
- `regulation_or_standard`
- `trade_policy`

### `technology_substitution`

- `process_upgrade`
- `material_substitution`
- `equipment_substitution`
- `architecture_shift`
- `domestic_substitution`

### `event_shock`

- `geopolitical`
- `disaster_or_accident`
- `public_health`
- `trade_restriction`
- `temporary_supply_demand_dislocation`

The type/subtype pair is selected explicitly. Observation title, description, Provider text, claim text or AI output cannot populate it automatically.

Multiple driver assertions are allowed and displayed in explicit `position` order. Position is presentation only and is not priority or weight.

## Offering vocabulary

`offering` assertions use one exact state code:

- `product`
- `material`
- `equipment`
- `service`
- `software`
- `process_capability`
- `capacity_resource`
- `other_explicit`

`subject_text` is required and names the exact offering/capability. It remains analyst-entered D3 text and must be evidence-linked. `other_explicit` requires rationale explaining why no reviewed code fits.

## Execution-evidence vocabularies

The codes below are descriptive research states. They are not numeric maturity scores and are not required to progress monotonically. Later evidence may move a state backward, to disputed, or to missing through a new immutable revision.

### Customer stage

- `unknown`
- `target_identified`
- `technical_contact`
- `sample_or_trial`
- `qualification_in_progress`
- `approved_supplier`
- `commercial_supply`
- `recurring_supply`
- `not_applicable`

### Certification stage

- `unknown`
- `not_started`
- `preparation`
- `submitted`
- `testing`
- `approved`
- `suspended_or_expired`
- `rejected`
- `not_applicable`

### Capacity stage

- `unknown`
- `announced`
- `funded_or_approved`
- `under_construction`
- `installed`
- `commissioning`
- `operational`
- `expansion_suspended`
- `not_applicable`

### Production stage

- `unknown`
- `research_or_lab`
- `pilot`
- `small_batch`
- `ramping`
- `mass_production`
- `stable_mass_production`
- `suspended`
- `not_applicable`

### Order/commercialization stage

- `unknown`
- `inquiry_or_intent`
- `sample_order`
- `framework_agreement`
- `purchase_order`
- `delivery_started`
- `recurring_orders`
- `cancelled_or_expired`
- `not_applicable`

## Evidence ownership and links

Candidate table: `stage1_beneficiary_semantic_assertion_claim_links`.

Each row contains:

- `assertion_id`;
- exact `claim_revision_id`;
- relation `support / contradict / context`;
- `recorded_at_utc`.

### Closed evidence boundary

A semantic assertion may link only a claim revision that is already frozen by the selected `beneficiary_revision_id` through accepted v0.5C claim-link records.

Consequences:

- the semantic layer cannot introduce a new claim-to-beneficiary relationship;
- it cannot link arbitrary claims merely because they share a case or stock code;
- it never links directly to `EvidenceItem`;
- evidence items, grades and claim-evidence relations are read through the existing Evidence Ledger graph;
- if a needed claim is absent, the analyst must first create a separately reviewed Stage 1 beneficiary revision that freezes it.

### Evidence-state rules

#### `supported`

- `state_code` must be a positive reviewed code, not `unknown` or `not_applicable`;
- at least one `support` claim revision is required;
- at least one support path must reach visible A/B/C evidence;
- no visible contradiction may remain unresolved for the assertion;
- all links must be cutoff-visible and no later than the semantic revision’s recorded boundary.

#### `disputed`

- at least one support and one contradiction path are required, or the linked claim graph must expose an accepted unresolved conflict;
- the chosen state remains the analyst’s disputed hypothesis, not an accepted fact;
- overall profile status must be `disputed` or `draft`.

#### `missing`

- `state_code` must be `unknown`;
- no positive stage may be implied;
- a verification item is required;
- absence of public evidence is not evidence of a negative stage.

#### `not_applicable`

- `state_code` must be `not_applicable`;
- rationale is required;
- at least one support or context claim is required to explain why the field does not apply;
- if that evidence does not exist, the assertion must be `missing`, not `not_applicable`.

## Verification items

Candidate table: `stage1_beneficiary_semantic_verification_items`.

Each immutable item contains:

- profile revision ID;
- optional assertion ID;
- verification question;
- expected evidence type;
- status fixed to `open` in v1;
- recorded UTC.

V1 does not add task assignment, due date, notification, monitoring or completion workflow. A later revision may omit a resolved question or record a new state; it does not mutate the old item.

## Overall status rules

### `draft`

- incomplete or still-being-reviewed profile;
- may contain supported, disputed, missing or not-applicable assertions;
- cannot be treated as an accepted semantic handoff.

### `supported`

- exposure is supported;
- at least one driver and one offering are supported;
- no assertion is disputed;
- execution fields may be supported, missing or not-applicable;
- every missing field has a verification item.

### `disputed`

- at least one material assertion is disputed;
- conflicts are shown explicitly;
- no deterministic resolver chooses a winner.

### `rejected`

- preserves an explicit analyst decision that the profile revision should not be used as current supported research;
- historical data remains visible;
- rejection is not deletion.

## Derivation and semantic levels

### D0

- stable IDs and foreign keys;
- exact beneficiary/map/claim revision IDs;
- taxonomy version;
- cutoff, UTC, revision number and supersession;
- stored analyst responsibility label.

### D1

- latest cutoff-visible semantic revision selection;
- exact evidence-grade and relation counts from frozen claim graphs;
- deterministic validation of vocabulary, chronology and link membership;
- deterministic conflict/missing summaries.

### D2

No new D2 rule engine exists in v1. Taxonomy/version validation is deterministic, but value selection is not rule-derived.

### D3

- exposure kind;
- driver type/subtype selection;
- offering classification and text;
- customer/certification/capacity/production/order states;
- rationale and overall status.

The UI must label these as analyst research judgments, not verified operating facts or investment conclusions.

## Chronology, visibility and supersession

- `information_cutoff_date` and `recorded_at_utc` are separate.
- A semantic revision is visible at cutoff only when its own cutoff and recorded UTC are visible.
- Its frozen beneficiary revision, selected map revision, driver observation revisions, claim revisions, links and underlying evidence must also be visible.
- `supersedes_revision_id` must be null for revision 1 and must equal the exact latest prior revision for later revisions.
- Revision numbers are gap-free per profile under the command transaction.
- No later Stage 1 or claim revision is substituted for a frozen link.
- A later Stage 1 revision creates a visible historical mismatch until a new semantic profile revision explicitly freezes it.
- Existing Stage 2 records remain unchanged and do not automatically acquire or follow semantic profile revisions.

## Command and transaction boundary

### V1 write surface

The only candidate write surface is an explicit local command:

```text
python -m scripts.record_beneficiary_semantics --input <local-json-path>
```

Optional `--dry-run` validates and renders the normalized command without database writes.

The command:

1. validates the complete input before database mutation where possible;
2. requires explicit beneficiary ID, beneficiary revision ID and map revision ID;
3. loads the exact accepted frozen graph;
4. validates every assertion and claim link;
5. acquires the profile/revision allocation boundary;
6. inserts identity, revision, assertions, links and verification items in one transaction;
7. rolls back everything on any failure;
8. emits bounded non-sensitive JSON containing IDs, counts and status only.

There is no browser POST, background job, scheduled update, import-time write or startup-time write.

### Optimistic expectation

For revisions after the first, command input must include `expected_latest_revision_id`. A mismatch fails closed as a conflict before insertion.

## Candidate read surfaces

### Detail API

Candidate:

```text
GET /industry-alpha/beneficiary-semantics/{beneficiary_id}?as_of_cutoff=YYYY-MM-DD
```

It returns:

- profile identity;
- latest cutoff-visible revision;
- full revision history visible at cutoff;
- exact frozen legacy beneficiary kind and revision;
- typed assertions, evidence states and exact claim links;
- conflicts, missing fields and verification items;
- explicit D0/D1/D3 and non-advisory notices.

It does not return a score, rank, probability, target price or recommendation.

### Industry Research page

The existing `/industry-research` initial workspace query remains unchanged.

A beneficiary row may expose an explicit “查看类型化证据语义” action. Only that action loads the detail API. No semantic profile is loaded per row during initial map workspace rendering, preventing N+1 behavior.

The page remains read-only and renders untrusted values with DOM APIs and `textContent`; no `innerHTML`.

### HTTP failure boundary

- 422 — malformed UUID/date or invalid query input;
- 404 — beneficiary/profile/revision not found or not cutoff-visible;
- 503 — database configuration/query/integrity failure with stable redacted text.

Command-domain conflicts use deterministic local errors and non-zero exit status; no mutation HTTP API exists in v1.

## Persistence and migration design

Candidate Alembic revision:

`20260721_0012_typed_beneficiary_evidence_semantics.py`

Candidate tables:

1. `stage1_beneficiary_semantic_profiles`;
2. `stage1_beneficiary_semantic_profile_revisions`;
3. `stage1_beneficiary_semantic_assertions`;
4. `stage1_beneficiary_semantic_assertion_claim_links`;
5. `stage1_beneficiary_semantic_verification_items`.

### Upgrade

- creates only the five new tables, constraints and indexes;
- adds no column to accepted v0.5A-v0.6D tables;
- performs no backfill;
- does not map legacy beneficiary kinds;
- existing beneficiaries simply have no semantic profile until explicitly recorded.

### Downgrade

Downgrade performs a preflight before dropping anything:

- if all five tables are empty, downgrade may drop them in dependency order;
- if any semantic row exists, downgrade fails with a deterministic actionable Alembic error before any schema change;
- downgrade never deletes, rewrites or exports accepted semantic history automatically.

### Runtime rollback

Any command validation, uniqueness, chronology, evidence or integrity failure rolls back the complete attempted revision. No partial identity, assertion, link or verification rows remain.

## Production-realistic offline golden path

The implementation must extend the deterministic research fixture with one explicit beneficiary that already freezes:

- one selected map revision;
- one `driver` observation revision;
- exact claim revisions with A/B/C support evidence;
- at least one contradiction or missing-evidence example.

The command creates a semantic profile containing, for example:

- exposure: `conditional`;
- driver: `demand_expansion / capacity_expansion` linked to the exact driver observation;
- offering: exact `material` or `equipment` subject text;
- customer: `qualification_in_progress`;
- certification: `testing`;
- capacity: `commissioning`;
- production: `pilot`;
- order: `sample_order` or `unknown` with a verification item.

The golden path must prove:

- deterministic normalized output across clean SQLite and PostgreSQL builds where existing test policy supports both;
- no network calls;
- exact claim membership and evidence-state validation;
- historical cutoff before creation returns not visible;
- later semantic revision preserves the earlier revision unchanged;
- later Stage 1 revision does not relink old semantic history;
- repeated stale expected revision fails with zero partial writes;
- read API and explicit page action render the same exact frozen values.

## Bounded implementation candidate

A later Product Task may authorize only the following file families, with an exact list frozen in its Issue:

- one `.codex/tasks/issue-<implementation>-typed-beneficiary-evidence-semantics.md` snapshot;
- one Alembic migration `20260721_0012_typed_beneficiary_evidence_semantics.py`;
- domain-local models, contracts, commands, repository and query modules under `industry_alpha/`;
- the existing Industry Alpha API router for one read-only detail route;
- one explicit local recording script;
- minimal Industry Research HTML/JavaScript integration using existing CSS;
- deterministic fixture extension only if required by the approved golden path;
- focused SQLite/PostgreSQL migration, command, query, API/page and no-network tests;
- documentation for the local command and semantic boundary.

The implementation should not modify:

- existing v0.5A-v0.6D table definitions;
- Company Research or Guarded AI input contracts;
- `backend/main.py` unless a separately justified route-registration need is proven; the existing router should be reused;
- dependency files;
- Provider code;
- Docker/CI configuration;
- release/version files.

## Required implementation tests

### Vocabulary and contract

- exact taxonomy version;
- exact field-kind/state-code matrix;
- required assertion cardinality;
- no numeric ordering or score fields;
- strict analyst-label and text bounds.

### Identity and frozen links

- explicit beneficiary identity only;
- beneficiary revision belongs to beneficiary;
- selected map revision matches beneficiary revision;
- driver observation is exact, frozen and `observation_kind=driver`;
- every claim is already frozen by the beneficiary revision;
- later compatible-looking revisions are rejected.

### Evidence states

- supported requires A/B/C-backed support and no unresolved contradiction;
- disputed requires support plus contradiction/conflict;
- missing requires `unknown` and a verification item;
- not-applicable requires evidence and rationale;
- direct EvidenceItem linking is impossible;
- D-grade-only evidence cannot establish supported positive state.

### Chronology and append-only behavior

- exact cutoff/UTC visibility;
- gap-free revision allocation;
- expected-latest conflict;
- immutable prior revisions;
- update/delete rejection under the accepted append-only policy;
- atomic rollback on every failure;
- populated downgrade refusal and empty downgrade success.

### Query/API/page

- latest and historical cutoff views;
- exact legacy/new taxonomy separation;
- conflicts and missing fields visible;
- initial Industry Research workspace query count unchanged;
- semantic detail loaded only on explicit action;
- stable 422/404/503 behavior;
- no `innerHTML` and safe DOM rendering.

### Safety

- import/startup/tests/fixture reads make no network call;
- no LLM/Guarded AI call;
- no inference from stock code, name, Provider industry, rationale or claim text;
- no ranking, score, price, recommendation, alert, portfolio or trading field.

## Locked exclusions

- no Evidence Ingestion restart, PDF workflow, crawling, scraping, browsing or external search;
- no AI/LLM-owned taxonomy, extraction, accepted state or evidence promotion;
- no automatic company, map, driver or claim selection;
- no automatic mapping from legacy beneficiary kind;
- no generic rule engine, agent framework, RAG, vector database, embeddings or tools;
- no browser mutation route in v1;
- no cross-company comparison, ranking, score, weight or research-priority total;
- no Canonical Price or Comparison Eligibility;
- no fair value, target price, expected return, upside/downside or buy/sell/hold;
- no monitoring, alerts, tasks, portfolio or trading;
- no Provider, dependency, release or version change.

## Stop conditions

Implementation must not be authorized if independent review finds that:

- a required semantic value cannot be entered explicitly under the closed vocabulary;
- positive states require claims not frozen by the selected beneficiary revision;
- the design requires parsing or inferring from free text, Provider metadata, identifiers or AI output;
- existing Stage 1 or Stage 2 history must be mutated, backfilled or automatically relinked;
- a populated downgrade would delete history;
- the first slice requires a browser mutation surface, authentication system, ranking, valuation, ingestion or monitoring.

## Definition-of-Ready checklist

The architecture is ready for a separately authorized implementation only if the reviewer confirms:

- exact two-file documentation scope;
- separate append-only semantic layer;
- raw legacy taxonomy preserved without mapping;
- exact v1 taxonomy and vocabularies;
- explicit analyst-owned D3 values only;
- exact beneficiary/map/driver/claim revision freezes;
- closed Evidence Ledger ownership and evidence-state rules;
- no direct evidence duplication;
- complete chronology/supersession/history behavior;
- one no-backfill migration and fail-closed populated downgrade;
- CLI-only write and read-only API/page candidate;
- bounded golden path and tests;
- all locked exclusions intact.

## Completion gate

This preflight is not implementation authorization.

The PR carrying it must remain Draft/Open/unmerged until an independent reviewer verifies one fixed HEAD and records:

`TYPED BENEFICIARY SEMANTICS PREFLIGHT APPROVED at fixed head <HEAD_SHA>`

Do not create an implementation Issue, migration or production code until that approval is present and the owner explicitly authorizes the next step.