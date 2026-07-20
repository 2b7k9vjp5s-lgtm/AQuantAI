# Evidence Intelligence MVP Architecture Preflight

## Status and authority

- Authority: Issue #134.
- Base branch: `main` at `0136674af2c213cdc550a5605108ea67ac357616`.
- Work type: Architecture Preflight, documentation only.
- Released version remains `0.2.0`; merged capability remains v0.6D.
- This document authorizes no production code, API, UI, test, fixture, schema, migration, Provider, release or version change.

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

The product program is split into separately governed slices:

1. Research Change Feed / Evidence Timeline — current first slice.
2. Industry Beneficiary Analysis — later slice using existing industry-map, beneficiary, candidate-pool and company-research contracts.
3. Investment Research Analysis — later slice using company research, expectations, valuation observations, catalyst, risk and quality judgments, plus canonical price/comparison eligibility where required.
4. Evidence ingestion and guarded AI assistance — later Architecture Task.

The system may help identify direct, conditional, indirect or merely conceptual industry exposure and compare research priority. It must not present those outputs as guaranteed facts, buy/sell advice, target prices, return promises or automatic trading signals.

## One-sentence user job

When the user opens AQuantAI, they can determine within approximately five minutes which evidence, research cases, industry maps and company-research records were newly recorded or revised in a bounded recent period, while preserving provenance, cutoff, revision and non-advisory meaning.

## Chosen first vertical slice

### Opening experience

- Page candidate: `GET /evidence-intelligence`
- Read API candidate: `GET /evidence-intelligence/feed`
- Primary question: **What research evidence or accepted research object changed recently, when was the information known, when was it recorded, and where can I inspect the available context?**

### Included record types

Exactly four event types:

1. `EvidenceItem` creation.
2. `ResearchCaseRevision` creation.
3. `IndustryMapRevision` creation.
4. `Stage2CompanyResearchRevision` creation.

### Locked exclusions

- Beneficiary or opportunity ranking.
- Investment-attractiveness scoring.
- Buy/sell/hold guidance, target price, expected return or timing judgment.
- New evidence ingestion or external network access.
- AI summaries, AI importance ranking or positive/negative labelling.
- Valuation, catalyst, risk or quality-judgment feed events.
- Evidence-addition or unresolved-conflict metrics.
- Industry-to-company mapping UI.
- New persistent state, schema, migration, Provider or canonical-price work.

## Existing-source inventory

| Display object | Existing owner | Existing path | Persisted source | Existing fields used |
| --- | --- | --- | --- | --- |
| Evidence item | v0.5 Evidence Ledger | `industry_alpha/models.py`, `industry_alpha/repository.py`, `industry_alpha/query.py` | `evidence_items` | `id`, `case_id`, `evidence_grade`, `source_kind`, `source_title`, `source_locator`, `information_date`, `recorded_at_utc`, `summary`, `supersedes_evidence_id` |
| Research case revision | v0.5 Evidence Ledger | same domain | `research_case_revisions` | `id`, `case_id`, `revision_no`, `title`, `summary`, `information_cutoff_date`, `recorded_at_utc`, `supersedes_revision_id` |
| Industry map revision | Stage 1 industry map | `industry_alpha/chain_map_models.py`, `industry_alpha/chain_map_repository.py`, `industry_alpha/chain_map_query.py` | `industry_map_revisions` | `id`, `map_id`, `revision_no`, `title`, `scope`, `information_cutoff_date`, `recorded_at_utc`, `supersedes_revision_id` |
| Company research revision | v0.6A | `industry_alpha/stage2_models.py`, `industry_alpha/stage2_repository.py`, `industry_alpha/stage2_query.py` | `stage2_company_research_revisions` | `id`, `company_research_id`, `revision_no`, `research_question`, `summary`, `workflow_state`, `conclusion_status`, `information_cutoff_date`, `recorded_at_utc`, `supersedes_revision_id` |
| Company identity context | v0.6A | `Stage2CompanyResearch` | `stage2_company_research` | `id`, `case_id`, `map_id`, `source`, `stock_code`, `created_at_utc` |

No beneficiary status, investment status, company name, exchange, currency, unit or importance may be inferred from codes, free text, Provider identity or UI context.

## Existing list-query limitation

The current list services are correct for their existing detail/list contracts but are unsuitable for a global feed:

- `EvidenceLedgerQueryService.list_cases()` loads the complete case graph once per case.
- `IndustryChainMapQueryService.list_maps()` calls `load_map()` once per map and loads nodes, relationships, observations, links and evidence.
- `Stage2CompanyResearchQueryService.list_research()` calls `load()` once per identity and loads the full Stage 2 frozen graph.

The Feed must not compose those list services. The later implementation should add one stateless, read-only scalar repository/query boundary that selects only the approved columns with bounded per-source limits. This is not a new domain meaning or persistent state.

## Field qualification matrix

| Feed field | Source | Minimum semantic level | Derivation | Rule |
| --- | --- | ---: | ---: | --- |
| `event_type` | explicit selected model/table | accepted source level | D1 deterministic projection | Fixed allow-list only. |
| `event_id` | source row `id` | accepted source level | D0 | Stable UUID. |
| `object_id` | `case_id`, `map_id` or `company_research_id` | accepted source level | D0 | No inferred join. |
| `revision_no` | revision row | accepted source level | D0 | Null only for EvidenceItem. |
| `primary_text` | `source_title`, case/map `title`, or company `research_question` | accepted source level | D1 display projection of one explicit field | Response also returns `primary_text_source_field`; no rewriting or summarisation. |
| `summary` | source row | accepted source level | retains source-domain level | No AI rewrite. Optional null remains null. |
| `information_date` | EvidenceItem | accepted source level | D0 | Separate from chronology. |
| `information_cutoff_date` | revision row | accepted source level | D0 | Separate from chronology. |
| `recorded_at_utc` | source row | accepted source level | D0 | Primary feed ordering. |
| `source_kind` | EvidenceItem | accepted source level | D0 | Null for revision events. |
| `evidence_grade` | EvidenceItem | accepted evidence contract | D2 user-assigned provenance classification | Label as provenance classification, not truth probability. |
| `source_locator` | EvidenceItem | accepted source level | D0 | Optional; no guessed URL. |
| `supersedes_id` | source row | accepted source level | D0 | Historical event remains visible. |
| `detail_path` | explicit route table | N/A | D1 deterministic routing | Return only for verified existing routes; otherwise null. |

Display does not elevate Semantic Level. D2/D3 values retain explicit labels and must not be presented as D0/D1.

## Query contract

### Parameters

- `as_of_cutoff`: optional date; existing source-domain visibility rules remain authoritative.
- `recorded_from`: optional inclusive UTC timestamp.
- `recorded_to`: optional exclusive UTC timestamp.
- `event_type`: optional explicit allow-listed filter.
- `limit`: default 50, maximum 100.
- `cursor`: optional opaque cursor.

### Evaluation time and bounds

- Capture `evaluated_at_utc` exactly once per request.
- Without explicit recorded bounds, query `[evaluated_at_utc - 7 days, evaluated_at_utc)`.
- Maximum accepted window is 30 calendar days.
- Empty results remain empty; there is no fallback to older records.

### Ordering and cursor

Stable descending order:

1. `recorded_at_utc DESC`
2. fixed event-type order ASC: evidence, case revision, industry-map revision, company-research revision
3. `event_id` text DESC

The cursor contains only the last row's three ordering values, encoded as strict base64url JSON for local use. It is opaque to the UI, versioned, size-bounded and rejected on malformed content. No offset pagination.

### Source query and merge

- Apply cutoff and recorded-window filters inside each source query.
- Fetch at most `limit + 1` rows per selected source after the cursor boundary.
- Merge in application code using the fixed ordering tuple.
- Return at most `limit` rows and a next cursor only when more ordered rows exist.
- Do not use title, stock code, company name, evidence grade or inferred importance for ordering.

### Deduplication

- One persisted EvidenceItem equals one feed event.
- One persisted revision row equals one feed event.
- No content-based deduplication occurs in the read feed.
- Superseded rows remain visible if within the requested bounds.

### Missing and conflict handling

- Optional summary or source locator remains null and is displayed as unavailable.
- Required identity, chronology and cutoff fields are already non-null in accepted models; any corrupt/unreadable row fails closed and is covered by deterministic failure tests.
- The Feed does not resolve conflicts, choose a winning claim or label a change positive/negative.
- A missing verified detail route produces `detail_path = null`; the implementation must not guess a route.

### Cutoff and chronology

- Existing domain cutoff helpers remain authoritative.
- `recorded_at_utc` determines Feed order.
- `information_date` or `information_cutoff_date` is displayed separately.
- A later-recorded item with older information remains later in chronology while visibly retaining the older information date.

## Non-advisory presentation contract

Allowed labels:

- Evidence added
- Research case revised
- Industry map revised
- Company research revised
- Information date
- Research cutoff
- Recorded time
- Source / provenance
- View available context

Prohibited labels:

- Opportunity, recommended, top pick, strong beneficiary
- Positive/negative signal
- Buy/sell/hold
- Good price, expected return, importance score

Recency, revision frequency and evidence count must not be styled as investment attractiveness.

## Domain invariance and task classification

The later implementation qualifies as a **Product Task** only if it:

- reads existing accepted rows and visibility rules;
- adds no table, migration or persistent state;
- changes no Provider, cutoff, revision, append-only or provenance behavior;
- adds no score, classification or Semantic Level elevation;
- leaves all v0.5, Stage 1 and v0.6A command paths unchanged;
- uses explicit joins only from existing foreign keys;
- introduces no fallback or inferred identity.

A new stateless scalar read repository is allowed as presentation/query composition. If implementation requires a new semantic join, field meaning, classification, materialized Feed state or changed invariant, it defaults to Architecture Task and stops.

## Performance and security

- Bounded per-source queries and cursor pagination are mandatory.
- No existing full-graph list service may be called by the Feed.
- No N+1 graph loading.
- No source content, credentials, raw connection strings or raw database exceptions in logs or user errors.
- Existing local-user assumptions remain unchanged; no multi-user authorization is introduced.
- Page, API, tests and fixtures perform no hidden network access.

## Validation matrix

| Layer | Required checks |
| --- | --- |
| Scalar repository | all four source projections; source-side cutoff/window/cursor filters; bounded row count; no graph loading. |
| Query merge | fixed cross-source ordering; equal-timestamp ties; cursor continuation without gaps/duplicates; event filter; empty result. |
| Semantics | information date vs recorded time; superseded events remain; optional nulls; D2 evidence-grade wording; no inferred fields. |
| API | parameter validation; 30-day maximum; limit maximum; strict cursor rejection; deterministic JSON; 503 database boundary. |
| Presentation | neutral labels; clear timestamps/source; loading/empty/error states; keyboard and responsive behaviour; no ranking language. |
| Regression | full existing pytest suite and existing local research demo; do not invent pass counts. |
| PostgreSQL | execute the repository/integration path when the accepted CI or local environment provides PostgreSQL. |

## Candidate implementation scope after DoR approval

Candidate new files:

- `industry_alpha/evidence_intelligence_contracts.py`
- `industry_alpha/evidence_intelligence_repository.py`
- `industry_alpha/evidence_intelligence_query.py`
- `backend/api/evidence_intelligence.py`
- `evidence_intelligence/static/evidence_intelligence.html`
- `evidence_intelligence/static/evidence_intelligence.css`
- `evidence_intelligence/static/evidence_intelligence.js`
- `tests/test_evidence_intelligence_repository.py`
- `tests/test_evidence_intelligence_query.py`
- `tests/test_evidence_intelligence_api.py`

Candidate modified files:

- `backend/main.py` for router/static-page registration only.
- packaging discovery only if the new package is not already included by the accepted package pattern.

No domain model, command, migration, Provider, fixture source contract, release or version file is in scope.

## Follow-on product roadmap

These functions are incorporated into project direction but are not authorized by Issue #134.

### Slice 2 — Industry Beneficiary Analysis

User job: identify all companies with direct, conditional, indirect or merely conceptual exposure to an industry driver, explain the product/process position and possible financial transmission, and show the exact evidence, conflicts, revision and cutoff.

Expected presentation:

- industry driver type, chain node, bottleneck and value-pool shift;
- company product/process position;
- beneficiary classification with D2 rule version or D3 analyst ownership;
- customer, certification, capacity and production-stage evidence;
- financial-transmission hypothesis;
- table and graph views without recommendation ranking.

### Slice 3 — Investment Research Analysis

User job: compare research attractiveness only after the complete beneficiary universe is visible.

Dimensions:

- industry certainty;
- company competitive position;
- earnings transmission and elasticity;
- market expectations and expectation gap;
- valuation observations;
- catalysts, risks and falsification conditions;
- evidence freshness, quality and conflicts.

Any composite research-priority score must expose every deterministic input, rule version, missing-value treatment and risk penalty. It must not be presented as investment advice. Canonical price and comparison eligibility remain prerequisites for strict price/valuation comparison beyond current v0.6B observation semantics.

### Slice 4 — Evidence ingestion and AI assistance

Requires separate Architecture Preflight for source authorization, immutable raw capture, normalization, deduplication, entity matching, human acceptance and AI permissions. AI may draft summaries and candidate links, but may not self-promote output to D0, assign accepted evidence grades, mutate deterministic state or issue trading guidance.

## Definition of Ready decision

The repository inventory confirms the exact four source models and fields. It also confirms that existing list services perform full per-object graph loading and therefore must not be reused for the Feed. A bounded scalar read repository can be implemented without new persistence or semantic change.

**Recommendation: Issue #134 is ready for independent DoR approval as a conditional Product Task preflight.**

Stop and return to Architecture Preflight if implementation discovers any need for inferred fields, new persistent state, a new semantic relationship, changed cutoff/revision/provenance rules or strict price/valuation comparison.
