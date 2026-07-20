# Issue #138 — Evidence Intelligence Research Change Feed

## Authority

- GitHub Issue: #138
- Approved architecture: Issue #134 / PR #136
- Related roadmap: #137
- Base commit: `c1cf6312230b52119ddd4055471f4c6e3bd50948`
- Branch: `agent/issue-138-evidence-intelligence-feed`
- Work type: application implementation / conditional Product Task
- Release remains `0.2.0`; merged domain capability remains v0.6D

## Objective

Implement one local, read-only Research Change Feed that projects accepted scalar fields from `EvidenceItem`, `ResearchCaseRevision`, `IndustryMapRevision`, and `Stage2CompanyResearchRevision`, with bounded time filters, cutoff visibility, deterministic cursor pagination, neutral Chinese-first presentation, and no new domain meaning.

## Allowed files

1. `.codex/tasks/issue-138-evidence-intelligence-feed.md`
2. `industry_alpha/evidence_intelligence_contracts.py`
3. `industry_alpha/evidence_intelligence_repository.py`
4. `industry_alpha/evidence_intelligence_query.py`
5. `backend/api/evidence_intelligence.py`
6. `backend/main.py`
7. `evidence_intelligence/static/evidence_intelligence.html`
8. `evidence_intelligence/static/evidence_intelligence.css`
9. `evidence_intelligence/static/evidence_intelligence.js`
10. `tests/test_evidence_intelligence_repository.py`
11. `tests/test_evidence_intelligence_query.py`
12. `tests/test_evidence_intelligence_api.py`

No other file may change unless a concrete CI failure proves that one minimal packaging adjustment is required. Such a change must be reported before implementation continues.

## Fixed implementation decisions

- API: `GET /evidence-intelligence/feed`.
- Page: `GET /evidence-intelligence`.
- No existing full-graph list/detail service may be composed to build the Feed.
- Use one stateless scalar repository over exactly four accepted source tables.
- Apply recorded window and cutoff filters inside each source query.
- Default window is 7 days; maximum window is 30 days.
- Default limit is 50; maximum limit is 100.
- Stable order is `recorded_at_utc DESC`, fixed event-type order ASC, `event_id DESC`.
- Cursor contains only version, recorded time, event type, and event ID.
- Superseded rows remain visible when in bounds.
- Missing optional values remain null/unavailable; required corrupt values fail closed.
- Detail links use only verified existing Industry Alpha routes.
- The page is Chinese-first, responsive, keyboard usable, and explicitly non-advisory.

## Locked exclusions

- no schema or migration;
- no Provider or external network path;
- no evidence ingestion;
- no beneficiary/company mapping;
- no score, ranking, recommendation, target price, expected return, or signal;
- no AI summary or importance classification;
- no valuation, catalyst, risk, or judgment Feed events;
- no canonical price or comparison eligibility;
- no release, tag, or version change.

## Stop conditions

Stop and return to Architecture Preflight if implementation requires inferred fields, a new persistent relationship, changed cutoff/revision/provenance semantics, materialized Feed state, a new classification contract, or strict price/valuation comparison.

## Validation commands

```bash
python -m pytest tests/test_evidence_intelligence_repository.py tests/test_evidence_intelligence_query.py tests/test_evidence_intelligence_api.py
python -m pytest
python -m scripts.demo_research_flow
```

Record exact CI results and limitations in the Draft PR and Issue. Keep the PR Draft and unmerged for independent review.
