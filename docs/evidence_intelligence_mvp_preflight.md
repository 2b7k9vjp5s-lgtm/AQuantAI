# Evidence Intelligence MVP Architecture Preflight

## Status and authority

- Authority: Issue #134.
- Base branch: `main`.
- Work type: Architecture Preflight, documentation only.
- Released version remains `0.2.0`.
- Merged capability remains v0.6D.
- No production code, API, UI, test, fixture, schema, migration, Provider, release or version change is authorized by this document.

## Product direction incorporated

AQuantAI will evolve toward one integrated research workflow:

```text
Industry change
  -> industry-chain and bottleneck analysis
  -> beneficiary-company analysis
  -> financial-transmission analysis
  -> expectations / valuation / catalyst / risk review
  -> bounded investment-research priority
```

The system may help a user identify companies that are directly, conditionally, indirectly or only conceptually exposed to an industry change, and may help compare research attractiveness. It must not present those outputs as guaranteed facts, buy/sell advice, target prices, return promises or automatic trading signals.

The user-facing program is therefore split into three governed product slices:

1. Research Change Feed / Evidence Timeline — current first slice.
2. Industry Beneficiary Analysis — later separately authorized slice using existing industry-map, beneficiary, candidate-pool and company-research contracts.
3. Investment Research Analysis — later separately authorized slice using company research, expectations, valuation observations, catalyst, risk and quality judgments, plus future canonical price/comparison eligibility where required.

This preflight authorizes only the definition of slice 1.

## One-sentence user job

When the user opens AQuantAI, they can determine within approximately five minutes which research cases, evidence items, industry maps and company-research records were newly recorded or revised in a bounded recent period, while preserving provenance, cutoff, revision and non-advisory meaning.

## Chosen first vertical slice

### Opening experience

- Page: `GET /evidence-intelligence`
- Read API candidate: `GET /evidence-intelligence/feed`
- Primary question: **What research evidence or accepted research object changed recently, when was the information known, when was it recorded, and where can I inspect the full context?**

### Included record types

The minimum slice includes exactly four event types:

1. `EvidenceItem` creation.
2. `ResearchCaseRevision` creation.
3. `IndustryMapRevision` creation.
4. Stage 2 `CompanyResearchRevision` creation.

### Locked exclusions from the first slice

- Beneficiary ranking or opportunity ranking.
- Investment-attractiveness scoring.
- Buy/sell/hold guidance.
- Target price, expected return or timing judgment.
- New evidence ingestion.
- AI summaries or AI importance ranking.
- Valuation, catalyst, risk and quality-judgment feed events.
- Evidence-addition counts or unresolved-conflict counts.
- Industry-to-company mapping UI.
- New persistent state, schema or migration.
- Canonical price, comparison eligibility or v0.6E.

## Existing-source inventory

| Display object | Existing owner | Existing repository/query boundary | Persisted source | Notes |
| --- | --- | --- | --- | --- |
| Evidence item | v0.5 Evidence Ledger | `industry_alpha.repository.EvidenceLedgerRepository`; `industry_alpha.query.EvidenceLedgerQueryService` | `evidence_items` | Existing fields include evidence grade, source kind/title/locator, information date, recorded UTC, summary and supersession link. |
| Research case revision | v0.5 Evidence Ledger | same owner | `research_case_revisions` | Existing fields include revision number, title, research question, summary, workflow/conclusion state, information cutoff, recorded UTC and superseded revision. |
| Industry map revision | Stage 1 industry map | `industry_alpha.chain_map_repository.IndustryChainMapRepository`; `industry_alpha.chain_map_query.IndustryChainMapQueryService` | `industry_map_revisions` | Existing fields include title, scope, information cutoff, recorded UTC and supersession link. |
| Company research revision | v0.6A | `industry_alpha.stage2_repository.Stage2CompanyResearchRepository`; `industry_alpha.stage2_query.Stage2CompanyResearchQueryService` | existing v0.6A revision tables | Feed must consume accepted repository/query semantics and must not infer beneficiary or investment status. |

The implementation inventory must verify the exact v0.6A model and table names before coding. Failure to identify an existing accepted field is a stop condition, not permission to add a schema field.

## Field qualification matrix

| Feed field | Source owner | Minimum semantic level | Derivation level | Existing / computed | Display rule |
| --- | --- | ---: | ---: | --- | --- |
| `event_type` | feed projection over accepted object kind | L1+ within accepted domain contract | D1 deterministic projection | Computed from explicit selected table/query branch | Neutral labels only: evidence added, case revised, industry map revised, company research revised. |
| `object_id` | domain owner | Existing accepted level | D0 | Existing | Stable UUID, used for detail navigation. |
| `revision_id` | revision-owning domain | Existing accepted level | D0 | Existing where applicable | Null only for EvidenceItem event. |
| `revision_no` | revision-owning domain | Existing accepted level | D0 | Existing where applicable | Never inferred from ordering. |
| `title` | domain owner | Existing accepted level | D0 | Existing | Evidence uses `source_title`; revisions use their accepted title/display field. |
| `summary` | domain owner | Existing accepted level | D0 or existing D3 according to source field | Existing | Must retain source-domain meaning; feed does not rewrite or summarize. |
| `information_date` | Evidence Ledger | Existing accepted level | D0 | Existing for evidence | Display separately from recorded time. |
| `information_cutoff_date` | revision-owning domain | Existing accepted level | D0 | Existing for revisions | Display separately from recorded time. |
| `recorded_at_utc` | domain owner | Existing accepted level | D0 | Existing | Primary feed chronology. |
| `source_kind` | Evidence Ledger | Existing accepted level | D0 | Existing for evidence | No inference for revisions. |
| `evidence_grade` | Evidence Ledger | Existing accepted contract | D2 user-assigned provenance classification | Existing for evidence | Must be labelled as a provenance classification, not truth probability. |
| `source_locator` | Evidence Ledger | Existing accepted level | D0 | Existing for evidence | Render as text/link only under existing safety rules. |
| `detail_path` | API/presentation adapter | N/A | D1 deterministic routing | Computed from explicit event type and ID | Must resolve to an existing accepted detail route or be omitted. |

No field may be promoted to a higher Semantic Level because it is displayed. D2/D3 values must retain explicit labels and may not be presented as D0/D1.

## Query contract

### Scope

The feed is the ordered union of the four included event types visible under the requested cutoff and recorded-time window.

### Required parameters

- `as_of_cutoff`: optional date; existing domain cutoff semantics apply independently to each source.
- `recorded_from`: optional UTC timestamp/date boundary.
- `recorded_to`: optional UTC timestamp/date boundary.
- `event_type`: optional explicit allow-listed filter.
- `limit`: default 50, maximum 100.
- `cursor`: opaque stable pagination cursor.

### Default bounds

- Default recorded window: most recent 7 calendar days relative to an explicit server/request evaluation time.
- Maximum user-selected recorded window: 30 calendar days for the MVP.
- Empty result is valid and must not trigger fallback to older records.

### Ordering

Stable descending order:

1. `recorded_at_utc DESC`
2. explicit event-type order ASC
3. stable event identity UUID DESC or other documented stable UUID text order

The implementation must not use title, stock code, company name or inferred importance as a tie-breaker.

### Deduplication

- One persisted EvidenceItem equals one feed event.
- One persisted revision row equals one feed event.
- No content-based deduplication occurs in the read feed.
- Superseded records remain visible as historical feed events if they fall in the requested bounds.

### Missing values

- Missing optional source locator or summary is displayed as unavailable, not inferred.
- A record missing a required identity, chronology or cutoff field fails closed and is excluded with deterministic diagnostics in tests; implementation must not fabricate values.
- A missing detail route omits the link rather than constructing a guessed route.

### Conflicts

The feed reports change chronology only. It does not resolve evidence conflicts, select a winning claim or label a change positive/negative. Conflict views remain in the owning ledger detail experience.

### Cutoff and chronology

- Existing domain cutoff rules remain authoritative.
- `recorded_at_utc` determines feed ordering.
- `information_date` or `information_cutoff_date` is displayed separately.
- A later-recorded item with an older information date remains later in feed chronology while clearly showing its older information date.

## Non-advisory presentation contract

Allowed wording:

- Evidence added
- Research case revised
- Industry map revised
- Company research revised
- Information date
- Research cutoff
- Recorded time
- Source / provenance
- View full context

Prohibited wording in the first slice:

- Opportunity
- Recommended
- Top pick
- Strong beneficiary
- Positive/negative signal
- Buy/sell/hold
- Good price
- Expected return
- Importance score

Recency, evidence count and revision activity must not be styled as investment attractiveness.

## Domain invariance proof

The later implementation can qualify as a Product Task only if it:

- reads existing accepted records and query semantics;
- creates no table, migration or persistent state;
- does not change Provider behavior;
- does not change cutoff, revision, append-only or provenance rules;
- adds no new classification, score or aggregation contract;
- does not alter v0.5, Stage 1 or v0.6A domain commands;
- does not elevate Semantic Level;
- keeps D2/D3 labels explicit;
- does not introduce fallback or inferred joins.

If a cross-domain read requires a new semantic join, a materialized feed table, a new classification, a new field meaning or a changed repository invariant, the work defaults to an Architecture Task and stops for a new preflight.

## Performance and security

- Use bounded queries and cursor pagination.
- Avoid calling existing full-ledger `list_cases()` per feed row.
- Avoid N+1 graph loading; project only required scalar fields.
- Query each explicit source with a bounded limit, merge deterministically in application code or use a reviewed SQL union that preserves ownership and visibility semantics.
- Do not log source content, connection strings, credentials or raw database exceptions.
- Existing local-user access assumptions remain unchanged; no multi-user authorization is introduced.
- No hidden network request occurs during page load, API read, tests or fixtures.

## Validation matrix

| Layer | Required checks |
| --- | --- |
| Query unit | event projection for all four types; stable ordering; cursor continuation; each time filter; cutoff visibility; empty result; missing optional values; superseded revisions remain visible. |
| Domain invariance | existing append-only, cutoff and repository tests remain unchanged and green. |
| API | parameter validation; maximum limit/window; deterministic JSON; 503 database configuration boundary; no hidden network. |
| Fixture/integration | deterministic mixed-domain fixture containing equal timestamps, different information dates, supersession and one missing optional locator. |
| PostgreSQL | accepted PostgreSQL path if current CI/environment supports it; do not invent a pass count. |
| Presentation | neutral labels, keyboard navigation, responsive layout, empty/error/loading states, no advisory or ranking language. |
| Regression | full existing pytest suite and the existing local research demo. |

## Candidate implementation scope after DoR approval

Candidate new files:

- `industry_alpha/evidence_intelligence_contracts.py`
- `industry_alpha/evidence_intelligence_query.py`
- `backend/api/evidence_intelligence.py`
- `evidence_intelligence/static/evidence_intelligence.html`
- `evidence_intelligence/static/evidence_intelligence.css`
- `evidence_intelligence/static/evidence_intelligence.js`
- `tests/test_evidence_intelligence_query.py`
- `tests/test_evidence_intelligence_api.py`

Candidate modified files:

- `backend/main.py` for router/static-page registration only.
- package discovery/configuration only if required by the existing packaging contract.

Exact file scope must be revalidated against repository state when the implementation Issue is opened.

## Product Task classification

**Candidate classification: Product Task, conditional.**

Evidence:

- all displayed source fields already exist in accepted domains;
- no persistent state is required;
- no Provider, cutoff, revision, provenance or append-only behavior needs to change;
- no score, classification or Semantic Level elevation is required;
- the UI is a read-only projection and navigation experience.

The classification fails and defaults to Architecture Task if the implementation inventory cannot produce the feed without a new cross-domain semantic contract, inferred relationship or schema change.

## Follow-on product roadmap

These items are incorporated into the project direction but are not authorized by Issue #134:

### Slice 2 — Industry Beneficiary Analysis

User job: determine which companies have direct, conditional, indirect or merely conceptual exposure to an industry driver, why the exposure exists, what evidence supports it and how it may transmit to revenue/profit.

Expected display:

- driver type;
- industry-chain node and bottleneck;
- company product/process position;
- beneficiary classification with D2 rule version or D3 analyst ownership;
- customer/qualification/capacity evidence;
- financial-transmission hypothesis;
- evidence quality, conflicts, revision and cutoff;
- table and graph views without recommendation ranking.

### Slice 3 — Investment Research Analysis

User job: compare research attractiveness only after the complete beneficiary universe is visible.

Expected dimensions:

- industry certainty;
- company competitive position;
- financial transmission and earnings elasticity;
- expectations gap;
- valuation observations;
- catalyst timing;
- risk and falsification conditions;
- evidence freshness and quality.

Any composite score must expose every deterministic input, rule version, missing-value treatment and risk penalty. It must be presented as research priority, not investment advice. Canonical price and comparison eligibility remain prerequisites for any strict price/valuation comparison that exceeds current v0.6B observation semantics.

### Slice 4 — Evidence ingestion and AI assistance

Requires separate Architecture Preflight for Provider/source authorization, immutable raw capture, normalization, deduplication, entity matching, human acceptance and AI permissions. AI may draft summaries and candidate links but may not self-promote outputs to D0 facts, assign accepted evidence grades, mutate deterministic state or issue trading guidance.

## Unresolved questions and stop conditions

1. Confirm the exact v0.6A company-research revision model, accepted read fields and detail route.
2. Confirm whether each existing query service exposes a bounded scalar read without full graph loading; otherwise define a read-only repository projection without changing domain semantics.
3. Confirm the supported cursor encoding and whether cursor content is signed or merely opaque for local use.
4. Confirm the explicit request-time reference used for the default seven-day window.
5. Confirm current PostgreSQL test availability and CI expectations.
6. Stop if any included field requires inference, new persistence, a new semantic join or a changed domain contract.

## Definition-of-Ready recommendation

Issue #134 may proceed to independent DoR review after the repository-path inventory for the v0.6A company-research revision and the scalar-query/N+1 boundary is verified. No implementation branch or implementation PR should be created before that review is accepted.
