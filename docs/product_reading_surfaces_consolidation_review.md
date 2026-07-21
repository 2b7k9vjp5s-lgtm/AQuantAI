# Product Reading Surfaces Consolidation Review

## Status and authority

- Authority: Issue #144.
- Related roadmap: Issue #137.
- Required base: `74b81515aaec1db9eb3dfcff0e20644f1beab3aa`.
- Reviewed product slices:
  - Slice 1 — Evidence Intelligence / Research Change Feed, merged through PR #139;
  - Slice 2A — Industry Beneficiary Workspace v1, merged through PR #143.
- Work type: consolidation/refactoring characterization, documentation only.
- Released version remains `0.2.0`; merged capability remains v0.6D plus the two read-only product surfaces.
- This document authorizes no production code, API, UI, model, schema, migration, Provider, dependency, fixture, test, release or version change.

## Executive decision

The two merged product reading surfaces are coherent enough to support the next product architecture preflight without a production refactor.

The accepted consolidation decision is:

1. **Keep product repositories and query projections domain-local.** Evidence chronology, industry-beneficiary projection and Stage 2 research graphs have different owners, cutoff rules, failure meanings and payload semantics.
2. **Do not create a generic workspace framework.** Repeated FastAPI router/session/static-page and JavaScript DOM patterns are small presentation scaffolding, not an independently valuable infrastructure boundary.
3. **Do not compose existing Stage 2 list services for the next workspace.** Current v0.6A-v0.6D list methods load one graph per identity and therefore are unsuitable as a multi-section company overview boundary.
4. **Allow a bounded Company Research Workspace Architecture Preflight next.** The first slice should aggregate existing v0.6A-v0.6D records for one explicitly selected persisted company-research identity, with fixed-count scalar overview reads and on-demand accepted detail reads.
5. **Do not introduce investment-priority scoring or price attractiveness.** Canonical Price and Comparison Eligibility have no Definition of Ready. Existing valuation observations may be displayed only as their exact persisted research context.

No consolidation implementation Issue is recommended at this point.

## Current product runtime inventory

### Research Feed

Runtime surfaces:

- page: `GET /evidence-intelligence`;
- feed API: `GET /evidence-intelligence/feed`.

Accepted purpose:

- display accepted evidence and research revision chronology;
- separate information date or research cutoff from recorded UTC;
- expose source, provenance and exact detail navigation;
- use stable deterministic ordering and opaque cursor pagination;
- avoid interpreting recency or evidence volume as investment attractiveness.

The feed uses bounded scalar reads from four accepted event sources. It does not load complete Evidence Ledger, Industry Map or Stage 2 graphs during the initial feed request.

### Industry Research

Runtime surfaces:

- page: `GET /industry-research`;
- map selector: `GET /industry-research/maps`;
- workspace overview: `GET /industry-research/maps/{map_id}/workspace`;
- accepted existing detail routes for explicit Stage 1 and Stage 2 drill-down.

Accepted purpose:

- require explicit persisted map selection and optional cutoff;
- display the complete cutoff-visible persisted Stage 1 beneficiary set for that map;
- retain raw `direct / secondary / potential` and assessment-state values;
- display exact stock and ingestion-run provenance;
- preserve exact historical Stage 2 frozen-beneficiary-revision links;
- keep all rows visible before downstream valuation or market-pricing analysis.

The initial workspace uses one accepted map-detail read plus fixed-count scalar beneficiary overview reads. It does not load one full company graph per row.

### Existing Stage 2 read domains

The accepted Stage 2 read graph is:

```text
v0.6A company research and financial-transmission hypotheses
  -> v0.6B expectations and valuation observations
  -> v0.6C catalyst and risk assessments
  -> v0.6D industry and company quality judgments
```

Every downstream record freezes exact accepted upstream revisions and links. Existing contracts are research-only and explicitly prohibit scores, rankings, target prices, timing conclusions, recommendations and trading.

## API consistency review

| Concern | Research Feed | Industry Research | Consolidation decision |
| --- | --- | --- | --- |
| Request validation | Complete request validated before DB construction; malformed cursor/time/type/limit returns 422 | FastAPI UUID/date validation returns 422 | Keep route-local validation. A generic validator would erase different request contracts. |
| Database construction | Lazy session factory after validation | Lazy session factory per workspace API | Pattern is consistent. Duplication is too small to justify shared runtime infrastructure. |
| Missing selected object | Not applicable to global feed | Missing or cutoff-invisible map returns 404 | Keep product-local because object visibility semantics differ. |
| Query/integrity failure | Redacted deterministic 503 | Redacted deterministic 503 | Maintain shared behavior by tests and review, not by premature abstraction. |
| Cutoff | Event-source information date/cutoff plus recorded UTC visibility | Owning map, Stage 1 and Stage 2 date-granular cutoff semantics | Keep owning-domain semantics local. Do not create a new product cutoff owner. |
| Missing data | Empty feed remains empty | Empty persisted beneficiary set remains empty; no fallback | Consistent fail-closed rule. |
| Notices | Feed-specific chronology boundary | Beneficiary and investment-analysis boundary | Keep notices domain-specific. |

No API inconsistency blocks the next preflight.

## Query and graph-loading characterization

### Accepted current paths

- Evidence Intelligence performs bounded scalar queries per accepted event source, merges in application memory and paginates through a stable cursor.
- Industry Research uses a scalar map selector, a fixed beneficiary overview query set and exactly one accepted map-detail graph for the explicitly selected map.
- Company and evidence graphs are loaded only after explicit user action.

### Existing Stage 2 list services

The v0.6A-v0.6D list services follow an identity-list plus graph-load pattern:

```text
list identities
  -> for each identity: load complete domain graph
  -> choose latest cutoff-visible revision
  -> project summary
```

This is accepted for existing narrow APIs and local fixture use, but it creates query and graph growth proportional to the number of identities. The next Company Research product overview must therefore not compose:

- `Stage2CompanyResearchQueryService.list_research()`;
- `Stage2ExpectationQueryService.list_expectations()`;
- `Stage2ValuationQueryService.list_valuations()`;
- `Stage2CatalystQueryService.list_catalysts()`;
- `Stage2RiskQueryService.list_risks()`;
- `Stage2IndustryJudgmentQueryService.list_judgments()`;
- `Stage2CompanyJudgmentQueryService.list_judgments()`.

The next preflight should define one stateless read-only aggregation repository with a fixed small query count for one explicit `company_research_id`. Existing accepted detail services may remain the authoritative on-demand graph readers.

### No current refactor requirement

No evidence shows that the two product surfaces share one neutral graph-loading algorithm. Their only common property is being read-only product pages. A framework extracted now would primarily rename route, session, response and DOM boilerplate while introducing cross-domain coupling.

## Repetition and keep/consolidate matrix

| Repeated pattern | Evidence | Decision now | Revisit trigger |
| --- | --- | --- | --- |
| FastAPI router and lazy DB session factory | Similar structure in product APIs | Keep local | Three or more product APIs require exactly the same dependency ordering and error contract. |
| Static directory mount and page route in `backend/main.py` | One block per page | Keep explicit | Mount registration becomes materially error-prone or requires configuration-driven plugins. |
| Chinese-first page shell | Header, boundary notice, loading/empty/error regions | Keep page-local | A reviewed design-system task defines accessible shared components without changing product semantics. |
| Small JS DOM helpers | `createElement`, `textContent`, metadata rendering | Keep page-local | A third page repeats identical tested functions and shared delivery does not require a build system. |
| Cutoff serialization | Similar date query strings | Keep product/domain-local | One accepted neutral cutoff request contract is proven across all affected domains. |
| Evidence/claim serialization | Similar nested payload shapes in v0.6B-v0.6D | Keep domain-local | A neutral claim contract reaches Definition of Ready; PR #93 already rejected aesthetic consolidation. |
| Notices and unsupported lists | Present in every research contract | Keep domain-local | Exact keys and meanings become identical across accepted contracts. |
| Fixed-count overview repository | Used by Evidence and Industry product slices | Use the pattern, not one generic implementation | A truly neutral ordered scalar projection contract appears in three domains. |
| Safe DOM rendering | No `innerHTML` for untrusted values | Preserve as invariant and regression test | Never relax; shared utility remains optional. |

## Test and validation review

The merged product slices retain the repository-wide PostgreSQL CI path and existing fixture demo. PR #143 fixed-head GitHub Actions run #222 completed successfully, including:

- PostgreSQL 16 service;
- dependency installation;
- complete test step;
- local fixture demo;
- cleanup.

This documentation-only consolidation review adds no runtime behavior and requires no new application test. The independent reviewer must still verify the complete changed-file inventory and that no production file changed.

Test-matrix growth remains a controlled architecture debt. Future product workspace tests should continue to separate:

- repository query-count and integrity tests;
- projection/cutoff tests;
- API error-boundary tests;
- static page safety and explicit-selection tests;
- repository-wide PostgreSQL regression and fixture demo.

## Next-stage input reachability

### Reachable with existing accepted contracts

For one explicit `company_research_id`, current persisted contracts can supply:

- exact company-research identity and frozen Stage 1 handoff;
- company-research revision workflow, question, summary and conclusion status;
- financial-transmission hypotheses, direction, mechanism, metrics, lag, confidence, evidence, conflicts and missing evidence;
- market expectation observations with subject, horizon, kind, direction, status, confidence and basis;
- valuation observations with method, metric context, observed value, missing reason, unit, currency, comparison basis, assumptions and optional exact local price-row provenance;
- catalyst assessments with category, observation window, trigger criteria, status, confidence, uncertainty and frozen links;
- risk assessments with category, downside path, invalidation condition, mitigants, status, confidence, uncertainty and frozen links;
- industry and company quality judgments with exact frozen v0.6A-v0.6C revision links, evidence state, outcome, criteria, rationale and follow-up verification;
- exact evidence-grade counts, contradictions, missing evidence, information cutoffs, recorded UTC and revision history.

These fields are sufficient for a useful **single-company research reading workspace**.

### Not reachable without new semantics or infrastructure

The following are not authorized or reliably derivable:

- canonical current market price;
- comparison-eligible valuation multiple;
- fair value, target price, upside/downside percentage or expected return;
- cross-company valuation comparison;
- deterministic expectation-gap calculation;
- total investment-attractiveness score or research-priority ranking;
- buy, sell, hold, good-price or good-timing state;
- automatic monitoring, reminder, watchlist or task lifecycle;
- automatically inferred customer, certification, order, capacity or production state beyond persisted claims and hypotheses.

A non-null `observed_value`, currency string or linked `daily_price` row must not be promoted to canonical comparison data.

## Smallest recommended next Architecture Preflight

### Candidate name

`Company Research Workspace v1`

### One-sentence user job

A local user can explicitly select one persisted Stage 2 company-research identity and inspect its exact frozen Stage 1 context, financial-transmission hypotheses, expectations, valuation observations, catalysts, risks, quality judgments, evidence conflicts and missing information in one cutoff-aware reading workspace without receiving a score, ranking, target price or recommendation.

### Candidate product surfaces

- Chinese-first page: `GET /company-research`;
- scalar selector: `GET /company-research/items?map_id=<uuid>&as_of_cutoff=YYYY-MM-DD`;
- one-company overview: `GET /company-research/items/{company_research_id}/workspace?as_of_cutoff=YYYY-MM-DD`;
- existing accepted detail routes used only on explicit drill-down where an overview cannot remain bounded.

The architecture preflight must decide the exact routes; the names above are not implementation authorization.

### Required architecture decisions

1. exact selector scope and whether `map_id` is required or optional;
2. fixed query count independent of expectation, valuation, catalyst, risk and judgment counts;
3. exact latest-visible and frozen-history rules across v0.6A-v0.6D;
4. handling of multiple identities or revisions that violate exact ownership expectations;
5. overview fields versus on-demand detail fields;
6. presentation separation among facts/provenance, persisted research states, D3 judgments, conflicts and unavailable data;
7. explicit treatment of valuation observations as non-canonical context;
8. empty-section and partial-research behavior without fallback or generated content;
9. one production-realistic offline golden path using existing accepted persistence contracts;
10. exact API 422/404/503 and integrity-failure boundaries.

### Migration decision

**No schema, migration or persistent workspace state is recommended for v1.**

If the preflight discovers that one-company aggregation cannot be reached through existing exact foreign keys and accepted revisions, it must stop rather than add inferred joins or new persistence within the same slice.

## Locked exclusions for the next slice

- no schema or migration;
- no Provider or external network path;
- no mutation, watchlist, task, alert or notification state;
- no canonical market-price contract;
- no Comparison Eligibility;
- no expectation-gap computation;
- no cross-company comparison or ranking;
- no score, weight, research-priority total or risk-adjusted total;
- no target price, fair value, expected return or upside;
- no buy/sell/hold, good-price or good-timing conclusion;
- no AI-generated accepted evidence, links, hypotheses or judgments;
- no automatic extraction of product, customer, certification, capacity, production or order fields from free text;
- no release, tag or version change.

## Architecture baseline synchronization delta

The authoritative baseline currently predates the merged product sequence. The next accepted documentation synchronization should record:

- merged runtime surfaces now include Research Feed and Industry Research in addition to Dashboard, Market Cockpit and Industry Alpha APIs;
- Research Feed and Industry Research are read-only product projections over accepted contracts and add no semantic level;
- the two-slice consolidation review recommends no production refactor;
- the next product gate is a Company Research Workspace Architecture Preflight, not Slice 3 implementation;
- Canonical Price and Comparison Eligibility remain a separately governed parallel infrastructure track.

This review document is the authoritative consolidation finding for Issue #144. Updating `docs/architecture_baseline.md` may occur in this documentation PR or a directly linked documentation synchronization commit, but no application feature may start from the stale sequence text.

## Final decision table

| Question | Decision |
| --- | --- |
| Production consolidation required before next preflight? | No. |
| Generic product workspace framework justified? | No. |
| Shared Stage 2 evidence serializer justified? | No; keep domain-local. |
| Existing Stage 2 list APIs suitable for next product overview? | No; do not compose due per-identity graph loading. |
| Existing v0.6A-v0.6D persistence sufficient for a useful single-company workspace? | Yes, within exact existing semantics. |
| Schema or migration required for the first company workspace? | No. |
| Canonical price or comparison eligibility available? | No. |
| Cross-company attractiveness score or ranking authorized? | No. |
| Next action after independent acceptance? | Open a bounded Company Research Workspace v1 Architecture Preflight. |

## Completion and review gate

- Keep the linked PR Draft/Open/unmerged.
- Verify the diff remains documentation only.
- Record exact base/head and changed files.
- Obtain independent Definition-of-Ready approval for the consolidation findings.
- Do not start Company Research implementation from this review.
- After owner-authorized merge, create the separate Company Research Workspace Architecture Preflight Issue.