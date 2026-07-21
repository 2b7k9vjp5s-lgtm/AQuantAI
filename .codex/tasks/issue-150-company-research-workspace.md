# Issue #150 — Company Research Workspace v1

## Authority

- Product Task Issue: #150.
- Approved Architecture Preflight: Issue #148 / PR #149.
- Required base: `b2554e24de3166475c016f8d09826989e8535e51`.
- Implementation branch: `feat/company-research-workspace-v1`.
- Release remains `0.2.0`.

## Objective

Implement a Chinese-first, read-only workspace for one explicitly selected persisted `company_research_id`. The workspace reads the exact frozen Stage 1 provenance and cutoff-visible v0.6A-v0.6D research record without ranking, scoring, price-attractiveness or recommendation semantics.

## Identity and routes

- Primary identity: persisted `company_research_id` only.
- No silent first-row selection.
- No identity inference from stock code, company name, Provider industry, free text, title similarity or LLM output.
- Page: `GET /company-research`.
- Selector: `GET /company-research/research?as_of_cutoff=YYYY-MM-DD`.
- Workspace: `GET /company-research/research/{company_research_id}/workspace?as_of_cutoff=YYYY-MM-DD`.

## Query contract

- New stateless domain-specific repository/query boundary.
- Selector: 3 SQL statements; accepted maximum is 3.
- Selected workspace: 14 SQL statements; accepted maximum is 24.
- Query counts are independent of identity, revision, claim and evidence row counts.
- No composition of existing Stage 2 list services.
- No per-row owning-domain detail calls.
- Full claim/evidence graphs remain explicit on-demand reads through existing owning-domain APIs.

## Cutoff and integrity

- Identity creation is visible by recorded UTC.
- Revisions require information-cutoff and recorded-UTC visibility.
- Latest means the deterministic latest visible persisted revision.
- Required frozen Stage 1, stock and ingestion provenance is fail-closed.
- Downstream frozen company-research revisions must be cutoff-visible.
- Hypothesis revisions must be frozen by a visible company-research revision.
- Historical revision mismatch remains visible and is never automatically repaired.
- Exact claim/evidence and Stage 1 handoff boundaries are validated.
- Optional modules return valid empty states without fallback or generation.

## Presentation

Separate:

- D0 persisted identity/provenance;
- D1 deterministic counts;
- D2 Stage 1/evidence classifications;
- D3 research judgments.

Use “估值观察”, never “估值结论”. Optional local daily-price rows are L1 source context only, not Canonical Price or Comparison Eligibility.

## Error contract

- malformed UUID/date: 422;
- missing/cutoff-invisible identity: 404;
- database/configuration/integrity failure: credential-safe 503;
- no raw DB URL, credentials or exception text;
- no external network during import, startup, tests or ordinary reads.

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
12. `backend/main.py` only for router/static/page registration.

No other file is authorized.

## Locked exclusions

No schema, migration, Provider, dependency, release/version, generic workspace framework, Canonical Price, Comparison Eligibility, computed expectation gap, fair value, target price, expected return, upside/downside, cross-company comparison/ranking, research-priority ranking, attractiveness score, buy/sell/hold, good-price/good-timing, Watchlist, monitoring, alerts, reminders, portfolio, paper trading, execution state, automatic company discovery, identity inference or automatic relinking.

## Verification

- selector count remains exactly 3 under row growth;
- workspace count remains exactly 14 under row growth;
- exact identity and provenance checks;
- cutoff/UTC and frozen mismatch checks;
- optional empty modules;
- deterministic sorting;
- safe DOM (`textContent`, `replaceChildren`, no untrusted `innerHTML`);
- 422/404/503 and credential-safe errors;
- strict JSON serialization;
- full pytest and local PostgreSQL fixture demo.

## Completion gate

Keep the implementation PR Draft/Open/unmerged. Independent fixed-head implementation approval and explicit owner authorization are required before merge or Issue closure.
