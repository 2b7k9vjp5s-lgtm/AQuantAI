# Company Research Workspace v1 Architecture Preflight

## Status

- Architecture Preflight for Issue #148.
- Required base: `7f7014d06ebb9b71c3b24bc559fdd4bd61a625f3`.
- Documentation only.
- No production implementation is authorized by this document.
- Candidate Definition-of-Ready result: **supported, subject to independent fixed-head approval**.

## 1. Problem and user objective

AQuantAI already persists one exact Stage 2 company-research identity and its downstream v0.6A-v0.6D research records, but the current product surfaces do not provide one coherent single-company reading workspace.

The user objective is:

> Explicitly select one persisted `company_research_id` and read, at one optional cutoff, its frozen Stage 1 background, financial-transmission hypotheses, expectations, valuation observations, catalysts, risks, quality judgments, conflicts, missing evidence and revision chronology without turning the result into ranking, scoring, price attractiveness or investment advice.

This is a Product Task candidate only because the useful path is reachable from existing accepted read contracts and requires no new data meaning or persistent state.

## 2. Current-state findings

### 2.1 Existing product surfaces

The repository currently contains:

- Evidence Intelligence / Research Change Feed;
- Industry Beneficiary Workspace v1;
- existing owning-domain Industry Alpha APIs for Stage 1 and Stage 2 detail reads.

The required consolidation review concluded that no generic workspace framework or production consolidation refactor is justified. Company Research must therefore use a domain-specific product repository/query boundary while preserving owning-domain serializers and detail semantics.

### 2.2 Existing Stage 2 list-service shape

The following services list identities and then load one complete graph per identity:

- `Stage2CompanyResearchQueryService.list_research()`;
- `Stage2ExpectationQueryService.list_expectations()`;
- `Stage2ValuationQueryService.list_valuations()`;
- `Stage2CatalystQueryService.list_catalysts()`;
- `Stage2RiskQueryService.list_risks()`;
- `Stage2IndustryJudgmentQueryService.list_judgments()`;
- `Stage2CompanyJudgmentQueryService.list_judgments()`.

That behavior remains valid for the existing owning-domain APIs, but composing these services would create query growth proportional to the number of records. They are therefore prohibited as the initial product overview implementation path.

### 2.3 Exact input reachability

One persisted `Stage2CompanyResearch` row already owns exact foreign keys to:

- case and map identity;
- candidate pool and candidate pool revision;
- candidate pool membership;
- Stage 1 beneficiary and beneficiary revision;
- selected map revision;
- stock basic record;
- source and stock code;
- exact Stage 1 handoff assertion, claim and evidence links.

The same `company_research_id` is stored on:

- financial hypotheses;
- market expectations;
- valuation snapshots;
- catalyst assessments;
- risk assessments;
- industry judgments;
- company judgments.

Downstream revisions freeze an exact `company_research_revision_id` and, where applicable, exact hypothesis, expectation, valuation, catalyst and risk revision IDs. Existing claims, claim revisions, claim-evidence links and evidence rows provide the evidence/conflict/missing-evidence path.

Therefore, no stock-code matching, company-name matching, Provider-industry matching, text similarity, LLM inference or revision compatibility heuristic is needed or allowed.

## 3. Accepted identity contract

### 3.1 Primary identity

`company_research_id` is the only primary workspace identity.

### 3.2 Selection

- Selection is explicit.
- The page initially shows the selector and boundary notice without selecting the first row.
- A URL may carry an explicit `company_research_id`, but absence of the parameter is not replaced by a default.
- `map_id`, stock code, source and Stage 1 IDs are display/filter context only.

### 3.3 No inference or fallback

The system must not:

- infer identity from stock code or name;
- select the newest research identity for the same stock;
- relink a downstream record to a newer research revision;
- use Provider industry, free text, title similarity or LLM output as a join;
- silently fall back to another company research identity.

## 4. Accepted product routes

### 4.1 Page

`GET /company-research`

Serves the Chinese-first read-only workspace page.

### 4.2 Selector API

`GET /company-research/research?as_of_cutoff=YYYY-MM-DD`

Returns lightweight selector rows only.

### 4.3 Workspace API

`GET /company-research/research/{company_research_id}/workspace?as_of_cutoff=YYYY-MM-DD`

Returns one bounded cross-domain overview for the explicitly selected identity.

### 4.4 Existing explicit detail APIs

Full owning-domain graphs remain available only after explicit user action through existing routes:

- `/industry-alpha/company-research/{company_research_id}`;
- `/industry-alpha/market-expectations/{expectation_id}`;
- `/industry-alpha/valuation-snapshots/{valuation_id}`;
- `/industry-alpha/catalyst-assessments/{catalyst_id}`;
- `/industry-alpha/risk-assessments/{risk_id}`;
- `/industry-alpha/industry-judgments/{judgment_id}`;
- `/industry-alpha/company-judgments/{judgment_id}`.

The initial workspace must not call these routes once per row.

## 5. Selector response contract

The selector response contains:

```text
as_of_cutoff
research[]
  company_research_id
  case_id
  map_id
  source
  stock_code
  created_at_utc
  frozen_stage1
    candidate_pool_id
    candidate_pool_revision_id
    candidate_pool_membership_id
    beneficiary_id
    beneficiary_revision_id
    selected_map_revision_id
    stock_basic_record_id
  latest_revision
    revision_id
    revision_no
    workflow_state
    conclusion_status
    research_question
    summary
    information_cutoff_date
    recorded_at_utc
  availability
    hypothesis_count
    expectation_count
    valuation_count
    catalyst_count
    risk_count
    industry_judgment_count
    company_judgment_count
notices
```

Rules:

- counts are deterministic D1 availability counts over cutoff-visible persisted identities/revisions;
- counts are not scores and must not influence ordering;
- no full claim/evidence graph appears in selector rows;
- rows sort by `source`, `stock_code`, `company_research_id`;
- UI wording uses `排序`, never `排名`.

## 6. Workspace response contract

The selected workspace response contains the following top-level sections.

### 6.1 Identity

- `company_research_id`;
- `case_id`;
- `map_id`;
- `source`;
- `stock_code`;
- `created_at_utc`;
- requested `as_of_cutoff`.

### 6.2 Frozen Stage 1 provenance

Exact persisted IDs and display summaries for:

- candidate pool;
- candidate pool revision;
- membership;
- beneficiary;
- beneficiary revision;
- selected map revision;
- stock basic row;
- ingestion run;
- handoff assertion/claim/evidence link counts and IDs.

Required provenance is fail-closed. Missing required frozen rows do not degrade to guessed context.

### 6.3 Company research

- latest cutoff-visible revision raw fields;
- revision chronology summaries;
- verification item summaries/counts;
- hypothesis identity/latest-revision summaries;
- IDs required for explicit detail reads.

### 6.4 Expectations

For each identity:

- `expectation_id` and `expectation_key`;
- latest cutoff-visible revision ID/no;
- exact frozen `company_research_revision_id`;
- subject, period horizon, expectation kind, direction, status, confidence and basis;
- information cutoff and recorded UTC;
- frozen hypothesis revision IDs;
- conflict, missing-evidence and evidence-grade counts;
- historical mismatch flag;
- detail route.

### 6.5 Valuation observations

For each identity:

- `valuation_id` and `valuation_key`;
- latest cutoff-visible revision ID/no;
- exact frozen `company_research_revision_id`;
- valuation method, metric context, `observed_value`, missing-data reason, unit, currency, comparison basis, assumptions, status and confidence;
- information cutoff and recorded UTC;
- optional exact local daily-price row/run provenance summary;
- frozen hypothesis revision IDs;
- conflict, missing-evidence and evidence-grade counts;
- historical mismatch flag;
- detail route.

The section title and notices must say “估值观察” rather than “估值结论”.

### 6.6 Catalysts and risks

Catalyst summaries preserve:

- category, subject, status, confidence, basis, uncertainty;
- expected observation window and trigger observation criteria;
- exact frozen research/hypothesis/expectation/valuation revision IDs.

Risk summaries preserve:

- category, subject, status, confidence, basis, uncertainty;
- downside path, thesis invalidation condition and mitigants;
- exact frozen research/hypothesis/expectation/valuation revision IDs.

Neither section is a monitor, alert, timing model or recommendation.

### 6.7 Industry and company judgments

Industry judgment summaries preserve:

- outcome, evidence state, confidence, decision criteria, rationale, uncertainty and follow-up verification;
- driver durability, value-pool direction and chain-bottleneck support;
- exact frozen research and downstream revision links.

Company judgment summaries preserve:

- outcome, evidence state, confidence, decision criteria, rationale, uncertainty and follow-up verification;
- beneficiary credibility, financial-transmission credibility and execution risks;
- exact frozen research and downstream revision links.

These remain D3 analytical judgments and must be visually separated from facts and D1 counts.

### 6.8 Conflicts, missing evidence and chronology

The overview returns bounded summaries rather than every evidence body:

- per-module conflict count;
- per-module missing-evidence count;
- evidence-grade counts A/B/C/D;
- affected claim keys and exact claim/evidence IDs where available;
- revision chronology summaries;
- latest-visible research revision ID;
- each module's frozen research revision ID;
- explicit `historical_revision_mismatch` boolean.

A mismatch is historical information, not an error and not an invitation to relink automatically.

## 7. Overview/detail boundary

### Initial workspace may include

- identities and exact persisted IDs;
- latest visible raw revision fields;
- revision chronology summaries;
- counts and small conflict/missing summaries;
- frozen revision IDs;
- mismatch flags;
- detail links.

### Initial workspace must not include

- every full claim/evidence payload for every module item;
- full evidence source bodies;
- one owning-domain detail call per item;
- inferred combined conclusions;
- cross-company comparisons.

Full graphs load only after an explicit user action on one selected item.

## 8. Query architecture

### 8.1 New domain-specific boundary

A later Product Task should add:

- `CompanyResearchWorkspaceRepository`;
- `CompanyResearchWorkspaceQueryService`;
- dedicated contracts;
- dedicated API router and static page.

It must not create a generic workspace framework.

### 8.2 Selector budget

Maximum: **3 SQL statements**.

Candidate statement groups:

1. joined scalar projection for company research identity and exact frozen Stage 1/stock provenance;
2. all cutoff-visible company research revisions for the selected identity set, reduced deterministically to latest per identity in application code;
3. one unioned/scalar module-availability projection covering hypotheses, expectations, valuations, catalysts, risks and both judgment kinds.

No selector row may trigger a full graph load.

### 8.3 Selected workspace budget

Maximum: **24 SQL statements**, independent of row count.

Candidate fixed projection groups:

1. root identity plus required Stage 1/stock/run provenance;
2. company research revisions;
3. verification items;
4. financial hypothesis identities and revisions;
5. research-to-hypothesis and Stage 1 handoff links;
6. expectation identities and revisions;
7. valuation identities and revisions;
8. optional referenced daily-price rows and ingestion runs;
9. catalyst identities and revisions;
10. risk identities and revisions;
11. industry judgment identities and revisions;
12. company judgment identities and revisions;
13. all hypothesis/expectation/valuation cross-links;
14. all catalyst/risk cross-links;
15. all judgment cross-links;
16. all selected module claim links;
17. referenced claim identities and revisions;
18. selected module evidence boundary links;
19. referenced source claim-evidence links;
20. referenced evidence rows;
21. Stage 1 beneficiary assertion links;
22. referenced node/relationship/observation revisions;
23. deterministic integrity/duplicate projection if needed;
24. reserved fixed statement for an implementation-proven missing scalar family.

An implementation may combine groups and use fewer statements. It may not exceed 24. The implementation task must record the exact final count, and tests must prove that adding module identities, revisions, links, claims or evidence rows does not increase it.

### 8.4 Prohibited composition

The product repository/query must not call existing list/get services in a loop. Existing domain query services remain available for explicit detail only.

## 9. Cutoff, chronology and revision rules

### Identity visibility

A company research or module identity is visible only when its `created_at_utc` is visible at the requested cutoff.

### Revision visibility

A revision is visible only when:

- `information_cutoff_date <= as_of_cutoff`; and
- stored `recorded_at_utc` date is `<= as_of_cutoff`.

With no cutoff, all persisted chronology remains eligible under existing rules.

### Latest revision

Latest means the last cutoff-visible persisted revision under deterministic `(revision_no, revision_id)` ordering. It does not mean latest wall-clock record outside the cutoff.

### Frozen historical relations

Every downstream latest summary exposes its exact `company_research_revision_id`. If it differs from the workspace latest visible research revision, the UI shows both IDs and `历史修订不一致`, without repair or fallback.

### Supersession

Revision number, revision ID, supersedes revision ID, information cutoff and recorded UTC remain visible in chronology.

## 10. Field ownership and semantic qualification

| Display family | Owner | Derivation | Semantic qualification | Presentation rule |
| --- | --- | --- | --- | --- |
| persisted IDs, revision numbers, cutoff dates, UTC timestamps | owning persistence model | D0 | not price-semantic | show exact raw values |
| source, stock code and provider-normalized stock row | market-data persistence | D0 | L1 where Provider-normalized | source/provenance visible |
| optional daily-price row | market-data persistence | D0 observation | L1 unless a later contract proves otherwise | context only, never canonical |
| Stage 1 beneficiary class and assertion relationship | v0.5C / Stage 1 | D2 | non-price | show raw classification and rule/provenance context |
| evidence grade and relation | evidence ledger | D2 classification over D0 evidence metadata | non-price | do not present as certainty score |
| module availability/conflict/missing counts | product read model | D1 | inherits bounded inputs | disclose input scope and cutoff |
| company research summary and financial hypotheses | v0.6A | D3 | non-price | research judgment, not fact |
| expectations | v0.6B | D3 | non-price | expectation context, not forecast promise |
| valuation observations | v0.6B | D3 with optional L1 price context | not comparison eligible | label as observations only |
| catalysts and risks | v0.6C | D3 | non-price | not alerts, timing or tasks |
| industry/company quality judgments | v0.6D | D3 | non-price | separate judgment section |

No UI label, non-null field, count or cross-domain display may upgrade Semantic Level or Derivation Level.

## 11. Price and investment-attractiveness boundary

The workspace may display exact stored valuation observation fields and optional local price provenance.

It must not calculate, infer, label or imply:

- canonical current price;
- Comparison Eligibility;
- comparable valuation multiple;
- computed expectation gap;
- fair value;
- target price;
- expected return;
- upside/downside;
- good price;
- good timing;
- buy/sell/hold;
- investment attractiveness score;
- research-priority ranking.

Currency and unit presence do not create comparability. A linked daily-price row remains local provenance/context.

## 12. Deterministic ordering

- selector: source, stock code, company research UUID;
- research revisions: revision number, revision UUID;
- module identities: stored key, identity UUID;
- module revisions: revision number, revision UUID;
- frozen revision IDs: lexical UUID order unless owning semantics specify another accepted order;
- evidence summaries: relation, evidence grade, information date, evidence UUID;
- conflicts: module kind, claim key, claim revision UUID, evidence UUID;
- missing evidence: module kind, claim key, claim revision UUID.

No sort order is described as ranking or opportunity priority.

## 13. Golden path

1. User opens `/company-research`.
2. Page displays the read-only/non-advisory boundary and no selected company.
3. Page requests selector rows with the optional cutoff.
4. User explicitly selects one `company_research_id`.
5. Page requests the selected workspace using the same cutoff.
6. API verifies root identity visibility and required frozen Stage 1 provenance.
7. Repository executes the fixed statement set and returns cutoff-visible scalar projections.
8. Query service deterministically assembles summaries, counts, chronology and mismatch flags.
9. UI displays raw stored categories and separates D0/D1/D2/D3 sections.
10. User may explicitly open one existing owning-domain detail route for a full claim/evidence graph.

## 14. Failure and empty-state contracts

### 422

FastAPI validation handles malformed UUID and malformed date input.

### 404

Return 404 for:

- missing `company_research_id`;
- root identity created after the requested cutoff;
- root identity with no visible company research revision at the cutoff.

### 503

Return credential-safe 503 for:

- database configuration unavailable;
- schema/migration unavailable;
- SQLAlchemy/database failure;
- required frozen Stage 1 row missing;
- dangling required exact revision/link/evidence relation;
- incompatible duplicate exact relation;
- repository integrity failure.

Do not return raw database URLs, credentials or exception details.

### Valid empty/unavailable state

The following are optional and may be empty:

- expectations;
- valuations;
- catalysts;
- risks;
- industry judgments;
- company judgments;
- verification items;
- conflicts;
- missing-evidence entries.

Empty does not trigger fallback, fabricated content or automatic discovery.

### External network

Imports, startup, tests, fixture demos, selector reads, workspace reads and detail navigation perform no hidden external network access.

## 15. Presentation contract

The page is Chinese-first and read-only.

Required sections:

1. company research selector;
2. cutoff control;
3. identity and frozen Stage 1 provenance;
4. company research summary and chronology;
5. financial-transmission hypotheses;
6. market expectations;
7. valuation observations;
8. catalysts;
9. risks;
10. industry judgments;
11. company judgments;
12. conflicts and missing evidence;
13. historical revision mismatch notice;
14. boundary notice.

Safety and accessibility:

- use DOM `textContent` for untrusted values;
- do not use untrusted `innerHTML`;
- keyboard-operable selector and details;
- visible loading, empty and error states;
- no red/green buy/sell signal language;
- no score-like progress bars or opportunity badges;
- raw stored categorical values remain visible beside any Chinese explanation.

## 16. Migration, dependency and consolidation decision

Accepted:

- no schema;
- no migration;
- no Provider change;
- no dependency change;
- no release or version change;
- no new persistent state;
- no generic workspace framework;
- no production consolidation refactor;
- no change to existing Stage 2 owning-domain APIs.

## 17. Candidate implementation slice

A later Product Task may be limited to:

### New files

- `industry_alpha/company_research_workspace_contracts.py`
- `industry_alpha/company_research_workspace_repository.py`
- `industry_alpha/company_research_workspace_query.py`
- `backend/api/company_research.py`
- `company_research/static/company_research.html`
- `company_research/static/company_research.css`
- `company_research/static/company_research.js`
- `tests/test_company_research_workspace_repository.py`
- `tests/test_company_research_workspace_query.py`
- `tests/test_company_research_api.py`
- matching implementation task snapshot

### Modified file

- `backend/main.py` only for router/static registration and page serving.

No other file is presumed authorized. The implementation Issue must repeat the exact allowed list.

## 18. Required implementation tests

### Repository

- exact root identity and required provenance;
- selector statement count at most 3;
- workspace statement count at most 24;
- constant count after adding multiple records to every module;
- no existing list/get service composition;
- deterministic scalar ordering;
- dangling/duplicate integrity failure.

### Query

- cutoff and UTC visibility;
- latest visible revision selection;
- frozen historical mismatch visibility;
- raw field preservation;
- D1 counts from exact visible input scope;
- valid absent-module states;
- conflict/missing aggregation;
- strict JSON and deterministic ordering;
- no price/comparison/recommendation fields.

### API

- page and static registration;
- selector and workspace success;
- no silent default;
- malformed UUID/date 422;
- missing/cutoff-invisible 404;
- safe 503;
- no credential leakage.

### UI

- explicit selection required;
- cutoff carried consistently;
- safe `textContent` rendering;
- no untrusted `innerHTML`;
- keyboard and accessible status behavior;
- raw category labels and boundary notices;
- explicit detail navigation only.

### Regression

- PostgreSQL 16 CI;
- complete pytest suite;
- local fixture demo;
- no external network.

## 19. Locked exclusions

The v1 implementation must not include:

- Canonical Price;
- Comparison Eligibility;
- expectation-gap computation;
- fair value or target price;
- expected return or upside/downside;
- cross-company comparison/ranking;
- total score or recommendation;
- buy/sell/hold;
- good-price/good-timing state;
- Watchlist, alerts, reminders or tasks;
- portfolio, paper trading or execution;
- automatic company discovery;
- new beneficiary taxonomy or typed roadmap fields;
- inferred/fallback identity;
- automatic revision relinking;
- schema, migration, Provider, dependency, release or version changes.

## 20. Stop conditions

Do not recommend implementation if review finds that the useful path requires:

- inferred identity;
- silent fallback;
- changed Stage 2 field meaning;
- changed revision/cutoff/provenance rules;
- schema/migration;
- live network or new Provider;
- canonical/comparison-eligible price;
- scoring/ranking/recommendation state;
- query growth proportional to records.

## 21. Definition-of-Ready assessment

The preflight finds that:

- one explicit user objective exists;
- one exact identity exists;
- all required v0.6A-v0.6D modules are reachable through persisted foreign keys;
- a useful overview can be built from bounded scalar projections;
- full graphs can remain explicit owning-domain detail reads;
- chronology and frozen historical mismatches can remain visible;
- no schema, migration, Provider, dependency or persistent state is required;
- price attractiveness, comparison, ranking and recommendation semantics remain excluded;
- a bounded implementation and test file list can be stated.

Therefore, Company Research Workspace v1 is a **Definition-of-Ready candidate** for one later read-only Product Task, provided an independent reviewer approves this exact preflight HEAD.

## 22. Review gate

The preflight PR must remain Draft/Open/unmerged until independent review records:

`DEFINITION OF READY APPROVED at fixed head <HEAD_SHA>`

No implementation Issue, production code, ready-for-review transition, merge or Issue closure is authorized before that approval and explicit owner authorization.