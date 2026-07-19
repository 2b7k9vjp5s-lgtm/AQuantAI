# Stage 1 Beneficiary Classifications

## Boundary

v0.5C records local, evidence-backed company-beneficiary classifications and an unranked candidate-pool handoff. It does not calculate scores, weights, beneficiary purity, financial transmission, valuation, recommendations, signals, or trades.

Every record is append-only and belongs to one v0.5A research case and one v0.5B industry map. Corrections append a revision; accepted identities, revisions, links, and memberships are never overwritten.

## Exact Identities

A beneficiary identity is unique by research case, industry map, `source`, and `stock_code`. Each immutable beneficiary revision freezes:

- one reviewed kind: `direct`, `secondary`, or `potential`;
- one assessment status: `draft`, `supported`, `disputed`, or `rejected`;
- a bounded rationale summary;
- one exact successful `stock_basic` row and its ingestion provenance;
- one exact selected v0.5B map revision;
- at least one exact assertion revision contained in that map revision;
- at least one exact v0.5A claim revision;
- information cutoff and actual UTC recording timestamp.

The exact company row supplies the displayed name, exchange, industry, listing date, status, source, series key, ingestion run, and snapshot cutoff. A later company snapshot cannot rewrite an accepted classification.

## Evidence Rules

- `supported` requires at least one visible supported claim with A/B/C supporting evidence and no visible contradiction at the beneficiary revision timestamp.
- D-only evidence cannot independently support a classification.
- `disputed` requires a disputed claim or visible contradictory evidence.
- Draft, rejected, conflicting, and missing-evidence states remain explicit in reads.
- Claims and map assertions must share the beneficiary research case and map boundary.
- Customer, order, capacity, revenue exposure, market share, certification, and financial-transmission facts are never inferred from company names, sectors, or D-grade leads.

Visibility uses both information date and actual UTC recorded date. Querying an earlier cutoff excludes later identities, revisions, links, evidence, and memberships. Later evidence links cannot be backdated into an already frozen beneficiary revision.

## Candidate Pool

A candidate-pool identity belongs to the same research case and industry map. Each pool revision selects one exact map revision and freezes exact supported beneficiary revisions. All members must share that map-revision boundary, and a pool revision may contain at most one revision of a beneficiary identity.

Candidate ordering is deterministic by beneficiary kind, source, stock code, and stable identifier. This order is not a rank. Candidate pools contain no score, weight, target price, recommendation, or investment-priority meaning; they are only a handoff for separately authorized Stage 2 research.

## Read-Only API

```text
GET /industry-alpha/maps/{map_id}/beneficiaries
GET /industry-alpha/beneficiaries/{beneficiary_id}
GET /industry-alpha/maps/{map_id}/candidate-pools
GET /industry-alpha/candidate-pools/{candidate_pool_id}
```

All routes accept optional `as_of_cutoff=YYYY-MM-DD`. There are no HTTP mutation routes or browser editing UI.

## Offline Demo

```bash
python -m scripts.demo_stage1_beneficiaries
```

The isolated SQLite demo creates exact local company rows, supported direct and secondary classifications, a D-only draft, a disputed classification, an unranked two-member pool, and a later revision excluded from the earlier cutoff. It performs no network, provider, scraper, or LLM call.
