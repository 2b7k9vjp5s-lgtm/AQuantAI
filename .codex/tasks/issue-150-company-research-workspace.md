# Issue #150 — Company Research Workspace v1

## Authority
- Product Task: Issue #150.
- Approved preflight: Issue #148 / PR #149.
- Required base: `b2554e24de3166475c016f8d09826989e8535e51`.
- Branch: `feat/company-research-workspace-v1`.
- Version remains `0.2.0`.

## Objective
Create a Chinese-first, read-only workspace for one explicitly selected persisted `company_research_id`. Read exact frozen Stage 1 provenance and cutoff-visible v0.6A-v0.6D research without ranking, scoring or recommendations.

## Routes and identity
- `GET /company-research`
- `GET /company-research/research?as_of_cutoff=YYYY-MM-DD`
- `GET /company-research/research/{company_research_id}/workspace?as_of_cutoff=YYYY-MM-DD`
- No silent first-row selection.
- No inference from stock code, name, industry text, free text, similarity or LLM output.

## Query contract
- New stateless domain-specific repository/query boundary.
- Selector: exactly 2 SQL statements, below the approved maximum of 3.
- Workspace: exactly 14 SQL statements, below the approved maximum of 24.
- Counts remain constant as identities, revisions, claims and evidence increase.
- No composition of existing Stage 2 list services and no per-row detail calls.

## Cutoff and integrity
- Identity visibility uses recorded UTC.
- Revision visibility requires information cutoff and recorded UTC.
- Required frozen Stage 1, stock and ingestion rows fail closed when absent or incompatible.
- Downstream frozen company-research revisions must be cutoff-visible.
- Hypothesis revisions must be frozen by a visible company-research revision.
- Historical mismatch remains visible and is not relinked.
- Optional modules use explicit empty states.

## Authorized files
1. `.codex/tasks/issue-150-company-research-workspace.md`
2. `industry_alpha/company_research_workspace_contracts.py`
3. `industry_alpha/company_research_workspace_repository.py`
4. `industry_alpha/company_research_workspace_query.py`
5. `backend/api/company_research.py`
6. `company_research/static/company_research.html`
7. `company_research/static/company_research.css`
8. `company_research/static/company_research.js`
9. `tests/test_company_research_workspace_repository.py`
10. `tests/test_company_research_workspace_query.py`
11. `tests/test_company_research_api.py`
12. `backend/main.py` only for registration.

No other file is authorized.

## Boundaries
Use D0/D1/D2/D3 separation. “估值观察” may show optional L1 local price provenance but is not Canonical Price, Comparison Eligibility, fair value, target price, expected return, upside/downside, ranking, score, buy/sell/hold, good price or good timing.

No schema, migration, Provider, dependency, release/version, generic framework, monitoring, alerts, portfolio, trading, automatic discovery, identity inference or automatic relinking.

## Verification
- SQL counts and row-growth invariance.
- Exact identity, cutoff, UTC, provenance and historical mismatch.
- Explicit empty modules.
- Deterministic sorting.
- Safe DOM with `textContent` and `replaceChildren`.
- 422/404/503 boundaries and redacted internal failures.
- Full pytest and local PostgreSQL fixture demo.

## Completion gate
Keep the implementation PR Draft/Open/unmerged until independent fixed-head implementation approval and explicit owner authorization.