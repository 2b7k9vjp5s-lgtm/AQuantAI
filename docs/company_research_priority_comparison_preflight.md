# Company Research Priority Comparison v1 Architecture Preflight

## Status and authority

- Authority: Issue #171.
- Related roadmap: Issue #137, Slice 3.
- Required base: `1c176994320bda72f57805676d5e39d48d45d057`.
- Predecessor capability: Typed Beneficiary Evidence Semantics v1, PR #165 and PR #169.
- Risk tier: Strict because the roadmap phase concerns comparison, scoring, ranking, valuation and investment-decision semantics.
- Work type: Architecture Preflight and Definition of Ready, documentation only.
- Released version remains `0.2.0`.
- This document authorizes no production code, API/UI behavior, schema, migration, Provider, dependency, fixture, test, release or version change.

## Executive decision

The broad idea of a “research-priority comparison” is narrowed for v1 to a **component-only Company Research Comparison Matrix**.

The first implementable slice may:

1. select one exact persisted `Stage1CandidatePoolRevision`;
2. display every exact membership in that unranked frozen universe;
3. attach only deterministic, cutoff-visible and recorded-time-visible existing Stage 1, Typed Beneficiary and Company Research components;
4. preserve missing, disputed, stale, conflicting and not-applicable states;
5. use neutral deterministic ordering;
6. link to existing per-company detail on explicit action.

The first slice must not:

- calculate a total score;
- create a research-priority rank or order;
- classify price attractiveness;
- compare valuation numbers as if they were canonical;
- create a recommendation, target price or expected return;
- hide companies that lack Typed Semantics or Company Research.

Because the accepted v1 contains no schema, migration, network, AI transmission, ranking, scoring, recommendation or valuation-comparison behavior, its later implementation may use the **Standard** workflow after this Strict architecture gate is independently approved and the owner explicitly advances it.

Any later D2 score, ranking, categorical priority label, price comparison or recommendation-like output remains a new Strict task.

## One-sentence user job

For one explicit persisted candidate-pool revision and explicit as-of boundaries, review every company in that exact unranked universe side by side across accepted industry-benefit, typed execution-evidence and company-research components, while retaining complete membership visibility and avoiding unexplained totals or investment advice.

## Why the candidate-pool revision is the selector

`Stage1CandidatePoolRevision` is the only existing cross-company object that freezes an exact, unranked set of Stage 1 beneficiary revisions.

It owns:

- one exact candidate-pool identity;
- one exact selected Industry Map revision;
- title and scope text;
- information cutoff date;
- recorded UTC;
- append-only supersession history;
- exact membership rows.

Each `Stage1CandidatePoolMembership` freezes:

- exact candidate-pool revision;
- exact beneficiary identity;
- exact beneficiary revision.

`Stage2CompanyResearch` is uniquely keyed by the exact candidate-pool revision and exact candidate-pool membership. Therefore, at most one Company Research identity can attach to one comparison row without first/latest guessing.

The selected pool is the **complete persisted comparison universe for that exact pool revision**. It is not claimed to be the complete listed market, complete industry, or a Provider-discovered universe. The UI must show the pool title, scope, map revision, cutoff, recorded UTC and member count prominently.

## Explicit comparison selector

A request requires all three values:

1. `candidate_pool_revision_id` — exact frozen universe;
2. `as_of_cutoff` — maximum information cutoff date visible to the comparison;
3. `as_of_recorded_at_utc` — maximum recorded UTC visible to the comparison.

No current-time, latest-record, first-row or default-pool selection is allowed.

Rules:

- `as_of_cutoff` must be on or after the candidate-pool revision cutoff;
- `as_of_recorded_at_utc` must be on or after the candidate-pool revision recorded UTC;
- both values are echoed in the response and page;
- omission or invalid chronology fails before any component projection;
- future records outside either boundary are excluded and may produce a neutral “newer revision not visible” notice without exposing their content.

## Frozen universe and neutral ordering

Every membership of the selected candidate-pool revision appears exactly once.

Rows are ordered by:

1. `source` ascending;
2. `stock_code` ascending;
3. `beneficiary_id` ascending as a deterministic tie-breaker.

This ordering has no investment meaning. The page must label it as neutral identifier ordering.

The initial v1 offers no sort by evidence state, exposure, confidence, catalyst, risk, valuation or judgment because such sorting can imply priority even without a score.

## Exact row identity

Each row carries:

- candidate-pool revision ID;
- candidate-pool membership ID;
- beneficiary ID;
- exact frozen beneficiary revision ID;
- selected map revision ID;
- source and stock code;
- stock-basic record provenance;
- pool cutoff and recorded UTC;
- comparison cutoff and recorded UTC.

Rows never infer identity from company name, title, Provider industry, security-code prefix or free text.

## Deterministic Company Research attachment

A Company Research identity may attach only when all of the following hold:

- `candidate_pool_revision_id` equals the selected pool revision;
- `candidate_pool_membership_id` equals the exact row membership;
- `beneficiary_id` equals the membership beneficiary;
- `beneficiary_revision_id` equals the exact membership beneficiary revision;
- `selected_map_revision_id` equals the pool selected map revision;
- identity creation time is not later than `as_of_recorded_at_utc`.

The existing unique constraint on `(candidate_pool_revision_id, candidate_pool_membership_id)` makes attachment deterministic.

If no visible identity exists, the row remains visible with `company_research_state = missing`.

If an impossible duplicate, identity mismatch or frozen-boundary mismatch is observed, the whole comparison fails closed as an integrity error; it does not choose one row.

## Company Research revision visibility

For an attached Company Research identity, the comparison selects the highest revision number satisfying both:

- `information_cutoff_date <= as_of_cutoff`;
- `recorded_at_utc <= as_of_recorded_at_utc`.

No visible revision produces `research_revision_state = missing_at_as_of` while retaining the row and identity provenance.

Later revisions remain hidden. A boolean notice may state that newer history exists only when this can be determined without loading or exposing later content.

All v0.6A-v0.6D children use the same two-boundary visibility rule and retain their exact owning IDs and revision IDs.

## Typed Beneficiary semantic attachment

Typed semantics attach only through the exact row beneficiary identity and frozen beneficiary revision.

The selected semantic profile revision must:

- belong to the exact beneficiary identity;
- freeze the exact membership beneficiary revision;
- freeze the same selected map revision;
- use taxonomy version `aquantai.typed-beneficiary-evidence-semantics.v1`;
- satisfy both comparison as-of boundaries.

If multiple visible semantic revisions exist, select the highest revision number within that exact frozen beneficiary-revision lineage.

A semantic revision for a newer or different beneficiary revision must not be silently attached. The row displays `typed_semantics_state = historical_mismatch` or `missing`, without leaking the mismatched revision’s values.

Legacy Stage 1 `direct / secondary / potential` and Typed Semantic `direct / conditional / indirect / conceptual` remain separate columns and may disagree.

## Component matrix contract

The initial matrix presents accepted stored state without collapsing it into a total.

### Universe and Stage 1

- source and stock code;
- exact beneficiary revision;
- legacy beneficiary kind;
- legacy assessment status;
- pool and map provenance.

### Typed Beneficiary Semantics

- exposure state and evidence state;
- driver type/subtype and evidence state;
- offering state;
- customer state;
- certification state;
- capacity state;
- production state;
- order state;
- profile overall status;
- explicit missing/disputed/not-applicable notices.

The matrix may compact repeated assertions into safe text chips but cannot invent a “best”, “worst” or combined state.

### Company Research v0.6A

- Company Research presence;
- workflow state;
- conclusion status;
- exact research revision and cutoff;
- financial-hypothesis rows as a compact list of exact status, direction and confidence values.

No hypothesis count or confidence total may be styled as attractiveness.

### Expectations and valuation observations v0.6B

- expectation rows: exact subject, direction, status and confidence;
- valuation context: exact method, status and presence only;
- numeric observed values remain accessible in explicit per-company detail but are not placed in cross-company sortable or normalized columns;
- a linked daily-price row remains L1 context, not Canonical Price.

The matrix must not calculate expectation gap, valuation multiple comparison, price demandingness, fair value, target price or expected return.

### Catalysts and risks v0.6C

- exact catalyst state and timing text where already stored;
- exact risk state, likelihood/impact text and falsification conditions where already stored;
- no net catalyst-minus-risk score;
- no timing signal or alert state.

### Industry and company judgments v0.6D

- exact stored judgment status, evidence state and analyst text;
- industry judgment and company judgment remain separate;
- no conversion to a numeric priority or recommendation.

### Evidence, conflict and freshness

The initial matrix shows only bounded summary state already owned by the source domains:

- accepted / disputed / missing / not-applicable;
- exact selected revision and cutoff;
- newer-history notice;
- conflict or verification-required notice.

Full claim/evidence graphs load only after explicit user action through existing owning-domain detail boundaries.

Evidence count, recency and document volume must not be colored or ordered as investment attractiveness.

## Derivation-level contract

The initial comparison contains no new D2 or D3 comparison result.

- exact stored facts and revisions remain D0 where applicable;
- deterministic row assembly and neutral ordering are D1 presentation mechanics;
- existing Typed Semantic values remain accepted analyst-owned D3 judgments;
- existing Stage 2 judgments retain their owning derivation level;
- the matrix itself does not promote or reinterpret any value.

A future categorical priority label, score or ranking requires a new Strict architecture task with explicit D2 rules or explicit persisted D3 ownership.

## Missing, disputed, stale and not-applicable behavior

Each row has independent component availability states.

Exact response states include:

- `available`;
- `missing`;
- `missing_at_as_of`;
- `historical_mismatch`;
- `disputed`;
- `not_applicable`;
- `newer_revision_not_visible` as a notice, not a component value.

Rules:

- missing Typed Semantics does not remove the row;
- missing Company Research does not remove the row;
- missing child domains do not remove Company Research identity;
- disputed and not-applicable are never collapsed into missing;
- stale/newer-history notices do not expose later content;
- no missing state is converted into zero, neutral score or lowest rank.

## Query architecture

The initial comparison uses one product-local repository/query boundary and a fixed maximum of **14 SQL statements**, independent of member count.

Candidate statement families:

1. candidate-pool revision, pool, map and case header;
2. all memberships, exact beneficiary revisions and stock rows;
3. Company Research identities by exact membership;
4. visible Company Research revisions;
5. visible Typed Semantic profile revisions;
6. Typed Semantic assertions and verification state;
7. visible financial-hypothesis revisions;
8. visible expectation revisions;
9. visible valuation-context revisions;
10. visible catalyst revisions;
11. visible risk revisions;
12. visible industry-judgment revisions;
13. visible company-judgment revisions;
14. bounded conflict/missing/freshness summary links needed by the matrix.

Requirements:

- no per-row query loop;
- no composition of the existing 14-SQL Company Research workspace per company;
- no initial full claim/evidence graph loading;
- query-count tests must prove the bound with one member and many members;
- repository rows remain scalar and product-local;
- no generic comparison or workspace framework is justified.

The implementation may use fewer statements but may not exceed the reviewed maximum without a new review.

## Candidate API and page

Candidate read-only API:

`GET /company-comparison/candidate-pool-revisions/{candidate_pool_revision_id}`

Required query parameters:

- `as_of_cutoff=YYYY-MM-DD`;
- `as_of_recorded_at_utc=<RFC3339 UTC>`.

Candidate page:

`/company-comparison`

Page behavior:

- no silent default pool;
- explicit selector and as-of inputs;
- initial result shows every pool member;
- neutral identifier ordering only;
- no score/rank column;
- full detail loads on explicit action;
- safe DOM methods and no untrusted `innerHTML`;
- accessible loading, empty, partial-data and error states;
- Chinese-first labels with technical IDs/revisions available on demand.

## No schema or migration

The accepted v1 is a read-only projection over existing accepted tables.

- no new persistent comparison identity;
- no comparison snapshot table;
- no score, rank, category or review-state table;
- no migration;
- rollback is removal of the product-local route, query and static surface;
- accepted Stage 1, Typed Semantic and Stage 2 history remains unchanged.

Persisted comparison snapshots, analyst priority state or rule-classification history would require a new Strict architecture task and migration decision.

## Production-realistic offline golden path

Fixture setup uses existing production-reachable contracts:

1. one Industry Map and exact map revision;
2. one Stage 1 candidate-pool revision with three exact memberships;
3. member A has exact Typed Semantics and complete v0.6A-v0.6D Company Research;
4. member B has legacy Stage 1 plus Typed Semantics but no Company Research;
5. member C has legacy Stage 1 and Company Research but no exact Typed Semantic profile for the frozen beneficiary revision;
6. explicit `as_of_cutoff` and `as_of_recorded_at_utc` include selected records and exclude later revisions;
7. the API returns all three members in neutral order;
8. A shows all accepted components;
9. B shows Company Research missing without being removed;
10. C shows Typed Semantics missing or historical mismatch without attaching newer data;
11. no score, rank, recommendation or cross-company valuation calculation appears;
12. full evidence/company detail remains an explicit secondary action.

The golden path performs no network access and uses no fields unavailable to production.

## Most important fail-closed path

A request points to an exact candidate-pool revision, but one Company Research identity or Typed Semantic revision does not match the membership’s frozen beneficiary/map boundary.

Required behavior:

- stop the comparison projection;
- return a typed integrity failure;
- identify only safe object IDs and boundary type;
- do not choose a compatible-looking row;
- do not return a partial comparison that could hide the integrity problem;
- perform no network or mutation.

Other typed failures include invalid as-of chronology, unknown pool revision, empty pool, unsupported taxonomy version and query-bound violation in tests.

## Candidate implementation risk and file families

After architecture approval and owner authorization, the component-only implementation may be classified **Standard** because it adds read-only behavior over accepted models and excludes every Strict trigger.

Candidate file families:

- `company_comparison/` contracts, repository, query and static assets;
- one read-only backend API module and minimal router/page registration;
- focused tests for selector, exact membership, revision visibility, missing/mismatch behavior, fixed query count, API and safe UI;
- optional local fixture extension using existing production-reachable commands.

No model, migration, dependency, Provider, Guarded AI, release or version file is authorized for the candidate implementation.

## Required tests for a later implementation

- exact pool selector and no default selection;
- complete membership preservation with missing components;
- exact Stage 2 attachment through candidate-pool membership;
- exact Typed Semantic beneficiary-revision match;
- cutoff and recorded-UTC visibility;
- later-information exclusion;
- deterministic neutral ordering;
- fixed query count with row growth;
- no initial full evidence N+1;
- valuation numbers not used in cross-company comparison;
- no score, rank, recommendation or prohibited wording;
- safe DOM and explicit detail action;
- no network;
- full relevant regression and offline golden path.

## Locked exclusions

- no computed total, score, rank or research-priority ordering;
- no categorical “high priority” label in v1;
- no Canonical Price or Comparison Eligibility implementation;
- no expectation-gap or valuation-attractiveness calculation;
- no fair value, target price, expected return, upside/downside or buy/sell/hold;
- no evidence ingestion, crawling, scraping, browsing or external search;
- no AI-owned comparison or accepted state;
- no monitoring, alerts, tasks, portfolio or trading;
- no generic comparison, rule-engine, agent, RAG, vector or Provider framework;
- no schema, migration, dependency, release or version change.

## Stop conditions

Stop without implementation authorization if:

- exact candidate-pool membership cannot serve as the complete bounded universe;
- Company Research attachment requires name/code/text matching or first/latest guessing;
- Typed Semantics cannot be matched to the exact frozen beneficiary revision;
- as-of visibility cannot prevent later-information leakage;
- initial comparison requires per-company Company Research workspace queries;
- numeric valuation comparison cannot be excluded from v1;
- the UI cannot preserve every member while showing missing data;
- the output would imply investment priority, recommendation or price attractiveness;
- more than one new infrastructure boundary is required.

## Definition of Ready finding

Company Research Priority Comparison v1 reaches Definition of Ready only as the narrowed **component-only comparison matrix** described above.

The architecture explicitly rejects a score, ranking, categorical priority label, valuation comparison or recommendation for the first slice.

Keep the architecture PR Draft/Open/unmerged pending:

1. exact two-file inventory verification;
2. GitHub Actions success at one fixed head;
3. author-side architecture review;
4. independent fixed-head architecture approval;
5. explicit owner authorization before any implementation Issue or merge.

Required approval text:

`COMPANY RESEARCH PRIORITY COMPARISON PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`
