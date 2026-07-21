# Issue #144 — Product Reading Surfaces Consolidation Review

## Authority

- GitHub Issue: #144
- Related roadmap: #137
- Required base: `74b81515aaec1db9eb3dfcff0e20644f1beab3aa`
- Branch: `docs/product-reading-surfaces-consolidation-review`
- Work type: consolidation/refactoring characterization — documentation only
- Released version remains `0.2.0`
- No production implementation is authorized

## Objective

Characterize the merged Research Feed and Industry Beneficiary Workspace product surfaces, evaluate repeated infrastructure and Stage 2 read reachability, and determine the smallest safe next architecture preflight before Slice 3.

## Mandatory start checks

1. Confirm `main` contains required base `74b81515aaec1db9eb3dfcff0e20644f1beab3aa`.
2. Read `.codex/WORKFLOW.md`, `docs/architecture_baseline.md`, Issue #137, Issue #144, merged PR #139 and merged PR #143.
3. Read the merged Evidence Intelligence and Industry Research routers, repositories, queries, pages and tests.
4. Read existing v0.6A-v0.6D Stage 2 query/repository/contracts and `backend/api/industry_alpha.py`.
5. Confirm this branch and Draft PR contain documentation only.
6. Do not modify PR #38 or unrelated branches.

Stop if the base, work type or authorization differs.

## Authorized files

- `docs/product_reading_surfaces_consolidation_review.md`
- `.codex/tasks/issue-144-product-reading-surfaces-consolidation-review.md`
- `docs/architecture_baseline.md` only if current-state synchronization is completed in this PR

No other file is authorized.

## Required characterization

### Current runtime surfaces

Record:

- Research Feed page/API and bounded event-source reads;
- Industry Research page/selector/workspace/detail behavior;
- current v0.6A-v0.6D Stage 2 read domains;
- exact non-advisory and provenance boundaries.

### API consistency

Compare:

- validation ordering;
- lazy DB construction;
- 422/404/503 behavior;
- cutoff and recorded UTC semantics;
- empty-state and no-fallback behavior;
- notices and unsupported-field disclosures.

### Query architecture

Verify:

- Evidence Intelligence uses bounded scalar event-source reads;
- Industry Research uses fixed-count overview reads plus one explicit map detail;
- initial product pages avoid per-row full graph loading;
- current Stage 2 list services use identity-list plus per-identity graph loading and must not be composed for a new product workspace.

### Repetition decisions

For each repeated pattern, decide keep local, consolidate now or revisit later:

- FastAPI router/session factory;
- static page registration;
- page shell and safe DOM helpers;
- cutoff serialization;
- evidence/claim serializers;
- notices;
- fixed-count product overview repositories;
- test layers.

Do not recommend consolidation merely for aesthetic uniformity.

### Next-stage reachability

Determine whether one explicit persisted `company_research_id` can reach, through accepted exact foreign keys and revisions:

- frozen Stage 1 handoff;
- company-research revisions and hypotheses;
- expectations;
- valuation observations;
- catalysts;
- risks;
- industry/company judgments;
- evidence, conflicts, missing evidence, cutoff and UTC chronology.

Explicitly identify unavailable semantics:

- canonical current price;
- comparison eligibility;
- deterministic expectation gap;
- cross-company ranking;
- total research-priority score;
- target price, fair value, expected return, buy/sell or timing state.

### Recommended next preflight

Define only the candidate scope for a Company Research Workspace v1 Architecture Preflight. Do not create its implementation Issue or code in this branch.

The recommendation must include:

- one-sentence user job;
- candidate read surfaces;
- fixed-query requirement;
- exact selector/cutoff/frozen-history questions;
- production-realistic offline golden path requirement;
- migration decision;
- exclusions and stop conditions.

## Migration decision

No schema, migration, Provider, dependency, runtime behavior, fixture or version change is authorized in this review.

## Validation

Before handoff:

1. Confirm the complete base-to-head diff is documentation only.
2. Record exact base/head SHA.
3. Record complete changed-file inventory.
4. Confirm no application test is required because runtime behavior is unchanged.
5. Confirm no production code, model, schema, migration, dependency, Provider, fixture, release or version file changed.
6. Keep the PR Draft/Open/unmerged.
7. Stop for independent Definition-of-Ready review.

## Independent review checklist

The reviewer must verify:

- the consolidation cadence requirement is correctly applied;
- findings match merged product code and Stage 2 read contracts;
- no generic framework is proposed without evidence;
- no N+1 list service is authorized for the next product overview;
- the next-stage golden path is reachable through existing exact persistence contracts;
- Canonical Price and Comparison Eligibility remain separate;
- no score, ranking, recommendation, target price, expected return or trading state is introduced;
- the proposed next action is architecture preflight only.

Approval text:

`CONSOLIDATION REVIEW APPROVED at fixed head <HEAD_SHA>`

## Prohibited actions

- no production refactor;
- no new API or UI;
- no model/schema/migration;
- no Provider or external network path;
- no new tests or fixtures;
- no company-research implementation;
- no price/comparison semantics;
- no score, ranking or recommendation;
- no release/tag/version change;
- no merge or Issue closure without owner authorization.