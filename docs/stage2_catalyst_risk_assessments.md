# Stage 2 Catalyst And Risk Assessments

v0.6C adds local, append-only catalyst and company-risk research judgments. These records preserve what was knowable at a dated boundary; they are not monitoring tasks, alerts, scores, recommendations, timing outputs, or trades.

## Frozen Boundary

Each revision freezes:

- one exact v0.6A company-research revision;
- its selected accepted financial-transmission hypothesis revisions;
- at least one exact v0.6B expectation or valuation revision from the same company research;
- exact claim revisions and only the claim/evidence links already frozen by those v0.6B revisions.

The assessment timestamp cannot precede any frozen upstream record or its prior assessment revision. Historical reads apply both `information_cutoff_date` and UTC recorded-date visibility, so later research, evidence, links, expectations, valuations, or prices cannot rewrite an earlier view.

## Evidence Rules

- `supported` requires a supported claim with visible A/B/C support and no visible contradiction.
- D-grade evidence cannot independently support an assessment.
- `disputed` requires a disputed claim or visible contradiction.
- Missing evidence remains explicit as `尚未获得可靠公开证据`.
- Catalyst observation criteria, risk downside paths, invalidation conditions, mitigants, basis, and uncertainty are bounded text, not numeric scores or forecasts.

## Read-Only API

- `GET /industry-alpha/catalyst-assessments`
- `GET /industry-alpha/catalyst-assessments/{catalyst_id}`
- `GET /industry-alpha/risk-assessments`
- `GET /industry-alpha/risk-assessments/{risk_id}`

All routes accept optional `as_of_cutoff=YYYY-MM-DD`. List routes also accept optional `company_research_id`. No HTTP mutation routes or browser editing UI are provided.

## Offline Demo

```bash
python -m scripts.demo_stage2_catalyst_risk_assessments
```

The demo uses an isolated in-memory SQLite database, deterministic fixtures, strict JSON, and no network access.

## Unsupported

v0.6C does not provide good-price/good-timing or final conclusions, target prices, expected returns, scores, ranks, monitoring, reminders, task lifecycle, watchlists, crowding/timing models, automated data collection, LLM execution, portfolios, brokers, orders, or trading.
