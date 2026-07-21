# Issue #148 Task Snapshot — Company Research Workspace v1 Architecture Preflight

## Authority

- GitHub Issue: `#148 [Architecture Preflight] Define Company Research Workspace v1`
- Required base: `7f7014d06ebb9b71c3b24bc559fdd4bd61a625f3`
- Related roadmap: Issue #137
- Related consolidation: Issue #144 / PR #145
- Related architecture sync: Issue #146 / PR #147
- Work type: documentation-only Architecture Preflight

The GitHub Issue is authoritative. This task snapshot exists to make the accepted work executable and reviewable under `.codex/WORKFLOW.md`.

## Start protocol

Before changing anything:

1. verify branch `docs/company-research-workspace-preflight` starts from the required base;
2. read `.codex/WORKFLOW.md`;
3. read `docs/architecture_baseline.md`;
4. read `docs/product_reading_surfaces_consolidation_review.md`;
5. read Issue #148 completely;
6. inspect the current Stage 2 repositories, query services, API routes and the two merged product surfaces;
7. do not modify production code.

## Objective

Produce one architecture document that decides whether a bounded, Chinese-first, read-only Company Research Workspace v1 can be implemented from existing v0.6A-v0.6D persisted contracts using one explicit `company_research_id`, one optional cutoff and a fixed query budget.

The preflight must either:

- establish Definition-of-Ready inputs for a later bounded Product Task; or
- stop and explain which unresolved architecture dependency prevents implementation.

It must not implement the workspace.

## Authorized files

Only:

1. `.codex/tasks/issue-148-company-research-workspace-preflight.md`
2. `docs/company_research_workspace_preflight.md`

No production code, API, UI, repository, query, contracts, tests, fixtures, models, schema, migrations, Provider, dependencies, release or version file may change.

## Required source inventory

At minimum inspect:

- `backend/api/industry_alpha.py`
- `backend/api/industry_research.py`
- `backend/api/evidence_intelligence.py`
- `backend/main.py`
- `industry_alpha/stage2_repository.py`
- `industry_alpha/stage2_query.py`
- `industry_alpha/stage2_expectations_repository.py`
- `industry_alpha/stage2_expectations_query.py`
- `industry_alpha/stage2_assessments_repository.py`
- `industry_alpha/stage2_assessments_query.py`
- `industry_alpha/stage2_judgments_repository.py`
- `industry_alpha/stage2_judgments_query.py`
- current Stage 1 repository/query contracts
- current Evidence/claim contracts
- `industry_alpha/beneficiary_workspace_*`
- `industry_alpha/evidence_intelligence_*`
- merged PRs #139, #143, #145 and #147

## Mandatory architecture decisions

### Identity

- `company_research_id` is the only primary identity.
- Selection is explicit.
- No silent first row.
- No stock-code, name, Provider, free-text, title-similarity or LLM inference.
- No automatic relinking to a newer apparently compatible identity or revision.

### Product surface

Decide exact contracts for:

- page `GET /company-research`;
- selector `GET /company-research/research?as_of_cutoff=YYYY-MM-DD`;
- workspace `GET /company-research/research/{company_research_id}/workspace?as_of_cutoff=YYYY-MM-DD`.

Define response sections, raw stored values, IDs, chronology, notices and error mapping.

### Selector contract

The selector must be a lightweight read model, not a collection of full Stage 2 graphs.

Candidate fields:

- company research identity;
- source and stock code;
- creation UTC;
- map/case/frozen Stage 1 IDs;
- latest cutoff-visible research revision summary;
- deterministic module-availability counts;
- explicit cutoff and notices.

No ordering may be presented as ranking.

### Workspace overview contract

The first selected workspace response should contain bounded summaries for:

- identity and exact frozen Stage 1 provenance;
- latest company research revision and revision chronology summaries;
- financial hypotheses;
- expectations;
- valuation observations;
- catalysts;
- risks;
- industry judgments;
- company judgments;
- conflicts and missing-evidence counts/summaries;
- frozen company-research revision IDs and mismatch flags;
- links/IDs for explicit owning-domain detail reads.

Do not preload every full claim/evidence graph for every module item.

### Detail behavior

Full claim/evidence/revision graphs may be loaded only after explicit user action through existing owning-domain detail routes or a separately accepted bounded detail contract.

The initial workspace must not issue one request or query per item.

### Query budget

Accept or reject the following fixed budgets with evidence:

- selector: at most 3 SQL statements;
- selected workspace: at most 24 SQL statements;
- count independent of number of identities, revisions, links, claims or evidence rows.

The later Product Task must record its exact count and add constant-count regression tests.

Existing list services must not be composed for the overview because they use identity-list plus one graph load per identity.

### Cutoff and chronology

- identity visibility uses recorded UTC;
- revision visibility requires both information cutoff and recorded UTC date;
- latest means latest cutoff-visible persisted revision;
- exact downstream `company_research_revision_id` remains visible;
- latest-versus-frozen historical mismatch is shown, never repaired;
- supersession and revision IDs remain visible.

### Field ownership

Document exact owner and meaning for:

- Stage 1 handoff/provenance;
- v0.6A company research and hypotheses;
- v0.6B expectations and valuation observations;
- v0.6C catalysts and risks;
- v0.6D industry/company judgments;
- evidence and claim graphs;
- optional local price provenance.

No field meaning may change.

### Semantic qualification

For every display family, document:

- Semantic Level L0-L3;
- Derivation Level D0-D3;
- whether it is direct stored data, deterministic aggregation or analytical judgment;
- presentation restrictions.

D3 must remain visibly separate from fact/provenance and D1 counts.

### Price boundary

Allow exact stored valuation context only.

Do not create or imply:

- Canonical Price;
- Comparison Eligibility;
- computed expectation gap;
- fair value;
- target price;
- expected return;
- upside/downside;
- normalized comparability;
- good price or timing.

### Fail-closed behavior

Define:

- 422 malformed UUID/date;
- 404 missing/cutoff-invisible selected identity;
- 503 database/config/schema unavailable;
- absent optional modules as valid unavailable/empty states;
- missing required frozen Stage 1 provenance as failure;
- duplicate incompatible exact relations as failure;
- dangling revision/evidence links as failure;
- credential-safe UI/API errors;
- no external network.

### Ordering

Use deterministic neutral ordering:

- selector: source, stock code, UUID;
- module identities: stored key, UUID;
- revisions: revision number, UUID;
- evidence: relation, grade, information date, UUID;
- conflicts/missing: module, claim key, revision/evidence UUID.

Use `排序`, never `排名`.

### Migration and dependencies

Expected result:

- no schema/migration;
- no Provider/dependency;
- no release/version change;
- no persistent state;
- no generic workspace framework;
- no consolidation refactor.

Stop if evidence contradicts this.

## Candidate implementation authorization

Only if Definition of Ready is supported, the architecture document may recommend a later Product Task limited to candidate files such as:

New:

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

Modified:

- `backend/main.py` only for router/static registration and page serving.

The preflight itself does not authorize these changes.

## Required test plan

Specify later tests for:

- no silent selection;
- exact identity lookup;
- cutoff/UTC visibility;
- selector and workspace constant query counts;
- latest/frozen mismatch visibility;
- absent modules;
- conflicts/missing evidence;
- dangling provenance/link failure;
- neutral ordering;
- 422/404/503;
- strict JSON;
- credential-safe errors;
- safe DOM text handling, no untrusted `innerHTML`;
- PostgreSQL fixture parity;
- complete existing pytest and fixture demo.

## Locked exclusions

Do not authorize:

- price canonicalization or comparison eligibility;
- any calculated price attractiveness or expectation gap;
- company comparison/ranking/scoring/recommendations;
- Watchlist/tasks/alerts/portfolio/trading;
- automatic company discovery;
- new beneficiary taxonomy or typed roadmap fields;
- inferred or fallback identity;
- schema/migration/Provider/dependency/version/release changes;
- production implementation in this PR.

## Validation and hand-off

Before stopping:

1. record exact base and final HEAD;
2. record exact changed files;
3. verify documentation-only scope;
4. run full existing CI or verify the triggered GitHub Actions run;
5. perform author review against Issue #148;
6. keep PR Draft/Open/unmerged;
7. request independent review using:

`DEFINITION OF READY APPROVED at fixed head <HEAD_SHA>`

Do not merge, close Issue #148 or create an implementation Issue without explicit owner authorization.