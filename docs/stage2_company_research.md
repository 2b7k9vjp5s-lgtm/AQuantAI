# Stage 2 Company Research Foundation

v0.6A adds a local, read-only and append-only company-research boundary. It starts only from one exact membership in one frozen v0.5C candidate-pool revision. It does not discover companies or widen a Stage 1 pool.

## Frozen Handoff

Each company-research identity permanently records the exact research case, industry map, candidate-pool identity/revision, membership, beneficiary identity/revision, selected map revision, successful `stock_basic` row, source and stock code. The accepted handoff also snapshots the exact Stage 1 assertion links, claim revisions and claim-evidence links visible when Stage 2 begins. Later Stage 1 links or revisions, evidence links or company snapshots cannot rewrite that boundary.

## Research Files And Hypotheses

Research-file revisions are immutable and keep workflow state separate from conclusion status. Financial-transmission hypothesis identities bind one exact Stage 1 assertion link. Their revisions record mechanism, direction, operating metric, financial-statement line, expected lag/horizon, confidence, explicit basis, cutoff and UTC timestamp.

Each hypothesis revision freezes exact claim revisions and the exact evidence links visible at its own cutoff and recording timestamp. `supported` requires A/B/C support and no contradiction. D-only support cannot produce a supported hypothesis. `disputed` requires a disputed claim or visible contradiction. Missing evidence and conflicts remain explicit in reads.

A completed research-file revision freezes exact hypothesis revisions and must include at least one accepted hypothesis, no hidden missing-evidence state, and a non-empty `后续验证清单`. Corrections append a superseding revision; ordinary ORM updates and deletes fail.

## Historical Reads

Current and `as_of_cutoff=YYYY-MM-DD` reads apply both the information cutoff and the UTC recording date. A later research revision, hypothesis, evidence boundary or checklist item is not visible in an earlier view. Responses are deterministically ordered and strict JSON.

Read-only routes:

```text
GET /industry-alpha/company-research?candidate_pool_revision_id=<uuid>
GET /industry-alpha/company-research?map_id=<uuid>&as_of_cutoff=YYYY-MM-DD
GET /industry-alpha/company-research/{company_research_id}
GET /industry-alpha/company-research/{company_research_id}?as_of_cutoff=YYYY-MM-DD
```

There are no HTTP mutation routes or browser editor. Outputs are local research hypotheses, not valuations, scores, weights, rankings, target prices, recommendations or investment advice.

## Offline Demo

```bash
python -m scripts.demo_stage2_company_research
```

The demo uses an isolated in-memory database, performs no provider, network, scraper or LLM call, and does not write configured PostgreSQL data.

## Exclusions

v0.6A adds no valuation model, company score, weight, rank, target price, recommendation, Quant Core automatic scoring, LLM execution, scraping, watchlist, portfolio, broker, order or trading behavior. v0.6B remains unauthorized.
